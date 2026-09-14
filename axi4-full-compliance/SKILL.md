---
name: axi4-full-compliance
description: >
  Review memory-mapped AXI4 Full Verilog/SystemVerilog RTL, bursts, and transaction
  traces for protocol compliance. Use for AXI burst, LAST, ID ordering, outstanding
  transaction, narrow-transfer or 4KB-boundary debugging. Distinguish AXI4 from
  AXI3, AXI4-Lite, AXI-Stream, and AXI5 before applying the rules.
---

# AXI4 Full Compliance Review

Review the AXI4 subset of Arm IHI0022H. This is an evidence-based RTL review,
not a simulator, formal proof, or certification. Do not infer the protocol
from the mere presence of a clock or one signal name.

## Workflow

1. Identify each interface, role (master/slave/interconnect), clock/reset,
   parameter configuration, data/ID widths, and supported transaction subset.
   Keep upstream/downstream bridge state separate. Confirm AXI4 rather than AXI3.
2. Read [protocol-rules.md](references/protocol-rules.md). Map all five channels,
   including each payload and handshake. Resolve aliases and omitted defaults
   from the selected specification and integration contract.
3. Reconstruct accepted address queues and data/response progress. Trace AW-first,
   W-first, simultaneous traffic, independent channel stalls, and back-to-back
   bursts. Count accepted beats, not cycles where VALID is merely high.
4. For concrete address/length/size examples, use
   [check_burst.py](scripts/check_burst.py) as described in
   [burst-helper.md](references/burst-helper.md). It checks geometry and optional
   WSTRB masks only; it does not establish RTL or transaction-order compliance.
5. Consult [common-violations.md](references/common-violations.md) when fixing a
   finding. A repair must preserve queued transactions under response stalls;
   a counter alone is not a complete buffering solution.
6. Use [report-template.md](references/report-template.md). Cite exact signals,
   lines, rule IDs, and a feasible failing trace. Include a fix and targeted
   verification for each proven violation, and list remaining unknowns.

## Boundaries that prevent false positives

- W can arrive before AW. A slave may defer acceptance, but a master cannot wait
  for AWREADY before offering write data. Registered ready feedback that frees
  a consumed buffer is not equivalent to waiting for READY to offer VALID.
- Narrow and unaligned transfers are not automatically illegal. WRAP requires
  transfer-size alignment, not alignment to the entire wrap region.
- Different read IDs can interleave; AXI4 write data cannot interleave bursts.
- EXOKAY belongs to exclusive accesses in Full AXI; do not apply the Lite ban.
- No arbitrary ready timeout, global serialization, or mandatory burst capability
  beyond the documented endpoint contract. Distinguish a master restriction
  from a receiving endpoint's obligations for admitted traffic.
- Review AXI3 WID/locked accesses and AXI5/ACE extensions under their own specs;
  do not silently reinterpret them as ordinary AXI4 signals.
