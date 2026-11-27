"""Run the desktop FMS comparisons against a prepared synthetic database."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from time import monotonic, sleep, time
from uuid import uuid4

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MODES = ('baseline', 'web', 'standalone')


def tick(mark: float) -> None:
    """Wait only until an absolute monotonic schedule marker."""
    sleep(max(0.0, mark - monotonic()))


def process_load(roots: dict[str, int]) -> dict:
    """Sum sampled CPU percent and RSS KiB across each process tree."""
    listing = subprocess.check_output(
        ['ps', '-axo', 'pid=,ppid=,pcpu=,rss='], text=True
    )
    rows = [line.split() for line in listing.splitlines() if line.strip()]
    result = {}
    for label, root in roots.items():
        pids = {root}
        while True:
            descendants = {
                int(pid) for pid, parent, _, _ in rows if int(parent) in pids
            }
            if descendants <= pids:
                break
            pids |= descendants
        chosen = [
            (float(cpu), int(rss)) for pid, _, cpu, rss in rows if int(pid) in pids
        ]
        result[label] = {
            'cpu_percent': sum(cpu for cpu, _ in chosen),
            'rss_kib': sum(rss for _, rss in chosen),
        }
    return result


def run_trial(mode: str, directory: Path, psql: list[str], duration: int) -> None:
    """Replay identical telemetry while exercising the selected native clients."""
    if mode not in MODES:
        raise ValueError(f'Unsupported benchmark mode: {mode}')
    directory.mkdir()
    epoch = f'{directory.name}-{uuid4().hex[:10]}'
    manifest = {'epoch': epoch, 'duration_seconds': duration, 'mode': mode}
    (directory / 'run.json').write_text(json.dumps(manifest), encoding='utf-8')
    start = time() + 8
    anchor = monotonic() + 8
    pg_prefix = [*psql, '-X', '-v', 'ON_ERROR_STOP=1', '-At']
    identity = subprocess.check_output(
        [*pg_prefix, '-c', 'SELECT current_database()'], text=True
    ).strip()
    if identity != 'amo_bench':
        raise ValueError('The benchmark requires the isolated amo_bench database.')

    def db_stats(name: str) -> None:
        sql = (
            'SELECT row_to_json(s) FROM pg_stat_database s '
            'WHERE datname = current_database()'
        )
        (directory / name).write_bytes(subprocess.check_output([*pg_prefix, '-c', sql]))

    db_stats('db-before.json')
    env = dict(os.environ, AMO_FMS_TRACE=str(directory / 'qt.jsonl'))
    qt_dir = ROOT / 'GUI/MainControllerPC/AMOAdmin'

    def qt_driver(name: str, role: str) -> tuple[str, list[str], Path]:
        return (
            name,
            [
                'uv',
                'run',
                '--locked',
                'python',
                str(HERE / 'qt_driver.py'),
                role,
                str(directory),
                str(start),
                str(duration),
            ],
            qt_dir,
        )

    drivers = [qt_driver('qt', 'baseline')]
    if mode == 'standalone':
        drivers.append(qt_driver('admin', 'admin'))
    if mode == 'web':
        drivers.append(
            (
                'chrome',
                [
                    'node',
                    str(HERE / 'web_driver.mjs'),
                    os.environ['AMO_ADMIN_WEB_URL'],
                    str(directory / 'web.jsonl'),
                    str(start),
                    str(duration),
                ],
                ROOT,
            )
        )
    children: list[subprocess.Popen[bytes]] = []
    try:
        for name, args, cwd in drivers:
            with (directory / f'{name}.log').open('wb') as log:
                children.append(
                    subprocess.Popen(
                        args,
                        env=dict(env, AMO_FMS_TRACE=str(directory / f'{name}.jsonl'))
                        if name == 'admin'
                        else env,
                        cwd=cwd,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                    )
                )
        with (
            (directory / 'replay.txt').open('wb') as replay,
            (directory / 'process.jsonl').open('w', encoding='utf-8') as stats,
        ):
            for seq in range(1, duration + 1):
                tick(anchor + seq - 1)
                subprocess.run(
                    [
                        *pg_prefix,
                        '-v',
                        f'epoch={epoch}',
                        '-v',
                        f'sequence={seq}',
                        '-f',
                        str(HERE / 'vehicle_samples.sql'),
                    ],
                    check=True,
                    stdout=replay,
                )
                if seq % 3 == 1:
                    server_pids = os.environ['AMO_BENCH_SERVER_PIDS'].split(',')
                    roots = dict(
                        zip(
                            ('main', 'gateway', 'postgres'),
                            map(int, server_pids),
                            strict=True,
                        )
                    )
                    roots.update(
                        (name, child.pid)
                        for (name, _, _), child in zip(drivers, children, strict=True)
                    )
                    stats.write(
                        json.dumps({'utc': time(), 'load': process_load(roots)}) + '\n'
                    )
        for child in children:
            if child.wait(timeout=25):
                raise RuntimeError(
                    f'Benchmark driver {child.pid} failed in {directory}.'
                )
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
                child.wait(timeout=5)
        db_stats('db-after.json')


def main() -> None:
    """Rotate run order for each repetition and retain measurements on failure."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--duration', type=int, default=39)
    parser.add_argument('--start-repetition', type=int, default=0)
    parser.add_argument('psql', nargs='+')
    args = parser.parse_args()
    if args.repeats < 1 or args.duration < 24 or args.start_repetition < 0:
        parser.error('Use at least one repetition and a 24-second duration.')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    for index in range(args.start_repetition, args.start_repetition + args.repeats):
        for step in range(len(MODES)):
            mode = MODES[(index + step) % len(MODES)]
            target = output / f'r{index + 1}-{mode}'
            print(target, flush=True)
            run_trial(mode, target, args.psql, args.duration)


if __name__ == '__main__':
    main()
