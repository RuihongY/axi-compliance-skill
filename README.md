# AXI Compliance Skills for Claude

A collection of Claude skills that review Verilog / SystemVerilog RTL against
the ARM AMBA AXI family of specifications and produce structured compliance
reports.

---

## Skills in this repo

| Skill | Spec | Description |
|-------|------|-------------|
| [`axi4-stream-compliance`](./axi4-stream-compliance/) | IHI0051 | AXI4-Stream protocol checker (TVALID/TREADY/TDATA/TLAST/TKEEP/TSTRB) |
| [`axi4-lite-compliance`](./axi4-lite-compliance/) | IHI0022 | AXI4-Lite protocol checker (5 channels: AW/W/B/AR/R) |

Each skill produces:

- 🔴 **CRITICAL** — Direct spec violations causing data loss or functional failure
- 🟡 **WARNING** — Non-recommended patterns risking interoperability issues
- 🔵 **INFO** — Observations and best-practice suggestions
- ✅ **Corrected code snippets** for every CRITICAL finding
- 📋 **SVA assertion templates** ready to drop into your testbench

---

## Coverage summary

### `axi4-stream-compliance` — 25 rules across 8 categories
Handshake, Reset, Signal Stability, Widths, TKEEP/TSTRB, TLAST framing,
Combinatorial dependency, Optional signals.

### `axi4-lite-compliance` — 30+ rules across 8 categories
Per-channel handshake (×5), Reset, Per-channel stability, Widths,
Address alignment, Response codes (incl. EXOKAY illegal in Lite),
Inter-channel ordering & deadlock avoidance, Non-Lite signal detection.

---

## How to install a skill

1. Download the `.skill` file you want:
   - [`axi4-stream-compliance.skill`](./axi4-stream-compliance.skill)
   - [`axi4-lite-compliance.skill`](./axi4-lite-compliance.skill)
2. In Claude, open **Settings → Skills → Install from file**.
3. Drag in the `.skill` file.

## How to use

Paste your RTL into a conversation and ask Claude to check it:

```
Check this AXI4-Lite slave for protocol compliance:

module my_csr_slave (
  input             ACLK, ARESETn,
  input             AWVALID,
  output reg        AWREADY,
  ...
```

Claude will automatically detect the relevant AXI signals and trigger the
appropriate skill — no need to name it.

---

## Per-skill file structure

Each skill follows the same layout:

```
<skill-name>/
├── SKILL.md                        # Entry point: when to trigger, workflow
├── scripts/
│   └── extract_signals.py          # Auto-extract signal widths from RTL files
├── references/
│   ├── protocol-rules.md           # Full rule catalogue with ARM spec refs
│   ├── common-violations.md        # Annotated anti-patterns (❌/✅ pairs)
│   └── report-template.md          # Output format + SVA assertion library
└── evals/
    └── evals.json                  # Test cases (compliant + violating RTL)
```

---

## Roadmap

- [ ] AXI4 Full (memory-mapped, with bursts) compliance checker
- [ ] CHI / ACE-Lite (cache coherent) compliance checker
- [ ] AHB / AHB-Lite compliance checker

---

## License

MIT — use freely, contributions welcome.

*Based on ARM AMBA specifications IHI0051 (AXI-Stream) and IHI0022 (AXI / AXI-Lite).*
