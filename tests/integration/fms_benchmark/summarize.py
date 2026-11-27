"""Summarize paint timing, lost updates and API time from recorded runs."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from math import ceil
from pathlib import Path
from statistics import median


def quantiles(values: list[float]) -> dict:
    """Return the sample count, median, nearest-rank p95 and maximum."""
    ordered = sorted(values)
    if not ordered:
        return {'count': 0}
    return {
        'count': len(ordered),
        'p50': round(median(ordered), 3),
        'p95': round(ordered[ceil(0.95 * len(ordered)) - 1], 3),
        'max': round(ordered[-1], 3),
    }


def read_lines(path: Path) -> list[dict]:
    """Read JSON Lines if the associated client ran in this condition."""
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines()]


def summarize(run: Path) -> dict:
    """Join current-epoch vehicle sequences between snapshot and paint."""
    trace = read_lines(run / 'qt.jsonl')
    manifest = run / 'run.json'
    epoch_key = (
        json.loads(manifest.read_text())['epoch'] if manifest.is_file() else run.name
    )
    replay = [
        line.split('|', maxsplit=3)
        for line in (run / 'replay.txt').read_text().splitlines()
        if '|' in line
    ]
    inputs = {
        (vehicle, int(sequence))
        for vehicle, epoch, sequence, _ in replay
        if epoch == epoch_key
    }

    fetched: dict[tuple[str, int], int] = {}
    qt_delivery: list[float] = []
    poll_rtt: list[float] = []
    in_flight: int | None = None
    painted: set[tuple[str, int]] = set()
    latency: dict[str, list[float]] = defaultdict(list)
    times: dict[str, list[int]] = defaultdict(list)
    api: dict[str, list[float]] = defaultdict(list)
    failed_api = 0
    admin_trace = read_lines(run / 'admin.jsonl')
    if any(row['event'].startswith('poll_') for row in admin_trace):
        raise ValueError('The independent admin process attempted a fleet poll.')
    for row in trace + admin_trace:
        event = row['event']
        if event == 'poll_started':
            in_flight = row['monotonic_ns']
        elif event == 'poll_response' and in_flight is not None:
            poll_rtt.append((row['monotonic_ns'] - in_flight) / 1_000_000)
            in_flight = None
        if event == 'admin_response' and row['endpoint'] != '/api/admin/menu':
            endpoint = row['endpoint']
            if row['status'] == 200:
                api[endpoint].append(row['elapsed_ms'])
            else:
                failed_api += 1
        if event not in ('snapshot_received', 'map_painted'):
            continue
        for vehicle, (epoch, seq, timestamp) in row['samples']:
            if epoch != epoch_key:
                continue
            key = (vehicle, seq)
            if event == 'snapshot_received':
                fetched.setdefault(key, row['monotonic_ns'])
            elif key not in painted:
                painted.add(key)
                utc_ms = datetime.fromisoformat(timestamp).timestamp() * 1000
                latency[vehicle].append(row['utc_ns'] / 1_000_000 - utc_ms)
                if key in fetched:
                    qt_delivery.append((row['monotonic_ns'] - fetched[key]) / 1_000_000)
                times[vehicle].append(row['monotonic_ns'])
    web_rows = read_lines(run / 'web.jsonl')
    searched = [row for row in web_rows if row.get('searched')]
    member_endpoint = '/api/admin/members/page'
    browser_member_loads = [
        row for row in searched if row['endpoint'] == member_endpoint
    ]
    # The Web workspace refreshes the persisted search when revisiting Members.
    # The first and last matching requests are the two explicit form submissions.
    automatic_members = browser_member_loads[1:-1]
    for row in searched:
        if any(row is automatic for automatic in automatic_members):
            continue
        if row['status'] == 200:
            api[row['endpoint']].append(row['elapsed_ms'])
        else:
            failed_api += 1
    if not trace or set(latency) != {'1', '2', '3', '4'}:
        raise ValueError(f'Incomplete four-vehicle trace in {run}')
    db_before = json.loads((run / 'db-before.json').read_text())
    db_after = json.loads((run / 'db-after.json').read_text())
    same_run = [row for row in trace if row['event'] == 'snapshot_received']
    snapshots = [row['monotonic_ns'] for row in same_run]
    starts = [row['monotonic_ns'] for row in trace if row['event'] == 'poll_started']
    skipped = sum(row['event'] == 'poll_skipped' for row in trace)
    duration = len(inputs) // 4
    response_errors = sum(
        row['event'] == 'poll_response' and row['status'] != 200 for row in trace
    )
    load: dict[str, list[dict]] = defaultdict(list)
    for sample in read_lines(run / 'process.jsonl'):
        for name, values in sample.get('load', {}).items():
            load[name].append(values)
    return {
        'duration_seconds': duration,
        'process_load': {
            name: {
                'cpu_percent': quantiles([v['cpu_percent'] for v in values]),
                'max_rss_kib': max(v['rss_kib'] for v in values),
            }
            for name, values in load.items()
        },
        'poll_started': len(starts),
        'poll_skipped': skipped,
        'poll_unfired': max(
            0, 1 + (1000 * (duration - 1)) // 7500 - len(starts) - skipped
        ),
        'poll_errors': response_errors,
        'max_snapshot_gap_ms': max(
            (
                (b - a) / 1_000_000
                for a, b in zip(snapshots, snapshots[1:], strict=False)
            ),
            default=0,
        ),
        'snapshot_samples_not_painted': len(fetched.keys() - painted),
        'input_samples_not_selected': len(inputs - fetched.keys()),
        'poll_rtt_ms': quantiles(poll_rtt),
        'qt_delivery_ms': quantiles(qt_delivery),
        'latency_ms': quantiles(
            [value for series in latency.values() for value in series]
        ),
        'vehicles': {
            key: {
                'latency_ms': quantiles(series),
                'max_paint_gap_ms': max(
                    (
                        (b - a) / 1_000_000
                        for a, b in zip(times[key], times[key][1:], strict=False)
                    ),
                    default=0,
                ),
            }
            for key, series in latency.items()
        },
        'admin_ms': {key: quantiles(series) for key, series in api.items()},
        'admin_errors': failed_api,
        'web_total_api': len(web_rows),
        'web_members_automatic_reloads': len(automatic_members),
        'database_delta': {
            key: db_after[key] - db_before[key]
            for key in (
                'xact_commit',
                'blks_read',
                'blks_hit',
                'tup_returned',
                'temp_bytes',
            )
        },
    }


def main() -> None:
    """Print structured results suitable for reproducing the report table."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    results = {
        run.name: summarize(run)
        for run in sorted(args.directory.iterdir())
        if run.is_dir()
    }
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
