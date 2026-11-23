"""Build a comparison table from complete, validated repetitions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_table(data: dict, repeats: int) -> str:
    """Validate all expected runs and return ranges across repetitions."""
    modes = ('baseline', 'web', 'combined')
    expected = {f'r{index}-{mode}' for index in range(1, repeats + 1) for mode in modes}
    if set(data) != expected:
        raise ValueError(f'Expected {sorted(expected)}, got {sorted(data)}.')
    lines = [
        '| Condition | Runs | Receipt → paint p95 (ms) | Poll RTT p95 (ms) | '
        'Qt receive → paint p95 (ms) | Longest fresh paint gap (ms) | '
        'Poll skipped / unfired / failed | Unpainted snapshot rows | '
        'Input rows not selected | Search failures |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |',
    ]
    for mode in modes:
        rows = [data[f'r{index}-{mode}'] for index in range(1, repeats + 1)]
        for row in rows:
            expected_calls = (
                0 if mode == 'baseline' else (6 if row['duration_seconds'] >= 42 else 3)
            )
            observed = sum(item['count'] for item in row['admin_ms'].values())
            if observed + row['admin_errors'] != expected_calls:
                raise ValueError(
                    f'{mode}: expected {expected_calls} searches, got {observed}.'
                )
        skipped, unfired, failed = (
            sum(r[key] for r in rows)
            for key in ('poll_skipped', 'poll_unfired', 'poll_errors')
        )
        fresh_gap = max(
            entry['max_paint_gap_ms'] for r in rows for entry in r['vehicles'].values()
        )
        lines.append(
            f'| {mode} | {len(rows)} | {span(rows, "latency_ms")} | '
            f'{span(rows, "poll_rtt_ms")} | {span(rows, "qt_delivery_ms")} | '
            f'{fresh_gap:.1f} | {skipped}/{unfired}/{failed} | '
            f'{sum(r["snapshot_samples_not_painted"] for r in rows)} | '
            f'{sum(r["input_samples_not_selected"] for r in rows)} | '
            f'{sum(r["admin_errors"] for r in rows)} |'
        )
    lines.extend(
        [
            '',
            '| Search endpoint | Web p95 range (ms) | Integrated PyQt p95 range (ms) |',
            '| --- | ---: | ---: |',
        ]
    )
    endpoints = (
        '/api/admin/members/page',
        '/api/operations/trip-history',
        '/api/operations/test-history',
    )
    for endpoint in endpoints:
        values = []
        for mode in ('web', 'combined'):
            durations = [
                data[f'r{i}-{mode}']['admin_ms'][endpoint]
                for i in range(1, repeats + 1)
            ]
            values.append(
                span([{'elapsed': duration} for duration in durations], 'elapsed')
            )
        lines.append(f'| `{endpoint}` | {values[0]} | {values[1]} |')
    return '\n'.join(lines)


def span(rows: list[dict], key: str) -> str:
    """Return the min–max range of run-level p95 estimates."""
    p95 = [row[key]['p95'] for row in rows]
    return f'{min(p95):.1f}–{max(p95):.1f}'


def main() -> None:
    """Read the summary JSON and print the audited Markdown table."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('summary', type=Path)
    parser.add_argument('--repeats', type=int, default=3)
    args = parser.parse_args()
    print(build_table(json.loads(args.summary.read_text()), args.repeats))


if __name__ == '__main__':
    main()
