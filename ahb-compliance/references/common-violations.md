# AHB failure patterns

## Capturing the data of the wrong transfer — T1/T3

```verilog
// Wrong: HWDATA at this edge belongs to the prior data phase.
if (HSEL && HREADY && HTRANS[1]) mem[HADDR] <= HWDATA;
```
Capture address, size and write intent on acceptance. In the following data
phase use that captured state with HWDATA, qualified by completion and response
policy. Preserve it through wait states; accept the next address on the same
completion edge without overwriting the old transfer before its side effect.

```text
edge 1: accept write address A; data belongs to older transfer
edge 2: accept address B; HWDATA belongs to A
edge 3: HWDATA belongs to B (if B was a write)
```

## Testing local ready instead of bus ready — T1

```verilog
// Wrong when another slave owns the stalled data phase.
if (HSEL && HREADYOUT && HTRANS[1]) captured_addr <= HADDR;
// Correct acceptance condition; remaining data-phase bookkeeping is separate.
if (HSEL && HREADY && HTRANS[1]) captured_addr <= HADDR;
```

## Current selection controls an old response — R1

```verilog
// Wrong concept: selecting HRDATA/HRESP using the current address decode.
assign HRDATA = HSEL_A ? A_RDATA : B_RDATA;
```
Register accepted selection when HREADY is high, then use that data-phase
selection for response muxing. Test alternating slaves with one stalled transfer.

## One-cycle ERROR — R2

Returning HRESP=1 and HREADYOUT=1 immediately skips the first error cycle.
Use explicit first/final error states, with `(HRESP,HREADYOUT)` equal to `(1,0)`
then `(1,1)`. If extra wait cycles are needed, insert `(0,0)` before the pair.
A stalled following address can be cancelled during that error sequence.

## IDLE is not a write, and does not cancel a write — T2

Do not accept transfers using HSEL alone; include HTRANS[1] and HREADY.
Also do not clear a pending write because current HTRANS is IDLE. IDLE belongs
to the next address phase while the prior write can still be completing.

## Burst-address mistakes — B1/B3/B4

INCR4 words from 0x3F8 would cross 1KB. WRAP4 words from 0x3FC instead visits
0x3FC, 0x3F0, 0x3F4, 0x3F8. Halfwords increment by two even on a 32-bit bus.
An unaligned halfword at address 1 is illegal; AXI's unaligned rule does not apply.

## Legacy SPLIT treated as completion — L3/L4

A split transaction must not retire as successful or update memory twice upon
replay. Distinguish the response sequence, arbiter masking, later HSPLIT release,
and eventual regrant. The last two steps cannot be proven from HRESP alone.
