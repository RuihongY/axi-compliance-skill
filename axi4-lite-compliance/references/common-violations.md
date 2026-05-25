# AXI4-Lite Common RTL Violations
*Annotated anti-pattern library for AMBA AXI4-Lite*

The bugs below appear repeatedly in homemade register banks, vendor wizard
output that has been hand-edited, and quickly-written CSR slaves.

---

## V1 — BVALID Asserted Before W Handshake (Ordering)
**Rule**: O1
**Frequency**: Very common in beginner register banks

```verilog
// ❌ VIOLATION — slave responds to AW alone, ignoring W
always @(posedge ACLK or negedge ARESETn) begin
  if (!ARESETn) begin
    AWREADY <= 1'b0;
    BVALID  <= 1'b0;
    BRESP   <= 2'b00;
  end else begin
    if (AWVALID & ~AWREADY) AWREADY <= 1'b1;
    if (AWVALID & AWREADY) begin
      BVALID <= 1'b1;        // ← BUG: responds before W is accepted
      BRESP  <= 2'b00;
    end else if (BVALID & BREADY) begin
      BVALID <= 1'b0;
    end
  end
end
```

```verilog
// ✅ FIXED — track BOTH AW and W completion
reg aw_captured, w_captured;
always @(posedge ACLK or negedge ARESETn) begin
  if (!ARESETn) begin
    AWREADY     <= 1'b0;
    WREADY      <= 1'b0;
    BVALID      <= 1'b0;
    aw_captured <= 1'b0;
    w_captured  <= 1'b0;
  end else begin
    // AW handshake
    if (AWVALID & ~AWREADY & ~aw_captured) AWREADY <= 1'b1;
    if (AWVALID & AWREADY) begin
      aw_captured <= 1'b1;
      AWREADY     <= 1'b0;
    end
    // W handshake (independent of AW)
    if (WVALID & ~WREADY & ~w_captured) WREADY <= 1'b1;
    if (WVALID & WREADY) begin
      w_captured <= 1'b1;
      WREADY     <= 1'b0;
    end
    // B response only once BOTH AW and W have been captured
    if (aw_captured & w_captured & ~BVALID) begin
      BVALID <= 1'b1;
      BRESP  <= 2'b00;
    end else if (BVALID & BREADY) begin
      BVALID      <= 1'b0;
      aw_captured <= 1'b0;
      w_captured  <= 1'b0;
    end
  end
end
```

---

## V2 — RVALID Asserted Without AR Handshake
**Rule**: O2
**Frequency**: Common in combinatorial read-data paths

```verilog
// ❌ VIOLATION — RVALID is high whenever the master tries to read
assign RVALID = ARVALID;
assign RDATA  = reg_file[ARADDR[7:2]];

// Problem: if ARREADY=0 (slave busy), RVALID is still asserted but the
// AR handshake never completed — master may use stale or wrong data.
```

```verilog
// ✅ FIXED
reg ar_captured;
reg [ADDR_W-1:0] captured_addr;
always @(posedge ACLK or negedge ARESETn)
  if (!ARESETn) begin
    ARREADY     <= 1'b0;
    ar_captured <= 1'b0;
    RVALID      <= 1'b0;
  end else begin
    if (ARVALID & ~ARREADY & ~ar_captured) ARREADY <= 1'b1;
    if (ARVALID & ARREADY) begin
      ar_captured   <= 1'b1;
      captured_addr <= ARADDR;
      ARREADY       <= 1'b0;
    end
    if (ar_captured & ~RVALID) begin
      RDATA  <= reg_file[captured_addr[7:2]];
      RRESP  <= 2'b00;
      RVALID <= 1'b1;
    end else if (RVALID & RREADY) begin
      RVALID      <= 1'b0;
      ar_captured <= 1'b0;
    end
  end
```

---

## V3 — EXOKAY Response (Illegal in Lite)
**Rule**: P1
**Frequency**: Seen when code is copy-pasted from Full AXI4 examples

```verilog
// ❌ VIOLATION — BRESP=2'b01 (EXOKAY) is not allowed in AXI4-Lite
always @(posedge ACLK) begin
  if (exclusive_write_succeeded)
    BRESP <= 2'b01;   // EXOKAY — only valid in Full AXI4 exclusive access
end

// ✅ FIXED — use OKAY; if exclusive access support is needed, you need
// Full AXI4, not Lite.
always @(posedge ACLK) BRESP <= 2'b00;  // OKAY
```

---

## V4 — Wrong DATA_WIDTH
**Rule**: W1
**Frequency**: Common in custom slaves where designers pick a "logical" width

```verilog
// ❌ VIOLATION — 16-bit data is not AXI4-Lite
module my_csr_slave (
  output reg [15:0] RDATA,    // ← only 32 or 64 allowed
  output reg [ 1:0] WSTRB,    // ← width also wrong (should be DATA/8)
  ...
);

// ✅ FIXED — pad to 32-bit
module my_csr_slave (
  output reg [31:0] RDATA,
  output reg [ 3:0] WSTRB,
  ...
);
```

---

## V5 — AWPROT / ARPROT Wrong Width
**Rule**: W3
**Frequency**: Common — engineers often pick 4 bits or 1 bit

```verilog
// ❌ VIOLATION
input  [3:0] AWPROT;   // 4 bits — incompatible with standard masters
input        ARPROT;   // 1 bit  — equally wrong

// ✅ FIXED
input  [2:0] AWPROT;   // exactly 3 bits per spec
input  [2:0] ARPROT;
```

---

## V6 — WSTRB Width Mismatch
**Rule**: W2
**Frequency**: Common when DATA_WIDTH is parameterized but WSTRB is hardcoded

```verilog
// ❌ VIOLATION — 64-bit data needs 8-bit WSTRB, not 4
module slave #(parameter DATA_W = 64) (
  input [DATA_W-1:0] WDATA,
  input [       3:0] WSTRB,   // ← should be DATA_W/8 = 8 bits
);

// ✅ FIXED
  input [DATA_W/8-1:0] WSTRB,
```

---

## V7 — Slave Ignores WSTRB
**Rule**: Not a hard violation, but a common bug
**Frequency**: Very common

```verilog
// ⚠️ WARNING — write always updates all 32 bits, ignoring WSTRB
if (w_handshake)
  reg_file[awaddr_capt] <= WDATA;

// ✅ BETTER — honor byte enables
if (w_handshake) begin
  if (WSTRB[0]) reg_file[awaddr_capt][ 7: 0] <= WDATA[ 7: 0];
  if (WSTRB[1]) reg_file[awaddr_capt][15: 8] <= WDATA[15: 8];
  if (WSTRB[2]) reg_file[awaddr_capt][23:16] <= WDATA[23:16];
  if (WSTRB[3]) reg_file[awaddr_capt][31:24] <= WDATA[31:24];
end
```

---

## V8 — Inter-Channel Deadlock (AWREADY Waiting on BREADY)
**Rule**: O3
**Frequency**: Rare but catastrophic when it happens

```verilog
// ❌ VIOLATION — creates deadlock
// Designer reasoning: "Don't accept a new write until the master takes the last B response"
assign AWREADY = ~BVALID;

// Deadlock case: master raises BREADY only after seeing BVALID.
// 1. Master asserts AWVALID, waits for AWREADY.
// 2. Slave keeps AWREADY=0 because BVALID=0 (no outstanding response).
// 3. Without AW handshake, no write happens, no B is generated.
// 4. BVALID never asserts, master never sees response, BREADY may stay low.
// 5. → AWREADY stays low forever → deadlock.

// ✅ FIXED — single-outstanding by tracking an in-flight flag
reg in_flight;
assign AWREADY = AWVALID & ~in_flight;
always @(posedge ACLK)
  if (!ARESETn)            in_flight <= 0;
  else if (AW & W done)    in_flight <= 1;
  else if (BVALID & BREADY) in_flight <= 0;
```

---

## V9 — Burst Signals Present (Not AXI4-Lite!)
**Rule**: X1
**Frequency**: Common in copy-paste from AXI4 Full examples

```verilog
// ❌ VIOLATION — these signals do not belong on AXI4-Lite
module my_lite_slave (
  input        AWVALID, AWREADY,
  input [ 7:0] AWLEN,    // ← burst length: Full AXI only
  input [ 2:0] AWSIZE,   // ← burst size: Full AXI only
  input [ 1:0] AWBURST,  // ← burst type: Full AXI only
  input [ 3:0] AWID,     // ← transaction ID: Full AXI only
  ...
);

// ✅ FIXED — strip them out; for AXI4-Lite, only AWADDR + AWPROT on AW
```

---

## V10 — Read Data Updated During Stall
**Rule**: S1
**Frequency**: Common in combinatorial read paths

```verilog
// ❌ VIOLATION — RDATA recomputed every cycle while RVALID is high
always @(posedge ACLK)
  RDATA <= reg_file[ARADDR[7:2]];  // ARADDR may change after AR handshake

// ✅ FIXED — capture address at AR handshake, hold RDATA stable until RREADY
always @(posedge ACLK) begin
  if (ARVALID & ARREADY)
    captured_addr <= ARADDR;
  if (ar_captured & ~RVALID)
    RDATA <= reg_file[captured_addr[7:2]];  // captured once
end
```

---

## V11 — TVALID/AWVALID Not Reset
**Rule**: R1
**Frequency**: Common when reset is added as an afterthought

```verilog
// ❌ VIOLATION — BVALID, RVALID have no reset value
always @(posedge ACLK) begin
  if (cond1) BVALID <= 1;
  if (cond2) RVALID <= 1;
end

// ✅ FIXED — ALL VALID outputs must be reset to 0
always @(posedge ACLK or negedge ARESETn) begin
  if (!ARESETn) begin
    BVALID <= 1'b0;
    RVALID <= 1'b0;
    // Plus AWREADY, WREADY, ARREADY also reset to a known state
  end else begin
    ...
  end
end
```
