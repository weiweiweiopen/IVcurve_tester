#!/usr/bin/env python3
from pathlib import Path
import uuid


ROOT = Path(__file__).resolve().parent.parent
SCHEMATIC = ROOT / "IVcurve-tester-carrier-r0.kicad_sch"
MUX_SCHEMATIC = ROOT.parent / "MUX-ADG706" / "MUX-ADG706.kicad_sch"
SYMBOL_LIBRARY = ROOT / "ivcurve_carrier.kicad_sym"


def expression_end(text, start):
    depth = 0
    quoted = escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index + 1
    raise ValueError("unbalanced S-expression")


def top_level_spans(text):
    spans = []
    depth = 0
    start = None
    quoted = escaped = False
    for index, char in enumerate(text):
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
            continue
        if char == '"':
            quoted = True
        elif char == "(":
            if depth == 1:
                start = index
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 1 and start is not None:
                spans.append((start, index + 1))
                start = None
    return spans


def stable_uuid(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"ivcurve-carrier-onboard-mux:{name}"))


def label(name, x, y, orientation, key):
    return (
        f'\t(label "{name}" (at {x} {y} {orientation}) (fields_autoplaced) '
        f'(effects (font (size 1.27 1.27)) (justify left bottom)) '
        f'(uuid "{stable_uuid(key)}"))'
    )


text = SCHEMATIC.read_text()

# Cache the proven symbol from the fabricated daughterboard design.
if '(symbol "ADG706:ADG706BRUZ-REEL7"' not in text:
    source = MUX_SCHEMATIC.read_text()
    start = source.index('(symbol "iv_symbols:ADG706_edited"')
    symbol = source[start:expression_end(source, start)].replace(
        '(symbol "iv_symbols:ADG706_edited"', '(symbol "ADG706:ADG706BRUZ-REEL7"', 1
    ).replace("ADG706_edited", "ADG706BRUZ-REEL7").replace("pin power_in line", "pin passive line")
    lib_start = text.index("\t(lib_symbols")
    lib_end = expression_end(text, lib_start)
    text = text[:lib_end - 1] + "\n\t\t" + symbol + "\n\t" + text[lib_end - 1:]
else:
    text = text.replace('(symbol "ADG706_0_0"', '(symbol "ADG706BRUZ-REEL7_0_0"')

cached_start = text.index('(symbol "ADG706:ADG706BRUZ-REEL7"')
cached_symbol = text[cached_start:expression_end(text, cached_start)].replace(
    '(symbol "ADG706:ADG706BRUZ-REEL7"', '(symbol "ADG706BRUZ-REEL7"', 1
)
SYMBOL_LIBRARY.write_text(
    '(kicad_symbol_lib\n\t(version 20231120)\n\t(generator "eeschema")\n\t'
    + cached_symbol + '\n)\n'
)

if '(symbol "Device:C"' not in text:
    device_library = Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols/Device.kicad_sym").read_text()
    start = device_library.index('\t(symbol "C"\n') + 1
    capacitor = device_library[start:expression_end(device_library, start)].replace(
        '(symbol "C"', '(symbol "Device:C"', 1
    )
    lib_start = text.index("\t(lib_symbols")
    lib_end = expression_end(text, lib_start)
    text = text[:lib_end - 1] + "\n\t\t" + capacitor + "\n\t" + text[lib_end - 1:]

# Remove the daughterboard connectors and their local wire stubs. Also make the
# operation safe to rerun by replacing any prior integrated instances.
remove = []
generated_label_keys = {
    *(f"U1-label-left-{index}" for index in range(17)),
    *(f"U1-label-right-{index}" for index in range(8)),
    "R19-left", "R19-right", "C1-left", "C1-right",
}
for start, end in top_level_spans(text):
    item = text[start:end]
    if item.startswith("(symbol") and any(
        f'(property "Reference" "{ref}"' in item for ref in ("J3", "J4", "U1", "C1", "R19")
    ):
        remove.append((start, end))
    elif item.startswith("(wire") and (
        "(xy 185.42 " in item or
        ("(xy 246.38 " in item and not "(xy 246.38 207.01)" in item)
    ):
        remove.append((start, end))
    elif item.startswith("(wire") and f'(uuid "{stable_uuid("button-wire")}")' in item:
        remove.append((start, end))
    elif item.startswith("(label") and any(token in item for token in ("(at 175.26 ", "(at 236.22 ")):
        remove.append((start, end))
    elif item.startswith("(label") and any(
        f'(uuid "{stable_uuid(key)}")' in item for key in generated_label_keys
    ):
        remove.append((start, end))
for start, end in reversed(remove):
    text = text[:start] + text[end:]

text = text.replace("EXISTING ADG706 DAUGHTERBOARD", "ONBOARD ADG706 MULTIPLEXER")

project = "IVcurve-tester-carrier-r0"
path = "/b58c3670-e5c1-4ce7-9ca3-ad16d66f7fab"
u_pins = (1, *range(4, 13), *range(14, 29))
u1 = f'''\t(symbol (lib_id "ADG706:ADG706BRUZ-REEL7") (at 210.82 105.41 0) (unit 1)
\t\t(exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no) (fields_autoplaced yes)
\t\t(uuid "{stable_uuid('U1')}")
\t\t(property "Reference" "U1" (at 198.12 76.2 0) (effects (font (size 1.27 1.27)) (justify left)))
\t\t(property "Value" "ADG706BRUZ" (at 198.12 133.35 0) (effects (font (size 1.27 1.27)) (justify left)))
\t\t(property "Footprint" "ivcurve_carrier:ADG706_TSSOP-28" (at 210.82 105.41 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(property "Datasheet" "https://www.analog.com/media/en/technical-documentation/data-sheets/adg706_707.pdf" (at 210.82 105.41 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(property "Description" "16-channel low-voltage analog multiplexer; integrated from MUX-ADG706 daughterboard" (at 210.82 105.41 0) (effects (font (size 1.27 1.27)) (hide yes)))
{chr(10).join(f'\t\t(pin "{pin}" (uuid "{stable_uuid(f"U1-pin-{pin}")}"))' for pin in u_pins)}
\t\t(instances (project "{project}" (path "{path}" (reference "U1") (unit 1))))
\t)'''

def passive_symbol(kind, reference, value, footprint, x, y):
    return f'''\t(symbol (lib_id "Device:{kind}") (at {x} {y} 90) (unit 1)
\t\t(exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no) (fields_autoplaced yes)
\t\t(uuid "{stable_uuid(reference)}")
\t\t(property "Reference" "{reference}" (at {x} {y - 3.81} 90) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "{value}" (at {x} {y + 3.81} 90) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "ivcurve_carrier:{footprint}" (at {x} {y} 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(property "Datasheet" "~" (at {x} {y} 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(property "Description" "Onboard ADG706 support component" (at {x} {y} 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(pin "1" (uuid "{stable_uuid(reference + '-pin-1')}"))
\t\t(pin "2" (uuid "{stable_uuid(reference + '-pin-2')}"))
\t\t(instances (project "{project}" (path "{path}" (reference "{reference}") (unit 1))))
\t)'''

objects = [u1]
left_channels = {
    "MUX_EN": 82.55,
    "MUX_S1": 87.63, "MUX_S2": 90.17, "MUX_S3": 92.71, "MUX_S4": 95.25,
    "MUX_S5": 97.79, "MUX_S6": 100.33, "MUX_S7": 102.87, "MUX_S8": 105.41,
    "MUX_S9": 107.95, "MUX_S10": 110.49, "MUX_S11": 113.03, "MUX_S12": 115.57,
    "MUX_S13": 118.11, "MUX_S14": 120.65, "MUX_S15": 123.19, "MUX_S16": 125.73,
}
for index, (name, y) in enumerate(left_channels.items()):
    objects.append(label(name, 193.04, y, 180, f"U1-label-left-{index}"))
for index, (name, y) in enumerate((
    ("+3V3", 82.55), ("MUX_A0", 87.63), ("MUX_A1", 90.17),
    ("MUX_A2", 92.71), ("MUX_A3", 95.25), ("DUT_N", 100.33),
    ("GND", 123.19), ("GND", 125.73),
)):
    objects.append(label(name, 228.6, y, 0, f"U1-label-right-{index}"))

objects.extend([
    f'\t(wire (pts (xy 246.38 207.01) (xy 240.03 207.01)) (stroke (width 0) (type default)) (uuid "{stable_uuid("button-wire")}"))',
    passive_symbol("R", "R19", "1k EN_PULLDOWN", "R_0805_HandSolder", 260.35, 105.41),
    label("MUX_EN", 256.54, 105.41, 180, "R19-left"),
    label("GND", 264.16, 105.41, 0, "R19-right"),
    passive_symbol("C", "C1", "100n", "C_0805_HandSolder", 260.35, 118.11),
    label("+3V3", 256.54, 118.11, 180, "C1-left"),
    label("GND", 264.16, 118.11, 0, "C1-right"),
])

insert_at = text.index("\t(sheet_instances")
text = text[:insert_at] + "\n\n".join(objects) + "\n\n" + text[insert_at:]
SCHEMATIC.write_text(text)
print("PASS: J3/J4 replaced by onboard U1 ADG706, C1, and R19")
