# AXI4-Stream Protocol Rules Reference
*Based on ARM IHI0051B (AMBA AXI-Stream Protocol Specification)*

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

## H — Handshake Rules {#h-handshake}

### H1 — TVALID Stickiness (CRITICAL if violated)
**Rule**: Once a Master asserts TVALID, it MUST NOT deassert TVALID until the
handshake completes (i.e., until the clock edge where both TVALID=1 and TREADY=1).

**ARM Spec**: Section 2.2.1 — "A Transmitter is not permitted to withdraw a
transfer once TVALID has been asserted."

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

## R — Reset Rules {#r-reset}

### R1 — TVALID Must Be LOW After Reset (CRITICAL if violated)
**Rule**: After deassertion of ARESETn (or after synchronous reset), TVALID
must be driven LOW. The Master must not assert TVALID until reset is fully
deasserted.

**ARM Spec**: Section 2.7 — "A master interface must drive TVALID LOW for the
first clock cycle after ARESETn goes HIGH."

**RTL check**: The reset branch of every TVALID register must set it to 0.

```verilog
// CORRECT
always @(posedge ACLK or negedge ARESETn)
  if (!ARESETn) TVALID <= 1'b0;   // ← required
  else          TVALID <= next_valid;

// VIOLATION — TVALID not reset
always @(posedge ACLK)
  TVALID <= next_valid;
```

---

### R2 — ARESETn Must Be Active-Low (WARNING if polarity wrong)
**Rule**: The global reset is named ARESETn and is active-LOW.

**RTL check**: Reset sensitivity in `always` blocks should use `negedge ARESETn`
(async) or `if (!ARESETn)` / `if (~ARESETn)` (sync). Signals named `ARESETN`
used as active-high are non-standard.

---

### R3 — Reset Style Consistency (WARNING if mixed)
**Rule**: All flip-flops in the same clock domain should use the same reset style
(all synchronous OR all asynchronous). Mixing within the same module is a common
source of CDC and synthesis issues.

---

### R4 — TREADY After Reset (INFO)
**Rule**: The spec does not mandate a specific reset value for TREADY. A Slave
may come out of reset with TREADY=0 or TREADY=1.

---

## S — Signal Stability Rules {#s-signal-stability}

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

## W — Signal Width Rules {#w-signal-widths}

### W1 — TDATA Width Must Be a Multiple of 8 Bits (CRITICAL if violated)
**Rule**: TDATA must be N×8 bits wide (byte-aligned). Widths of 7, 15, 24, etc.
are non-compliant.

**ARM Spec**: Section 2.3 — data bus width defined in bytes.

**RTL check**: `(TDATA_WIDTH % 8 == 0)` and TDATA_WIDTH ∈ {8, 16, 32, 64, 128, 256, 512, 1024}.

---

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

## K — TKEEP / TSTRB Rules {#k-tkeep-tstrb}

### K1 — No Null Bytes Mid-Packet (CRITICAL if violated)
**Rule**: When TLAST=0 (packet not yet finished), ALL bits of TKEEP must be 1.
Null bytes (TKEEP=0 for a byte lane) are only allowed on the last beat (TLAST=1).

**ARM Spec**: Section 2.4 — Byte qualifiers

**RTL check**: If TLAST is driven LOW while TKEEP has any zero bits, that is a violation.

```verilog
// VIOLATION example (conceptual):
// TLAST=0, TKEEP=8'b00001111  ← mid-packet null bytes
```

---

### K2 — Null Bytes at Last Beat Ordering (WARNING)
**Rule**: On the last beat (TLAST=1), null bytes (TKEEP=0) must only occupy
the most-significant byte lanes (high-order positions). Having null bytes
below valid bytes is non-standard.

Example for 4-byte bus, 3 valid bytes:
- CORRECT: `TKEEP = 4'b0111` (null byte at MSB)
- NON-STANDARD: `TKEEP = 4'b1110` (null byte at LSB)

---

### K3 — TSTRB Must Be Subset of TKEEP (CRITICAL if violated)
**Rule**: `TSTRB & ~TKEEP` must always be zero — i.e., a byte cannot be a
data/position byte if its TKEEP bit is 0.
`TSTRB[i]=1` is only valid when `TKEEP[i]=1`.

---

### K4 — TSTRB Without TKEEP (WARNING)
**Rule**: If TSTRB is present but TKEEP is absent, position bytes are not
supported by the interface. This is an unusual configuration — flag for review.

---

## L — TLAST / Packet Framing Rules {#l-tlast}

### L1 — TLAST Marks End of Packet (INFO)
**Rule**: TLAST is asserted on the last beat of a packet. It is optional — if
absent, every transfer is implicitly a single-beat packet.

---

### L2 — TID/TDEST Must Not Change Mid-Packet (CRITICAL if violated)
**Rule**: When `Continuous_Packets` mode is used, TID and TDEST must not change
while TLAST=0. For general interconnects, changing TID/TDEST mid-packet causes
interleaving issues.

**RTL check**: If TID or TDEST is updated without a preceding TLAST=1 handshake,
that is a violation in continuous-packet contexts.

---

### L3 — TLAST Tied LOW (WARNING)
**Rule**: Tying TLAST permanently LOW means packets never end. This is technically
allowed only for infinite byte-stream interfaces with no packet boundaries.
In most IP designs, this is a bug.

**RTL check**: `assign TLAST = 1'b0;` — flag as warning with explanation.

---

### L4 — TLAST Must Change Only on Transfer (relates to S1)
**Rule**: TLAST is a payload signal. While TVALID=1 and TREADY=0, TLAST
must not change (covered by S1 but worth calling out explicitly).

---

## C — Combinatorial Dependency Rules {#c-combinatorial}

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

## X — Optional Signal Rules {#x-optional-signals}

### X1 — Unconnected Optional Signals (INFO)
If TKEEP, TSTRB, TID, TDEST, or TUSER are declared in the port list but
never driven or used, note it as INFO.

### X2 — Missing TKEEP With Non-Byte-Granular TDATA (WARNING)
If TDATA is wider than 8 bits and TKEEP is absent, the interface cannot
express partial last-beat transfers. Acceptable for fixed-width payloads
but worth flagging.

### X3 — TUSER Width Alignment (INFO)
TUSER width not a multiple of (TDATA_WIDTH/8) — note as INFO per spec recommendation.
