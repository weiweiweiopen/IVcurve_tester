# IV Curve Tester carrier r0 — connection matrix

## Hardware baseline

- Controller: generic 16-pin ESP32-C3 Super Mini on removable headers. Nominal
  module size is 22.5 x 18 mm with 2.54 mm pitch and 15.24 mm row spacing.
- Display target: photographed Adafruit product 4814, 2.13-inch 250 x 122
  SSD1680 tri-color FeatherWing. The OLED is deliberately omitted.
- Firmware defaults to #4814 (`EINK_ADAFRUIT_4814_TRICOLOR_RW` /
  `ThinkInk_213_Tricolor_RW`).
- MUX: ADG706BRUZ integrated directly on the carrier with 100 nF local
  decoupling and a 1 kΩ enable pulldown. The former daughterboard is only the
  verified electrical reference.
- ADC target: Play-Zone GY-ADS1115 at I2C address `0x48`, nominally 25.5 x 9 mm
  with one 1x10 row at 2.54 mm pitch.
- User input: the active-low reset button on the eInk FeatherWing.

## Net contract

### ESP32-C3 Super Mini to onboard ADG706

| ADG706 pin | Function | Carrier net | ESP32-C3 Super Mini |
|---:|---|---|---:|
| 1 | VDD | `+3V3` | 3V3 |
| 12, 27 | GND, VSS | `GND` | GND |
| 18 | active-high enable | `MUX_EN` | GPIO20 |
| 17 | address bit 0 | `MUX_A0` | GPIO0 |
| 16 | address bit 1 | `MUX_A1` | GPIO1 |
| 15 | address bit 2 | `MUX_A2` | GPIO5 |
| 14 | address bit 3 | `MUX_A3` | GPIO10 |
| 28 | common drain | `DUT_N` | — |

R19 pulls enable low. Firmware must configure GPIO20 low before any address pin changes, then assert it only during an intentional load measurement.

### Load bank to onboard ADG706

| Firmware channel | ADG706 pin/signal | Load reference | PCB population | Required stored value |
|---:|---|---|---:|---|
| 0 | 19 / S1 | R1 | 1206 DNP / LOAD_TBD | measured assembled `R_eff[0]` |
| 1 | 20 / S2 | R2 | 1206 DNP / LOAD_TBD | measured assembled `R_eff[1]` |
| 2 | 21 / S3 | R3 | 1206 DNP / LOAD_TBD | measured assembled `R_eff[2]` |
| 3 | 22 / S4 | R4 | 1206 DNP / LOAD_TBD | measured assembled `R_eff[3]` |
| 4 | 23 / S5 | R5 | 1206 DNP / LOAD_TBD | measured assembled `R_eff[4]` |
| 5 | 24 / S6 | R6 | 1206 DNP / LOAD_TBD | measured assembled `R_eff[5]` |
| 6 | 25 / S7 | R7 | 1206 DNP / LOAD_TBD | measured assembled `R_eff[6]` |
| 7 | 26 / S8 | R8 | 1206 DNP / LOAD_TBD | measured assembled `R_eff[7]` |
| 8 | 11 / S9 | R9 | 1206 DNP / LOAD_TBD | measured assembled `R_eff[8]` |
| 9 | 10 / S10 | R10 | 1206 DNP / LOAD_TBD | measured assembled `R_eff[9]` |
| 10 | 9 / S11 | R11 | 1206 DNP / LOAD_TBD | measured assembled `R_eff[10]` |
| 11 | 8 / S12 | R12 | 1206 DNP / LOAD_TBD | measured assembled `R_eff[11]` |
| 12 | 7 / S13 | R13 | 1206 DNP / LOAD_TBD | measured assembled `R_eff[12]` |
| 13 | 6 / S14 | R14 | 1206 DNP / LOAD_TBD | measured assembled `R_eff[13]` |
| 14 | 5 / S15 | R15 | 1206 DNP / LOAD_TBD | measured assembled `R_eff[14]` |
| 15 | 4 / S16 | R16 | 1206 DNP / LOAD_TBD | measured assembled `R_eff[15]` |

Each resistor connects from common `DUT_P` to its corresponding S1–S16 input. ADG706 D returns to `DUT_N`. Channel binary order is `0000 = S1` through `1111 = S16`.

The existing global `64 Ω` firmware subtraction is invalid for a released design. Store and use the measured total path resistance for every channel, including the resistor, MUX on-resistance, connector contact resistance, and copper.

### ADC module

| ADC signal | Carrier net | ESP32-C3 Super Mini / circuit |
|---|---|---|
| VDD | `+3V3` | 3V3 |
| GND | `DUT_N` / `GND` | GND |
| SDA | `I2C_SDA` | GPIO8 |
| SCL | `I2C_SCL` | GPIO9 |
| ADDR | `GND` | address `0x48` |
| ALERT/RDY | `ADC_ALERT` | no connect in r0 |
| A0 | `ADC_VIN` | protected sense from `DUT_P` |
| A1–A3 | — | no connect in proto-faithful r0 |

The module PCB can be populated with ADS1015 or ADS1115. Confirm its IC marking or verify the conversion behavior before assembly release. The ADS input must remain between GND and its supply rail even when the PGA range is set wider.

Viewed from the labeled side, the GY module row is `V, G, SCL, SDA, ADDR,
ALERT, A0, A1, A2, A3`; only A0 is used. The two module mounting holes are not
drilled in the carrier footprint until their positions are measured on the
actual purchased module.

### Adafruit FeatherWing mating headers

Use one 1x16 and one 1x12 2.54 mm male header, with 20.32 mm row spacing,
matching the factory female sockets on Adafruit #4814.

| Feather pad | Feather signal | Carrier net | ESP32-C3 Super Mini |
|---:|---|---|---:|
| 1 | RESET/button | `BUTTON_N` | GPIO21 input; active low |
| 2 | 3V | `+3V3` | 3V3 |
| 4 | GND | `GND` | GND |
| 11 | SPI SCK | `EPD_SCLK` | GPIO4 |
| 12 | SPI MOSI | `EPD_MOSI` | GPIO6 |
| 13 | SPI MISO | — | no connect; panel is write-only |
| 19 | SD CS / D5 | — | no connect; SD card unused |
| 20 | SRAM CS / D6 | — | no connect; internal framebuffer used |
| 21 | EINK CS / D9 | `EPD_CS_N` | GPIO7 |
| 22 | EINK D/C / D10 | `EPD_DC` | GPIO3 |

The FeatherWing BUSY signal is available only on a separate breakout pad. Leave it unconnected for r0 and use `EPD_BUSY = -1`.

### Button and DUT connector

| Item | Pin 1 | Pin 2 |
|---|---|---|
| FeatherWing reset button | `BUTTON_N` / GPIO21 | FeatherWing onboard reset network |
| DUT input | `DUT_P` | `DUT_N` |

GPIO21 uses the ESP32 internal pull-up. Firmware must debounce the FeatherWing
reset pulse, ignore its startup auto-reset pulse, and reinitialize ePaper before
scanning. GPIO8 and GPIO9 are boot straps but the I2C pull-ups hold both high
during reset; GPIO2 is deliberately unused. The DUT connector must have explicit
`+` and `−` silkscreen and reverse-polarity handling must be decided before
fabrication release.

## Electrical limits that block fabrication release

1. Document maximum DUT open-circuit voltage, short-circuit current, available power, and maximum load dwell time.
2. ADG706 S or D continuous absolute-maximum current is 30 mA. The minimum load channel must not violate it in normal operation or a credible fault.
3. ADS1115 powered at 3.3 V does not tolerate an input above the 3.3 V rail merely because a wider PGA range is selected.
4. Measure every resistor and complete switched path before firmware release.
5. Verify the ADC module IC, pin order, row spacing, and orientation against the physical board.

The firmware currently uses a 25 mA conservative guard: it measures the 1 MΩ channel first, predicts each later channel from 95% of its nominal load resistance without credit for DUT source resistance or MUX resistance, and skips loads above the guard. This is a secondary safeguard, not permission to omit hardware current limiting or ADC overvoltage protection.

## Release gates

- Schematic: zero ERC errors; no isolated labels used to disguise unused pins. Use explicit no-connect flags.
- PCB: zero DRC errors and zero unconnected items after a final zone refill.
- Routing: manually route `DUT_P`, `DUT_N`, ADC sense, and the 16 load paths. External autorouting is allowed only for remaining low-risk digital nets after placement is frozen.
- Ground: continuous B.Cu GND plane, antenna copper keepout on both layers, no orphan islands, and GND stitching vias around digital return paths. Do not split analog and digital ground planes.
- Verification: continuity test every channel, confirm MUX truth-table order, verify ADC address and scale, and test first with a current-limited source.
- Manufacturing: inspect Gerber and drill outputs in an independent viewer after ERC/DRC pass.
