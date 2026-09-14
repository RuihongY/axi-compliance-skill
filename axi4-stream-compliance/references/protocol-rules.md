# AXI4-Stream Protocol Rules Reference
*Baseline: Arm IHI0051A (AXI4-Stream). Section numbers below refer to issue A.*

Sources: [Arm specification entry](https://developer.arm.com/documentation/ihi0051/a),
[Arm-authored PDF mirror](https://zipcpu.com/doc/axi-stream.pdf).
Vendor packet profiles can impose additional restrictions; identify them separately.

---

## Table of Contents
1. [H — Handshake Rules](#h-handshake)
2. [R — Reset Rules](#r-reset)
3. [S — Signal Stability Rules](#s-signal-stability)
4. [W — Signal Width Rules](#w-signal-widths)
5. [K — TKEEP / TSTRB Rules](#k-tkeep-tstrb)
6. [L — TLAST / Packet Framing Rules](#l-tlast)
7. [C — Combinatorial Dependency Rules](#c-combinatorial)
8. [X — Optional Signal Rules](#x-optional-signals)

---

<a id="h-handshake"></a>
## H — Handshake Rules

### H1 — TVALID Stickiness (CRITICAL if violated)
**Rule**: Once a Master asserts TVALID, it MUST NOT deassert TVALID until the
handshake completes (i.e., until the clock edge where both TVALID=1 and TREADY=1).

**ARM Spec**: Section 2.2.1.

**RTL check**: In every `always` block driving TVALID, confirm that TVALID is
only cleared on reset or on the cycle where `TVALID & TREADY` is true.

**Common mistake**:
```verilog
// VIOLATION: TVALID dropped without handshake
always @(posedge ACLK)
  if (!ARESETn)     TVALID <= 0;
  else if (send_en) TVALID <= 1;
  else              TVALID <= 0;  // ← drops TVALID even if TREADY not seen
```

**Fix**:
```verilog
always @(posedge ACLK)
  if (!ARESETn)              TVALID <= 0;
  else if (send_en)          TVALID <= 1;
  else if (TVALID & TREADY)  TVALID <= 0;  // only clear after handshake
```

---

### H2 — Master Must Not Gate TVALID on TREADY (CRITICAL if violated)
**Rule**: A Master is not permitted to wait until TREADY is asserted before
asserting TVALID. TVALID must be driven by the Master's own readiness, not
conditioned on the Slave's TREADY.

**ARM Spec**: Section 2.2.1

**RTL check**: Confirm TVALID is not assigned as `TVALID = some_condition & TREADY`.

**Common mistake**:
```verilog
assign TVALID = data_ready & TREADY;  // VIOLATION
```

---

### H3 — Slave TREADY Flexibility (INFO if noted)
**Rule**: A Slave IS permitted to assert TREADY before TVALID is seen, and is
permitted to deassert TREADY at any time before a handshake.

**Implication**: Do not flag toggling TREADY without TVALID as a violation.

---

### H4 — Both Must Be Asserted for Transfer (INFO — understanding check)
**Rule**: A transfer (beat) occurs on the rising edge of ACLK when both
TVALID=1 AND TREADY=1.

---

<a id="r-reset"></a>
## R — Reset Rules

### R1 — TVALID Reset Behavior (CRITICAL if violated)
Check TVALID during reset and at reset release (§2.7). A combinatorial VALID
can be reset through its source state; a literal TVALID reset assignment is
not required. Check the signal behavior, not just assignment syntax.

### R2 — Reset Polarity and Mapping
The interface reset is active-low. Custom RTL names and an internal inverted
reset are legal; trace the actual mapping before reporting a polarity bug.

### R3 — Reset Implementation Review (INFO)
Mixed synchronous/asynchronous register resets are not themselves an AXI
violation. Check externally visible VALID reset behavior and synchronous
reset release; do not require payload registers to share a reset style.

### R4 — TREADY After Reset (INFO)
**Rule**: The spec does not mandate a specific reset value for TREADY. A Slave
may come out of reset with TREADY=0 or TREADY=1.

---

<a id="s-signal-stability"></a>
## S — Signal Stability Rules

### S1 — Payload Stability During Stall (CRITICAL if violated)
**Rule**: While TVALID=1 and TREADY=0 (stall condition), ALL the following
signals MUST remain stable (unchanged):
- TDATA
- TLAST
- TKEEP (if present)
- TSTRB (if present)
- TID (if present)
- TDEST (if present)
- TUSER (if present)

**ARM Spec**: Section 2.2.1

**RTL check**: In the `always` block driving these signals, when TVALID=1 and
TREADY=0, confirm the signal is not updated.

```verilog
// VIOLATION: TDATA updated even during stall
always @(posedge ACLK)
  TDATA <= fifo_dout;  // ← updates every cycle regardless of backpressure
```

**Fix pattern**:
```verilog
always @(posedge ACLK)
  if (!ARESETn)          TDATA <= '0;
  else if (TVALID & TREADY)  TDATA <= fifo_dout;  // advance only on transfer
  else if (!TVALID)          TDATA <= fifo_dout;  // or when no inflight data
```

---

### S2 — TVALID Held Through Stall (relates to H1 — cross-reference)
See H1. All payload signals stable implies TVALID itself also stable (=1).

---

<a id="w-signal-widths"></a>
## W — Signal Width Rules

### W1 — TDATA Width Must Be a Multiple of 8 Bits (CRITICAL if violated)
**Check**: A present TDATA has positive width divisible by 8. A 24-bit or
40-bit bus is legal; do not impose a power-of-two whitelist. See §2.1 and A.1.

### W2 — TKEEP Width Must Equal TDATA_WIDTH / 8 (CRITICAL if violated)
**Rule**: Each TKEEP bit corresponds to one byte of TDATA.
TKEEP must be exactly `TDATA_WIDTH / 8` bits wide.

---

### W3 — TSTRB Width Must Equal TDATA_WIDTH / 8 (CRITICAL if violated)
**Rule**: Same as TKEEP — one strobe bit per byte lane.

---

### W4 — TID Width Recommendation (WARNING if exceeded)
**Rule**: TID is recommended to be no wider than 8 bits.
Wider values are not prohibited but may cause interoperability issues.

---

### W5 — TDEST Width Recommendation (WARNING if exceeded)
**Rule**: TDEST is recommended to be no wider than 4 bits.

---

### W6 — TUSER Width Recommendation (INFO)
**Rule**: TUSER width should be an integer multiple of TDATA_WIDTH/8
(i.e., an integer number of bits per byte).

---

<a id="k-tkeep-tstrb"></a>
## K — TKEEP / TSTRB Rules

### K1 — Null Bytes Are Permitted (INFO)
Sparse or all-zero TKEEP is legal, including before TLAST. Do not add a
base-protocol assertion requiring full TKEEP on non-final beats (§2.4.1).

### K2 — Sparse Byte Lanes Are Permitted (INFO)
Do not require a contiguous low-lane TKEEP mask. Such restrictions require
an explicit endpoint profile, including on the last beat (§2.4).

### K3 — TSTRB Must Be Subset of TKEEP (CRITICAL if violated)
**Rule**: When TVALID is HIGH, `TSTRB & ~TKEEP` must be zero — i.e., a byte cannot be a
data/position byte if its TKEEP bit is 0.
`TSTRB[i]=1` is only valid when `TKEEP[i]=1`.

---

### K4 — TSTRB Without TKEEP (INFO)
Omitted TKEEP defaults to all ones; TSTRB can still identify position bytes.
Omitted TSTRB defaults to TKEEP (§3.1.2).

<a id="l-tlast"></a>
## L — TLAST / Packet Framing Rules

### L1 — TLAST Marks End of Packet (INFO)
Preserve packet boundaries. Missing TLAST does not automatically imply
single-beat packets; check the chosen default or generated boundary policy (§3.1.3).

### L2 — Packet Identity and Interleaving
Track packets by (TID, TDEST). Beat-level interleaving between streams is
permitted; an ID change alone is not a violation (§2.5, §4.1).
Any restriction on interleaving must come from the endpoint contract.
All sidebands still obey stall stability (S1).

### L3 — TLAST Tied LOW (INFO unless a contract conflicts)
Constant-low TLAST is a supported choice (§3.1.3). Report a compatibility
problem only when a known consumer needs boundaries for progress.

### L4 — TLAST Must Hold During Stall (relates to S1)
**Rule**: TLAST is a payload signal. While TVALID=1 and TREADY=0, TLAST
must not change (covered by S1 but worth calling out explicitly).

---

<a id="c-combinatorial"></a>
## C — Combinatorial Dependency Rules

### C1 — TVALID Must Not Combinatorially Depend on TREADY (CRITICAL)
**Rule**: A Master driving TVALID must not create a path where TVALID is
derived from TREADY. This creates a combinatorial loop if the Slave also
derives TREADY from TVALID (which is permitted by spec).

**RTL check**: In `assign` statements and combinatorial `always` blocks,
trace TVALID's fanin cone — TREADY must not appear.

```verilog
// VIOLATION — combinatorial loop risk
assign TVALID = data_avail & TREADY;

// VIOLATION — registered but logically equivalent
always @(posedge ACLK)
  TVALID <= data_avail & TREADY;
```

---

### C2 — TREADY Combinatorially From TVALID (INFO — flag, not violation)
**Rule**: A Slave IS permitted to derive TREADY combinatorially from TVALID.
This is spec-compliant but creates timing pressure (long path). Flag as INFO
with a suggestion to register TREADY.

```verilog
// Spec-compliant but timing-risky
assign TREADY = ~fifo_full & TVALID;  // INFO: consider registering TREADY
```

---

<a id="x-optional-signals"></a>
## X — Optional Signal Rules

### X1 — Unconnected Optional Signals (INFO)
If TKEEP, TSTRB, TID, TDEST, or TUSER are declared in the port list but
never driven or used, note it as INFO.

### X2 — Missing TKEEP (INFO)
Omission means every lane is kept. Do not warn merely because TDATA is wide;
check whether the application needs partial transfers.

### X3 — TUSER Width Alignment (INFO)
TUSER width not a multiple of (TDATA_WIDTH/8) — note as INFO per spec recommendation.
