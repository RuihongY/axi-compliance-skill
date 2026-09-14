# AMBA Compliance Skills for Claude

A collection of Claude skills that review Verilog / SystemVerilog RTL against
the Arm AMBA AXI and AHB specifications and produce structured compliance
reports.

---

## Skills in this repo

| Skill | Spec | Description |
|-------|------|-------------|
| [`axi4-stream-compliance`](./axi4-stream-compliance/) | IHI0051 | AXI4-Stream protocol checker (TVALID/TREADY/TDATA/TLAST/TKEEP/TSTRB) |
| [`axi4-lite-compliance`](./axi4-lite-compliance/) | IHI0022H | AXI4-Lite protocol checker (5 channels: AW/W/B/AR/R) |
| [`axi4-full-compliance`](./axi4-full-compliance/) | IHI0022H | Memory-mapped AXI4 bursts, LAST, IDs, ordering and exclusives |
| [`ahb-compliance`](./ahb-compliance/) | IHI0033A / IHI0011A | AHB-Lite pipelines and responses; legacy AHB arbitration and RETRY/SPLIT |

Each skill produces:

- 🔴 **CRITICAL** — Direct spec violations causing data loss or functional failure
- 🟡 **WARNING** — Non-recommended patterns risking interoperability issues
- 🔵 **INFO** — Observations and best-practice suggestions
- ✅ **Corrected code snippets** for every CRITICAL finding
- 📋 **SVA assertion templates** to adapt to the selected interface

---

## Coverage summary

### `axi4-stream-compliance` — AXI4-Stream baseline (IHI0051A)
Handshake, Reset, Signal Stability, Widths, TKEEP/TSTRB, TLAST framing,
Combinatorial dependency, Optional signals.

### `axi4-lite-compliance` — AXI4-Lite baseline (IHI0022H)
Per-channel handshake (×5), Reset, Per-channel stability, Widths,
Address/byte-lane handling, Response codes (incl. EXOKAY illegal in Lite),
Inter-channel ordering & deadlock avoidance, Interface classification and optional ID reflection.

---

### `axi4-full-compliance` — memory-mapped AXI4 (IHI0022H)
FIXED/INCR/WRAP geometry, 4KB boundaries, narrow/unaligned lanes, WSTRB,
accepted beat counts, WLAST/RLAST, W-before-AW, per-ID read/response ordering,
write-data serialization, backpressure, reset and exclusive-access review.

### `ahb-compliance` — AHB-Lite and legacy AHB
Address/data phase separation, HREADY versus HREADYOUT, HSEL response muxing,
IDLE/BUSY/SEQ/NONSEQ, alignment, 1KB incrementing boundaries, wrap bursts,
two-cycle ERROR and reset. Legacy-only guidance covers arbitration, ownership,
locks, RETRY, SPLIT and HSPLIT. AHB5 extensions are outside this baseline.

## How to install a skill

1. Download the `.skill` file you want:
   - [`axi4-stream-compliance.skill`](./axi4-stream-compliance.skill)
   - [`axi4-lite-compliance.skill`](./axi4-lite-compliance.skill)
   - [`axi4-full-compliance.skill`](./axi4-full-compliance.skill)
   - [`ahb-compliance.skill`](./ahb-compliance.skill)
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

State the protocol variant when known, for example:

- "Review this AXI4 Full DMA for 4KB boundary and WLAST bugs."
- "Check this AHB-Lite slave for address/data phase and ERROR response timing."
- "Review this legacy AMBA2 AHB arbiter's SPLIT/HSPLIT handling."

The relevant skill can be selected automatically; explicitly naming it also works.

---

## Per-skill file structure

Each skill has an entrypoint, focused references, a helper, and model review cases:

```
<skill-name>/
├── SKILL.md                        # Entry point: when to trigger, workflow
├── scripts/
│   └── *.py                       # Signal inventory or concrete burst geometry
├── references/
│   ├── protocol-rules.md           # Review checkpoints with Arm spec refs
│   ├── common-violations.md        # Annotated anti-patterns (❌/✅ pairs)
│   └── report-template.md          # Output format + SVA assertion library
└── evals/
    └── evals.json                  # Test cases (compliant + violating RTL)
```

---

## Development and validation

Python 3.9+ is sufficient for all helpers, regression tests, and packaging:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/build_skills.py
python3 scripts/build_skills.py --check
```

Edit the skill folders first, then rebuild all four `.skill` archives. Packaging
is deterministic and self-contained; CI checks that committed archives match
the sources. The automated tests cover extractor behavior, burst arithmetic, CLI errors and package integrity.

The `evals/evals.json` files are **model review cases**, not RTL simulations or
results from these Python tests. For a behavioral evaluation, give an assistant
the selected skill and each prompt, save its answer, then judge it against
`expected_output`. Existing text checks are smoke checks only; `rubric` assertions
require semantic review. New cases exercise legal sparse streams, ID reflection,
capacity backpressure, READY timing, and incomplete inputs. The new Full AXI
and AHB suites add 24 cases for burst/ordering and phase/response behavior. They have not been
model-run as part of the Python regression suite.

The Stream/Lite extractors are conservative regex helpers, not Verilog elaborators. They
handle individual port declarations and simple decimal parameter/range forms;
comma-grouped ports, typedefs, macros, parameter overrides, and multiple modules
or interfaces need manual verification. Unsupported width expressions remain
unknown. Reset hints do not prove reset behavior (`tvalid_cleared_in_reset` is
`null` pending manual analysis). A positive `if (resetn)` is not evidence of an
active-high reset.

Reports distinguish base-protocol violations from documented endpoint/profile
requirements. Legal 24-bit Stream data, sparse TKEEP, constant-low TLAST, and
Lite ID reflection must not fail solely for those features. An incomplete
review is **INCONCLUSIVE**, and PASS is limited to the stated review scope.

---

## Burst geometry helpers

The two new skills include standalone JSON-driven checks. Save a descriptor,
then run the appropriate command from the repository root:

```sh
python3 axi4-full-compliance/scripts/check_burst.py axi-burst.json
python3 ahb-compliance/scripts/check_burst.py ahb-burst.json
```

Example AXI descriptor (word WRAP4 starting at 12):
`{"addr":12,"len":3,"size":2,"burst":2,"data_width":32}`.
Example AHB descriptor (word WRAP4 starting at 1020):
`{"addr":1020,"size":2,"burst":2,"data_width":32}`.

See each skill's `references/burst-helper.md` for the schema and exit codes.
These scripts check nominal geometry only, not RTL or handshake traces.
SVA templates and semantic model-evaluation cases require separate execution;
passing Python tests is not a simulation or formal compliance result.

## Roadmap

- [x] AXI4 Full (memory-mapped, with bursts) review skill and geometry helper
- [ ] CHI / ACE-Lite (cache coherent) compliance checker
- [x] AHB / AHB-Lite review skill and geometry helper

---

## License

MIT — use freely, contributions welcome.

*Based on Arm AMBA specifications IHI0051, IHI0022, IHI0033 and IHI0011.*
