#!/usr/bin/env python3
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent.parent
SCH = ROOT / "IVcurve-tester-carrier-r0.kicad_sch"
PCB = ROOT / "IVcurve-tester-carrier-r0.kicad_pcb"
RESISTORS = Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/Resistor_SMD.pretty")
LOAD_FP = RESISTORS / "R_1206_3216Metric_Pad1.30x1.75mm_HandSolder.kicad_mod"
SIGNAL_FP = RESISTORS / "R_0603_1608Metric_Pad0.98x0.95mm_HandSolder.kicad_mod"


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


def remove_uuid_object(text, object_uuid):
    marker = f'(uuid "{object_uuid}")'
    marker_at = text.find(marker)
    assert marker_at >= 0, object_uuid
    start = text.rfind("\n\t(", 0, marker_at) + 2
    return text[:start] + text[expression_end(text, start):]


def reference(item):
    match = re.search(r'\(property "Reference" "([^"]+)"', item)
    return match.group(1) if match else None


def footprints(text):
    result = {}
    for match in re.finditer(r"\n\t\(footprint ", text):
        start = match.start() + 2
        end = expression_end(text, start)
        item = text[start:end]
        ref = reference(item)
        if ref:
            result[ref] = (start, end, item)
    return result


def property_value(item, name):
    return re.search(rf'\(property "{name}" "([^"]*)"', item).group(1)


def set_property(item, name, value):
    return re.sub(rf'(\(property "{name}" ")[^"]*', rf'\g<1>{value}', item, count=1)


def pad_nets(item):
    result = {}
    for match in re.finditer(r'\(pad "([^"]+)"', item):
        pad = item[match.start():expression_end(item, match.start())]
        net = re.search(r'\(net "([^"]+)"\)', pad)
        if net:
            result[match.group(1)] = net.group(1)
    return result


def mirror_text(item):
    starts = [match.start() for match in re.finditer(r'\(effects\b', item)]
    for start in reversed(starts):
        end = expression_end(item, start)
        effects = item[start:end]
        if "(justify" not in effects:
            insertion = effects.rfind("\n")
            effects = effects[:insertion] + "\n\t\t\t(justify mirror)" + effects[insertion:]
            item = item[:start] + effects + item[end:]
    return item


def make_backside_resistor(path, old_item, ref):
    at = re.search(r'\n\t\t\(at ([^)]+)\)', old_item).group(1)
    footprint_uuid = re.search(r'\(uuid "([^"]+)"\)', old_item).group(1)
    value = property_value(old_item, "Value")
    nets = pad_nets(old_item)

    item = path.read_text().strip().replace("\n", "\n\t")
    item = item.replace('"F.Cu"', '"B.Cu"').replace('"F.Mask"', '"B.Mask"').replace('"F.Paste"', '"B.Paste"')
    item = item.replace('"F.SilkS"', '"B.SilkS"').replace('"F.Fab"', '"B.Fab"').replace('"F.CrtYd"', '"B.CrtYd"')
    item = mirror_text(item)
    item = set_property(item, "Reference", ref)
    item = set_property(item, "Value", value)
    if ref in {"R17", "R18", "R19"}:
        item = re.sub(
            rf'(\(property "Reference" "{ref}"\s+)\(at [^)]+\)',
            r'\g<1>(at 0 -2 0)', item, count=1,
        )
    layer_end = item.index("\n", item.index('(layer "B.Cu")')) + 1
    item = item[:layer_end] + f'\t\t(uuid "{footprint_uuid}")\n\t\t(at {at})\n' + item[layer_end:]

    for match in reversed(list(re.finditer(r'\(pad "([^"]+)"', item))):
        pin = match.group(1)
        if pin not in nets:
            continue
        end = expression_end(item, match.start())
        pad = item[match.start():end]
        insertion = pad.rfind("\n")
        pad = pad[:insertion] + f'\n\t\t\t(net "{nets[pin]}")' + pad[insertion:]
        item = item[:match.start()] + pad + item[end:]
    return item


sch = SCH.read_text()
if "ivcurve_carrier:Load_2512_HandSolder" in sch:
    assert sch.count("ivcurve_carrier:Load_2512_HandSolder") == 16
    assert sch.count("ivcurve_carrier:R_0805_HandSolder") == 3
    for object_uuid in (
        "5d3aae75-2026-53c0-8968-8485aff443c6",  # J6.1 no-connect
        "99385bf2-6f9c-578e-8e53-3e853365978a",  # SW1
        "6b325b0e-5a9b-5d41-8455-a83d392818cf",  # BUTTON_N wire
        "89f3e061-6737-511e-81c4-1f56a783158b",  # GND wire
        "bbf89bd4-0663-5edc-9b07-2c09300575d5",  # GND label
    ):
        sch = remove_uuid_object(sch, object_uuid)
    button_uuid = "4cc36eb0-67b0-50bd-8941-89dcb1026c74"
    button_at = sch.find(f'(uuid "{button_uuid}")')
    button_start = sch.rfind("\n\t(", 0, button_at) + 2
    button_end = expression_end(sch, button_start)
    button = sch[button_start:button_end].replace("(at 240.03 207.01 0)", "(at 64.77 198.12 0)")
    sch = sch[:button_start] + button + sch[button_end:]
    sch = sch.replace("ivcurve_carrier:Load_2512_HandSolder", "Resistor_SMD:R_1206_3216Metric_Pad1.30x1.75mm_HandSolder")
    sch = sch.replace("ivcurve_carrier:R_0805_HandSolder", "Resistor_SMD:R_0603_1608Metric_Pad0.98x0.95mm_HandSolder")
    SCH.write_text(sch)
else:
    assert sch.count("Resistor_SMD:R_1206_3216Metric_Pad1.30x1.75mm_HandSolder") == 16
    assert sch.count("Resistor_SMD:R_0603_1608Metric_Pad0.98x0.95mm_HandSolder") == 3

pcb = PCB.read_text()
items = footprints(pcb)
assert {*((f"R{i}") for i in range(1, 20)), "J6"} <= set(items)

if "SW1" in items:
    start, end, _ = items["SW1"]
    pcb = pcb[:start] + pcb[end:]
    items = footprints(pcb)

replacements = []
for index in range(1, 20):
    ref = f"R{index}"
    start, end, old_item = items[ref]
    path = LOAD_FP if index <= 16 else SIGNAL_FP
    replacements.append((start, end, make_backside_resistor(path, old_item, ref)))
for start, end, item in sorted(replacements, reverse=True):
    pcb = pcb[:start] + item + pcb[end:]

items = footprints(pcb)
start, end, j6 = items["J6"]
pad = re.search(r'\(pad "1"', j6)
pad_end = expression_end(j6, pad.start())
pad_text = re.sub(r'\n\s*\(net "[^"]+"\)', "", j6[pad.start():pad_end])
insertion = pad_text.rfind("\n")
pad_text = pad_text[:insertion] + '\n\t\t\t(net "/BUTTON_N")' + pad_text[insertion:]
j6 = j6[:pad.start()] + pad_text + j6[pad_end:]
pcb = pcb[:start] + j6 + pcb[end:]

items = footprints(pcb)
start, end, c1 = items["C1"]
for pin, net in (("2", "/GND"), ("1", "/+3V3")):
    pad = re.search(rf'\(pad "{pin}"', c1)
    pad_end = expression_end(c1, pad.start())
    pad_text = re.sub(r'\n\s*\(net "[^"]+"\)', "", c1[pad.start():pad_end])
    insertion = pad_text.rfind("\n")
    pad_text = pad_text[:insertion] + f'\n\t\t\t(net "{net}")' + pad_text[insertion:]
    c1 = c1[:pad.start()] + pad_text + c1[pad_end:]
pcb = pcb[:start] + c1 + pcb[end:]
PCB.write_text(pcb)

final = footprints(pcb)
assert "SW1" not in final
assert all('(layer "B.Cu")' in final[f"R{i}"][2] for i in range(1, 20))
assert pad_nets(final["J6"][2])["1"] == "/BUTTON_N"
assert pad_nets(final["C1"][2]) == {"1": "/+3V3", "2": "/GND"}
print("PASS: J6.1 replaced SW1; 16 load resistors use backside 1206 and R17-R19 use backside 0603")
