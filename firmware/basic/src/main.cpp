#include <Arduino.h>
#include <SPI.h>
#include <Wire.h>
#include <Adafruit_ADS1X15.h>
#include <Adafruit_ThinkInk.h>
#include "board_pins.h"
#include "calibration.h"

class ThinkInk_213_Tricolor_FPC7528B : public ThinkInk_213_Tricolor_MFGNR {
 public:
  using ThinkInk_213_Tricolor_MFGNR::ThinkInk_213_Tricolor_MFGNR;

  void begin(thinkinkmode_t mode = THINKINK_TRICOLOR) {
    ThinkInk_213_Tricolor_MFGNR::begin(mode);
    _xram_offset = 1;  // This FeatherWing maps its visible rows one RAM byte in.
  }
};

Adafruit_ADS1115 ads;
// Official order: DC, RESET, EPD CS, SRAM CS, BUSY, SPI pointer.
ThinkInk_213_Tricolor_FPC7528B display(Pins::DC, Pins::RESET, Pins::CS,
                                   Pins::SRAM, Pins::BUSY, &SPI);
bool adcReady=false, displayStarted=false, suppressUntilRelease=false;
uint32_t lastDisplay=0;
float rawV[16], estimatedMA[16];
int validPoints=0;
String command;
void off() { digitalWrite(Pins::EN, LOW); }
struct LoadOffOnExit { ~LoadOffOnExit() { off(); } };
bool abortRequested() {
  if (digitalRead(Pins::BUTTON)==LOW) return true;
  if (Serial.available() && Serial.peek()=='!') { Serial.read(); return true; }
  return false;
}
bool waitAbortable(uint32_t ms) {
  uint32_t start=millis();
  while (uint32_t(millis()-start)<ms) {
    if (abortRequested()) { off(); return false; }
    delay(1);
  }
  return true;
}
bool readRegisterChecked(uint8_t reg, uint16_t &v) {
  Wire.beginTransmission(0x48); Wire.write(reg);
  if (Wire.endTransmission(false)!=0) return false;
  if (Wire.requestFrom(uint8_t(0x48),uint8_t(2))!=2) return false;
  v=(uint16_t(Wire.read())<<8)|Wire.read(); return true;
}
bool sample(float &v) {
  // ADS1115 AIN0 to GND, +/-4.096 V scale, single shot, 128 SPS.
  // Checked writes/reads: stock convenience APIs hide I2C error results.
  constexpr uint16_t config=ADS1X15_REG_CONFIG_OS_SINGLE |
      ADS1X15_REG_CONFIG_MUX_SINGLE_0 | ADS1X15_REG_CONFIG_PGA_4_096V |
      ADS1X15_REG_CONFIG_MODE_SINGLE | RATE_ADS1115_128SPS |
      ADS1X15_REG_CONFIG_CQUE_NONE;
  Wire.beginTransmission(0x48); Wire.write(ADS1X15_REG_POINTER_CONFIG);
  Wire.write(uint8_t(config>>8)); Wire.write(uint8_t(config));
  if (Wire.endTransmission()!=0) return false;
  const uint32_t started=millis();
  uint16_t status=0;
  do {
    if (abortRequested() || uint32_t(millis()-started)>=100) return false;
    if (!readRegisterChecked(ADS1X15_REG_POINTER_CONFIG,status)) return false;
    if ((status & 0x7FFF)!=(config & 0x7FFF)) return false;
    delay(1);
  } while (!(status & ADS1X15_REG_CONFIG_OS_NOTBUSY));
  uint16_t raw;
  if (!readRegisterChecked(ADS1X15_REG_POINTER_CONVERT,raw)) return false;
  if (int16_t(raw)>=32760 || int16_t(raw)<0) return false;
  v=ads.computeVolts(int16_t(raw));
  return isfinite(v) && v<adcAbortVolts;
}
void render() {
  off(); // Never refresh EPD with the load enabled.
  if (display.ioFailed()) { Serial.println("EPD_FAULT sticky; inspect BUSY/wiring then reboot"); return; }
  if (displayStarted && uint32_t(millis()-lastDisplay)<13000) {
    Serial.println("EPD_SKIPPED refresh interval; serial results remain available"); return;
  }
  if (!displayStarted) {
    display.begin(THINKINK_TRICOLOR);
    display.setRotation(0); // SSD1680 native landscape: 250x122.
    displayStarted=true;
  }
  if (display.ioFailed() || display.width()!=250 || display.height()!=122) {
    Serial.println("EPD_INIT_FAIL"); return;
  }
  display.clearBuffer(); display.setTextColor(EPD_BLACK); display.setTextSize(1);
  display.setCursor(2,2); display.println("I-V: UNCALIBRATED / NOMINAL");
  display.setCursor(2,16); display.print("Valid points: "); display.println(validPoints);
  display.setCursor(2,30); display.println("rawV; I estimate excludes unknown Ron");
  for (int i=0;i<validPoints;i++) {
    int col=i/8, row=i%8;
    display.setCursor(2+col*125,44+row*9);
    display.printf("%02d %.3fV %.2fmA",i+1,rawV[i],estimatedMA[i]);
  }
  display.fillRect(220,16,8,8,EPD_RED);
  display.drawRect(231,16,8,8,EPD_BLACK); // third ink is white, not yellow.
  display.display(true); lastDisplay=millis();
  Serial.println(display.ioFailed()?"EPD_BUSY_TIMEOUT (inner driver aborted)":"EPD_REFRESH_RETURNED; visual result unverified");
}
void scan() {
  off(); LoadOffOnExit cleanup;
  validPoints=0;
  if (!adcReady) { Serial.println("SCAN_REJECT ADC initialization failed; EN=LOW"); return; }
  Serial.println("SCAN UNCALIBRATED: rawV, nominal R-only current estimate; NOT hard current protection. ! or button aborts.");
  for (int ch=0;ch<16;ch++) {
    off();
    if (abortRequested()) { Serial.println("ABORT_REQUEST"); break; }
    for (int bit=0;bit<4;bit++) digitalWrite(Pins::MUX_A[bit],(ch>>bit)&1);
    if (!waitAbortable(2)) break;
    digitalWrite(Pins::EN,HIGH);
    if (!waitAbortable(ch==0?150:25)) break;
    float discard, v=0; bool ok=sample(discard);
    for (int n=0;n<4 && ok;n++) { float x; ok=sample(x); if(ok) v+=x/4; }
    off(); // Disable before calculation, logging or display.
    if (!ok) { Serial.println("ABORT ADC/bus/voltage/timeout/operator; EN=LOW"); break; }
    rawV[ch]=v;
    const float corrected=v*adcGainCorrection+adcOffsetVolts;
    const bool pathKnown=isfinite(measuredPathOhms[ch]) && measuredPathOhms[ch]>0;
    const float r=pathKnown?measuredPathOhms[ch]:nominalLoadOhms[ch];
    estimatedMA[ch]=1000*corrected/r; validPoints++;
    Serial.printf("R%d rawV=%.6f correctedV=%.6f Rnom=%.3f I_est_mA=%.6f voltage=%s path=%s\n",
       ch+1,v,corrected,nominalLoadOhms[ch],estimatedMA[ch],voltageCalibrated?"calibrated":"UNCALIBRATED",pathKnown?"measured_total":"NOMINAL_no_Ron");
    if (estimatedMA[ch]>=nominalAbortMilliAmps) {
      Serial.println("ABORT nominal estimate threshold; NOT a measured current or hardware protection"); break;
    }
  }
  off(); Serial.println("SCAN_END EN=LOW"); render();
  suppressUntilRelease=(digitalRead(Pins::BUTTON)==LOW);
}
void setup() {
  digitalWrite(Pins::EN,LOW); pinMode(Pins::EN,OUTPUT);
  digitalWrite(Pins::CS,HIGH); pinMode(Pins::CS,OUTPUT);
  digitalWrite(Pins::SRAM,HIGH); pinMode(Pins::SRAM,OUTPUT);
  for (int p: Pins::MUX_A) { digitalWrite(p,LOW); pinMode(p,OUTPUT); }
  pinMode(Pins::BUTTON,INPUT_PULLUP); // BUSY=-1: module testpad is not wired.
  Serial.begin(115200); // No wait-for-USB loop.
  Wire.begin(Pins::SDA,Pins::SCL); Wire.setClock(100000); Wire.setTimeOut(25);
  adcReady=ads.begin(0x48,&Wire); ads.setGain(GAIN_ONE); ads.setDataRate(RATE_ADS1115_128SPS);
  SPI.begin(Pins::SCK,Pins::MISO,Pins::MOSI);
  off(); Serial.println("SCAN or press/release. ! during measurement aborts. No WiFi/SD. DUT range and EN effectiveness UNVERIFIED.");
}
void loop() {
  static int previous=HIGH, stable=HIGH; static uint32_t changed=0;
  static bool armed=false;
  int now=digitalRead(Pins::BUTTON);
  if(suppressUntilRelease) {
    previous=stable=now; armed=false; changed=millis();
    if(now==HIGH) suppressUntilRelease=false;
  }
  if(now!=previous) {previous=now; changed=millis();}
  if(now!=stable && uint32_t(millis()-changed)>=30) {
    stable=now;
    if(stable==LOW) armed=true;
    else if(armed) {armed=false; scan();}
  }
  while(Serial.available()) {
    char c=Serial.read();
    if(c=='\n' || c=='\r') { command.trim(); if(command=="SCAN") scan(); command=""; }
    else if(command.length()<32) command+=c;
    else command="";
  }
  delay(1);
}
