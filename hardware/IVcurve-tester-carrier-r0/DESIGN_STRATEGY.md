# IV Curve Tester recovery strategy

## Decision

Continue in the current project context. Do not start a new OpenCode session and
do not migrate the project to Spec Kit before the electrical baseline is stable.

Build a proto-faithful carrier first:

1. ESP32-C3 Super Mini on removable headers.
2. ADG706BRUZ integrated on the carrier with the proven daughterboard support circuit.
3. Sixteen hand-solderable backside 1206 SMD load positions between `DUT_P` and
   `S1`–`S16`, shipped DNP so values can be selected later.
4. A removable Play-Zone GY-ADS1115 module using its single 1x10 header.
5. Standard FeatherWing 1x16 + 1x12 mating headers for Adafruit #4814.
6. The FeatherWing reset button as the measure trigger, plus one polarized DUT connector.
7. No OLED; the e-paper is the only off-module display.

The MUX is now integrated to remove the two large daughterboard headers. The ADC
remains removable so its exact fitted converter can still be verified.

## What happened to v2

The v2 PCB was not derived from, traced over, or geometrically checked against
the existing MUX Gerber. It reused the ADG706 symbol, footprint, and STEP model,
then generated a new 120 mm x 80 mm board with hard-coded placement and copper.

The current `hardware/IVcurve-tester-v2/IVcurve-tester-v2.kicad_pcb` has:

- 15 real DRC errors, including seven shorts and two track crossings.
- 96 unconnected items.
- Declared GND zones with no saved filled polygons.

The `00:07:30` `IVcurve-tester-v2.kicad_pcb.bak` is the least damaged v2 point:
zero real DRC rule errors and 99 unconnected items. The later routing reduced the
unconnected count by only three while introducing the shorts. Preserve both as
forensic evidence; do not add more copper to the current v2 file.

## Lightweight specification instead of Spec Kit

Spec Kit is useful for retaining requirements and acceptance gates, but its
official templates are software-oriented and do not perform KiCad ERC/DRC,
routing, zone filling, or SPICE analysis. For this board, the smallest adequate
specification is:

- `CONNECTION_MATRIX.md`: authoritative pin/net contract and electrical limits.
- KiCad schematic: authoritative connectivity.
- KiCad PCB rules/net classes: authoritative physical constraints.
- `simulation/`: parameterized analog safety and operating-point checks.
- A short exception register for every intentionally waived ERC/DRC item.

No exception is accepted merely because a warning is inconvenient.

## ERC treatment

1. Use explicit no-connect flags on genuinely unused IC/module pins.
2. Use `PWR_FLAG` only where a connector or regulator really drives a rail.
3. Fix output-to-output conflicts and pin-type errors at the symbol or circuit;
   do not globally suppress the rule.
4. Record any remaining accepted warning with reference, pin, reason, and the
   evidence that makes it safe.
5. Release gate: zero ERC errors. Warnings must be zero or explicitly reviewed.

ERC proves rule consistency, not circuit correctness. Pin mapping, voltage,
current, polarity, and connector orientation still require independent review.

## Routing treatment

- Manually route `DUT_P`, `DUT_N`, ADC sense, power, and all sixteen switched
  load paths. Keep each load loop short and easy to probe.
- Route ADC sense from the DUT connector before the high-current load branches;
  do not sense after a shared narrow return segment.
- Freeze placement, net classes, keepouts, and critical routes before considering
  an external autorouter.
- If used, an autorouter may handle only remaining low-risk digital nets. Export
  DSN, route externally, import SES, refill zones, and rerun strict DRC. Imported
  routes are candidates, not accepted results.
- Do not use the v2 hard-coded segment-injection scripts as an autorouter.

## Ground treatment

- Use one continuous B.Cu ground plane; do not split analog and digital grounds.
- Control return currents with placement and route geometry.
- Keep both copper layers clear beneath and immediately around the C3 antenna.
- Use selective F.Cu ground where it does not cut signal return paths.
- Add GND stitching vias near digital return transitions and board edges, not as
  a decorative grid.
- Refill zones after every relevant routing change. Inspect thermals, orphan
  islands, neck-downs, and the independent Gerber view before release.

## Simulation treatment

Use CPU-based ngspice analyses for the analog path:

- DC sweep / operating points across DUT source resistance, all sixteen loads,
  ADG706 on-resistance typical/max, and resistor tolerance.
- Gate every point against MUX current, resistor power, ADC input range, and the
  intended dwell time.
- Transient settling after a MUX step, including ADC input/source impedance and
  sample timing.
- Noise only if measurements show it matters.

Short, slow SPI/I2C traces on this carrier do not justify a GPU solver. Use IBIS
only if later integration creates a real digital signal-integrity problem.

ERC, DRC, zone fill, external routing, firmware builds, and ngspice are CPU-bound
here. Forcing a GPU adds setup and nondeterminism without reducing the critical
path.

## Fabrication blockers

- Confirm maximum DUT Voc, Isc, source type, available power, and load dwell.
- Confirm whether the purple module contains ADS1115 or ADS1015 and measure its
  header geometry/orientation.
- Measure all sixteen installed resistors and complete switched-path resistance.
- Add/verify ADC input protection and ensure the pin never exceeds its 3.3 V
  supply rail.
- Keep ADG706 S/D continuous current below 30 mA with engineering margin.
- Complete schematic ERC, PCB DRC, continuity, bring-up, and independent Gerber
  inspection before ordering boards.

## Primary references

- [Adafruit product #4814](https://www.adafruit.com/product/4814)
- [Adafruit 2.13-inch FeatherWing pinout](https://learn.adafruit.com/adafruit-2-13-eink-display-breakouts-and-featherwings/pinouts)
- [ADG706/ADG707 data sheet](https://www.analog.com/media/en/technical-documentation/data-sheets/adg706_707.pdf)
- [TI ADS1115 product and data sheet](https://www.ti.com/product/ADS1115)
- [KiCad 10 Schematic Editor documentation](https://docs.kicad.org/10.0/en/eeschema/eeschema.html)
- [KiCad 10 PCB Editor documentation](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html)
