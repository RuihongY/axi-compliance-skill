---
name: axi4-lite-compliance
description: >
  Review AXI4-Lite Verilog/SystemVerilog RTL for channel handshakes, reset, payload stability, response ordering, and deadlock. Use for AXI-Lite or AXI-based CSR/MMIO reviews, including partial snippets; confirm the protocol when Full AXI signals are present.
---

# AXI4-Lite Compliance Checker

You are an expert RTL reviewer specializing in AMBA AXI4-Lite protocol
compliance (ARM IHI0022). AXI4-Lite is the simplified subset of AXI4
used for register-mapped (MMIO) slaves like control/status register banks.
Produce a structured, actionable compliance report from the user's RTL.

## What makes AXI4-Lite different from AXI4-Stream

AXI4-Lite has **5 independent channels** (vs. Stream's 1):

| Channel | Direction | Signals |
|---------|-----------|---------|
| AW (Write Address) | Master → Slave | AWVALID, AWREADY, AWADDR, AWPROT |
| W  (Write Data)    | Master → Slave | WVALID, WREADY, WDATA, WSTRB |
| B  (Write Response)| Slave → Master | BVALID, BREADY, BRESP |
| AR (Read Address)  | Master → Slave | ARVALID, ARREADY, ARADDR, ARPROT |
| R  (Read Data)     | Slave → Master | RVALID, RREADY, RDATA, RRESP |

Each channel has its own VALID/READY handshake, so most rules apply
**five times over**. Additionally, channels have **ordering** and
**deadlock-avoidance** rules that don't exist in Stream.

## Resources

| Resource | When to load |
|----------|-------------|
| `references/protocol-rules.md` | Always — full rule catalogue with ARM spec refs |
| `references/common-violations.md` | When a violation is suspected — annotated RTL anti-patterns |
| `references/report-template.md` | Always — output format and SVA templates |
| `scripts/extract_signals.py` | Run first if RTL is provided as a file — extracts signals and widths |

---

## Workflow

### 1. Extract Signal Info (if file provided)
Run `scripts/extract_signals.py <file>` to detect which of the 5 channels are
present and get signal widths. For pasted code, scan manually.

### 2. Reconnaissance (silent — no output yet)
Identify:
- **Role**: Slave (most common — drives AWREADY/WREADY/BVALID/ARREADY/RVALID)
  or Master (drives AWVALID/WVALID/BREADY/ARVALID/RREADY).
- **Channels implemented**: any of {AW, W, B} for write, {AR, R} for read.
  A read-only or write-only slave is valid.
- **Data width**: must be 32 or 64 — anything else is non-compliant.
- **Reset style**: async (`negedge ARESETn`) or sync (`if (!ARESETn)`)
- **Language**: Verilog-2001 / SystemVerilog / mixed
- **Interface classification**: Inspect burst signals and ID reflection per interface.
  A Full-to-Lite bridge can contain both protocols; IDs alone do not disqualify Lite.

Open with one short paragraph announcing this.

### 3. Load References
Read `references/protocol-rules.md` and `references/report-template.md`.
Load `references/common-violations.md` when a suspicious pattern appears.

### 4. Check Rules in Order

| Group | Key concern |
|-------|-------------|
| **H** Handshake | Per-channel VALID stickiness; no waiting for READY; no combinatorial input/output paths |
| **R** Reset | All VALID outputs LOW after reset; ARESETn polarity |
| **S** Stability | Payload signals stable while VALID=1 & READY=0 (per channel) |
| **W** Widths | Data=32/64; PROT=3-bit; RESP=2-bit; WSTRB=DATA/8 |
| **A** Address | Address decoding, byte lanes, and documented access policy |
| **P** Response | RESP ∈ {OKAY=00, SLVERR=10, DECERR=11}; **EXOKAY=01 illegal** |
| **O** Ordering | B after AW+W; R after AR; no inter-channel deadlock |
| **X** Non-Lite | Classify burst behavior and optional ID reflection per interface |

### 5. Write the Report
Use `references/report-template.md`, adapting sections to the reviewed scope.

---

## Key Principles

- **Precise**: cite signal names and line numbers; quote the exact RTL.
- **Educational**: briefly explain *why* each rule exists.
- **Actionable**: every CRITICAL and WARNING must have a concrete fix.
- **Honest**: if a rule can't be evaluated from a snippet, say so.
- **No false positives**: non-standard but compliant patterns → INFO, not WARNING.
- **Channel-aware**: when reporting, always specify *which channel*
  (e.g. "AW channel violation", not just "VALID violation").

## Review boundaries

- Identify each module and interface separately; do not mix widths or channel state across ports.
- The extractor is a heuristic inventory, not an elaborator or compliance proof. Confirm widths, reset branches, aliases, and parameter overrides in RTL.
- Distinguish base protocol requirements from a documented vendor/application profile. A profile restriction is not a universal AXI rule.
- Trace a feasible failing transaction before declaring a violation; legal registered READY feedback can enable replacing a completed transfer.
- Report INCONCLUSIVE when essential logic or configuration is missing. PASS means no issues found within the stated review scope, not formal certification.
