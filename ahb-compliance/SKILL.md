---
name: ahb-compliance
description: >
  Review AHB and AHB-Lite Verilog/SystemVerilog RTL and bus traces for pipelined
  transfer, HREADY, burst, response and arbitration compliance. Use for HTRANS,
  HSEL, HREADYOUT, wait-state, ERROR, RETRY or SPLIT debugging. Confirm legacy
  AHB versus AHB-Lite; AHB5 extensions and APB need separate specifications.
---

# AHB / AHB-Lite Compliance Review

Use AMBA 3 AHB-Lite IHI0033A for the Lite baseline and AMBA 2 AHB IHI0011A
for legacy arbitration and RETRY/SPLIT. A newer interface called "AHB" might
mean AHB5: do not infer legacy response semantics from that label alone.

## Workflow

1. State the variant, master/slave/interconnect role, bus width, reset,
   endianness, selected slave, and whether arbitration is within scope.
2. Read [protocol-rules.md](references/protocol-rules.md). For legacy AHB,
   additionally read [legacy-ahb.md](references/legacy-ahb.md).
3. Draw a cycle table separating current address phase from the preceding
   accepted transfer's data phase. Record HREADY, HSEL, HTRANS, HWRITE,
   HADDR/HSIZE/HBURST, HWDATA/HRDATA, HRESP and the response mux selection.
   An address is accepted on a rising edge with HREADY high. For a particular
   slave, only HSEL && HTRANS[1] then creates an active transfer.
4. For concrete burst addresses, use [check_burst.py](scripts/check_burst.py)
   according to [burst-helper.md](references/burst-helper.md). This checks
   normal burst geometry, not timing, arbitration, early termination or RTL.
5. Use [common-violations.md](references/common-violations.md) to construct
   counterexamples and fixes. Use [report-template.md](references/report-template.md)
   for findings, bounded conclusions and assertion adaptation.

## Review discipline

- HREADY is not AXI READY. There are no five independent VALID/READY channels.
  Do not sample HWDATA as if it accompanied the current address phase.
- Distinguish a slave's HREADYOUT from the bus HREADY input; the latter governs
  acceptance when the preceding transfer belongs to a different slave.
- Current HSEL/HTRANS cannot erase the previous transfer's data phase.
- Do not impose unconditional stability of all signals whenever HREADY is low:
  IDLE/BUSY transitions and error recovery have specified exceptions.
- AHB-Lite has one-bit HRESP (OKAY/ERROR). Legacy AHB has two-bit HRESP and
  arbitration; Lite does not require RETRY/SPLIT support or HBUSREQ/HGRANT.
- Report unknown variant/configuration as INCONCLUSIVE for affected rules.
  A review or helper PASS is not formal certification of the RTL.
