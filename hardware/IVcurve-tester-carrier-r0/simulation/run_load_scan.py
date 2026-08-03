#!/usr/bin/env python3
"""Run iv_load_scan.cir with an installed libngspice shared library."""

from __future__ import annotations

import argparse
import csv
import ctypes
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path


CHANNEL_COUNT = 16
MUX_DESIGN_CURRENT_A = 0.025
MUX_ABSMAX_CURRENT_A = 0.030
ADC_MIN_V = 0.0


class NgComplex(ctypes.Structure):
    _fields_ = [("cx_real", ctypes.c_double), ("cx_imag", ctypes.c_double)]


class VectorInfo(ctypes.Structure):
    _fields_ = [
        ("v_name", ctypes.c_char_p),
        ("v_type", ctypes.c_int),
        ("v_flags", ctypes.c_short),
        ("v_realdata", ctypes.POINTER(ctypes.c_double)),
        ("v_compdata", ctypes.POINTER(NgComplex)),
        ("v_length", ctypes.c_int),
    ]


SEND_CHAR = ctypes.CFUNCTYPE(
    ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p
)
SEND_STAT = ctypes.CFUNCTYPE(
    ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p
)
CONTROLLED_EXIT = ctypes.CFUNCTYPE(
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_bool,
    ctypes.c_bool,
    ctypes.c_int,
    ctypes.c_void_p,
)
BG_THREAD = ctypes.CFUNCTYPE(
    ctypes.c_int, ctypes.c_bool, ctypes.c_int, ctypes.c_void_p
)


@dataclass
class RunConfig:
    corner: str
    ron_ohm: float
    dut_corner: str
    voc_v: float
    source_model: str
    source_mode: int


class SharedNgSpice:
    def __init__(self, library_path: Path) -> None:
        self.messages: list[str] = []
        self.exit_status: int | None = None
        self.lib = ctypes.CDLL(str(library_path))

        def send_char(message: bytes | None, _ident: int, _user: int) -> int:
            if message:
                self.messages.append(message.decode("utf-8", errors="replace"))
            return 0

        def send_stat(message: bytes | None, _ident: int, _user: int) -> int:
            if message:
                self.messages.append(message.decode("utf-8", errors="replace"))
            return 0

        def controlled_exit(
            status: int,
            _immediate: bool,
            _quit_exit: bool,
            _ident: int,
            _user: int,
        ) -> int:
            self.exit_status = status
            return 0

        def bg_thread(_running: bool, _ident: int, _user: int) -> int:
            return 0

        self._callbacks = (
            SEND_CHAR(send_char),
            SEND_STAT(send_stat),
            CONTROLLED_EXIT(controlled_exit),
            BG_THREAD(bg_thread),
        )

        self.lib.ngSpice_Init.argtypes = [ctypes.c_void_p] * 7
        self.lib.ngSpice_Init.restype = ctypes.c_int
        rc = self.lib.ngSpice_Init(
            ctypes.cast(self._callbacks[0], ctypes.c_void_p),
            ctypes.cast(self._callbacks[1], ctypes.c_void_p),
            ctypes.cast(self._callbacks[2], ctypes.c_void_p),
            None,
            None,
            ctypes.cast(self._callbacks[3], ctypes.c_void_p),
            None,
        )
        if rc != 0:
            raise RuntimeError(f"ngSpice_Init returned {rc}")

        self.lib.ngSpice_Command.argtypes = [ctypes.c_char_p]
        self.lib.ngSpice_Command.restype = ctypes.c_int
        self.lib.ngGet_Vec_Info.argtypes = [ctypes.c_char_p]
        self.lib.ngGet_Vec_Info.restype = ctypes.POINTER(VectorInfo)

    def command(self, text: str) -> None:
        message_start = len(self.messages)
        rc = self.lib.ngSpice_Command(text.encode("utf-8"))
        new_messages = "\n".join(self.messages[message_start:])
        reported_error = bool(
            re.search(r"\berror\s*:", new_messages, flags=re.IGNORECASE)
            or re.search(r"command .* skipped", new_messages, flags=re.IGNORECASE)
        )
        if rc != 0 or reported_error:
            tail = "\n".join(self.messages[-20:])
            raise RuntimeError(f"ngspice command failed ({rc}): {text}\n{tail}")

    def value(self, name: str) -> float:
        vector = self.lib.ngGet_Vec_Info(name.encode("ascii"))
        if not vector or vector.contents.v_length < 1:
            raise RuntimeError(f"missing ngspice result vector: {name}")
        if not vector.contents.v_realdata:
            raise RuntimeError(f"non-real ngspice result vector: {name}")
        return float(vector.contents.v_realdata[0])


def find_library(explicit: str | None) -> Path:
    candidates = [
        explicit,
        os.environ.get("NGSPICE_LIB"),
        "/Applications/KiCad/KiCad.app/Contents/Frameworks/libngspice.0.dylib",
        "/Applications/KiCad/KiCad.app/Contents/PlugIns/sim/libngspice.0.dylib",
        "/opt/homebrew/lib/libngspice.dylib",
        "/usr/local/lib/libngspice.dylib",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate).resolve()
    raise FileNotFoundError(
        "No libngspice found. Set NGSPICE_LIB or pass --libngspice."
    )


def spice_number(token: str) -> float:
    match = re.fullmatch(
        r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)"
        r"(meg|[tgkmunpf])?",
        token.strip(),
        flags=re.IGNORECASE,
    )
    if not match:
        raise ValueError(f"unsupported SPICE number: {token}")
    scale = {
        None: 1.0,
        "t": 1e12,
        "g": 1e9,
        "meg": 1e6,
        "k": 1e3,
        "m": 1e-3,
        "u": 1e-6,
        "n": 1e-9,
        "p": 1e-12,
        "f": 1e-15,
    }[match.group(2).lower() if match.group(2) else None]
    return float(match.group(1)) * scale


def read_parameter(deck: str, name: str) -> float:
    match = re.search(
        rf"^\s*\.param\s+{re.escape(name)}\s*=\s*([^\s*]+)",
        deck,
        flags=re.MULTILINE | re.IGNORECASE,
    )
    if not match:
        raise ValueError(f"missing .param {name} in deck")
    return spice_number(match.group(1))


def run_case(
    ng: SharedNgSpice,
    config: RunConfig,
    load_values: list[float],
    rsrc_ohm: float,
    adc_supply_v: float,
    resistor_rating_w: float,
) -> list[dict[str, object]]:
    # ngspice's alterparam lookup is case-sensitive and normalizes .param names
    # to lower case when the deck is parsed.
    ng.command(f"alterparam ron={config.ron_ohm:.12g}")
    ng.command(f"alterparam voc={config.voc_v:.12g}")
    ng.command(f"alterparam source_mode={config.source_mode}")
    ng.command("reset")
    ng.command("op")

    rows: list[dict[str, object]] = []
    for channel, load_ohm in enumerate(load_values):
        vdut = ng.value(f"v(dut{channel})")
        vadc = ng.value(f"v(adc{channel})")
        current = abs(ng.value(f"i(vmeas{channel})"))
        analytic_current = config.voc_v / (
            rsrc_ohm + load_ohm + config.ron_ohm
        )
        current_delta_fraction = abs(current - analytic_current) / analytic_current
        # The ADC's finite 10 Mohm input causes a small expected deviation.  A
        # larger error usually means a requested corner was not applied.
        if current_delta_fraction > 1e-4:
            raise RuntimeError(
                f"channel {channel} {config.dut_corner}/{config.corner}/"
                f"{config.source_model}: simulated current {current:.12g} A "
                f"does not match analytic corner {analytic_current:.12g} A"
            )
        p_dut = vdut * current
        p_resistor = current * current * load_ohm
        p_mux = current * current * config.ron_ohm
        mux_design_pass = current <= MUX_DESIGN_CURRENT_A + 1e-12
        mux_absmax_pass = current <= MUX_ABSMAX_CURRENT_A + 1e-12
        adc_pass = ADC_MIN_V - 1e-6 <= vadc <= adc_supply_v + 1e-6
        resistor_pass = p_resistor <= resistor_rating_w + 1e-12
        rows.append(
            {
                "corner": config.corner,
                "dut_corner": config.dut_corner,
                "source_model": config.source_model,
                "channel": channel,
                "mux_input": f"S{channel + 1}",
                "load_ohm": load_ohm,
                "ron_ohm": config.ron_ohm,
                "voc_v": config.voc_v,
                "rsrc_ohm": rsrc_ohm,
                "vdut_v": vdut,
                "vadc_v": vadc,
                "load_current_a": current,
                "analytic_current_a": analytic_current,
                "current_model_delta_pct": current_delta_fraction * 100.0,
                "dut_power_w": p_dut,
                "resistor_power_w": p_resistor,
                "mux_power_w": p_mux,
                "mux_25ma_design_gate": "PASS" if mux_design_pass else "FAIL",
                "mux_30ma_absmax_gate": "PASS" if mux_absmax_pass else "FAIL",
                "adc_0_to_3v3_gate": "PASS" if adc_pass else "FAIL",
                "resistor_power_gate": "PASS" if resistor_pass else "FAIL",
                "all_design_gates": "PASS"
                if mux_design_pass and adc_pass and resistor_pass
                else "FAIL",
                "all_absmax_gates": "PASS"
                if mux_absmax_pass and adc_pass and resistor_pass
                else "FAIL",
            }
        )
    return rows


def main() -> int:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--deck", default=str(here / "iv_load_scan.cir"))
    parser.add_argument("--output", default=str(here / "results/load_scan_results.csv"))
    parser.add_argument("--libngspice")
    parser.add_argument(
        "--voc-corners",
        nargs="+",
        type=float,
        default=[0.9, 3.3],
        help="DUT open-circuit voltage corners in volts",
    )
    args = parser.parse_args()

    deck_path = Path(args.deck).resolve()
    deck_text = deck_path.read_text(encoding="utf-8")
    load_values = [read_parameter(deck_text, f"RCH{i}") for i in range(CHANNEL_COUNT)]
    default_voc_v = read_parameter(deck_text, "VOC")
    rsrc_ohm = read_parameter(deck_text, "RSRC")
    adc_supply_v = read_parameter(deck_text, "VADC_SUPPLY")
    resistor_rating_w = read_parameter(deck_text, "RESISTOR_RATING")

    library_path = find_library(args.libngspice)
    ng = SharedNgSpice(library_path)
    ng.command("set nomoremode")
    ng.command(f"source {deck_path}")

    dut_cases = [(f"{voltage:g}".replace(".", "v"), voltage) for voltage in args.voc_corners]
    configs = [
        RunConfig(ron_corner, ron_ohm, dut_corner, voc_v, source_model, source_mode)
        for dut_corner, voc_v in dut_cases
        for ron_corner, ron_ohm in (("typ", 6.0), ("max", 12.0))
        for source_model, source_mode in (("thevenin", 0), ("norton", 1))
    ]
    rows: list[dict[str, object]] = []
    for config in configs:
        rows.extend(
            run_case(
                ng,
                config,
                load_values,
                rsrc_ohm,
                adc_supply_v,
                resistor_rating_w,
            )
        )

    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    grouped: dict[tuple[str, str, str], list[dict[str, object]]] = {}
    for row in rows:
        grouped.setdefault(
            (
                str(row["dut_corner"]),
                str(row["corner"]),
                str(row["source_model"]),
            ),
            [],
        ).append(row)

    print(f"engine_library={library_path}")
    print(f"deck={deck_path}")
    print(f"result={output_path}")
    print(
        f"assumptions: default VOC={default_voc_v:g} V; simulated VOC="
        f"{'/'.join(f'{voltage:g}' for _, voltage in dut_cases)} V; "
        f"RSRC={rsrc_ohm:g} ohm, "
        f"ADC rail={adc_supply_v:g} V, resistor rating={resistor_rating_w:g} W"
    )
    for key, group in grouped.items():
        over_25ma = [row for row in group if row["mux_25ma_design_gate"] == "FAIL"]
        over_30ma = [row for row in group if row["mux_30ma_absmax_gate"] == "FAIL"]
        over_power = [row for row in group if row["resistor_power_gate"] == "FAIL"]
        peak_current = max(float(row["load_current_a"]) for row in group)
        peak_power = max(float(row["resistor_power_w"]) for row in group)
        print(
            f"{key[0]:>3} {key[1]:>3} {key[2]:>8}: "
            f">25mA={','.join(str(row['channel']) for row in over_25ma) or 'none'}; "
            f">30mA={','.join(str(row['channel']) for row in over_30ma) or 'none'}; "
            f">resistor_rating={','.join(str(row['channel']) for row in over_power) or 'none'}; "
            f"peak_current={peak_current * 1000:.3f} mA; "
            f"peak_resistor_power={peak_power * 1000:.3f} mW"
        )

    for dut_corner, _voltage in dut_cases:
        for corner in ("typ", "max"):
            thevenin = [
                row
                for row in rows
                if row["dut_corner"] == dut_corner
                and row["corner"] == corner
                and row["source_model"] == "thevenin"
            ]
            norton = [
                row
                for row in rows
                if row["dut_corner"] == dut_corner
                and row["corner"] == corner
                and row["source_model"] == "norton"
            ]
            max_error = max(
                abs(float(a["vdut_v"]) - float(b["vdut_v"]))
                for a, b in zip(thevenin, norton)
            )
            print(
                f"{dut_corner:>3} {corner:>3} Thevenin/Norton "
                f"max |delta Vdut|={max_error:.3e} V"
            )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(2)
