# AXI4-Stream Common RTL Violations
*Annotated anti-pattern library — real-world patterns seen in production RTL*

---

## V1 — TVALID Dropped Without Handshake
**Rule**: H1
**Frequency**: Very common — seen in FSM-based masters

```verilog
// ❌ VIOLATION
always @(posedge ACLK or negedge ARESETn) begin
  if (!ARESETn) begin
    TVALID <= 1'b0;
    TDATA  <= '0;
    state  <= IDLE;
  end else begin
    case (state)
      IDLE: begin
        if (fifo_valid) begin
          TVALID <= 1'b1;
          TDATA  <= fifo_data;
          state  <= SEND;
        end
      end
      SEND: begin
        // BUG: drops TVALID regardless of TREADY
        TVALID <= 1'b0;
        state  <= IDLE;
      end
    endcase
  end
end

// ✅ FIXED
      SEND: begin
        if (TREADY) begin          // only transition when slave accepted
          TVALID <= 1'b0;
          state  <= IDLE;
        end
        // If !TREADY: stay in SEND, keep TVALID=1, TDATA stable
      end
```

---

## V2 — Payload Updated During Stall
**Rule**: S1
**Frequency**: Very common — especially when TDATA is fed directly from a counter or FIFO read pointer

```verilog
// ❌ VIOLATION — TDATA changes every clock, ignoring backpressure
always @(posedge ACLK or negedge ARESETn) begin
  if (!ARESETn) begin
    TDATA  <= '0;
    TVALID <= 1'b0;
  end else begin
    TDATA  <= counter;          // ← updates every cycle
    TVALID <= (counter != '0);
    if (TVALID & TREADY)
      counter <= counter - 1;
  end
end

// ✅ FIXED — capture TDATA in a holding register
always @(posedge ACLK or negedge ARESETn) begin
  if (!ARESETn) begin
    TDATA   <= '0;
    TVALID  <= 1'b0;
    held    <= 1'b0;
  end else begin
    if (!held && source_valid) begin
      TDATA  <= source_data;    // latch data
      TVALID <= 1'b1;
      held   <= 1'b1;
    end else if (TVALID & TREADY) begin
      TVALID <= 1'b0;
      held   <= 1'b0;
    end
  end
end
```

---

## V3 — TVALID Gated by TREADY (Combinatorial Loop)
**Rule**: C1, H2
**Frequency**: Common in beginners' RTL — copied from AXI-MM patterns

```verilog
// ❌ VIOLATION — combinatorial loop if slave also gates TREADY on TVALID
assign TVALID = data_ready & TREADY;  // TVALID depends on TREADY

// ❌ VIOLATION — registered version, same logical error
always @(posedge ACLK)
  if (!ARESETn) TVALID <= 0;
  else          TVALID <= data_ready & TREADY;

// ✅ FIXED — TVALID driven by master's own state only
assign TVALID = data_ready;
```

---

## V4 — TVALID Not Reset to 0
**Rule**: R1
**Frequency**: Common when reset is added as an afterthought

```verilog
// ❌ VIOLATION — no reset value for TVALID
always @(posedge ACLK)
  TVALID <= next_valid;

// ❌ VIOLATION — incomplete reset (TDATA reset, TVALID forgotten)
always @(posedge ACLK or negedge ARESETn)
  if (!ARESETn) TDATA <= '0;   // TVALID not cleared!
  else begin
    TDATA  <= next_data;
    TVALID <= next_valid;
  end

// ✅ FIXED
always @(posedge ACLK or negedge ARESETn)
  if (!ARESETn) begin
    TVALID <= 1'b0;
    TDATA  <= '0;
  end else begin
    TDATA  <= next_data;
    TVALID <= next_valid;
  end
```

---

## V5 — TKEEP/TSTRB Width Mismatch
**Rule**: W2, W3
**Frequency**: Seen in parameterized designs with copy-paste errors

```verilog
// ❌ VIOLATION — TDATA is 64-bit, TKEEP should be 8 bits, not 4
module axis_master #(
  parameter DATA_WIDTH = 64
) (
  output [DATA_WIDTH-1:0]   TDATA,
  output [DATA_WIDTH/16-1:0] TKEEP,  // BUG: should be /8
  ...
);

// ✅ FIXED
  output [DATA_WIDTH/8-1:0]  TKEEP,
```

---

## V6 — Null Byte Mid-Packet
**Rule**: K1
**Frequency**: Rare but critical — breaks downstream packet parsers

```verilog
// ❌ VIOLATION — sending sparse TKEEP while TLAST=0
always @(posedge ACLK or negedge ARESETn) begin
  if (!ARESETn) begin
    TKEEP <= '0; TLAST <= 0; TVALID <= 0;
  end else if (start) begin
    TVALID <= 1;
    TLAST  <= 0;
    TKEEP  <= 4'b0011;  // BUG: mid-packet null bytes in lanes [3:2]
    TDATA  <= payload;
  end
end

// ✅ FIXED — mid-packet beats must have all TKEEP bits set
    TKEEP  <= 4'b1111;  // all bytes valid when TLAST=0
// Only on the last beat is partial TKEEP allowed:
    if (last_beat) TKEEP <= partial_keep_mask;
```

---

## V7 — TSTRB Set Where TKEEP Is Clear
**Rule**: K3
**Frequency**: Rare — usually a copy-paste error between TKEEP and TSTRB

```verilog
// ❌ VIOLATION — TSTRB[2]=1 but TKEEP[2]=0
assign TSTRB = 4'b0111;
assign TKEEP = 4'b0011;  // byte lane 2 null but TSTRB says it's a data byte

// ✅ RULE: TSTRB must always be a bitwise subset of TKEEP
// assert((TSTRB & ~TKEEP) == 0) at all times when TVALID=1
```

---

## V8 — TLAST Tied Low (Packet Never Ends)
**Rule**: L3
**Frequency**: Common in "quick integration" code

```verilog
// ❌ WARNING — packet framing disabled
module axis_source (
  output TVALID, TREADY, TDATA,
  output TLAST
);
  assign TLAST = 1'b0;  // packet never ends — downstream may buffer forever
```

---

## V9 — Mixed Reset Styles
**Rule**: R3
**Frequency**: Common in large modules edited by multiple engineers

```verilog
// ❌ WARNING — mixed async and sync resets in same module
always @(posedge ACLK or negedge ARESETn)   // async
  if (!ARESETn) TVALID <= 0;
  else          TVALID <= nxt_valid;

always @(posedge ACLK)                       // sync
  if (!ARESETn) TDATA <= '0;
  else          TDATA <= nxt_data;
```

---

## V10 — TDATA Width Not Multiple of 8
**Rule**: W1
**Frequency**: Seen in DSP datapaths where samples are 12 or 24-bit

```verilog
// ❌ VIOLATION — 12-bit TDATA is not byte-aligned
module adc_stream (
  output [11:0] TDATA,  // ADC is 12-bit — AXI-Stream requires 16-bit here
  ...
);
// ✅ FIXED — zero-pad or sign-extend to 16 bits
  output [15:0] TDATA,  // sample in [11:0], zeros in [15:12]
```

---

## V11 — TID/TDEST Changes Mid-Packet
**Rule**: L2
**Frequency**: Seen in mux/arbitration logic

```verilog
// ❌ VIOLATION — TID updated before TLAST seen
always @(posedge ACLK) begin
  if (switch_stream) begin
    TID   <= new_tid;   // BUG: changes TID while packet in flight
    TDATA <= new_data;
  end
end

// ✅ FIXED — only change TID after TLAST handshake
always @(posedge ACLK) begin
  if (TVALID & TREADY & TLAST)  // packet boundary
    TID <= next_tid;
end
```
