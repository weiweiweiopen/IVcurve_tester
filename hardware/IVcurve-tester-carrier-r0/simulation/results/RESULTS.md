# Static load-scan results

Run on 2026-08-01 with the CPU-only ngspice 44.2 shared library bundled with KiCad 10.0.3. The generated `load_scan_results.csv` contains 128 rows: 16 channels x two DUT voltages x two ADG706 on-resistance corners x two equivalent source forms.

## Assumptions

- DUT open-circuit voltage corners: 0.9 V and 3.3 V.
- DUT source resistance: 22 ohm. This is an example input, not a measured DUT value.
- ADG706 on-resistance: 6 ohm typical and 12 ohm maximum.
- Load bank: 1 Mohm, 20 kohm, 8.2 kohm, 4.3 kohm, 2.2 kohm, 1 kohm, 750 ohm, 470 ohm, 330 ohm, 220 ohm, 150 ohm, 100 ohm, 82 ohm, 51 ohm, 30 ohm, and 18 ohm.
- Resistor rating gate: 0.25 W continuous. Pulse rating and temperature derating are not modeled.
- ADS1115 rail: 3.3 V; input is a simplified 1 kohm series / 10 Mohm shunt / 5 pF / rail-clamp network.
- 25 mA is a conservative local design target. 30 mA is the ADG706 continuous absolute maximum and must not be treated as a normal operating target.

## Gate summary

| DUT corner | ADG706 RON | Above 25 mA | Above 30 mA | Above 0.25 W resistor gate |
|---:|---:|---|---|---|
| 0.9 V | 6 ohm typ | none | none | none |
| 0.9 V | 12 ohm max | none | none | none |
| 3.3 V | 6 ohm typ | S12-S16 (100, 82, 51, 30, 18 ohm) | S14-S16 (51, 30, 18 ohm) | none |
| 3.3 V | 12 ohm max | S13-S16 (82, 51, 30, 18 ohm) | S14-S16 (51, 30, 18 ohm) | none |

At 3.3 V, the draft 51, 30, and 18 ohm channels violate the 30 mA continuous absolute maximum under both RON corners for this 22 ohm DUT source model. They block release until the actual DUT source envelope and a current-limiting strategy are defined.

All modeled ADC-pin voltages remain in the 0 V to 3.3 V gate for these positive-source corners. That result does not prove the ADS1115 is protected against an unknown higher-voltage, negative, reverse-connected, or transient DUT.

## Corner sanity check

The S16 / 18 ohm channel changes when RON changes, confirming that the corner is applied to the circuit rather than only to the reporting calculation:

| DUT corner | RON | S16 current | S16 DUT voltage | S16 resistor power |
|---:|---:|---:|---:|---:|
| 0.9 V | 6 ohm | 19.565 mA | 0.469565 V | 6.890 mW |
| 0.9 V | 12 ohm | 17.308 mA | 0.519230 V | 5.392 mW |
| 3.3 V | 6 ohm | 71.739 mA | 1.721737 V | 92.637 mW |
| 3.3 V | 12 ohm | 63.461 mA | 1.903844 V | 72.492 mW |

The maximum resistor dissipation anywhere in the example sweep is 97.116 mW at 3.3 V / 6 ohm RON and 79.761 mW at 3.3 V / 12 ohm RON, both on S15 / 30 ohm. No channel crosses the assumed 0.25 W gate.

The Thevenin and Norton forms agree to a maximum absolute DUT-voltage difference of 8.882e-16 V, which is numerical roundoff and confirms their expected DC equivalence in this model.

## Interpretation limit

This is a static topology and limit check, not signal-integrity signoff. It does not include ADG706 leakage, charge injection or switching transients; ADS1115 switched-capacitor acquisition behavior; real DUT nonlinearity; resistor tolerance, pulse derating or self-heating; connector and copper resistance; PCB return paths; or settling time. Final release still requires the measured DUT envelope, final protection circuit, manufacturer models where available, and bench verification with a current-limited source.
