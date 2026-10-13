/*
I-V curve analyzer for low-power sources
Sixteen switched load paths; R1 is the high-impedance approximate Voc point.
Display on a 2.13-inch 250 x 122 e-ink FeatherWing.

Features:
* E-ink I-V curve display on button press
* Maximum Power Point (MPP) tracking
* Maximum current and voltage measurements
* Interactive display with button control
* Serial data output mode

Hardware Setup:
* ESP32-S3 Mini board
* Adafruit product 4778 2.9-inch tri-color e-ink display by default
* ADG706 16-channel multiplexer for resistor array
* One button starts one complete scan
*/

#include <SPI.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include "Adafruit_ThinkInk.h"
#include "hackteria_logo.h"
#include "board_config.h"
#include <Adafruit_ADS1X15.h>
#include <Adafruit_NeoPixel.h>

// ponytail: one button press = one complete 16-load scan = one e-ink update.

class ThinkInk_213_Tricolor_FPC7528B : public ThinkInk_213_Tricolor_MFGNR {
 public:
  using ThinkInk_213_Tricolor_MFGNR::ThinkInk_213_Tricolor_MFGNR;

  void begin(thinkinkmode_t mode = THINKINK_TRICOLOR) {
    ThinkInk_213_Tricolor_MFGNR::begin(mode);
    _xram_offset = 1;  // This FeatherWing maps its visible rows one RAM byte in.
  }
};

// The mating header is shared, but the panel driver is revision-specific.
#if defined(EINK_ADAFRUIT_4195_GDEY0213B74)
ThinkInk_213_Mono_GDEY0213B74 eink(EPD_DC, EPD_RESET, EPD_CS, SRAM_CS,
                                   EPD_BUSY, &SPI);
#elif defined(EINK_ADAFRUIT_4195_LEGACY_BN)
ThinkInk_213_Mono_BN eink(EPD_DC, EPD_RESET, EPD_CS, SRAM_CS, EPD_BUSY, &SPI);
#elif defined(EINK_ADAFRUIT_4814_TRICOLOR_MFGNR)
ThinkInk_213_Tricolor_FPC7528B eink(EPD_DC, EPD_RESET, EPD_CS, SRAM_CS,
                                    EPD_BUSY, &SPI);
#elif defined(EINK_ADAFRUIT_4778_TRICOLOR_Z94)
ThinkInk_290_Tricolor_Z94 eink(EPD_DC, EPD_RESET, EPD_CS, SRAM_CS, EPD_BUSY,
                               &SPI);
#elif defined(EINK_ADAFRUIT_4778_TRICOLOR_Z10)
ThinkInk_290_Tricolor_Z10 eink(EPD_DC, EPD_RESET, EPD_CS, SRAM_CS, EPD_BUSY,
                               &SPI);
#endif
Adafruit_ADS1115 ads;  // Create an ADS1115 instance
#ifdef hasADS1115
bool adsReady = false;
#endif


// Define LED states
#define LED_IDLE      0  // Blue
#define LED_MEASURING 1  // Yellow
#define LED_SENDING   2  // Purple
#define LED_SUCCESS   3  // Green
#define LED_ERROR     4  // Red

// Initialize NeoPixel
Adafruit_NeoPixel pixel(1, PIN_RGBLED, NEO_RGB + NEO_KHZ800);

// Function declarations
void initEink();
void drawOnEink();
void drawHackteriaLogoFit(int16_t x, int16_t y, int16_t maxWidth,
                          int16_t maxHeight, uint16_t color);
void runFullMeasurement();
void performMeasurementCycle(const char* source, bool updateEink);
bool pollSerialScanCommand();
float readMux(int channel);
void parkMuxAtR1();
void printMeasurements();
void drawDashedLine(int x0, int y0, int x1, int y1, uint16_t color, int dashLength, int gapLength);
void setupLED();
void setLEDState(uint8_t state);

// Pin assignments from board configuration
int s0 = PIN_MUX_S0;      // MUX control pin S0
int s1 = PIN_MUX_S1;      // MUX control pin S1
int s2 = PIN_MUX_S2;      // MUX control pin S2
int s3 = PIN_MUX_S3;      // MUX control pin S3
int SIG_pin = PIN_SIG;    // ADC input for voltage measurement

// Measurement and display variables
const int NUM_POINTS = 16;
const int average = 5;           // Number of readings to average
const int delayLoop = 10;        // Main loop delay
const int delayAveraging = 4;    // Delay between ADC readings for averaging
const int delayMuxSwitch = 100;  // Delay after switching a load
const int delayHighImpedanceRecovery = 2000;  // Let the DSSC recover on the 1 MOhm path.
const int delayAfterButtonRelease = 300;  // Keep the pressing hand out of the first sample.
const unsigned long debounceMs = 80;
const unsigned long minSerialScanIntervalMs = 60000;
const float muxCurrentGuardMa = 25.0f;  // Below the ADG706 30 mA absolute max.
const float r16EntryGuardMa = 20.0f;  // Extra headroom for the final 30 -> 18 ohm step.
const float r16GuardSampleMargin = 1.05f;
const float r16GuardOffsetMv = 2.0f;

// Interface Control Variables
bool lastButtonState = false; // Previous button state
unsigned long lastButtonEdgeTime = 0;
unsigned long lastScanStartTime = 0;
unsigned long scanSequence = 0;
char serialCommand[16];
size_t serialCommandLength = 0;
bool serialCommandOverflow = false;

// Global Measurement Variables
float vocValues[20];   // Array to store voltage measurements
float icalValues[20];  // Array to store calculated currents
float powValues[20];   // Array to store power values
float prevVocValues[20];   // Array to store previous voltage measurements
float prevIcalValues[20];  // Array to store previous current measurements
float prevPowValues[20];   // Array to store previous power values
bool pointValid[20];       // False when a load is skipped by the current guard.
bool prevPointValid[20];
float lastMuxMaxSampleMv = 0.0f;
float maxPower = 0;    // Maximum power point tracking
float maxCurrent = 0;  // Maximum current tracking
float maxVoltage = 0;  // Maximum voltage tracking
float prevMaxPower = 0;    // Previous maximum power
float prevMaxCurrent = 0;  // Previous maximum current
float prevMaxVoltage = 0;  // Previous maximum voltage
bool hasPreviousMeasurement = false;  // Flag to track if we have a previous measurement
int mppIndex = 0;      // Index of maximum power point
int prevMppIndex = 0;  // Previous maximum power point index

// Conservative load-only values for the pre-switch current guard. Using the
// load resistance without MUX/source resistance deliberately overestimates
// current. The 0.95 factor covers the draft assumption of 5% resistors.
const float nominalLoadOhms[NUM_POINTS]{
  1000000,
  20000,
  8200,
  4300,
  2200,
  1000,
  750,
  470,
  330,
  220,
  150,
  100,
  82,
  51,
  30,
  18
};

// Emergency software estimate until every assembled path can be measured.
// Three exhibition sweeps fit the low-voltage tail at about 1.5-1.9 ohms.
const float estimatedMuxRonOhms = 2.0f;

void setup() {
  Serial.begin(115200);
  delay(100);
  Serial.println("=========== Initializing I-V Scanner ===========");
  Serial.println("");

  // The daughterboard pulldown keeps EN low during reset. Drive it low before
  // configuring or changing any address input.
  pinMode(PIN_MUX_EN, OUTPUT);
  digitalWrite(PIN_MUX_EN, LOW);

  pinMode(s0, OUTPUT);
  pinMode(s1, OUTPUT);
  pinMode(s2, OUTPUT);
  pinMode(s3, OUTPUT);
  pinMode(PIN_BUTTON, INPUT_PULLUP);

  digitalWrite(s0, LOW);
  digitalWrite(s1, LOW);
  digitalWrite(s2, LOW);
  digitalWrite(s3, LOW);

  memset(vocValues, 0, sizeof(vocValues));
  memset(icalValues, 0, sizeof(icalValues));
  memset(powValues, 0, sizeof(powValues));
  memset(prevVocValues, 0, sizeof(prevVocValues));
  memset(prevIcalValues, 0, sizeof(prevIcalValues));
  memset(prevPowValues, 0, sizeof(prevPowValues));
  memset(pointValid, 0, sizeof(pointValid));
  memset(prevPointValid, 0, sizeof(prevPointValid));

  setupLED();
  setLEDState(LED_IDLE);

  Wire.begin(SDA_PIN, SCL_PIN);
  SPI.begin(SCLK, MISO, MOSI);

  #ifdef hasADS1115
  adsReady = ads.begin(0x48);
  if (!adsReady) {
    Serial.println("ERROR: ADS1115 not found at 0x48");
    setLEDState(LED_ERROR);
  } else {
    ads.setGain(GAIN_ONE);  // +/-4.096 V scale; inputs still must stay in rails.
    ads.setDataRate(RATE_ADS1115_128SPS);
  }
  #endif

  #ifdef hasEink
  initEink();
  #endif

  Serial.println("");
  Serial.println("=========== Ready: press button for one full 16-point scan ===========");
  Serial.println("Serial command: SCAN");
  Serial.println("");
}

void loop() {
  bool buttonDown = digitalRead(PIN_BUTTON) == LOW;
  bool serialScan = pollSerialScanCommand();

  if (buttonDown && !lastButtonState && millis() - lastButtonEdgeTime > debounceMs) {
    lastButtonEdgeTime = millis();

    // A hand pressing the nearby button can shade the DSSC. Measure only after
    // release, then give the light path a short moment to clear.
    while (digitalRead(PIN_BUTTON) == LOW) delay(10);
    delay(delayAfterButtonRelease);
    buttonDown = false;

    Serial.println("=========== Button pressed: full scan from R1 started ===========");
    lastScanStartTime = millis();
    performMeasurementCycle("button", true);
  } else if (serialScan) {
    unsigned long now = millis();
    if (lastScanStartTime != 0 &&
        now - lastScanStartTime < minSerialScanIntervalMs) {
      Serial.println("SCAN_REJECT source=serial reason=rate_limit");
    } else {
      lastScanStartTime = now;
      Serial.println("=========== Serial command: full scan from R1 started ===========");
      performMeasurementCycle("serial", false);
    }
  }

  lastButtonState = buttonDown;
  delay(delayLoop);
}

bool pollSerialScanCommand() {
  bool requested = false;
  while (Serial.available() > 0) {
    int value = Serial.read();
    if (value < 0) break;
    char incoming = static_cast<char>(value);
    if (incoming == '\r') continue;
    if (incoming == '\n') {
      if (!serialCommandOverflow && serialCommandLength > 0) {
        serialCommand[serialCommandLength] = '\0';
        if (strcmp(serialCommand, "SCAN") == 0) {
          requested = true;
        } else {
          Serial.print("COMMAND_REJECT value=");
          Serial.println(serialCommand);
        }
      } else if (serialCommandOverflow) {
        Serial.println("COMMAND_REJECT reason=too_long");
      }
      serialCommandLength = 0;
      serialCommandOverflow = false;
      continue;
    }
    if (serialCommandOverflow) continue;
    if (serialCommandLength + 1 < sizeof(serialCommand)) {
      serialCommand[serialCommandLength++] = incoming;
    } else {
      serialCommandOverflow = true;
    }
  }
  return requested;
}

void performMeasurementCycle(const char* source, bool updateEink) {
  #ifdef hasADS1115
  if (!adsReady) {
    digitalWrite(PIN_MUX_EN, LOW);
    Serial.printf("SCAN_REJECT source=%s reason=ADS1115_unavailable\n", source);
    setLEDState(LED_ERROR);
    delay(150);
    setLEDState(LED_IDLE);
    return;
  }
  #endif

  unsigned long scanId = ++scanSequence;
  setLEDState(LED_MEASURING);
  Serial.printf("SCAN_BEGIN id=%lu source=%s\n", scanId, source);

  runFullMeasurement();
  printMeasurements();

  int validCount = 0;
  for (int i = 0; i < NUM_POINTS; ++i) {
    if (pointValid[i]) ++validCount;
  }
  Serial.printf("SCAN_DATA_END id=%lu valid=%d skipped=%d\n",
                scanId, validCount, NUM_POINTS - validCount);
  Serial.flush();

  #ifdef hasEink
  if (updateEink) drawOnEink();
  #endif

  memcpy(prevVocValues, vocValues, sizeof(vocValues));
  memcpy(prevIcalValues, icalValues, sizeof(icalValues));
  memcpy(prevPowValues, powValues, sizeof(powValues));
  memcpy(prevPointValid, pointValid, sizeof(pointValid));
  prevMaxPower = maxPower;
  prevMaxCurrent = maxCurrent;
  prevMaxVoltage = maxVoltage;
  prevMppIndex = mppIndex;
  hasPreviousMeasurement = true;

  setLEDState(LED_SUCCESS);
  delay(150);
  setLEDState(LED_IDLE);
  Serial.printf("SCAN_CYCLE_END id=%lu\n", scanId);
}

void runFullMeasurement() {
  memset(vocValues, 0, sizeof(vocValues));
  memset(icalValues, 0, sizeof(icalValues));
  memset(powValues, 0, sizeof(powValues));
  memset(pointValid, 0, sizeof(pointValid));

  maxPower = 0;
  maxCurrent = 0;
  maxVoltage = 0;
  mppIndex = 0;

  for (int i = 0; i < NUM_POINTS; i++) {
    float resistance =
        max(1.0f, nominalLoadOhms[i] + estimatedMuxRonOhms);

    // Use zero guaranteed MUX resistance in the safety bound. R16 is special:
    // R15 remains connected after sampling, so its maximum observed terminal
    // voltage bounds a direct 30 -> 18 ohm transition for a stable PV source.
    if (i > 0) {
      if (i == NUM_POINTS - 1 && !pointValid[i - 1]) {
        Serial.printf("R%02d SKIPPED: previous lower-current guard failed\n", i + 1);
        parkMuxAtR1();
        continue;
      }
      float minimumPathOhms =
          max(1.0f, nominalLoadOhms[i] * 0.95f);
      float guardVoltageMv = vocValues[0];
      float guardLimitMa = muxCurrentGuardMa;
      if (i == NUM_POINTS - 1) {
        guardVoltageMv = lastMuxMaxSampleMv * r16GuardSampleMargin + r16GuardOffsetMv;
        guardLimitMa = r16EntryGuardMa;
      }
      float predictedCurrentMa = guardVoltageMv / minimumPathOhms;
      if (predictedCurrentMa > guardLimitMa) {
        Serial.printf("R%02d SKIPPED: predicted %.2f mA exceeds %.2f mA guard\n",
                      i + 1, predictedCurrentMa, guardLimitMa);
        parkMuxAtR1();
        continue;
      }
    }

    vocValues[i] = readMux(i);  // Get voltage directly from return value
    float observedCurrentUpperMa =
        lastMuxMaxSampleMv / max(1.0f, nominalLoadOhms[i] * 0.95f);
    if (observedCurrentUpperMa > muxCurrentGuardMa) {
      Serial.printf("R%02d SKIPPED: observed %.2f mA exceeds %.2f mA hard guard\n",
                    i + 1, observedCurrentUpperMa, muxCurrentGuardMa);
      parkMuxAtR1();
      continue;
    }
    pointValid[i] = true;
    icalValues[i] = vocValues[i] / resistance;  // mV / ohm = mA
    powValues[i] = vocValues[i] * icalValues[i];  // mV * mA = uW

    if (powValues[i] > maxPower) {
      maxPower = powValues[i];
      mppIndex = i;
    }

    if (icalValues[i] > maxCurrent) {
      maxCurrent = icalValues[i];
    }
    if (vocValues[i] > maxVoltage) {
      maxVoltage = vocValues[i];
    }

    Serial.printf("R%02d V=%.1f mV I=%.4f mA P=%.2f uW\n", i + 1, vocValues[i], icalValues[i], powValues[i]);
  }
}
float readMux(int channel) {
  float sig = 0;
  lastMuxMaxSampleMv = 0.0f;
  int16_t adc0;
  
  // The exhibition carrier does not reliably honor MUX_EN=LOW. Always set the
  // address explicitly, including R1, so a new scan cannot begin on R16/18 ohm.
  digitalWrite(PIN_MUX_EN, LOW);
  digitalWrite(s0, bitRead(channel, 0));
  digitalWrite(s1, bitRead(channel, 1));
  digitalWrite(s2, bitRead(channel, 2));
  digitalWrite(s3, bitRead(channel, 3));
  digitalWrite(PIN_MUX_EN, HIGH);
  delay(channel == 0 ? delayHighImpedanceRecovery : delayMuxSwitch);

  #ifdef hasADS1115
  ads.readADC_SingleEnded(0);  // Discard stale conversions after the transition.
  ads.readADC_SingleEnded(0);
  #endif
  
  // Take multiple readings and average
  for(int i = 0; i < average; i++) {
    float sampleMv = 0.0f;
    #ifdef hasADS1115
    adc0 = ads.readADC_SingleEnded(0);
    sampleMv += ads.computeVolts(adc0) * 1000.0f;
    #endif
    #ifdef hasESPADC
    sampleMv += analogReadMilliVolts(SIG_pin);  // Multiply by 2 to account for voltage divider
    #endif
    sig += sampleMv;
    lastMuxMaxSampleMv = max(lastMuxMaxSampleMv, sampleMv);
    
    delay(delayAveraging);
  }
  
  // Keep R15 engaged only long enough to gate and directly enter R16. Every
  // other completed point parks at R1; R16 therefore parks immediately.
  if (channel != NUM_POINTS - 2) parkMuxAtR1();
  return sig / average;
}

void parkMuxAtR1() {
  digitalWrite(PIN_MUX_EN, LOW);
  digitalWrite(s0, LOW);
  digitalWrite(s1, LOW);
  digitalWrite(s2, LOW);
  digitalWrite(s3, LOW);
}

void printMeasurements() {
  Serial.println("    ");
  Serial.println("=========== I calculated ===========");
  for(int i = 0; i < NUM_POINTS; i ++){
    if (pointValid[i]) Serial.println(icalValues[i], 6);
    else Serial.println("SKIPPED");
  }

  Serial.println("=========== Power calculated ===========");
  for(int i = 0; i < NUM_POINTS; i ++){
    if (pointValid[i]) Serial.println(powValues[i], 6);
    else Serial.println("SKIPPED");
  }
  Serial.println("    ");
  Serial.println("=========== V meas===========");
  for(int i = 0; i < NUM_POINTS; i ++){
    if (pointValid[i]) Serial.println(vocValues[i]);
    else Serial.println("SKIPPED");
  }  

  Serial.println("=========== MPP ===========");
  Serial.print("MPP Index: ");
  Serial.println(mppIndex);
  Serial.print("Voltage at MPP: ");
  Serial.print(vocValues[mppIndex]);
  Serial.println(" mV");
  Serial.print("Current at MPP: ");
  Serial.print(icalValues[mppIndex]);
  Serial.println(" mA");
  Serial.print("Power at MPP: ");
  Serial.print(powValues[mppIndex]);
  Serial.println(" uW");
  Serial.println("=========== DONE ===========");
  delay(10);
}


void initEink() {
  // Initialize E-ink with proper delays
  Serial.println("Initializing e-ink display");
  delay(100);
  #if defined(EINK_ADAFRUIT_4814_TRICOLOR_MFGNR) || \
      defined(EINK_ADAFRUIT_4778_TRICOLOR_Z94) || \
      defined(EINK_ADAFRUIT_4778_TRICOLOR_Z10)
  eink.begin(THINKINK_TRICOLOR);
  #else
  eink.begin(THINKINK_MONO);
  #endif
  eink.setRotation(0);
  delay(100);

  // Clear twice using the selected panel geometry. This removes pixels left by
  // firmware that previously addressed the FeatherWing as the wrong size.
  eink.clearDisplay();

  // This refresh is independent of the ADC so display wiring and both ink
  // planes can be checked even when the ADS1115 is absent.
  eink.clearBuffer();
  int sectionWidth = eink.width() / 3;
  eink.fillRect(0, 0, sectionWidth, eink.height(), EPD_BLACK);
  eink.fillRect(sectionWidth, 0, sectionWidth, eink.height(), EPD_RED);
  eink.fillRect(sectionWidth * 2, 0, eink.width() - sectionWidth * 2,
                eink.height(), EPD_WHITE);
  eink.display();
  eink.clearBuffer();
  Serial.println("E-ink black/red/white startup test completed");
  Serial.println("E-ink display initialized");
}

void drawOnEink() {
  eink.setRotation(0);
  eink.clearBuffer();
  eink.fillScreen(EPD_WHITE);

  const int panelW = eink.width();
  const int panelH = eink.height();
  const int dividerX = panelW * 5 / 8;
  const int plotX = 20;
  const int plotY = 10;
  const int plotW = dividerX - plotX - 5;
  const int plotH = panelH - plotY - 18;
  const int infoX = dividerX + 5;

  #if defined(EINK_ADAFRUIT_4814_TRICOLOR_MFGNR) || \
      defined(EINK_ADAFRUIT_4778_TRICOLOR_Z94) || \
      defined(EINK_ADAFRUIT_4778_TRICOLOR_Z10)
  const uint16_t currentColor = EPD_RED;
  #else
  const uint16_t currentColor = EPD_BLACK;
  #endif

  eink.drawRect(plotX, plotY, plotW + 1, plotH + 1, EPD_BLACK);

  // Four sections use the selected panel while keeping the curves clear.
  for (int section = 1; section < 4; section++) {
    int x = plotX + section * plotW / 4;
    int y = plotY + section * plotH / 4;
    for (int py = plotY + 1; py < plotY + plotH; py += 3) {
      eink.drawPixel(x, py, EPD_BLACK);
    }
    for (int px = plotX + 1; px < plotX + plotW; px += 3) {
      eink.drawPixel(px, y, EPD_BLACK);
    }
  }

  float xMax = max(1.0f, max(maxVoltage,
                             hasPreviousMeasurement ? prevMaxVoltage : 0.0f));
  float yMax = max(0.001f, max(maxCurrent,
                               hasPreviousMeasurement ? prevMaxCurrent : 0.0f));
  float xScale = plotW / (xMax * 1.1f);
  float yScale = plotH / (yMax * 1.1f);

  if (hasPreviousMeasurement) {
    for (int i = 1; i < NUM_POINTS; i++) {
      if (!prevPointValid[i - 1] || !prevPointValid[i]) continue;
      int x0 = constrain(plotX + (int)(prevVocValues[i - 1] * xScale),
                         plotX, plotX + plotW);
      int y0 = constrain(plotY + plotH -
                             (int)(prevIcalValues[i - 1] * yScale),
                         plotY, plotY + plotH);
      int x1 = constrain(plotX + (int)(prevVocValues[i] * xScale),
                         plotX, plotX + plotW);
      int y1 = constrain(plotY + plotH - (int)(prevIcalValues[i] * yScale),
                         plotY, plotY + plotH);
      drawDashedLine(x0, y0, x1, y1, EPD_BLACK, 2, 3);
    }
  }

  for (int i = 0; i < NUM_POINTS; i++) {
    if (!pointValid[i]) continue;
    int x = constrain(plotX + (int)(vocValues[i] * xScale),
                      plotX, plotX + plotW);
    int y = constrain(plotY + plotH - (int)(icalValues[i] * yScale),
                      plotY, plotY + plotH);
    if (i > 0 && pointValid[i - 1]) {
      int x0 = constrain(plotX + (int)(vocValues[i - 1] * xScale),
                         plotX, plotX + plotW);
      int y0 = constrain(plotY + plotH -
                             (int)(icalValues[i - 1] * yScale),
                         plotY, plotY + plotH);
      eink.drawLine(x0, y0, x, y, currentColor);
    }
    eink.fillCircle(x, y, 1, currentColor);
  }

  if (maxPower > 0 && mppIndex >= 0 && mppIndex < NUM_POINTS) {
    int mppX = constrain(plotX + (int)(vocValues[mppIndex] * xScale),
                         plotX, plotX + plotW);
    int mppY = constrain(plotY + plotH -
                             (int)(icalValues[mppIndex] * yScale),
                         plotY, plotY + plotH);
    eink.fillCircle(mppX, mppY, 3, currentColor);
  }

  eink.setTextWrap(false);
  eink.setTextColor(EPD_BLACK);
  eink.setTextSize(1);
  eink.setCursor(3, 2);
  eink.print("I");
  eink.setCursor(plotX + plotW / 2 - 21, panelH - 12);
  eink.print("Voltage");

  char value[20];
  // Keep the frame one pixel inside the glass so no edge is controller-clipped.
  eink.drawRect(1, 1, panelW - 2, panelH - 2, EPD_BLACK);
  eink.drawFastVLine(dividerX, 1, panelH - 2, EPD_BLACK);
  eink.setCursor(infoX, 5);
  eink.print("IV CURVE");

  snprintf(value, sizeof(value), "MPP %.3fuW", maxPower);
  eink.setCursor(infoX, 20);
  eink.print(value);

  snprintf(value, sizeof(value), "Voc~ %.2fV", vocValues[0] / 1000.0f);
  eink.setCursor(infoX, 34);
  eink.print(value);

  snprintf(value, sizeof(value), "Imax %.2fuA", maxCurrent * 1000.0f);
  eink.setCursor(infoX, 48);
  eink.print(value);

  float theoreticalPowerUw = vocValues[0] * maxCurrent;
  float fillFactorPercent =
      theoreticalPowerUw > 0 ? 100.0f * maxPower / theoreticalPowerUw : 0.0f;
  snprintf(value, sizeof(value), "FF %.0f%%", fillFactorPercent);
  eink.setCursor(infoX, 62);
  eink.print(value);

  eink.setCursor(infoX, 76);
  eink.print(hasPreviousMeasurement ? "new / previous" : "R1-R16 scan");

  drawHackteriaLogoFit(dividerX + 2, 87, panelW - dividerX - 4,
                       panelH - 89, EPD_RED);

  eink.display();
  Serial.println("E-ink refresh completed");
}

void drawHackteriaLogoFit(int16_t boxX, int16_t boxY, int16_t maxWidth,
                          int16_t maxHeight, uint16_t color) {
  const int sourceStride = HACKTERIA_LOGO_WIDTH / 8;
  int minX = HACKTERIA_LOGO_WIDTH;
  int minY = HACKTERIA_LOGO_HEIGHT;
  int maxX = -1;
  int maxY = -1;

  for (int y = 0; y < HACKTERIA_LOGO_HEIGHT; y++) {
    for (int x = 0; x < HACKTERIA_LOGO_WIDTH; x++) {
      uint8_t bits = pgm_read_byte(&hackteria_logo[y * sourceStride + x / 8]);
      if (bits & (0x80 >> (x & 7))) {
        minX = min(minX, x);
        minY = min(minY, y);
        maxX = max(maxX, x);
        maxY = max(maxY, y);
      }
    }
  }
  if (maxX < minX || maxY < minY) return;

  int sourceWidth = maxX - minX + 1;
  int sourceHeight = maxY - minY + 1;
  int drawWidth = maxWidth;
  int drawHeight = sourceHeight * drawWidth / sourceWidth;
  if (drawHeight > maxHeight) {
    drawHeight = maxHeight;
    drawWidth = sourceWidth * drawHeight / sourceHeight;
  }
  int x0 = boxX + (maxWidth - drawWidth) / 2;
  int y0 = boxY + (maxHeight - drawHeight) / 2;

  for (int y = 0; y < drawHeight; y++) {
    int sourceY0 = minY + y * sourceHeight / drawHeight;
    int sourceY1 = minY + (y + 1) * sourceHeight / drawHeight;
    sourceY1 = max(sourceY0 + 1, sourceY1);
    for (int x = 0; x < drawWidth; x++) {
      int sourceX0 = minX + x * sourceWidth / drawWidth;
      int sourceX1 = minX + (x + 1) * sourceWidth / drawWidth;
      sourceX1 = max(sourceX0 + 1, sourceX1);
      bool set = false;
      for (int sourceY = sourceY0; sourceY < sourceY1 && !set; sourceY++) {
        for (int sourceX = sourceX0; sourceX < sourceX1; sourceX++) {
          uint8_t bits = pgm_read_byte(
              &hackteria_logo[sourceY * sourceStride + sourceX / 8]);
          if (bits & (0x80 >> (sourceX & 7))) {
            set = true;
            break;
          }
        }
      }
      if (set) eink.drawPixel(x0 + x, y0 + y, color);
    }
  }
}

void drawDashedLine(int x0, int y0, int x1, int y1, uint16_t color, int dashLength, int gapLength) {
  int dx = abs(x1 - x0);
  int dy = abs(y1 - y0);
  int sx = x0 < x1 ? 1 : -1;
  int sy = y0 < y1 ? 1 : -1;
  
  // Total length of the line
  float lineLength = sqrt(dx * dx + dy * dy);
  if (lineLength < 1) {  // If line is too short, just draw a single pixel
    eink.drawPixel(x0, y0, color);
    return;
  }
  
  // Number of segments (dash + gap)
  int totalSegmentLength = dashLength + gapLength;
  int segments = max(1, (int)(lineLength / totalSegmentLength));
  
  // Draw each dash
  for (int i = 0; i < segments; i++) {
    float startPercent = (float)(i * totalSegmentLength) / lineLength;
    float endPercent = min((float)(i * totalSegmentLength + dashLength) / lineLength, 1.0f);
    
    if (startPercent >= 1.0f) break;  // Stop if we've gone past the end
    
    int xStart = x0 + (int)((x1 - x0) * startPercent);
    int yStart = y0 + (int)((y1 - y0) * startPercent);
    int xEnd = x0 + (int)((x1 - x0) * endPercent);
    int yEnd = y0 + (int)((y1 - y0) * endPercent);
    
    // Ensure we don't draw outside the line endpoints
    if (sx > 0) {
      xEnd = min(xEnd, x1);
    } else {
      xEnd = max(xEnd, x1);
    }
    if (sy > 0) {
      yEnd = min(yEnd, y1);
    } else {
      yEnd = max(yEnd, y1);
    }
    
    eink.drawLine(xStart, yStart, xEnd, yEnd, color);
  }
}


void setupLED() {
  pixel.begin();
  pixel.setBrightness(25);  // Set to 50% brightness
  pixel.show();
}

void setLEDState(uint8_t state) {
  switch(state) {
    case LED_SENDING:
      pixel.setPixelColor(0, pixel.Color(0, 0, 255));  // Blue
      break;
    case LED_MEASURING:
      pixel.setPixelColor(0, pixel.Color(148, 128, 0));  // Yellow
      break;
    case LED_IDLE:
      pixel.setPixelColor(0, pixel.Color(128, 0, 128));  // Purple
      break;
    case LED_SUCCESS:
      pixel.setPixelColor(0, pixel.Color(0, 255, 0));  // Green
      break;
    case LED_ERROR:
      pixel.setPixelColor(0, pixel.Color(255, 0, 0));  // Red
      break;
  }
  pixel.show();
}
