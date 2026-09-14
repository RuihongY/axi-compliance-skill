# AHB-Lite and shared AHB review checkpoints

Baseline: [Arm IHI0033A](https://documentation-service.arm.com/static/5f914801f86e16515cdc2a27),
particularly chapters 2–7. For legacy-only behavior use
[legacy-ahb.md](legacy-ahb.md); do not apply Lite response encodings to legacy AHB.

## T — Phase tracking (chapters 3 and 4)

- **T1**: Separate accepted address/control from data-phase state. Decode HSEL
  with the current address, but retain the accepted slave selection for response
  and read-data multiplexing. Gate address capture with bus HREADY.
- **T2**: HTRANS encodings are IDLE=0, BUSY=1, NONSEQ=2, SEQ=3. Only the latter
  two request an active data transfer. IDLE/BUSY do not write registers or consume
  a data beat. Their own data phase gets a zero-wait OKAY response; a current
  IDLE/BUSY address phase does not cancel an older stalled active data phase.
- **T3**: HWDATA belongs to the accepted preceding address/control. Use captured
  HWRITE/HADDR/HSIZE to direct it. Apply a write side effect once for the data
  transfer, not repeatedly while stalled. Reads need correct data at completion;
  do not require HRDATA to be meaningful throughout earlier wait cycles.
- **T4**: During ordinary waited active transfers, preserve required address/control
  and write data. Apply chapter 3.6 exceptions for IDLE/BUSY and ERROR response
  recovery before declaring a change illegal. A blanket AXI-style stall property
  over all H signals will produce false positives.

## B — Geometry and burst sequencing (chapter 3)

- **B1**: HSIZE encodes log2(bytes per transfer). Address alignment is required
  to that transfer size, which must fit the bus. Do not import AXI's unaligned
  start behavior. Byte/halfword transfers on a wider bus are legal.
- **B2**: HBURST selects SINGLE, INCR, WRAP4, INCR4, WRAP8, INCR8, WRAP16,
  INCR16 (encodings 0 through 7). NONSEQ begins a burst; SEQ continues it.
  BUSY inserts a gap, not an extra beat. Keep burst attributes consistent.
- **B3**: Incrementing bursts cannot cross a 1KB boundary. Break an undefined
  INCR into a new NONSEQ burst at the boundary. Count accepted active transfers,
  not clock cycles, and use HSIZE rather than bus width as the increment.
- **B4**: WRAP uses a region of burst_length * transfer_bytes. Start alignment
  is to the transfer size, not necessarily the wrap-region base. The helper
  returns the nominal full burst; early termination needs contextual review.
- **B5**: Distinguish ordinary fixed-length completion from a permitted early
  termination caused by ERROR or legacy ownership changes. Do not require all
  remaining beats after an error as in AXI. For BUSY/termination choices consult
  chapters 3.5–3.6 and the selected variant.

## R — Ready and response (chapters 4 and 5)

- **R1**: In Lite, normal wait states use HRESP=0 and HREADYOUT=0. Completion
  uses HREADYOUT=1. Verify muxed HREADY comes from the data-phase slave.
- **R2**: Lite ERROR has a first cycle with HRESP=1/HREADYOUT=0 followed by
  HRESP=1/HREADYOUT=1. Extra latency precedes that pair as OKAY wait states.
  Check both directions: every first error cycle leads to a final cycle, and
  a final error cycle is not invented without its first cycle.
- **R3**: A master can change the pending next transfer during error recovery.
  Do not report the resulting HTRANS/address change as a normal-stall failure.
- **R4**: A default responder errors on an active unmapped access, while idle
  traffic completes normally. Ignore unselected slave outputs unless the mux
  actually exposes them. A long delay needs a documented progress contract;
  the recommendation on wait counts is not a universal 16-cycle hard limit.

## C — Interface and reset (chapters 2, 6 and 7)

- **C1**: Baseline HADDR=32, HTRANS=2, HSIZE/HBURST=3, HPROT=4, HRESP=1
  for Lite; data widths of 8, 16, 32, 64, 128, 256, 512 and 1024 are legal.
  The 32-bit minimum is a recommendation, not a requirement. Check endian byte-lane mapping. Baseline AHB has no AXI WSTRB;
  derive byte enables from captured HSIZE/address, considering endianness.
- **C2**: Reset the master into IDLE and slaves to a ready state. Reset phase
  ownership and pending side-effect state; do not infer a protocol requirement
  to clear every payload register. Check HRESETn mapping and release timing.
- **C3**: Verify HMASTLOCK handling where locked sequences are supported, without
  inventing legacy bus-request/grant signals on a single-master Lite interface.
  Exclude AHB5 security/exclusive/extended-attribute requirements unless selected.
