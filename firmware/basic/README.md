# Basic Board Firmware

USB-powered I–V measurement firmware for the basic carrier and LOLIN S3 Mini.

## Operation

Press and release the button, or send `SCAN` followed by a newline over serial, to start a 16-load sweep. Send `!` or press the button during a sweep to abort.

The display is an Adafruit 4814 SSD1680 tricolor panel at 250 × 122 pixels. BUSY is not wired; the local EPD driver uses its fixed/bounded wait path.

## GPIO Assignments

| Function | GPIO |
|---|---|
| MUX A0 / A1 / A2 / A3 | 2 / 6 / 4 / 5 |
| MUX enable | 14 |
| I²C SDA / SCL | 8 / 9 |
| Button | 35 |
| SPI SCK / MISO / MOSI | 36 / 18 / 16 |
| EPD CS / DC | 37 / 38 |
| SRAM CS | 34 |

## Measurement Calibration

Calibration parameters are in `include/calibration.h`; measurement records belong in `calibration-record.md`.

The firmware reports `UNCALIBRATED / NOMINAL` until calibration is supplied. Nominal resistor values do not account for unknown ADG706 on-resistance or contact resistance. Use measured effective path resistances and ADC gain/offset corrections for calibrated results.

This application does not control the charging board's GPIO12 relay selection, GPIO13 DONE output, or GPIO11 power-warning input.

## Build and Program

Run from the repository root with PlatformIO:

```sh
pio run -d firmware/basic
pio run -d firmware/basic -t upload
pio device monitor -d firmware/basic -b 115200
```

The local Adafruit EPD 4.6.13 driver includes the bounded-wait patch used by this application. Keep the supplied driver API and patch when changing library versions.
