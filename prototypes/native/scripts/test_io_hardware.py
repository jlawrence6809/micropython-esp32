#!/usr/bin/env python3
"""Brief GPIO4/5 + missing-I2C tests ONLY on the disconnected spare; restore normal firmware."""
import argparse
from pathlib import Path
import subprocess
import sys
from ota import Bench, update, image_elf_hash

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('host')
parser.add_argument('--normal', type=Path, default=Path('build/garden_native_probe.bin'))
parser.add_argument('--diagnostic', type=Path, default=Path('build-io/garden_native_probe.bin'))
parser.add_argument('--confirm-disconnected-spare', action='store_true',
                    help='Explicitly confirm no relays/sensors/external equipment is attached')
args = parser.parse_args()
if not args.confirm_disconnected_spare:
    parser.error('Refusing physical test without --confirm-disconnected-spare')
bench = Bench(args.host)
normal, diagnostic = args.normal.read_bytes(), args.diagnostic.read_bytes()
normal_sha, diagnostic_sha = image_elf_hash(normal), image_elf_hash(diagnostic)
if normal_sha == diagnostic_sha:
    raise SystemExit('Normal and diagnostic images must differ')
before = bench.wait(lambda s: s['healthy'] and s['running_state'] == 'valid')
if before['elf_sha256'] != normal_sha or bench.get('/api/bench/io-status')['physical_selftest_ran']:
    raise SystemExit('Unexpected initial firmware; inspect before replacing any code')
try:
    update(bench, diagnostic)
    subprocess.run([sys.executable, str(Path(__file__).with_name('test_io_plan.py')),
                    args.host, '--expect-physical-selftest'], check=True)
finally:
    # Completion can be uncertain: inspect first, never blindly replay the test.
    current = bench.wait(lambda s: s['healthy'] and s['running_state'] == 'valid')
    io = bench.get('/api/bench/io-status')
    if current['elf_sha256'] == diagnostic_sha:
        print('Restoring verified normal simulation-only build', flush=True)
        update(bench, normal)
    elif current['elf_sha256'] == normal_sha and not io['physical_selftest_ran']:
        print('Normal image already active (diagnostic may have rolled back)', flush=True)
    else:
        raise RuntimeError('Unexpected spare state; inspect before further writes; do not connect equipment')
assert bench.get('/api/bench/io-status')['physical_selftest_ran'] is False
print('FINAL: normal firmware verified; physical selftest disabled')
