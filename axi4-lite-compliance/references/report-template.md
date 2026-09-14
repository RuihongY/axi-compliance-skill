# AXI4-Lite Report Template & Severity Definitions

---

## Severity Levels

| Level | Emoji | Meaning |
|-------|-------|---------|
| CRITICAL | 🔴 | Direct violation of ARM AXI4-Lite spec (IHI0022). Causes deadlock, data corruption, or master-slave mismatch. Must fix. |
| WARNING  | 🟡 | Deviation from spec recommendations or pattern that causes interoperability problems. Should fix. |
| INFO     | 🔵 | Observation, non-standard but compliant pattern, or missing optional capability. |

---

## Report Skeleton

````markdown
## AXI4-Lite Compliance Report

### Interface Summary
- **Role**: Slave / Master / Bridge
- **Language**: Verilog / SystemVerilog
- **Channels implemented**: AW, W, B, AR, R  (or subset — e.g., read-only slave)
- **Data width**: 32 / 64
- **Address width**: N bits
- **Optional signals**: AWPROT[2:0], WSTRB[3:0]
- **Reset style**: Async active-low (ARESETn) / Synchronous
- **Code completeness**: Full module / Partial snippet

---

### Findings

#### 🔴 CRITICAL — X issue(s) found

**[C-1] Rule O1 — BVALID Asserted Before W Handshake**
- **Channel**: Write Response (B)
- **Location**: `my_slave.sv`, line 47, write FSM
- **What's wrong**: BVALID is asserted as soon as AWVALID & AWREADY occur,
  without waiting for the W channel handshake. Spec requires both AW and W
  to complete before the slave generates a response.
- **Risk**: The master receives a "write complete" response before the data
  has been delivered, causing silent data loss.
- **Fix**: Track both `aw_done` and `w_done` flags and only assert BVALID
  when both are set. See code below.

---

#### 🟡 WARNING — Y issue(s) found

**[W-1] Documented Endpoint Compatibility Mismatch**
- **Location**: Cite the actual RTL and endpoint requirement.
- **Issue**: State the known contract and a feasible incompatible transfer.
- **Fix**: Adapt the endpoint or bridge to the required behavior.
- Do not instantiate this example without evidence of a mismatch.

---

#### 🔵 INFO — Z note(s)

**[I-1] Slave Ignores WSTRB**
- **Channel**: Write Data (W), lines 60–63
- **What's wrong**: Writes always overwrite all 32 bits; byte-enable
  information from WSTRB is discarded.
- **Note**: Classify the endpoint: a memory slave must honor strobes; a
  register slave may document full-word-only writes or reject unsupported masks.

---

### Corrected Code Snippets

*(Only for CRITICAL findings — show side-by-side)*

**Fix for [C-1]** — wait for both AW and W:

```verilog
// BEFORE (violating):
if (AWVALID & AWREADY) begin
  BVALID <= 1'b1;
  BRESP  <= 2'b00;
end

// AFTER (bookkeeping excerpt): reset these registers and gate request
// acceptance by per-channel capacity until the B response is consumed.
if (AWVALID & AWREADY) aw_done <= 1'b1;
if (WVALID  & WREADY ) w_done  <= 1'b1;
if (aw_done & w_done & ~BVALID) begin
  BVALID  <= 1'b1;
  BRESP   <= 2'b00;
end else if (BVALID & BREADY) begin
  BVALID  <= 1'b0;
  aw_done <= 1'b0;
  w_done  <= 1'b0;
end
```

---

### Verification Suggestions

Add these SVA properties — they catch the most common AXI4-Lite bugs:

```systemverilog
// AW channel: VALID stickiness (H1)
property awvalid_sticky;
  @(posedge ACLK) disable iff (!ARESETn)
  (AWVALID && !AWREADY) |=> AWVALID;
endproperty
assert property (awvalid_sticky);

// W channel: VALID stickiness (H1)
property wvalid_sticky;
  @(posedge ACLK) disable iff (!ARESETn)
  (WVALID && !WREADY) |=> WVALID;
endproperty
assert property (wvalid_sticky);

// B channel: VALID stickiness (H1)
property bvalid_sticky;
  @(posedge ACLK) disable iff (!ARESETn)
  (BVALID && !BREADY) |=> BVALID;
endproperty
assert property (bvalid_sticky);

// AR channel: VALID stickiness (H1)
property arvalid_sticky;
  @(posedge ACLK) disable iff (!ARESETn)
  (ARVALID && !ARREADY) |=> ARVALID;
endproperty
assert property (arvalid_sticky);

// R channel: VALID stickiness (H1)
property rvalid_sticky;
  @(posedge ACLK) disable iff (!ARESETn)
  (RVALID && !RREADY) |=> RVALID;
endproperty
assert property (rvalid_sticky);

// Payload stability — example for B channel (S1)
property bresp_stable;
  @(posedge ACLK) disable iff (!ARESETn)
  (BVALID && !BREADY) |=> $stable(BRESP);
endproperty
assert property (bresp_stable);

// Payload stability — R channel (S1)
property rdata_stable;
  @(posedge ACLK) disable iff (!ARESETn)
  (RVALID && !RREADY) |=> $stable(RDATA) && $stable(RRESP);
endproperty
assert property (rdata_stable);

// Ordering: B only after AW+W (O1) — needs scoreboard tracking
// (Simplified: B count <= min(AW count, W count) at any time)

// Ordering: R only after AR (O2)
// (Simplified: R count <= AR count at any time)

// Response codes (P1) — EXOKAY forbidden in Lite
property bresp_legal;
  @(posedge ACLK) disable iff (!ARESETn)
  BVALID |-> (BRESP != 2'b01);
endproperty
assert property (bresp_legal)
  else $error("AXI-Lite: BRESP=EXOKAY is illegal");

property rresp_legal;
  @(posedge ACLK) disable iff (!ARESETn)
  RVALID |-> (RRESP != 2'b01);
endproperty
assert property (rresp_legal)
  else $error("AXI-Lite: RRESP=EXOKAY is illegal");

// Sampled reset check (R1). Select implemented channels and DUT outputs;
// verify reset release timing separately.
property valids_low_after_reset;
  @(posedge ACLK)
  !ARESETn |-> (!AWVALID && !WVALID && !BVALID && !ARVALID && !RVALID);
endproperty
assert property (valids_low_after_reset);
```

---

### Overall Assessment

| Result | Criteria |
|--------|----------|
| ✅ **PASS** | No findings within a sufficiently complete, stated review scope |
| ⚠️ **PASS WITH WARNINGS** | Sufficient review scope, no proven violations, documented compatibility concerns |
| ❌ **FAIL** | At least one demonstrated violation (list any unchecked areas too) |
| **INCONCLUSIVE** | No demonstrated violation, but essential logic/configuration is unavailable |

**Result**: [Fill in]
**Summary**: [1-2 sentence plain-language summary for the engineer]
````

---

## Notes for Claude

- Always specify **which channel** a finding applies to (AW/W/B/AR/R).
  AXI4-Lite has 5 independent handshakes, so "VALID violation" is ambiguous.
- If the module is a read-only or write-only slave, do not flag the absent
  channels — say so explicitly under "Channels implemented".
- For partial snippets, list which rules could not be evaluated and why.
- Always provide SVA assertions, even on PASS results — they're valuable
  regression catches.
- Don't invent findings. If unsure, write "Cannot determine from this
  snippet — check [specific behavior]."

- Instantiate assertions only for signals present on the selected interface.
- State whether source behavior is asserted on DUT outputs or assumed on inputs in formal verification.
- Sample reset behavior separately from stall properties; disable-iff alone does not test reset.
- Do not claim simulation, formal proof, or model-evaluation success unless actually run.
