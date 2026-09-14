# Concrete AHB burst checks

Run `python3 scripts/check_burst.py descriptor.json` from this skill folder.
Example: a legal word WRAP4 starting inside its wrap region:

```json
{"addr":1020,"size":2,"burst":2,"data_width":32}
```

Fields are start HADDR, encoded HSIZE, encoded HBURST (0–7), and bus width in
bits. Optional `beats` defaults to the fixed nominal burst length. Undefined
INCR (HBURST=1) requires `beats` for the observed/planned sequence; the helper
accepts up to 4096 beats to bound resource use, not as a protocol maximum.

Output lists nominal addresses, alignment/size/length errors and incrementing
1KB crossing errors. Exit 0 is scoped geometry PASS, 1 a checked violation,
and 2 malformed or unreadable input. Legacy AHB and Lite share this geometry;
this does not infer which variant the caller uses.

This helper assumes a normal complete burst. An early end caused by ERROR,
RETRY/SPLIT or arbitration must be reviewed in context instead of presented as
an ordinary fixed-length descriptor. It does not parse RTL or check HTRANS,
HREADY, data phases, response cycles, locks, or slave decode compatibility.
