#!/usr/bin/env python3
from pathlib import Path
import re
import uuid


ROOT = Path(__file__).resolve().parent.parent
BOARD = ROOT / "IVcurve-tester-carrier-r0.kicad_pcb"
BODY = ROOT / "ivcurve_carrier.pretty" / "Adafruit_4814_2.13in_eInk_FeatherWing_Body.kicad_mod"


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


def stable_uuid(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"ivcurve-eink-body:{name}"))


def footprints(text):
    result = {}
    for match in re.finditer(r"\n\t\(footprint ", text):
        start = match.start() + 2
        end = expression_end(text, start)
        item = text[start:end]
        ref = re.search(r'\(property "Reference" "([^"]+)"', item)
        if ref:
            result[ref.group(1)] = (start, end, item)
    return result


def set_position(item, x, y, angle):
    return re.sub(r'\n\t\t\(at [^)]+\)', f'\n\t\t(at {x:.3f} {y:.3f} {angle:g})', item, count=1)


text = BOARD.read_text()
# Repair the first script revision, which inserted the body before a footprint's
# local embedded-font marker instead of the board-level marker.
bad_marker = '\n\t\t(footprint "Adafruit_4814_2.13in_eInk_FeatherWing_Body"'
bad_at = text.find(bad_marker)
if bad_at >= 0:
    start = bad_at + 3
    text = text[:start] + text[expression_end(text, start):]
items = footprints(text)
assert {"J6", "J7"} <= set(items)

j6_at = re.search(r'\n\t\t\(at ([^ ]+) ([^ )]+)(?: ([^ )]+))?\)', items["J6"][2])
x, y = float(j6_at.group(1)), float(j6_at.group(2))
j7_x, j7_y = x - 38.1, y - 20.32

start, end, item = items["J6"]
text = text[:start] + set_position(item, x, y, 270) + text[end:]
items = footprints(text)
start, end, item = items["J7"]
text = text[:start] + set_position(item, j7_x, j7_y, 90) + text[end:]

# Remove stale board-only body footprints and all old functional groups.
for start, end, item in reversed(list(footprints(text).values())):
    if re.search(r'\(property "Reference" "EINK1"', item):
        text = text[:start] + text[end:]
starts = [match.start() + 2 for match in re.finditer(r"\n\t\(group ", text)]
for start in reversed(starts):
    text = text[:start] + text[expression_end(text, start):]

body = BODY.read_text().strip()
body = "\t" + body.replace("\n", "\n\t")
layer_end = body.index("\n", body.index('(layer "F.Cu")')) + 1
body_uuid = stable_uuid("body-footprint")
body = body[:layer_end] + f'\t\t(uuid "{body_uuid}")\n\t\t(at {x:.3f} {y:.3f} 270)\n' + body[layer_end:]

items = footprints(text)
j6_uuid = re.search(r'\(uuid "([^"]+)"\)', items["J6"][2]).group(1)
j7_uuid = re.search(r'\(uuid "([^"]+)"\)', items["J7"][2]).group(1)
group = (
    f'\t(group "EINK_FEATHERWING_4814" (uuid "{stable_uuid("group")}") '
    f'(members "{j6_uuid}" "{j7_uuid}" "{body_uuid}"))'
)
insert = text.rindex("\t(embedded_fonts")
text = text[:insert] + body + "\n\n" + group + "\n" + text[insert:]
BOARD.write_text(text)

assert (round(j7_x - x, 3), round(j7_y - y, 3)) == (-38.1, -20.32)
print("PASS: added official-CAD eInk body and retained only its physical group")
