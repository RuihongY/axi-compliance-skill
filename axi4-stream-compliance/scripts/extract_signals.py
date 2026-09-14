#!/usr/bin/env python3
"""
extract_signals.py — AXI4-Stream signal extractor for RTL files
Usage: python3 extract_signals.py <file.v|file.sv>

Outputs a structured JSON report of all detected AXI4-Stream signals,
their widths, direction, and reset style. Claude reads this before
running the compliance checks so it doesn't have to parse RTL manually.
"""

from __future__ import annotations

import re
import sys
import json
from pathlib import Path

# Known AXI4-Stream signal names (canonical + common variants)
AXIS_SIGNALS = {
    "TVALID", "TREADY", "TDATA", "TLAST",
    "TKEEP", "TSTRB", "TUSER", "TID", "TDEST",
    "ACLK", "ARESETN", "ARESETn",
    # prefixed variants (m_axis_*, s_axis_*, m_tvalid, etc.)
}

# Regex patterns
PORT_RE = re.compile(
    r'\b(input|output|inout)\s+'          # direction
    r'(?:wire|reg|logic)?\s*'             # optional type
    r'(?:\[([^\]]+)\])?\s*'              # optional width [MSB:LSB]
    r'(\w+)',                             # signal name
    re.IGNORECASE
)

PARAM_RE = re.compile(
    r'\bparameter\b\s+(?:integer\s+)?(\w+)\s*=\s*([0-9]+)\s*(?=[,;)])',
    re.IGNORECASE
)

RESET_ASYNC_RE = re.compile(
    r'always(?:_ff)?\s*@\s*\([^)]*negedge\s+\w*reset\w*',
    re.IGNORECASE
)
RESET_SYNC_RE = re.compile(
    r'always(?:_ff)?\s*@\s*\(\s*posedge\s+\w*clk\w*\s*\)',
    re.IGNORECASE
)
RESET_LOW_RE = re.compile(
    r'if\s*\(\s*!\s*(?:ARESETN|ARESETn|resetn|rst_n)\s*\)',
    re.IGNORECASE
)




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


def is_axis_signal(name: str) -> bool:
    upper = name.upper()
    for s in AXIS_SIGNALS:
        if upper == s.upper() or upper.endswith("_" + s.upper()) or upper.startswith(s.upper() + "_"):
            return True
    return False


def analyze(filepath: str) -> dict:
    path = Path(filepath)
    if not path.exists():
        return {"error": f"File not found: {filepath}"}

    try:
        src = strip_comments(path.read_text(errors="replace"))
    except OSError as exc:
        return {"error": f"Cannot read {filepath}: {exc}"}

    # --- Parameters ---
    params = {}
    for m in PARAM_RE.finditer(src):
        params[m.group(1)] = int(m.group(2))

    # --- Ports ---
    signals = {}
    for m in PORT_RE.finditer(src):
        direction, width_expr, name = m.group(1), m.group(2), m.group(3)
        if not is_axis_signal(name):
            continue
        width = resolve_width(width_expr, params)
        signals[name] = {
            "direction": direction.lower(),
            "width": width,
            "width_expr": width_expr,
        }

    # --- Reset style ---
    has_async  = bool(RESET_ASYNC_RE.search(src))
    has_sync   = bool(RESET_SYNC_RE.search(src))
    active_low = bool(RESET_LOW_RE.search(src))

    # --- TVALID reset check ---
    tvalid_cleared_in_reset = None  # Requires branch/state analysis, not regex

    # --- TDATA width compliance ---
    tdata_width = None
    tkeep_width = None
    for name, info in signals.items():
        if name.upper() in ("TDATA",) or name.upper().endswith("_TDATA"):
            tdata_width = info["width"]
        if name.upper() in ("TKEEP",) or name.upper().endswith("_TKEEP"):
            tkeep_width = info["width"]

    tdata_ok = None
    if tdata_width:
        tdata_ok = (tdata_width % 8 == 0)

    tkeep_ok = None
    if tdata_ok and tkeep_width:
        tkeep_ok = (tkeep_width == tdata_width // 8)

    # --- Build report ---
    report = {
        "file": str(path),
        "language": "SystemVerilog" if path.suffix == ".sv" else "Verilog",
        "parameters": params,
        "axis_signals": signals,
        "reset": {
            "style": "async" if has_async else ("sync" if has_sync else "unknown"),
            "polarity": "active_low" if active_low else "unknown",
            "tvalid_cleared_in_reset": tvalid_cleared_in_reset,
        },
        "quick_checks": {
            "tdata_width": tdata_width,
            "tdata_byte_aligned": tdata_ok,
            "tkeep_width": tkeep_width,
            "tkeep_matches_tdata_bytes": tkeep_ok,
        },
        "notes": ["Heuristic inventory only: confirm grouped declarations, module/interface boundaries, parameters, and reset behavior manually."],
    }

    # Quick-check notes
    if tdata_ok is False:
        report["notes"].append(
            f"CRITICAL W1: TDATA width={tdata_width} is not a multiple of 8"
        )
    if tkeep_ok is False:
        report["notes"].append(
            f"CRITICAL W2: TKEEP width={tkeep_width} should be {tdata_width}//8={tdata_width//8 if tdata_width else '?'}"
        )

    return report


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 extract_signals.py <file.v|file.sv>")
        sys.exit(1)
    result = analyze(sys.argv[1])
    print(json.dumps(result, indent=2))
    sys.exit(1 if "error" in result else 0)
