# AXI4 Full review rules

Baseline: [Arm IHI0022H](https://developer.arm.com/-/media/Arm%20Developer%20Community/PDF/IHI0022H_amba_axi_protocol_spec.pdf),
AXI4 portions of A2, A3, A5 and A7. Section names matter: the document also
contains AXI3, AXI5 and ACE requirements that do not all apply to AXI4.
These are review checkpoints, not a reproduction of the specification.

## H — Channel handshakes and timing (A3.1–A3.3)

- **H1**: After a stalled VALID, that channel's VALID and payload must survive
  through the acceptance edge. Reset is an exception. Check AW/AR metadata,
  WDATA/WSTRB/WLAST, BID/BRESP, and RID/RDATA/RRESP/RLAST independently.
- **H2**: A source cannot require its destination's READY before offering VALID.
  Show the circular wait or withdrawal rather than rejecting every RHS reference
  to READY. WVALID must not wait for AWREADY or WREADY; AW and W are independent.
- **H3**: No combinatorial paths from interface inputs to outputs. A destination
  may wait for VALID using registered logic; that is not permission for a direct
  combinatorial VALID-to-READY path.
- **H4**: Reset driven VALID outputs to LOW, including source state that drives
  combinatorial VALID. Check reset release timing; do not impose a payload reset
  value or a particular spelling for an internal reset signal.

## B — Burst geometry (A3.4)

- **B1**: Interpret AxLEN as beats minus one. AXI4 INCR allows 1–256 beats;
  FIXED allows 1–16; WRAP allows 2, 4, 8 or 16. AxBURST=3 is reserved.
- **B2**: Bytes per beat are `2**AxSIZE` and cannot exceed the physical data bus.
  A smaller transfer is narrow, not a width violation. AXI4 data buses use
  power-of-two byte counts, 1–128; do not apply Stream's arbitrary-byte rule.
- **B3**: Check every addressed byte window stays in the starting 4KB page.
  For unaligned INCR, only the first window starts unaligned; subsequent beats
  start at `align_down(start, bytes) + beat_index * bytes`. Do not test the
  naive `start + beats * bytes` upper bound. FIXED repeats the same window.
- **B4**: WRAP starts aligned to the transfer size. Its region is
  `beats * bytes`; compute its lower boundary by rounding down to that region.
  The start need not equal the lower boundary. Follow wrap arithmetic, not
  linear address addition, when checking the final beat and boundary.
- **B5**: WSTRB can select any subset of the permitted byte lanes, including
  zero. It cannot enable a lane outside that beat's addressed window. Preserve
  strobes while W is stalled. Zero strobes do not cancel the W beat or response.
- **B6**: No early burst termination, even after an error; review all LEN+1 data
  transfers and LAST placement. Do not count an idle cycle or stalled beat twice.

## O — Outstanding transactions and ordering (A3.3, A3.4, A5)

- **O1**: BVALID requires both an accepted AW and the accepted final W beat of
  its transaction. One B response retires one write burst, not each data beat.
  Match accepted AW order to complete W bursts; W has no WID in AXI4.
- **O2**: RVALID requires a previously accepted AR. Keep remaining-beat state per
  transaction/ID, and require RLAST exactly on its final accepted beat. A single
  global read counter is insufficient when IDs interleave.
- **O3**: Preserve required same-ID ordering within the read and write response
  streams. Different IDs can complete out of order. There is no blanket ordering
  between reads and writes just because ARID equals AWID.
- **O4**: W bursts cannot interleave; complete the current write data burst before
  starting the next. Interleaving R beats across IDs is legal when supported.
- **O5**: Backpressure must protect every occupied queue entry and stalled
  response. Check simultaneous push/pop and full conditions. VALID must not be
  suppressed until a new request or a response READY arrives. Separate protocol
  deadlock from an unspecified system progress/timeout requirement.

## P — Responses, attributes, exclusives (A2, A4, A7)

- **P1**: Normal traffic uses OKAY/SLVERR/DECERR. EXOKAY indicates exclusive
  success; do not ban it as in Lite or allow it for ordinary accesses. Read errors
  do not remove the obligation to deliver the remaining beats with correct RID.
- **P2**: AXI4 AxLOCK is one bit and selects exclusives, not AXI3 locked traffic.
  Review monitor behavior only if exclusives are in scope. In a supporting slave,
  a failed exclusive write returns OKAY without modifying memory. A slave that
  does not support exclusives has different behavior: do not universally require
  suppression of writes merely because the response is OKAY.
- **P3**: For exclusives, also check the A7.2 restrictions (transaction alignment,
  size/length and matched read/write attributes). The geometry helper does not
  validate an exclusive sequence, monitor state or cache routing.
- **P4**: Check declared control widths (LEN 8, SIZE 3, BURST 2, LOCK 1,
  CACHE 4, PROT 3, RESP 2; QOS/REGION 4 when present). ID width and optional
  USER fields are interface contracts. Trace transformed IDs through bridges.
  Check reserved attribute combinations against the AXI4 tables, not ACE tables.
