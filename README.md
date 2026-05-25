# AXI4-Stream Compliance Checker — Claude Skill

A Claude skill that reviews Verilog / SystemVerilog RTL against the ARM AXI4-Stream
specification (IHI0051B) and produces a structured compliance report.

---

## What it does

Paste or upload your AXI4-Stream RTL and get:

- 🔴 **CRITICAL** — Direct spec violations that cause data loss or functional failure
- 🟡 **WARNING** — Non-recommended patterns that risk interoperability issues
- 🔵 **INFO** — Observations and best-practice suggestions
- ✅ **Corrected code snippets** for every CRITICAL finding
- 📋 **SVA assertion templates** ready to drop into your testbench

---

## Coverage — 25 rules across 8 categories

| Category | Rules | Examples |
|----------|-------|---------|
| **H** Handshake | 4 | TVALID stickiness; Master must not gate TVALID on TREADY |
| **R** Reset | 4 | TVALID=0 after reset; ARESETn polarity; consistent reset style |
| **S** Signal Stability | 2 | All payload signals stable while TVALID=1 & TREADY=0 |
| **W** Signal Widths | 6 | TDATA must be multiple of 8; TKEEP = TDATA/8; TID ≤ 8-bit |
| **K** TKEEP / TSTRB | 4 | No null bytes mid-packet; TSTRB must be subset of TKEEP |
| **L** TLAST / Framing | 4 | TID/TDEST must not change mid-packet; TLAST not tied LOW |
| **C** Combinatorial | 2 | TVALID must not combinatorially depend on TREADY |
| **X** Optional Signals | 3 | Missing TKEEP on wide bus; TUSER width alignment |

---

## How to use

### Install the skill

Download [`axi4-stream-compliance.skill`](./axi4-stream-compliance.skill) and
install it in Claude (Settings → Skills → Install from file).

### Trigger it

Just paste your RTL and ask:

```
Check this AXI4-Stream master for protocol compliance:

module axis_master (
  input  wire        ACLK, ARESETn,
  output reg         TVALID,
  input  wire        TREADY,
  output reg  [31:0] TDATA,
  output reg         TLAST
);
...
```

Claude will detect AXI4-Stream signals automatically and run the full compliance check.

---

## File structure

```
axi4-stream-compliance/
├── SKILL.md                        # Skill entry point & workflow
├── scripts/
│   └── extract_signals.py          # Extracts signal widths from RTL files
├── references/
│   ├── protocol-rules.md           # Full rule catalogue with ARM spec references
│   ├── common-violations.md        # 11 annotated anti-patterns with ❌/✅ code
│   └── report-template.md          # Report format + SVA assertion templates
└── evals/
    └── evals.json                  # 4 test cases (compliant + violating RTL)
```

---

## Example output

```
## AXI4-Stream Compliance Report

### Interface Summary
- Role: Master | Language: SystemVerilog
- Signals: TVALID, TREADY, TDATA[31:0], TKEEP[3:0], TLAST
- Reset: Async active-low (ARESETn)

### Findings

#### 🔴 CRITICAL — 1 issue

[C-1] Rule H1 — TVALID Deasserted Without Handshake
- Location: axis_master.sv, line 42 (SEND state)
- What's wrong: TVALID is cleared unconditionally without checking TREADY.
  The slave may miss the transfer entirely.
- Fix: only clear TVALID when (TVALID & TREADY) is true.

### Overall Assessment: ❌ FAIL
```

---

## Roadmap

- [ ] AXI4-Lite compliance checker
- [ ] AXI4 Full (memory-mapped) compliance checker
- [ ] Multi-file / top-level SoC review mode

---

## License

MIT — use freely, contributions welcome.

*Based on ARM AMBA AXI-Stream Protocol Specification IHI0051B.*
