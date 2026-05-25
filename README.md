# AXI4-Stream Compliance Checker — Claude Skill

> 🔴 **Open-source alternative to $100K/year commercial EDA tools (JasperGold / SpyGlass)**  
> A Claude skill that reviews Verilog / SystemVerilog RTL against the ARM AXI4-Stream specification (IHI0051).

---

## What it does

Paste or upload your AXI4-Stream RTL and get a structured compliance report:

- 🔴 **CRITICAL** — Direct spec violations causing data loss or functional failure  
- 🟡 **WARNING** — Non-recommended patterns causing interoperability issues  
- 🔵 **INFO** — Observations and best-practice suggestions  
- ✅ **Corrected code snippets** for every CRITICAL finding  
- 📋 **SVA assertion templates** you can drop into your testbench

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

Download [`axi4-stream-compliance.skill`](./axi4-stream-compliance.skill) and install it in Claude (Settings → Skills → Install from file).

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

Claude will automatically detect AXI4-Stream signals and run the full compliance check.

---

## File structure

```
axi4-stream-compliance/
├── SKILL.md                          # Skill entry point & workflow
└── references/
    ├── protocol-rules.md             # Full rule catalogue (ARM spec references)
    ├── common-violations.md          # 11 annotated anti-patterns with ❌/✅ code
    └── report-template.md           # Report format + SVA assertion templates
```

---

## Example output

```
## AXI4-Stream Compliance Report

### Interface Summary
- Role: Master
- Signals: TVALID, TREADY, TDATA[31:0], TLAST
- Reset: Async active-low (ARESETn)

### Findings

#### 🔴 CRITICAL — 1 issue found

**[C-1] Rule H1 — TVALID Deasserted Without Handshake**
- Location: axis_master.v, line 42
- What's wrong: TVALID is cleared unconditionally in the SEND state,
  regardless of whether TREADY was seen.
- Risk: Data loss — slave may miss transfers.
- Fix: See corrected code below.

#### 🔵 INFO — 1 note

**[I-1] Rule X2 — TKEEP absent on 32-bit bus**
- Recommendation: Add output [3:0] TKEEP for partial last-beat support.

### Overall Assessment: ❌ FAIL
```

---

## Roadmap

- [ ] AXI4-Lite compliance checker  
- [ ] AXI4 Full (memory-mapped) compliance checker  
- [ ] Yosys integration for automated signal-width extraction  
- [ ] Multi-file / full SoC review mode  

---

## Background

Commercial CDC/protocol checkers like Siemens Questa CDC, Cadence JasperGold, and Synopsys SpyGlass cost **$100,000+/year** and are inaccessible to most individual engineers, students, and small teams. This skill brings structured, spec-accurate AXI4-Stream checking to anyone with Claude.

---

## License

MIT — use freely, contributions welcome.

*Based on ARM AMBA AXI-Stream Protocol Specification IHI0051B.*
