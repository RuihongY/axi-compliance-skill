#!/usr/bin/env python3
"""
extract_signals.py — AXI4-Lite signal extractor for RTL files
Usage: python3 extract_signals.py <file.v|file.sv>

Detects which of the 5 AXI4-Lite channels (AW, W, B, AR, R) are present,
reports signal widths, flags non-Lite (Full AXI) signals, and runs quick
compliance checks (data width, PROT/RESP widths, WSTRB sizing).
"""

from __future__ import annotations

import re
import sys
import json
from pathlib import Path

# AXI4-Lite signals organized by channel
LITE_SIGNALS = {
    "AW": ["AWVALID", "AWREADY", "AWADDR", "AWPROT"],
    "W":  ["WVALID",  "WREADY",  "WDATA",  "WSTRB"],
    "B":  ["BVALID",  "BREADY",  "BRESP"],
    "AR": ["ARVALID", "ARREADY", "ARADDR", "ARPROT"],
    "R":  ["RVALID",  "RREADY",  "RDATA",  "RRESP"],
}

# Full AXI4 signals that must NOT be on a Lite interface
NON_LITE_SIGNALS = [
    "AWLEN", "AWSIZE", "AWBURST", "AWLOCK", "AWCACHE", "AWQOS", "AWREGION", "AWID",
    "ARLEN", "ARSIZE", "ARBURST", "ARLOCK", "ARCACHE", "ARQOS", "ARREGION", "ARID",
    "WLAST", "WID", "BID", "RLAST", "RID",
]

ALL_LITE = [s for ch in LITE_SIGNALS.values() for s in ch]

PORT_RE = re.compile(
    r'\b(input|output|inout)\s+'
    r'(?:wire|reg|logic)?\s*'
    r'(?:\[([^\]]+)\])?\s*'
    r'(\w+)',
    re.IGNORECASE
)
PARAM_RE = re.compile(
    r'\bparameter\b\s+(?:integer\s+)?(\w+)\s*=\s*([0-9]+)\s*(?=[,;)])',
    re.IGNORECASE
)
RESET_ASYNC_RE = re.compile(r'always(?:_ff)?\s*@\s*\([^)]*negedge\s+\w*reset\w*', re.IGNORECASE)
RESET_SYNC_RE  = re.compile(r'always(?:_ff)?\s*@\s*\(\s*posedge\s+\w*clk\w*\s*\)', re.IGNORECASE)
RESET_LOW_RE   = re.compile(r'if\s*\(\s*!\s*(?:ARESETN|ARESETn|resetn|rst_n|rstn)\s*\)', re.IGNORECASE)


def resolve_width(expr, params):
    """Resolve simple packed ranges conservatively; unsupported bounds stay unknown."""
    if expr is None:
        return 1

    def bound(value):
        value = value.strip()
        if re.fullmatch(r"[0-9]+", value):
            return int(value)
        if value in params:
            return params[value]
        match = re.fullmatch(r"([A-Za-z_][A-Za-z_0-9]*)(?:\s*/\s*([1-9][0-9]*))?\s*-\s*1", value)
        if match and match[1] in params:
            return params[match[1]] // int(match[2] or 1) - 1
        return None

    parts = expr.split(":")
    if len(parts) != 2:
        return None
    msb, lsb = map(bound, parts)
    return abs(msb - lsb) + 1 if msb is not None and lsb is not None else None


def strip_comments(src):
    """Hide comments and strings without changing line offsets."""
    return re.sub(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"',
                  lambda m: re.sub(r"[^\n]", " ", m[0]), src, flags=re.S)


def canonical_name(name):
    """Return canonical AXI-Lite signal name if `name` matches any variant.
    Handles prefixes like s_axi_, m_axi_, s00_axi_, etc."""
    upper = name.upper()
    for canonical in ALL_LITE + NON_LITE_SIGNALS:
        if upper == canonical:
            return canonical
        # Trailing match: e.g. S_AXI_AWVALID → AWVALID
        if upper.endswith("_" + canonical):
            return canonical
        # Leading match: e.g. AWVALID_M0 → AWVALID
        if upper.startswith(canonical + "_"):
            return canonical
    return None


def analyze(filepath):
    path = Path(filepath)
    if not path.exists():
        return {"error": f"File not found: {filepath}"}
    try:
        src = strip_comments(path.read_text(errors="replace"))
    except OSError as exc:
        return {"error": f"Cannot read {filepath}: {exc}"}

    # Parameters
    params = {}
    for m in PARAM_RE.finditer(src):
        params[m.group(1)] = int(m.group(2))

    # Signals (group by channel)
    channels = {ch: {} for ch in LITE_SIGNALS}
    full_axi_intrusions = {}

    for m in PORT_RE.finditer(src):
        direction, width_expr, name = m.group(1), m.group(2), m.group(3)
        canonical = canonical_name(name)
        if not canonical:
            continue
        width = resolve_width(width_expr, params)
        info = {
            "raw_name": name,
            "direction": direction.lower(),
            "width": width,
            "width_expr": width_expr,
        }
        if canonical in NON_LITE_SIGNALS:
            full_axi_intrusions[canonical] = info
        else:
            for ch, sigs in LITE_SIGNALS.items():
                if canonical in sigs:
                    channels[ch][canonical] = info
                    break

    # Reset style
    has_async = bool(RESET_ASYNC_RE.search(src))
    has_sync  = bool(RESET_SYNC_RE.search(src))
    active_low  = bool(RESET_LOW_RE.search(src))

    # Determine implemented channels (need at least VALID + READY for the channel)
    implemented = []
    for ch, sigs in channels.items():
        valid_sig = f"{ch}VALID" if ch != "AR" else "ARVALID"
        ready_sig = f"{ch}READY" if ch != "AR" else "ARREADY"
        if valid_sig in sigs and ready_sig in sigs:
            implemented.append(ch)

    # Slave or master? If the slave owns BVALID/AWREADY, etc.
    role = "unknown"
    if "AW" in implemented and "AWVALID" in channels["AW"]:
        awvalid_dir = channels["AW"]["AWVALID"]["direction"]
        if awvalid_dir == "input":
            role = "slave"
        elif awvalid_dir == "output":
            role = "master"

    # Data width (from WDATA or RDATA)
    data_w = None
    if "WDATA" in channels["W"]:  data_w = channels["W"]["WDATA"]["width"]
    if data_w is None and "RDATA" in channels["R"]:
        data_w = channels["R"]["RDATA"]["width"]

    # Quick checks
    notes = ["Heuristic inventory only: confirm grouped declarations, module/interface boundaries, parameters, and reset behavior manually."]
    if data_w is not None and data_w not in (32, 64):
        notes.append(f"CRITICAL W1: DATA width={data_w}, must be 32 or 64 for AXI4-Lite")

    if "WSTRB" in channels["W"]:
        wstrb_w = channels["W"]["WSTRB"]["width"]
        if data_w and wstrb_w and wstrb_w != data_w // 8:
            notes.append(f"CRITICAL W2: WSTRB width={wstrb_w}, should be {data_w//8}")

    for prot_sig, ch in [("AWPROT", "AW"), ("ARPROT", "AR")]:
        if prot_sig in channels[ch]:
            w = channels[ch][prot_sig]["width"]
            if w is not None and w != 3:
                notes.append(f"CRITICAL W3: {prot_sig} width={w}, must be 3 bits")

    for resp_sig, ch in [("BRESP", "B"), ("RRESP", "R")]:
        if resp_sig in channels[ch]:
            w = channels[ch][resp_sig]["width"]
            if w is not None and w != 2:
                notes.append(f"CRITICAL W4: {resp_sig} width={w}, must be 2 bits")

    if full_axi_intrusions:
        sigs = ", ".join(full_axi_intrusions.keys())
        notes.append(f"INFO X1: Extended AXI signals present ({sigs}); classify the interface and check ID reflection/bridge constraints manually")


    return {
        "file": str(path),
        "language": "SystemVerilog" if path.suffix == ".sv" else "Verilog",
        "parameters": params,
        "role": role,
        "channels_implemented": implemented,
        "channels": channels,
        "full_axi_intrusions": full_axi_intrusions,
        "reset": {
            "style": "async" if has_async else ("sync" if has_sync else "unknown"),
            "polarity": "active_low" if active_low else "unknown",
        },
        "quick_checks": {
            "data_width": data_w,
            "data_width_compliant": data_w in (32, 64) if data_w else None,
        },
        "notes": notes,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 extract_signals.py <file.v|file.sv>")
        sys.exit(1)
    result = analyze(sys.argv[1])
    print(json.dumps(result, indent=2))
    sys.exit(1 if "error" in result else 0)
