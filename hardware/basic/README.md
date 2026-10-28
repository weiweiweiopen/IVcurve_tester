# Basic USB-Powered I–V Board

The measurement architecture derives from **Marc Dusseiller's [IVcurve_tester](https://github.com/dusjagr/IVcurve_tester)**. This carrier uses a LOLIN S3 Mini, ADG706, ADS1115, and Adafruit 4814 display.

## Electrical Operation

- USB supplies the MCU, ADC, and display.
- J1 connects one DSSC through positive and negative collector pads.
- ADG706 selects one of 16 resistive loads.
- ADS1115 reads the DUT voltage. Current is calculated using the effective load-path resistance, including multiplexer and contact resistance.
- The display is an SSD1680-based, 250 × 122-pixel tricolor panel.

Enter measured load-path resistances and ADC corrections in the firmware calibration settings before relying on calibrated current or power readings. This board has no energy-harvesting or storage circuit.

## Circuit References

- [KiCad project](Marc_USB.kicad_pro)
- [Schematic PDF](schematic.pdf)
- [BOM](BOM.csv)
- [Pin/net map](checks/pin-map.csv)
- [Gerber files](fabrication/basic-JLCPCB.zip)
- [Firmware and GPIO assignments](../../firmware/basic/README.md)
