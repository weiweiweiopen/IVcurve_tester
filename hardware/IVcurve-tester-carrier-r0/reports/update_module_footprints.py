#!/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3
from pathlib import Path
import xml.etree.ElementTree as ET

import pcbnew


ROOT = Path(__file__).resolve().parent.parent
BOARD_PATH = ROOT / "IVcurve-tester-carrier-r0.kicad_pcb"
NETLIST = ROOT / "reports/IVcurve-tester-carrier-r0.net.xml"
LIBRARY = ROOT / "ivcurve_carrier.pretty"
loaders = [pcbnew.PCB_IO_KICAD_SEXPR(), pcbnew.PCB_IO_KICAD_SEXPR()]
templates = {
    "ESP32-C3_SuperMini_2x08": loaders[0].FootprintLoad(str(LIBRARY), "ESP32-C3_SuperMini_2x08"),
    "GY-ADS1115_1x10_Socket": loaders[1].FootprintLoad(str(LIBRARY), "GY-ADS1115_1x10_Socket"),
}

board = pcbnew.LoadBoard(str(BOARD_PATH))
footprints = {fp.GetReference(): fp for fp in board.GetFootprints()}

for group in list(board.Groups()):
    if group.GetName() in {"LOLIN_S3_MINI", "ESP32-C3_SUPER_MINI"}:
        group.RemoveAll()
        board.Remove(group)

def replace(reference, library_name, value):
    old = footprints.pop(reference)
    position, orientation = old.GetPosition(), old.GetOrientation()
    board.Remove(old)
    new = pcbnew.FOOTPRINT(templates[library_name])
    assert new is not None, library_name
    new.SetReference(reference)
    new.SetValue(value)
    new.SetPosition(position)
    new.SetOrientation(orientation)
    board.Add(new)
    footprints[reference] = new
    return new


if "J2" in footprints:
    board.Remove(footprints.pop("J2"))
controller = replace("J1", "ESP32-C3_SuperMini_2x08", "ESP32-C3_SUPER_MINI")
replace("J5", "GY-ADS1115_1x10_Socket", "GY-ADS1115_MODULE_0x48")
footprints = {fp.GetReference(): fp for fp in board.GetFootprints()}

pin_nets = {}
for net in ET.parse(NETLIST).getroot().findall("./nets/net"):
    for node in net.findall("node"):
        pin_nets[(node.get("ref"), node.get("pin"))] = net.get("name")
for footprint in footprints.values():
    for pad in footprint.Pads():
        net_name = pin_nets.get((footprint.GetReference(), pad.GetNumber()))
        if net_name:
            pad.SetNet(board.FindNet(net_name))

group = pcbnew.PCB_GROUP(board)
group.SetName("ESP32-C3_SUPER_MINI")
board.Add(group)
group.AddItem(footprints["J1"])
pcbnew.SaveBoard(str(BOARD_PATH), board)

check = pcbnew.LoadBoard(str(BOARD_PATH))
refs = {fp.GetReference(): fp for fp in check.GetFootprints()}
assert "J2" not in refs
assert refs["J1"].GetFPID().GetLibItemName() == "ESP32-C3_SuperMini_2x08"
assert refs["J5"].GetFPID().GetLibItemName() == "GY-ADS1115_1x10_Socket"
assert refs["J1"].GetPadCount() == 16 and refs["J5"].GetPadCount() == 10
assert {pad.GetNetname() for pad in refs["J1"].Pads() if pad.GetNetname()} >= {
    "/MUX_A0", "/MUX_A1", "/MUX_A2", "/MUX_A3", "/MUX_EN",
    "/I2C_SDA", "/I2C_SCL", "/EPD_SCLK", "/EPD_MOSI", "/EPD_CS_N",
    "/EPD_DC", "/BUTTON_N", "/+3V3", "/GND",
}
print("PASS: PCB uses ESP32-C3 Super Mini and GY-ADS1115 footprints with schematic nets")
