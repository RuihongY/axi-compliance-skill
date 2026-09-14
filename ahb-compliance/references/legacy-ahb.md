# Legacy AMBA 2 AHB: arbitration and split responses

Source: [Arm IHI0011A, AMBA Specification Rev 2.0](https://developer.arm.com/documentation/ihi0011/a),
AHB chapter 3, especially §§3.9, 3.11 and 3.12. A readable
[transcription of the Arm specification](https://studylib.net/doc/28398199/ihi0011a)
is also available.
Use these checkpoints only after confirming legacy AHB. The protocol revision
and the system's arbitration policy are separate facts.

- **L1 — Response encoding**: Two-bit HRESP uses OKAY=00, ERROR=01,
  RETRY=10, SPLIT=11. These are not AXI BRESP encodings. RETRY/SPLIT are
  not valid Lite responses. Validate the required two-cycle non-OKAY sequence,
  including the LOW-then-HIGH ready transition. RETRY/SPLIT require cancellation
  of the following transfer; after ERROR continuing it is optional; earlier additional wait states carry OKAY.
- **L2 — Ownership**: HBUSREQ/HGRANT select a master through the arbiter;
  a grant is not permission to switch address/control while HREADY is LOW.
  Track accepted address ownership separately from the previous data-phase
  master so HWDATA remains routed from the correct source after a handover.
- **L3 — RETRY**: The transfer must be attempted again under arbitration.
  It has not completed successfully; avoid double-committing a write when the
  master replays it. Do not confuse retry with an AXI error response.
- **L4 — SPLIT**: Track which master was split and its eligibility. HSPLIT
  releases the arbiter's masking for that master; it is not an immediate bus
  grant or a completion response. Other eligible masters can make progress.
  Do not impose one universal priority/fairness policy on the arbiter.
- **L5 — Locks and bursts**: Trace HLOCK/HMASTLOCK and ownership retention for
  a locked sequence, including the final data phase. A master can lose ownership
  before a nominal burst finishes; analyze the restart as a new NONSEQ burst,
  not an AXI-style remaining-beat obligation. Check the exact locked-response
  and default-master rules in the selected specification when such paths exist.

For a slave-only snippet with no arbiter, mark ownership, masking and fairness
outside scope rather than failing it for missing HBUSREQ/HGRANT/HSPLIT logic.
The geometry helper does not check any of L1–L5.
