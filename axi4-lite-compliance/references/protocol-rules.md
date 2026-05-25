# AXI4-Lite Protocol Rules Reference
*Based on ARM IHI0022 (AMBA AXI Protocol Specification, AXI4-Lite chapter B1)*

---

## Background — The 5 channels

| Channel | Owner of VALID | Owner of READY | Carries |
|---------|----------------|----------------|---------|
| AW | Master | Slave | AWADDR, AWPROT |
| W  | Master | Slave | WDATA, WSTRB |
| B  | Slave  | Master | BRESP |
| AR | Master | Slave | ARADDR, ARPROT |
| R  | Slave  | Master | RDATA, RRESP |

Every channel has its own VALID/READY handshake — rules H, R, S below apply
**per channel** (multiply count accordingly when reporting).

---

## Table of Contents
1. [H — Handshake Rules](#h-handshake)
2. [R — Reset Rules](#r-reset)
3. [S — Signal Stability Rules](#s-signal-stability)
4. [W — Signal Width Rules](#w-signal-widths)
5. [A — Address Rules](#a-address)
6. [P — Protection & Response Rules](#p-response)
7. [O — Ordering & Deadlock Rules](#o-ordering)
8. [X — Non-Lite Signal Rules](#x-non-lite)

---

## H — Handshake Rules {#h-handshake}

### H1 — VALID Stickiness (CRITICAL — applies to all 5 channels)
**Rule**: Once a source asserts VALID on any channel, it MUST NOT deassert
VALID until the handshake completes (VALID=1 AND READY=1 on the same edge).

**ARM Spec**: A3.2.1 — "Once VALID is asserted it must remain asserted
until the handshake occurs."

**Applies to**: AWVALID, WVALID, BVALID, ARVALID, RVALID — independently.

```verilog
// VIOLATION example
always @(posedge ACLK)
  if (!ARESETn)  BVALID <= 0;
  else if (rsp)  BVALID <= 1;
  else           BVALID <= 0;   // ← drops BVALID even if BREADY=0

// FIX
always @(posedge ACLK)
  if (!ARESETn)              BVALID <= 0;
  else if (BVALID & BREADY)  BVALID <= 0;  // clear only after handshake
  else if (rsp)              BVALID <= 1;
```

---

### H2 — VALID Must Not Be Gated on READY (CRITICAL — all 5 channels)
**Rule**: The source must not wait for the destination's READY to assert
its own VALID. VALID is driven by the source's own readiness only.

**ARM Spec**: A3.2.1

```verilog
// VIOLATION
assign AWREADY = aw_room & AWVALID;  // OK (slave can do this for AW)
assign BVALID  = rsp_ready & BREADY; // ← VIOLATION — BVALID gated on BREADY
```

---

### H3 — Destination READY May Precede VALID (INFO)
**Rule**: A destination IS permitted to assert READY before VALID is seen.
Do not flag READY toggling without VALID as a violation.

---

### H4 — Both Required for Transfer (INFO)
**Rule**: A transfer on any channel occurs on the rising ACLK edge
when both VALID=1 AND READY=1.

---

## R — Reset Rules {#r-reset}

### R1 — All VALID Outputs LOW After Reset (CRITICAL — per channel)
**Rule**: After ARESETn is deasserted (or after synchronous reset),
the source on each channel must drive VALID LOW for at least the
first clock edge. The destination must drive READY LOW or be in a known state.

**ARM Spec**: A3.1.2 — "The earliest point after reset that a master is
permitted to begin driving ARVALID, AWVALID, or WVALID HIGH is at a
rising ACLK edge after ARESETn is HIGH."

**RTL check**: Reset branch of every register driving AWVALID, WVALID,
BVALID, ARVALID, RVALID must set it to 0. Missing reset on any of these is
a CRITICAL bug.

---

### R2 — ARESETn Active-Low Required (WARNING)
**Rule**: Global reset is named ARESETn and is active-LOW. Active-high
or other names (`rst`, `resetb`, `reset_n`) are non-standard and risk
integration errors.

---

### R3 — Reset Style Consistency (WARNING)
**Rule**: All flip-flops in the same clock domain should use the same
reset style (all sync or all async). Mixing within a module is a common
synthesis hazard.

---

## S — Signal Stability Rules {#s-signal-stability}

### S1 — Payload Stable During Stall (CRITICAL — per channel)
**Rule**: While VALID=1 and READY=0 on any channel, every payload signal
on that channel MUST remain stable:

| Channel | Stable signals during stall |
|---------|------------------------------|
| AW | AWADDR, AWPROT |
| W  | WDATA, WSTRB |
| B  | BRESP |
| AR | ARADDR, ARPROT |
| R  | RDATA, RRESP |

**ARM Spec**: A3.2.1

```verilog
// VIOLATION — RDATA changes during a stall
always @(posedge ACLK)
  RDATA <= reg_file[ARADDR[7:2]];  // updates every cycle

// FIX — only update payload when transfer happens, or before VALID asserts
always @(posedge ACLK)
  if (!ARESETn)              RDATA <= '0;
  else if (read_accept)      RDATA <= reg_file[ARADDR[7:2]];  // capture once
  // else: hold value while RVALID stays high awaiting RREADY
```

---

## W — Signal Width Rules {#w-signal-widths}

### W1 — Data Width Must Be 32 or 64 (CRITICAL)
**Rule**: AXI4-Lite supports only `DATA_WIDTH = 32` or `DATA_WIDTH = 64`.
Any other width (16, 24, 128, ...) means the interface is NOT AXI4-Lite.

**ARM Spec**: B1.1 — "AXI4-Lite supports a data bus width of either 32-bit
or 64-bit."

---

### W2 — WSTRB Width Must Equal DATA_WIDTH/8 (CRITICAL)
**Rule**: WSTRB is one strobe bit per byte lane of WDATA. For 32-bit data,
WSTRB is 4 bits; for 64-bit data, WSTRB is 8 bits.

---

### W3 — AWPROT / ARPROT Must Be 3 Bits (CRITICAL)
**Rule**: AWPROT and ARPROT are exactly 3 bits wide, encoding
{Instruction/Data, Non-secure/Secure, Privileged/Unprivileged}.
Wider or narrower violates the spec.

```verilog
// VIOLATION
output [3:0] awprot;   // ← 4 bits, should be 3

// CORRECT
output [2:0] awprot;
```

---

### W4 — BRESP / RRESP Must Be 2 Bits (CRITICAL)
**Rule**: BRESP and RRESP are exactly 2 bits. See P1/P2 for value rules.

---

### W5 — Address Width Recommendation (INFO)
**Rule**: AXI4-Lite does not mandate an address width, but typical CSR
slaves use 12–32 bits. Widths outside this range are unusual — flag for
review.

---

## A — Address Rules {#a-address}

### A1 — Address Must Be Aligned to Data Bus Width (CRITICAL)
**Rule**: AWADDR and ARADDR must be aligned to the data bus width.
- For 32-bit data: AWADDR[1:0] == 2'b00 (4-byte aligned)
- For 64-bit data: AWADDR[2:0] == 3'b000 (8-byte aligned)

**ARM Spec**: A3.3.1 — "AXI4-Lite supports aligned transfers only."

**RTL check**: If the slave does not ignore or check the low address bits,
unaligned masters will silently corrupt data. The slave SHOULD either:
- Tie off the low bits in the decoder (e.g., `reg_idx = AWADDR[11:2]`), AND
- Return SLVERR for unaligned writes (defensive).

---

### A2 — AWADDR Width Should Equal ARADDR Width (INFO)
**Rule**: A slave generally has identical AWADDR and ARADDR widths.
Different widths are unusual — flag for review.

---

## P — Protection & Response Rules {#p-response}

### P1 — BRESP / RRESP Encoding (CRITICAL)
**Rule**: The 2-bit response codes have these legal encodings in AXI4-Lite:

| Encoding | Name | Meaning |
|----------|------|---------|
| `2'b00`  | OKAY    | Normal access success |
| `2'b01`  | EXOKAY  | **ILLEGAL in AXI4-Lite** (exclusive access not supported) |
| `2'b10`  | SLVERR  | Slave error (e.g., unaligned address, invalid register) |
| `2'b11`  | DECERR  | Decode error (no slave at this address) |

**ARM Spec**: B1.1.1 — "AXI4-Lite does not support exclusive accesses."

```verilog
// VIOLATION — EXOKAY response
assign BRESP = 2'b01;  // ← Illegal in AXI4-Lite, will confuse masters
```

---

### P2 — Slave Should Detect Decode Errors (INFO)
**Rule**: A well-behaved slave returns DECERR for accesses to unmapped
addresses within its region, and SLVERR for known-bad accesses (write to
read-only register, unaligned access, etc.). Pure OKAY-only slaves miss
useful diagnostics.

---

### P3 — AWPROT / ARPROT Default Handling (INFO)
**Rule**: Many simple slaves ignore AWPROT/ARPROT entirely (treating all
accesses as data/non-secure/unprivileged). This is acceptable but should
be documented.

---

## O — Ordering & Deadlock Rules {#o-ordering}

### O1 — B Response After AW AND W Handshakes (CRITICAL)
**Rule**: The slave MUST NOT assert BVALID until BOTH the AW handshake
AND the W handshake of the same transaction have completed.

**ARM Spec**: A3.3.1 — "A slave must wait for both AWVALID and AWREADY to
be asserted before asserting BVALID. A slave must also wait for WVALID
and WREADY to be asserted before asserting BVALID."

```verilog
// VIOLATION — BVALID asserted on AW handshake alone
always @(posedge ACLK)
  if (AWVALID & AWREADY)
    BVALID <= 1'b1;   // ← wrong — must wait for W handshake too

// FIX
reg aw_done, w_done;
always @(posedge ACLK) begin
  if (AWVALID & AWREADY) aw_done <= 1;
  if (WVALID  & WREADY ) w_done  <= 1;
  if (aw_done & w_done) begin
    BVALID  <= 1;
    aw_done <= 0;
    w_done  <= 0;
  end else if (BVALID & BREADY) begin
    BVALID <= 0;
  end
end
```

---

### O2 — R Response After AR Handshake (CRITICAL)
**Rule**: The slave MUST NOT assert RVALID until the AR handshake
(ARVALID & ARREADY) has completed.

```verilog
// VIOLATION
assign RVALID = read_pending;  // asserted before AR handshake captured

// FIX — track that AR was accepted
always @(posedge ACLK)
  if (!ARESETn)               RVALID <= 0;
  else if (ARVALID & ARREADY) RVALID <= 1;
  else if (RVALID & RREADY)   RVALID <= 0;
```

---

### O3 — Inter-Channel Deadlock Avoidance (CRITICAL)
**Rule**: VALID on one channel must not combinatorially depend on READY of
another channel. Doing so creates a deadlock when the destination of the
other channel is waiting on the first.

**Common deadlock examples**:

```verilog
// VIOLATION — AWREADY gated on BREADY
assign AWREADY = aw_capacity & BREADY;
// Deadlock if master sets BREADY low until it sees BVALID — slave never
// accepts AW, never produces B, never sets BVALID.

// VIOLATION — BVALID waiting for AW to be ready (cyclic)
assign BVALID = aw_done & ~AWVALID;
```

**Rule of thumb**: Each channel's VALID/READY logic should depend on
internal state and that channel's own counterpart signal — not on other
channels' handshake signals.

---

## X — Non-Lite Signal Rules {#x-non-lite}

### X1 — Burst Signals Must NOT Be Present (CRITICAL if found)
**Rule**: AXI4-Lite supports only single-beat transactions. The following
**Full AXI4** signals must NOT appear on an AXI4-Lite interface:

- AWLEN, AWSIZE, AWBURST, AWLOCK, AWCACHE, AWQOS, AWREGION, AWID
- ARLEN, ARSIZE, ARBURST, ARLOCK, ARCACHE, ARQOS, ARREGION, ARID
- WLAST, WID
- BID
- RLAST, RID

If any of these are present, the interface is **Full AXI4, not AXI4-Lite**.

**RTL check**: Search the port list. Their presence alone disqualifies
the module as AXI4-Lite.

---

### X2 — Optional Sideband Signals (INFO)
Some vendor-specific AXI4-Lite implementations add optional signals
(e.g. AWUSER, RUSER). These are tolerated in practice but not part of
the AXI4-Lite spec — note as INFO.

---

### X3 — Tied-Off PROT Bits (INFO)
If AWPROT/ARPROT are present but always tied to 3'b000, that's acceptable
for simple slaves — note as INFO so the designer knows the slave is
non-protection-aware.
