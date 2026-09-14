# AXI4 Full failure patterns and repair boundaries

## Counting cycles instead of accepted beats — B6/O2

```verilog
// Wrong while the receiver stalls.
if (RVALID) remaining <= remaining - 1;
// Counter update condition; initialize per accepted AR and per ID.
if (RVALID && RREADY) remaining <= remaining - 1;
```
Compute RLAST from the current transaction's remaining count and hold it with
RID/RDATA/RRESP. Test multiple stall cycles on both first and last beats.

## Early B response — O1

```verilog
// Wrong: W may not have arrived at all.
if (AWVALID && AWREADY) BVALID <= 1;
```
Queue AW descriptors and independently collect complete W bursts. Issue B for
an eligible pair only after its last W handshake; retain BID/BRESP until accepted.
Do not "fix" by requiring AWVALID and WVALID to overlap on one clock.

## Incorrect 4KB test — B3

For a 32-bit bus, address 0xFFF, SIZE=2, LEN=0 can access only the top byte of
the current word and does not cross 4KB. For LEN=1 the next transfer starts at
0x1000 and does cross. Checking `start + (LEN+1)*4 - 1` misclassifies the first
case. Check aligned transfer windows; do not let WSTRB=0 waive a burst boundary.

## Wrong wrap alignment — B4

WRAP4 of words starting at 0x0C visits 0x0C, 0x00, 0x04, 0x08. This is legal.
Requiring start modulo 16 to be zero would reject it. Requiring start modulo 4
to be zero is correct. WRAP with three beats or unaligned start is illegal.

## Global read counter / write interleaving — O2/O4

```text
AR ID=1 LEN=1 accepted; AR ID=2 LEN=0 accepted
R ID=1 LAST=0; R ID=2 LAST=1; R ID=1 LAST=1   # legal accepted sequence
```
Use a queue per RID, with a beat count for its oldest transaction. In contrast,
do not alternate W beats of two write bursts: AXI4 has no WID to disambiguate them.

## Treating all exclusive failures like Lite — P1/P2

Successful exclusive read/write responses can be EXOKAY. An exclusive-capable
slave must not write memory on a failed exclusive write. Establish whether the
slave supports exclusives before proposing a response or write-enable fix.
