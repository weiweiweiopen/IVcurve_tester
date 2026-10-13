#ifndef BOARD_CONFIG_H
#define BOARD_CONFIG_H

// PlatformIO may select a board with a build flag. Preserve C3 as the default
// for the original tester when no environment-specific selection is supplied.
#if !defined(BOARD_ESP32S3_MINI) && !defined(BOARD_ESP32C3_SUPER_MINI)
  #define BOARD_ESP32C3_SUPER_MINI
#endif

// Choose which MUX is used
#define MUX_ADG706
//#define MUX_4051

// Choose which ADC is used
#define hasADS1115
//#define hasESPADC

// Does the system has the E-ink display?
#define hasEink

// Select exactly one physical FeatherWing panel revision.
#if !defined(EINK_ADAFRUIT_4195_GDEY0213B74) && \
    !defined(EINK_ADAFRUIT_4195_LEGACY_BN) && \
    !defined(EINK_ADAFRUIT_4814_TRICOLOR_MFGNR) && \
    !defined(EINK_ADAFRUIT_4778_TRICOLOR_Z94) && \
    !defined(EINK_ADAFRUIT_4778_TRICOLOR_Z10)
  #define EINK_ADAFRUIT_4814_TRICOLOR_MFGNR
#endif
//#define EINK_ADAFRUIT_4195_LEGACY_BN

#ifdef BOARD_ESP32S3_MINI
    #define PIN_MUX_S0      2   // MUX control pin S0
    #define PIN_MUX_S1      6   // MUX control pin S1
    #define PIN_MUX_S2      4   // MUX control pin S2
    #define PIN_MUX_S3      5   // MUX control pin S3
    #define PIN_MUX_EN      14  // ADG706 enable; active high
    #define PIN_SIG         1   // ADC input for voltage measurement
    #define PIN_POT_Y       16  // ADC input for Y-axis scaling
    #define PIN_POT_X       18  // ADC input for X-axis scaling
    #define PIN_BUTTON      35  // Digital input for mode button
    #define PIN_RGBLED      47  // RGB LED control pin

    // I2C Pin Definitions
    #define SDA_PIN 8   // Default I2C SDA for S3-Mini
    #define SCL_PIN 9   // Default I2C SCL for S3-Mini
    
    // E-ink display pins
    #define EPD_DC      38
    #define EPD_CS      37
    #define SRAM_CS     33  // FeatherWing onboard SRAM, matching the original wiring
    #define EPD_RESET   -1  // FeatherWing uses its onboard auto-reset circuit
    #define EPD_BUSY    -1

    // SPI Pins for E-ink
    #define SCLK        12
    #define MISO        13
    #define MOSI        11
#endif

#ifdef BOARD_ESP32C3_SUPER_MINI
    #define PIN_MUX_S0      0
    #define PIN_MUX_S1      1
    #define PIN_MUX_S2      5
    #define PIN_MUX_S3      10
    #define PIN_MUX_EN      20  // ADG706 enable; active high
    #define PIN_SIG         -1  // External ADS1115 is used
    #define PIN_POT_Y       -1
    #define PIN_POT_X       -1
    #define PIN_BUTTON      21
    #define PIN_RGBLED      2   // No LED fitted; keeps the legacy LED API off shared buses

    // I2C Pin Definitions
    #define SDA_PIN 8
    #define SCL_PIN 9
    
    // E-ink display pins
    #define EPD_DC      3
    #define EPD_CS      7
    #define SRAM_CS     -1  // Use the ESP32-C3 framebuffer
    #define EPD_RESET   -1
    #define EPD_BUSY    -1

    // SPI Pins for E-ink
    #define SCLK        4
    #define MISO        -1  // Display is write-only; SD and SRAM are unused
    #define MOSI        6
#endif

// Verify that a board is selected
#if !defined(BOARD_ESP32S3_MINI) && !defined(BOARD_ESP32C3_SUPER_MINI)
    #error "Please select a board by uncommenting one of the board definitions at the top of board_config.h"
#endif

#ifdef hasEink
  #if (defined(EINK_ADAFRUIT_4195_GDEY0213B74) + \
        defined(EINK_ADAFRUIT_4195_LEGACY_BN) + \
        defined(EINK_ADAFRUIT_4814_TRICOLOR_MFGNR) + \
        defined(EINK_ADAFRUIT_4778_TRICOLOR_Z94) + \
        defined(EINK_ADAFRUIT_4778_TRICOLOR_Z10)) != 1
    #error "Select exactly one supported Adafruit e-ink panel revision"
  #endif
#endif

#endif // BOARD_CONFIG_H
