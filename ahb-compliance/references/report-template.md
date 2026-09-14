# Report and verification patterns

State variant/spec revision, role, bus width/endianness, signal mapping and
reviewed scope. Include a short address-phase/data-phase cycle table before any
pipeline finding. For each finding give rule ID, exact code/trace, expected
behavior, consequence and correction. CRITICAL means a proven protocol failure;
WARNING needs an actual endpoint risk; INFO is an observation.

Conclude FAIL for demonstrated violations, INCONCLUSIVE for missing essential
logic, or scoped PASS/PASS WITH WARNINGS. Mark legacy arbitration and AHB5
extensions outside scope when not provided. Do not equate helper success with
RTL compliance or claim simulation/formal execution without running it.

## Lite response SVA examples

These templates require `data_active`, a monitor register for this slave's
accepted active data phase, independent of current HSEL. Update it only when
bus HREADY is HIGH: `data_active <= HSEL && HTRANS[1]`; clear on reset. It
remains set across this slave's wait states. Substitute actual signal names.

```systemverilog
logic past_valid;
always_ff @(posedge HCLK or negedge HRESETn)
  if (!HRESETn) past_valid <= 1'b0;
  else past_valid <= 1'b1;

// First error cycle must be followed by final error cycle.
assert property (@(posedge HCLK) disable iff (!HRESETn)
  (data_active && HRESP && !HREADYOUT) |=>
    (data_active && HRESP && HREADYOUT));
// Final error cycle must have a first cycle. Include startup protection.
assert property (@(posedge HCLK) disable iff (!HRESETn)
  (data_active && HRESP && HREADYOUT) |->
    (past_valid && $past(data_active && HRESP && !HREADYOUT)));
```

For legacy AHB, compare the explicit two-bit non-OKAY response and preserve
its encoding through both cycles; do not reuse boolean HRESP expressions.

Check write enables using captured data-phase state, accepted/retired transfer
counts, and the design's error-side-effect policy. Check byte enables from the
captured address/size. Do not assert all HRDATA stable on wait cycles or
unconditionally assert HTRANS/HADDR stable while HREADY is LOW: IDLE/BUSY and
error recovery require the chapter 3.6 exceptions. Do not assert reset behavior
inside a property disabled by the same reset.

Directed verification should include back-to-back read/write transfers,
waited writes with a changing next address, alternating slave selection,
IDLE/BUSY during a prior wait, legal wrap and narrow accesses, 1KB crossings,
two-cycle ERROR and reset during waits. Add RETRY, SPLIT/HSPLIT, handover and
locked sequences for legacy multi-master AHB. A local slave testbench cannot
by itself establish system arbitration correctness.
