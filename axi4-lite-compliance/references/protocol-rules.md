# AXI4-Lite Protocol Rules Reference
*Baseline: Arm IHI0022H, sections A3 and B1.*

[Arm specification](https://developer.arm.com/documentation/ihi0022/h)
contains the source requirements; distinguish them from register-map policy.

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

<a id="h-handshake"></a>
## H — Handshake Rules

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
assign AWREADY = aw_room & AWVALID;  // violates H5: combinatorial input/output path
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

### H5 — No Combinatorial Input-to-Output Paths (CRITICAL)
A3.1.1/A3.2 prohibit combinatorial paths between interface inputs and
outputs, including VALID-to-READY. Waiting for VALID is allowed through
registered logic. This timing rule is separate from H2's logical dependency.

<a id="r-reset"></a>
## R — Reset Rules

### R1 — VALID Reset Behavior (CRITICAL — per driven channel)
During reset, master AWVALID/WVALID/ARVALID and slave BVALID/RVALID must be
LOW. They may assert after a rising ACLK edge with reset inactive (A3.1.2).
READY has no mandatory LOW reset value. Check driven outputs and state
feeding them; an input VALID belongs to the opposite endpoint.

### R2 — Reset Polarity and Mapping
The interface reset is active-low. Custom RTL names and an internal inverted
reset are legal; trace the actual mapping before reporting a polarity bug.

### R3 — Reset Implementation Review (INFO)
Mixed synchronous/asynchronous register resets are not themselves an AXI
violation. Check externally visible VALID reset behavior and synchronous
reset release; do not require payload registers to share a reset style.

<a id="s-signal-stability"></a>
## S — Signal Stability Rules

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

<a id="w-signal-widths"></a>
## W — Signal Width Rules

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

<a id="a-address"></a>
## A — Address Rules

### A1 — Address and Byte-Lane Handling
Do not impose a blanket aligned-address-only rule or mandatory SLVERR on
nonzero low address bits. Check address/WSTRB consistency and the documented
register-map policy (A3.4 and B1.1). A word-index decoder alone is not a bug.

### A2 — AWADDR Width Should Equal ARADDR Width (INFO)
**Rule**: A slave generally has identical AWADDR and ARADDR widths.
Different widths are unusual — flag for review.

---

<a id="p-response"></a>
## P — Protection & Response Rules

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

### P2 — Error Response Policy (INFO)
Check the documented register-map policy. Do not require every slave to
produce DECERR for internal holes or reject all unaligned addresses.

### P3 — AWPROT / ARPROT Default Handling (INFO)
**Rule**: Many simple slaves ignore AWPROT/ARPROT entirely (treating all
accesses as data/non-secure/unprivileged). This is acceptable but should
be documented.

---

<a id="o-ordering"></a>
## O — Ordering & Deadlock Rules

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

// Illustrative bookkeeping only: reset flags/VALID, gate AWREADY/WREADY
// by storage capacity, and do not accept a new pair while B is stalled.
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
assign RVALID = ARVALID;  // can assert before any AR handshake

// FIX — track that AR was accepted; ARREADY must prevent overwriting
// a stalled response, and RDATA/RRESP must be held with RVALID.
always @(posedge ACLK)
  if (!ARESETn)               RVALID <= 0;
  else if (ARVALID & ARREADY) RVALID <= 1;
  else if (RVALID & RREADY)   RVALID <= 0;
```

---

### O3 — Inter-Channel Deadlock Avoidance (CRITICAL when demonstrated)
Check legal AW-before-W, W-before-AW, simultaneous requests, and stalled
responses. A slave may wait for both AWVALID and WVALID before accepting a
write; the master must offer WVALID without waiting for AWREADY (A3.3).
A slave cannot require BREADY before producing BVALID. Buffer-capacity
backpressure is legal: refusing new requests while a response is pending
is not inherently deadlock. Show a feasible circular wait, not just a
cross-channel dependency. Apply H5 separately to combinatorial paths.

<a id="x-non-lite"></a>
## X — Non-Lite Signal Rules

### X1 — Classify Each Interface Before Reporting
AXI4-Lite transfers are single-beat. Burst-control ports require checking
whether the boundary is Full AXI, a constrained compatibility wrapper, or
one side of a bridge. Port names alone do not prove illegal behavior.
Optional ID reflection is explicitly supported (B1.1.4, B1.2): AWID/ARID
and BID/RID alone do not disqualify a Lite slave. Check response-ID pairing.
Report a violation when behavior exceeds the claimed Lite contract.

### X2 — Optional Sideband Signals (INFO)
Some vendor-specific AXI4-Lite implementations add optional signals
(e.g. AWUSER, RUSER). These are tolerated in practice but not part of
the AXI4-Lite spec — note as INFO.

---

### X3 — Tied-Off PROT Bits (INFO)
If AWPROT/ARPROT are present but always tied to 3'b000, that's acceptable
for simple slaves — note as INFO so the designer knows the slave is
non-protection-aware.
