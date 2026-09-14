#!/usr/bin/env python3
"""Build deterministic, self-contained .skill ZIPs; --check detects stale releases."""
import argparse
import io
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ('axi4-stream-compliance', 'axi4-lite-compliance',
          'axi4-full-compliance', 'ahb-compliance')


def package(name):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted((ROOT / name).rglob('*')):
            if not path.is_file() or '__pycache__' in path.parts or path.name.startswith('.'):
                continue
            if path.suffix not in ('.md', '.py', '.json', '.yaml'):
                raise ValueError(f'Unexpected package file: {path}')
            info = zipfile.ZipInfo(path.relative_to(ROOT).as_posix(), (2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())
    return output.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    stale = []
    for name in SKILLS:
        target = ROOT / (name + '.skill')
        data = package(name)
        if args.check:
            if not target.exists() or target.read_bytes() != data:
                stale.append(target.name)
        else:
            target.write_bytes(data)
            print(f'Built {target.name}')
    if stale:
        parser.exit(1, 'Stale packages: ' + ', '.join(stale) + '\nRun python3 scripts/build_skills.py\n')


if __name__ == '__main__':
    main()
