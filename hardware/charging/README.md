# Charging and Energy-Harvesting I–V Board

Based on Marc Dusseiller's I–V measurement architecture. The energy-harvesting, storage, switching, and derivative PCB design was completed by **Sol 6.1**.

## Power Circuit

- AEM10941 harvests energy from the DSSC, with the schematic configured for nominal 70% Voc MPPT.
- C201 and C202 are parallel 1.5F / 5V PHB supercapacitor packs: 3F total at a 5V rating.
- TPS7A02 supplies the always-on control domain.
- TPL5111 and READY logic produce `BOOST_EN = PM_READY AND TIMER_REQUEST`.
- TPS61023 boosts `VSTORE` to 5V.
- JP201 controls TPS22917's connection from the harvested 5V supply to module VBUS. Set JP201 OFF before connecting USB.

## Harvest/Measurement Switching

K1 uses both relay poles:

| Contact | Connection |
|---|---|
| COM3 | `DUT_P` |
| NC2 | `HARV_P` |
| NO4 | `LOAD_P` |
| COM6 | `DUT_P` |
| NO5 | `SENSE_P` |
| Pin7 | Unconnected |

With the coil off, the DSSC connects to the harvester. Energizing the coil connects the DSSC to the load bank and ADC sensing branch. Disable the ADG706 load before changing relay state and allow contact/input settling before sampling.

## MCU Control

| Signal | GPIO | Function |
|---|---:|---|
| `SCAN_MODE` | 12 | Energize K1 for measurement |
| `MCU_DONE` | 13 | Complete the timer-controlled power interval |
| `POWER_WARN_N` | 11 | Storage/power warning input |

Charging-specific firmware must manage relay selection, load enable, voltage warnings, and DONE timing. The basic USB firmware does not implement this complete sequence.

## Circuit References

- [KiCad project](Marc_USB.kicad_pro)
- [Schematic PDF](schematic.pdf)
- [BOM](BOM.csv)
- [Pin/net map](checks/pin-map.csv)
- [Gerber files](fabrication/charging-PROTOTYPE-JLCPCB.zip)
- [Charging mechanism and energy budget](../../README.md#charging-board)
