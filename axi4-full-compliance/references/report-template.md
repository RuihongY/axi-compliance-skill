# Reporting and assertion templates

Start with interface, role, revision, configuration and reviewed scope. Group
findings by rule and channel. Each finding needs location, reachable transaction
sequence, expected versus actual behavior, consequence, and a concrete repair.
Use CRITICAL for proven protocol violations, WARNING for an evidenced integration
risk, INFO for observations. Do not use warnings to disguise missing evidence.

End with FAIL if a violation is demonstrated; otherwise INCONCLUSIVE if essential
logic is missing, PASS WITH WARNINGS for a complete scoped review with concerns,
or PASS for no findings within that scope. List unreviewed obligations separately.

## SVA patterns

Adapt widths and names, include every implemented sideband, and instantiate only
existing channels. In formal use, assert DUT outputs and constrain environmental
inputs separately. These patterns are not a complete ready-made checker.

```systemverilog
assert property (@(posedge ACLK) disable iff (!ARESETn)
  (AWVALID && !AWREADY) |=> AWVALID &&
    $stable({AWADDR, AWLEN, AWSIZE, AWBURST, AWID, AWLOCK, AWCACHE, AWPROT}));
assert property (@(posedge ACLK) disable iff (!ARESETn)
  (WVALID && !WREADY) |=> WVALID && $stable({WDATA, WSTRB, WLAST}));
assert property (@(posedge ACLK) disable iff (!ARESETn)
  (BVALID && !BREADY) |=> BVALID && $stable({BID, BRESP}));
assert property (@(posedge ACLK) disable iff (!ARESETn)
  (ARVALID && !ARREADY) |=> ARVALID &&
    $stable({ARADDR, ARLEN, ARSIZE, ARBURST, ARID, ARLOCK, ARCACHE, ARPROT}));
assert property (@(posedge ACLK) disable iff (!ARESETn)
  (RVALID && !RREADY) |=> RVALID && $stable({RID, RDATA, RRESP, RLAST}));
// Select the VALID outputs driven by the DUT for this sampled reset check.
assert property (@(posedge ACLK)
  !ARESETn |-> (!AWVALID && !WVALID && !ARVALID && !BVALID && !RVALID));
```

LAST/ID/response assertions need an independent transaction scoreboard. Push
AR/AW only on acceptance, track W bursts separately (including W-before-AW),
and count accepted R/W beats. A visible BVALID/RVALID must already have eligible
prior requests, even if BREADY/RREADY is LOW. Merely comparing accepted response
counts with request counts misses illegally offered stalled responses. Check
LAST whenever a data beat is offered against its current count, then update the
count on acceptance. Support same-cycle push/pop without underflow or overwrites.

Test FIXED/INCR/WRAP, legal narrow/unaligned masks, first/last-beat stalls,
back-to-back bursts, W-before-AW, interleaved read IDs, same-ID ordering, errors
without truncation, and reset with pending transactions. Keep environment progress
assumptions explicit. Report whether simulation/formal tools were actually run.
