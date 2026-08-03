#!/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3
from pathlib import Path
import xml.etree.ElementTree as ET

import pcbnew


ROOT = Path(__file__).resolve().parent.parent
BOARD_PATH = ROOT / "IVcurve-tester-carrier-r0.kicad_pcb"
NETLIST = ROOT / "reports/IVcurve-tester-carrier-r0.net.xml"
LIBRARY = ROOT / "ivcurve_carrier.pretty"

definitions = (
    ("U1", "ADG706_TSSOP-28", "ADG706BRUZ", 120, 54),
    ("C1", "C_0805_HandSolder", "100n", 128, 54),
    ("R19", "R_0805_HandSolder", "1k EN_PULLDOWN", 110, 54),
)
loaders = []

board = pcbnew.LoadBoard(str(BOARD_PATH))
footprints = {fp.GetReference(): fp for fp in board.GetFootprints()}

for track in list(board.GetTracks()):
    board.Remove(track)

for group in list(board.Groups()):
    if group.GetName() in {"ADG706_DAUGHTERBOARD", "ONBOARD_ADG706"}:
        group.RemoveAll()
        board.Remove(group)

for reference in ("J3", "J4"):
    if reference in footprints:
        board.Remove(footprints.pop(reference))

pin_nets = {}
for net in ET.parse(NETLIST).getroot().findall("./nets/net"):
    for node in net.findall("node"):
        pin_nets[(node.get("ref"), node.get("pin"))] = net.get("name")

for reference, library_name, value, x, y in definitions:
    if reference in footprints:
        continue
    loaders.append(pcbnew.PCB_IO_KICAD_SEXPR())
    template = loaders[-1].FootprintLoad(str(LIBRARY), library_name)
    footprint = pcbnew.FOOTPRINT(template)
    footprint.SetReference(reference)
    footprint.SetValue(value)
    footprint.SetPosition(pcbnew.VECTOR2I_MM(x, y))
    for pad in footprint.Pads():
        net_name = pin_nets.get((reference, pad.GetNumber()))
        if net_name:
            pad.SetNet(board.FindNet(net_name))
    board.Add(footprint)
    footprints[reference] = footprint

assert not {"J3", "J4"} & footprints.keys()
assert footprints["U1"].GetPadCount() == 28
expected = {
    "1": "/+3V3", "12": "/GND", "27": "/GND", "28": "/DUT_N",
    "18": "/MUX_EN", "17": "/MUX_A0", "16": "/MUX_A1",
    "15": "/MUX_A2", "14": "/MUX_A3",
}
actual = {pad.GetNumber(): pad.GetNetname() for pad in footprints["U1"].Pads()}
assert all(actual[pin] == net for pin, net in expected.items())

group = pcbnew.PCB_GROUP(board)
group.SetName("ONBOARD_ADG706")
board.Add(group)
for reference in ("U1", "C1", "R19"):
    group.AddItem(footprints[reference])

assert pcbnew.SaveBoard(str(BOARD_PATH), board)
print("PASS: daughterboard headers removed; onboard ADG706 added; stale routes cleared")
