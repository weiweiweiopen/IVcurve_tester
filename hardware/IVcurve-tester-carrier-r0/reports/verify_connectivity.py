#!/usr/bin/env python3
import sys
import xml.etree.ElementTree as ET


def nodes(net):
    return {(node.attrib["ref"], node.attrib["pin"]) for node in net.findall("node")}


root = ET.parse(sys.argv[1] if len(sys.argv) > 1 else "IVcurve-tester-carrier-r0.net.xml").getroot()
nets = {net.attrib["name"].removeprefix("/"): nodes(net) for net in root.findall("./nets/net")}

assert nets["DUT_P"] == {("J8", "1"), ("R17", "1")} | {
    (f"R{i}", "1") for i in range(1, 17)
}
assert nets["DUT_N"] == {("U1", "28"), ("J5", "2"), ("J8", "2"), ("R18", "1")}
assert nets["ADC_VIN"] == {("J5", "7"), ("R17", "2")}

mux_pins = [19, 20, 21, 22, 23, 24, 25, 26, 11, 10, 9, 8, 7, 6, 5, 4]
for i, pin in enumerate(mux_pins, 1):
    assert nets[f"MUX_S{i}"] == {("U1", str(pin)), (f"R{i}", "2")}

expected = {
    "MUX_A0": {("J1", "16"), ("U1", "17")},
    "MUX_A1": {("J1", "15"), ("U1", "16")},
    "MUX_A2": {("J1", "1"), ("U1", "15")},
    "MUX_A3": {("J1", "6"), ("U1", "14")},
    "MUX_EN": {("J1", "7"), ("U1", "18"), ("R19", "1")},
    "I2C_SDA": {("J1", "4"), ("J5", "4")},
    "I2C_SCL": {("J1", "5"), ("J5", "3")},
    "BUTTON_N": {("J1", "8"), ("J6", "1")},
    "EPD_SCLK": {("J1", "12"), ("J6", "11")},
    "EPD_MOSI": {("J1", "2"), ("J6", "12")},
    "EPD_CS_N": {("J1", "3"), ("J7", "5")},
    "EPD_DC": {("J1", "13"), ("J7", "6")},
}
for name, expected_nodes in expected.items():
    assert nets[name] == expected_nodes

assert {("U1", "1"), ("C1", "1")} <= nets["+3V3"]
assert {("U1", "12"), ("U1", "27"), ("C1", "2"), ("R19", "2")} <= nets["GND"]

components = root.findall("./components/comp")
missing = [comp.attrib["ref"] for comp in components if not comp.findtext("footprint")]
print("PASS: 16 load paths, DUT polarity, ADC sense, C3 MUX/I2C/e-ink, and button nets match")
print(f"BLOCKED: {len(missing)} components have no footprint: {' '.join(missing)}")
