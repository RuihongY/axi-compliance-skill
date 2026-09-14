#!/usr/bin/env python3
"""Check nominal AHB burst geometry from JSON, excluding timing and termination."""
import argparse
import json
from pathlib import Path

# HBURST: SINGLE, INCR, WRAP4, INCR4, WRAP8, INCR8, WRAP16, INCR16.
LENGTHS = {0: 1, 2: 4, 3: 4, 4: 8, 5: 8, 6: 16, 7: 16}


def check(descriptor):
    required = {'addr', 'size', 'burst', 'data_width'}
    if not isinstance(descriptor, dict) or not required <= descriptor.keys() or descriptor.keys() - (required | {'beats'}):
        raise ValueError('required: addr, size, burst, data_width; optional: beats (required for INCR)')
    d = dict(descriptor)
    for key, value in d.items():
        if type(value) is not int:
            raise ValueError(f'{key} must be an integer')
    errors = []
    result = {'scope': 'AHB nominal geometry; no phase, response, or arbitration checks',
              'status': 'FAIL', 'errors': errors, 'addresses': []}
    if not 0 <= d['addr'] < 1 << 32:
        errors.append('B1: address must fit the baseline 32-bit address bus')
    if not 0 <= d['size'] <= 7 or not 0 <= d['burst'] <= 7:
        errors.append('B1: HSIZE and HBURST are 3-bit encodings')
    width = d['data_width']
    if width < 8 or width > 1024 or width & (width - 1):
        errors.append('C1: baseline data_width must be a power of two from 8 to 1024 bits')
    if errors:
        return result
    burst, size, start = d['burst'], 1 << d['size'], d['addr']
    if burst == 1 and 'beats' not in d:
        raise ValueError('undefined-length INCR requires an observed/planned beats count')
    beats = d.get('beats', LENGTHS.get(burst))
    if beats < 1 or beats > 4096:
        raise ValueError('helper accepts 1..4096 beats per descriptor; this is a resource bound')
    if burst != 1 and beats != LENGTHS[burst]:
        errors.append('B2: beat count differs from nominal HBURST length (early termination is outside this helper)')
    if size > width // 8 or start % size:
        errors.append('B1: HSIZE must fit the bus and HADDR must align to transfer size')
    if errors:
        return result
    span = size * beats
    base = start // span * span
    wrap = burst in (2, 4, 6)
    addresses = [base + (start - base + i * size) % span if wrap else start + i * size
                 for i in range(beats)]
    result['addresses'] = addresses
    if not wrap and any(a >> 10 != start >> 10 or (a + size - 1) >> 10 != start >> 10 for a in addresses):
        errors.append('B3: incrementing burst crosses a 1KB boundary; restart with NONSEQ')
    if any(a + size > 1 << 32 for a in addresses):
        errors.append('B1: burst overflows 32-bit address space')
    result['status'] = 'FAIL' if errors else 'PASS'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('descriptor', type=Path)
    args = parser.parse_args()
    try:
        result = check(json.loads(args.descriptor.read_text()))
    except (OSError, ValueError) as exc:
        print(json.dumps({'error': str(exc)}))
        return 2
    print(json.dumps(result, indent=2))
    return 1 if result['errors'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
