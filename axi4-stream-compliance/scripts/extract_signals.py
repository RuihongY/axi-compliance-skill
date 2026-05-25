#!/usr/bin/env python3
"""
extract_signals.py — AXI4-Stream signal extractor for RTL files
Usage: python3 extract_signals.py <file.v|file.sv>

Outputs a structured JSON report of all detected AXI4-Stream signals,
their widths, direction, and reset style. Claude reads this before
running the compliance checks so it doesn't have to parse RTL manually.
"""

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
    r'\bparameter\b\s+(?:integer\s+)?(\w+)\s*=\s*(\d+)',
    re.IGNORECASE
)

RESET_ASYNC_RE = re.compile(
    r'always\s*@\s*\([^)]*negedge\s+\w*reset\w*',
    re.IGNORECASE
)
RESET_SYNC_RE = re.compile(
    r'always\s*@\s*\(\s*posedge\s+\w*clk\w*\s*\)',
    re.IGNORECASE
)
RESET_HIGH_RE = re.compile(
    r'if\s*\(\s*(?:ARESETN|ARESETn|resetn|rst_n)\s*\)',
    re.IGNORECASE
)
RESET_LOW_RE = re.compile(
    r'if\s*\(\s*!\s*(?:ARESETN|ARESETn|resetn|rst_n)\s*\)',
    re.IGNORECASE
)

TVALID_CLEARED_RE = re.compile(
    r'TVALID\s*<=\s*1\'b0',
    re.IGNORECASE
)

TVALID_IN_RESET_RE = re.compile(
    r'(?:ARESETN|ARESETn|resetn|rst_n)[^;]*\n[^;]*TVALID\s*<=\s*1\'b0',
    re.IGNORECASE | re.DOTALL
)


def resolve_width(expr: str, params: dict) -> int | None:
    """Try to evaluate a width expression like 'DATA_WIDTH-1:0' → width."""
    if expr is None:
        return 1
    # Simple N:0 pattern
    m = re.match(r'(\d+)\s*:\s*0', expr.strip())
    if m:
        return int(m.group(1)) + 1
    # Param-based: DATA_WIDTH-1:0
    m = re.match(r'(\w+)\s*-\s*1\s*:\s*0', expr.strip())
    if m and m.group(1) in params:
        return params[m.group(1)]
    # Param/8-1:0 → means TDATA_WIDTH/8
    m = re.match(r'(\w+)\s*/\s*8\s*-\s*1\s*:\s*0', expr.strip())
    if m and m.group(1) in params:
        return params[m.group(1)] // 8
    return None  # unknown


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

    src = path.read_text(errors="replace")

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
    active_high= bool(RESET_HIGH_RE.search(src)) and not active_low

    # --- TVALID reset check ---
    tvalid_cleared_in_reset = bool(TVALID_IN_RESET_RE.search(src))

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
    if tdata_width and tkeep_width:
        tkeep_ok = (tkeep_width == tdata_width // 8)

    # --- Build report ---
    report = {
        "file": str(path),
        "language": "SystemVerilog" if path.suffix == ".sv" else "Verilog",
        "parameters": params,
        "axis_signals": signals,
        "reset": {
            "style": "async" if has_async else ("sync" if has_sync else "unknown"),
            "polarity": "active_low" if active_low else ("active_high" if active_high else "unknown"),
            "tvalid_cleared_in_reset": tvalid_cleared_in_reset,
        },
        "quick_checks": {
            "tdata_width": tdata_width,
            "tdata_byte_aligned": tdata_ok,
            "tkeep_width": tkeep_width,
            "tkeep_matches_tdata_bytes": tkeep_ok,
        },
        "notes": [],
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
    if not tvalid_cleared_in_reset and "TVALID" in signals:
        report["notes"].append(
            "POSSIBLE R1: TVALID does not appear to be cleared in reset block — verify manually"
        )
    if active_high:
        report["notes"].append(
            "WARNING R2: Reset appears active-HIGH — AXI4-Stream requires active-low ARESETn"
        )

    return report


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 extract_signals.py <file.v|file.sv>")
        sys.exit(1)
    result = analyze(sys.argv[1])
    print(json.dumps(result, indent=2))
