#!/usr/bin/env python3
"""Check AXI4 burst geometry from a JSON descriptor (not RTL or temporal behavior)."""
import argparse
import json
from pathlib import Path


def check(descriptor):
    if not isinstance(descriptor, dict):
        raise ValueError('descriptor must be a JSON object')
    required = {'addr', 'len', 'size', 'burst', 'data_width'}
    allowed = required | {'addr_width', 'wstrb'}
    if not required <= descriptor.keys() or descriptor.keys() - allowed:
        raise ValueError('required: addr, len, size, burst, data_width; optional: addr_width, wstrb')
    d = dict(descriptor)
    d.setdefault('addr_width', 32)
    for key in allowed - {'wstrb'}:
        if type(d[key]) is not int:
            raise ValueError(f'{key} must be an integer (no booleans or string literals)')
    errors = []
    result = {'scope': 'AXI4 ordinary burst geometry only', 'status': 'FAIL',
              'errors': errors, 'addresses': [], 'allowed_wstrb': []}
    for key, low, high in [('addr_width', 1, 64), ('len', 0, 255), ('size', 0, 7), ('burst', 0, 2)]:
        if not low <= d[key] <= high:
            errors.append(f'B1: {key} must be in {low}..{high}')
    width = d['data_width']
    if width < 8 or width > 1024 or width & (width - 1):
        errors.append('B2: data_width must be a power of two from 8 to 1024 bits')
    if errors:
        return result
    if not 0 <= d['addr'] < (1 << d['addr_width']):
        errors.append('B3: start address does not fit addr_width')
        return result
    beats, size, start, burst = d['len'] + 1, 1 << d['size'], d['addr'], d['burst']
    bus_bytes = width // 8
    if size > bus_bytes:
        errors.append('B2: transfer size exceeds data bus')
    if burst == 0 and beats > 16:
        errors.append('B1: FIXED supports at most 16 beats')
    if burst == 2 and (beats not in (2, 4, 8, 16) or start % size):
        errors.append('B4: WRAP needs 2/4/8/16 beats and transfer-size-aligned start')
    if errors:
        return result
    aligned = start // size * size
    span = beats * size
    wrap_base = start // span * span
    windows = []
    for i in range(beats):
        if burst == 0:
            addr = start
        elif burst == 1:
            addr = start if i == 0 else aligned + i * size
        else:
            addr = wrap_base + (start - wrap_base + i * size) % span
        last = addr // size * size + size - 1
        windows.append((addr, last))
        result['addresses'].append(addr)
        # Unaligned first/FIXED windows exclude lanes before the start address.
        result['allowed_wstrb'].append(((1 << (last - addr + 1)) - 1) << (addr % bus_bytes))
    if any(a >> 12 != start >> 12 or b >> 12 != start >> 12 for a, b in windows):
        errors.append('B3: burst crosses a 4KB boundary')
    if any(b >= 1 << d['addr_width'] for _, b in windows):
        errors.append('B3: burst overflows address width')
    if 'wstrb' in d:
        masks = d['wstrb']
        if not isinstance(masks, list) or any(type(m) is not int or m < 0 for m in masks):
            raise ValueError('wstrb must be a list of nonnegative integers')
        if len(masks) != beats:
            errors.append('B6: wstrb must contain one mask per beat')
        for i, (mask, permitted) in enumerate(zip(masks, result['allowed_wstrb'])):
            if mask & ~permitted:
                errors.append(f'B5: beat {i} enables byte lanes outside its transfer window')
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
