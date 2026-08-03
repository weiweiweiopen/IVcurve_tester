# Carrier r0 release blockers

Audit date: 2026-08-03

The schematic connectivity passes KiCad 10.0.5 ERC with zero violations and the
exported-netlist check verifies all sixteen load paths. The imported Freerouting
result has zero unconnected items. Fabrication output remains blocked by the two
intentional J8 board-edge contact violations and the physical and electrical
inputs below.

## Required human evidence

Provide one consolidated set containing:

1. DUT limits: maximum open-circuit voltage, short-circuit current, available
   power or minimum source impedance, reverse-polarity expectation, and maximum
   load dwell time.
2. ADC module: sharp, square-on photos of both sides; readable IC marking; a
   pin-by-pin label transcription; caliper measurements of board length/width,
   header pitch, row spacing, hole diameter, and each header's offset from two
   board edges; and the installed pin gender/length.
3. Every removable module: top and bottom photos with pin 1 marked, installed
   header gender, socket/header body dimensions and MPN if known, and caliper
   measurements sufficient to prove mating orientation and clearance.
4. JLC assembly parts: exact polarized DUT connector, S3/ADC
   sockets, and #4814 mating male headers must be qualified against available
   LCSC/JLC parts. The 16 load resistors are intentionally backside 1206 DNP positions.
5. Protection decision: approved ADC input protection/current-limiting circuit
   for the documented DUT envelope. The present R17 value is `0R PROTO /
   PROTECT_TBC`, so ADC A0 is not protected against overvoltage, reverse input,
   powered-off back-powering, or transients.

## Evidence already established

- ADG706BRUZ uses the verified TSSOP-28 pin mapping from the fabricated MUX board;
  C1 is 100 nF and R19 is the 1 kΩ enable pulldown.
- Firmware and schematic agree on A0/A1/A2/A3 = GPIO0/1/5/10, active-high enable
  = GPIO20, SDA/SCL = GPIO8/9, and channel order `0000=S1` through `1111=S16`.
- The photographed display is Adafruit #4814. It uses factory female sockets on
  the Feather 1x16/1x12, 2.54 mm pitch, 20.32 mm row-spacing contract, so the
  carrier uses mating male headers.
- The stored 3.3 V / 22 ohm example simulation exceeds the ADG706 30 mA
  continuous absolute maximum on the 51, 30, and 18 ohm channels.

No Gerber or drill package may be generated until these items are resolved and
the resulting PCB passes the complete release gates.
