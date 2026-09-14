# Report Template & Severity Definitions

---

## Severity Levels

| Level | Emoji | Meaning |
|-------|-------|---------|
| CRITICAL | 🔴 | Direct violation of ARM AXI4-Stream spec (IHI0051). Will cause functional failures: data loss, metastability, simulation/hardware mismatch. Must be fixed. |
| WARNING  | 🟡 | Deviation from spec recommendations, or a pattern that is not explicitly prohibited but causes real-world interoperability or reliability problems. Should be fixed. |
| INFO     | 🔵 | Non-standard choice, suboptimal pattern, or observation about missing optional signals. No functional risk, but worth the designer knowing. |

---

## Report Skeleton

````markdown
## AXI4-Stream Compliance Report

### Interface Summary
- **Role**: Master / Slave / Pass-through
- **Language**: Verilog / SystemVerilog
- **Signals present**: TVALID, TREADY, TDATA[N:0], TLAST, TKEEP[M:0], ...
- **Reset style**: Async active-low (ARESETn) / Synchronous
- **Code completeness**: Full module / Partial snippet

---

### Findings

#### 🔴 CRITICAL — X issue(s) found

**[C-1] Rule H1 — TVALID Deasserted Without Handshake**
- **Location**: `module_name.sv`, line 42, `always` block driving `m_axis_tvalid`
- **What's wrong**: TVALID is cleared unconditionally on the cycle after `send_en`
  falls, regardless of whether TREADY was seen. This violates the ARM spec rule
  that TVALID must remain high until the handshake (TVALID & TREADY) occurs.
- **Risk**: Data loss — the slave may miss transfers entirely if it wasn't ready.
- **Fix**: See corrected code below.

---

#### 🟡 WARNING — Y issue(s) found

**[W-1] Documented Endpoint Compatibility Mismatch**
- **Location**: Cite the actual RTL and endpoint requirement.
- **Issue**: State the known contract and a feasible incompatible transfer.
- **Fix**: Adapt the endpoint or bridge to the required behavior.
- Do not instantiate this example without evidence of a mismatch.

---

#### 🔵 INFO — Z note(s)

**[I-1] Rule X2 — TKEEP Absent on Wide Bus**
- **Location**: Port declaration, line 5
- **What's wrong**: TDATA is 64-bit but TKEEP is not declared. The interface
  cannot express partial last-beat transfers.
- **Recommendation**: Add `output [7:0] TKEEP` and drive it from your
  byte-enable logic, or document that all transfers are full-width.

---

### Corrected Code Snippets

*(Only for CRITICAL findings — show side-by-side)*

**Fix for [C-1]** — TVALID stickiness:

```verilog
// BEFORE (violating):
SEND: begin
  TVALID <= 1'b0;   // drops unconditionally
  state  <= IDLE;
end

// AFTER (compliant):
SEND: begin
  if (TVALID & TREADY) begin   // wait for handshake
    TVALID <= 1'b0;
    state  <= IDLE;
  end
end
```

---

### Verification Suggestions

Add these SVA (SystemVerilog Assertion) properties to catch violations in simulation:

```systemverilog
// Property 1: TVALID stickiness (H1)
property tvalid_sticky;
  @(posedge ACLK) disable iff (!ARESETn)
  (TVALID && !TREADY) |=> TVALID;
endproperty
assert property (tvalid_sticky)
  else $error("AXIS: TVALID dropped without handshake");

// Property 2: Payload stability during stall (S1)
property tdata_stable;
  @(posedge ACLK) disable iff (!ARESETn)
  (TVALID && !TREADY) |=> $stable(TDATA);
endproperty
assert property (tdata_stable)
  else $error("AXIS: TDATA changed while stalled");

// Property 3: sampled reset check (R1); verify asynchronous timing separately
property tvalid_during_reset;
  @(posedge ACLK)
  !ARESETn |-> !TVALID;
endproperty
assert property (tvalid_during_reset)
  else $error("AXIS: TVALID not low after reset");

// Sparse TKEEP and constant-low TLAST are legal: no blanket mask assertion.

// Property 4: TSTRB subset of TKEEP (K3)
property tstrb_subset_tkeep;
  @(posedge ACLK) disable iff (!ARESETn)
  TVALID |-> ((TSTRB & ~TKEEP) == '0);
endproperty
assert property (tstrb_subset_tkeep)
  else $error("AXIS: TSTRB bit set where TKEEP is 0");
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

- Always include line numbers when available. If code has none, use descriptive
  locations like "in the `SEND` state of the FSM" or "in the `always` block at ~line 40".
- For partial snippets, explicitly state which rules could not be evaluated and why.
- For pass results, still provide the SVA suggestions — they are useful even for
  compliant code.
- Don't invent findings. If you are unsure, say "Cannot determine from this snippet —
  check [specific thing]."

- Instantiate assertions only for signals present on the selected interface.
- State whether source behavior is asserted on DUT outputs or assumed on inputs in formal verification.
- Sample reset behavior separately from stall properties; disable-iff alone does not test reset.
- Do not claim simulation, formal proof, or model-evaluation success unless actually run.
