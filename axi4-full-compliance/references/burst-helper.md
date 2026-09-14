# Concrete AXI4 burst checks

Run `python3 scripts/check_burst.py descriptor.json` from the skill folder.
Use JSON integers, not Verilog literals. Example: a legal WRAP4 on a 32-bit bus:

```json
{"addr":12,"len":3,"size":2,"burst":2,"data_width":32,"wstrb":[15,15,15,15]}
```

Required fields map to AxADDR, encoded AxLEN, encoded AxSIZE, encoded AxBURST
(0 FIXED, 1 INCR, 2 WRAP), and data width in bits. Optional `addr_width`
defaults to 32 and supports 1–64. Optional `wstrb` is a mask per beat for writes;
omit it for read geometry. Supply a whole descriptor for one interface/burst.

Output contains status, rule-tagged errors, nominal addresses and permitted
WSTRB masks. Exit codes: 0 passes this limited geometry check; 1 is a checked
violation; 2 is malformed/unreadable input. Zero strobes are legal; they do not
waive LEN, LAST or boundary rules. Do not interpret a mask as actual data content.

No RTL parsing, VALID/READY, LAST, ID ordering, exclusives, attributes, or
implementation capability is checked. A correct descriptor does not prove the
RTL computes it correctly. For partial traces do not invent missing beats.
