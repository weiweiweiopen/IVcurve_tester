# IV Curve Tester carrier r0

This is the controlled recovery baseline for a proto-faithful carrier. It uses
an onboard ADG706, removable controller/display/ADC modules, sixteen load
resistors, and the FeatherWing reset button as the scan trigger. No carrier PCB
has been routed yet.

## Current status

- KiCad 10 schematic: ERC 0 errors / 0 warnings.
- Load matrix: all sixteen `DUT_P -> Rn -> MUX_Sn` paths netlist-verified.
- Display: photographed Adafruit #4814 2.13-inch tri-color FeatherWing; no OLED.
- PCB body outline: derived from Adafruit's official
  `Adafruit 2.13in Tri-Color eInk FeatherWing.brd`; J6, J7, board contour,
  59.2 x 29.2 mm panel, and 47.76 x 22.92 mm active area move as one group.
- Controller: ESP32-C3 Super Mini with the verified 16-pin header order.
- ADC: Play-Zone GY-ADS1115 single-row module; confirm the fitted IC marking.
- Firmware: #4814 panel is the default and uses the C3 internal framebuffer.
- Static simulation: 128 CPU/ngspice operating points reproduced and checked.
- Fabrication: blocked pending the PCB, final ADC footprint/protection, and JLC
  assembly-part qualification. Sixteen backside 1206 load positions ship DNP.

## Files

- `IVcurve-tester-carrier-r0.kicad_sch` — authoritative connectivity.
- `exports/IVcurve-tester-carrier-r0.svg` / `.png` — reviewed schematic preview.
- `reports/ERC.rpt` — final ERC report.
- `reports/IVcurve-tester-carrier-r0.net.xml` — exported verification netlist.
- `reports/v2-current-{erc,drc}.json` — reproducible audit of the rejected v2.
- `reports/v2-best-backup-drc.json` — DRC evidence for the rollback reference.
- `CONNECTION_MATRIX.md` — pin, signal, and load-channel contract.
- `ivcurve-carrier-connections.html` — visual system-level connection map.
- `DESIGN_STRATEGY.md` — recovery, ERC, routing, ground, and simulation policy.
- `simulation/` — reproducible static analog model and results.

## Reproduce checks

```sh
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli sch erc \
  --severity-all --exit-code-violations \
  IVcurve-tester-carrier-r0.kicad_sch

cd simulation
python3 run_load_scan.py
```

From the repository root, build the target firmware with:

```sh
pio run -e esp32-c3
```
