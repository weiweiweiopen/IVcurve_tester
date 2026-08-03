# Static load-scan model

This directory contains a deliberately small DC model for checking the carrier-r0 load-bank limits before schematic release.

## What is modeled

- The DUT can be represented as either a Thevenin source (`VOC` in series with `RSRC`) or its equivalent Norton source (`VOC / RSRC` in parallel with `RSRC`).
- Sixteen independent DUT replicas represent a one-channel-at-a-time static ADG706 scan. Each replica uses one draft load resistor and a parameterized `RON`.
- The ADG706 corners are 6 ohm typical and 12 ohm maximum at 3.3 V.
- The ADS1115 input is simplified to a 1 kohm sense lead, 10 Mohm input resistance, 5 pF placeholder capacitance, and two rail-clamp diodes on a 3.3 V supply.
- The result file reports DUT voltage, ADC-pin voltage, load current, DUT operating power, resistor power, MUX power, and release gates for every channel.

Default example assumptions are `VOC=3.3 V`, `RSRC=22 ohm`, and `RESISTOR_RATING=0.25 W`. They are test inputs, not measured DUT specifications. The direct deck uses its `VOC`; the Python harness overrides it with the requested voltage corners. Edit the other `.param` values near the top of `iv_load_scan.cir` or pass different voltage corners, then rerun.

## Reproduce with this Mac's KiCad ngspice engine

KiCad 10.0.3 includes ngspice 44.2 as a shared CPU library even though no standalone `ngspice` executable is installed:

```sh
cd hardware/IVcurve-tester-carrier-r0/simulation
python3 run_load_scan.py
```

For a different DUT voltage sweep:

```sh
python3 run_load_scan.py --voc-corners 0.5 0.9 1.8 3.3
```

To use a different shared library:

```sh
NGSPICE_LIB=/path/to/libngspice.dylib python3 run_load_scan.py
```

The script runs 0.9 V and 3.3 V DUT corners, 6 ohm and 12 ohm MUX corners, and both equivalent source forms. It writes `results/load_scan_results.csv`. It also compares every simulated load current with the closed-form `VOC / (RSRC + RLOAD + RON)` result; a mismatch above 0.01% stops the run so a silently unapplied corner cannot pass.

If a standard ngspice CLI is later installed, the deck itself can be checked without the Python harness:

```sh
ngspice -b -o results/ngspice.log iv_load_scan.cir
```

The CLI command performs the default operating point. The Python harness is what applies both RON corners, checks both source forms, calculates per-channel powers, and emits the CSV gates.

## Gates

- `mux_25ma_design_gate`: selected-channel current must be no more than the conservative 25 mA design target used by this model.
- `mux_30ma_absmax_gate`: absolute selected-channel current must be no more than the ADG706 30 mA continuous absolute maximum.
- `adc_0_to_3v3_gate`: the modeled ADC pin must remain between GND and 3.3 V.
- `resistor_power_gate`: modeled resistor dissipation must not exceed `RESISTOR_RATING`.

A passing row is not a fabrication approval. The real `VOC`, `ISC` or source resistance, transient load dwell, resistor pulse/temperature derating, assembled per-channel resistance, connector resistance, ADG706 leakage and charge injection, ADS1115 switched-capacitor input behavior, and ADC protection components are not yet known.

This static model also does not validate routing, return paths, MUX switching transients, settling time, ADC acquisition error, e-paper SPI integrity, or thermal coupling. Those require the final schematic/layout and, where appropriate, manufacturer models or bench measurements.
