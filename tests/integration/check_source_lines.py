"""Check the physical line limit for handwritten workspace source files."""

from __future__ import annotations

from pathlib import Path
from subprocess import check_output

ROOT = Path(__file__).resolve().parents[2]
LIMIT = 200
SOURCE_SUFFIXES = frozenset(
    {
        '.bash',
        '.c',
        '.cc',
        '.cpp',
        '.css',
        '.h',
        '.hh',
        '.hpp',
        '.html',
        '.ino',
        '.java',
        '.js',
        '.kt',
        '.kts',
        '.py',
        '.sh',
        '.sql',
        '.swift',
        '.toml',
        '.ts',
        '.vue',
        '.xml',
        '.yaml',
        '.yml',
    }
)


def physical_lines(content: bytes) -> int:
    """Count LF-delimited lines, including a final line without a newline."""
    return content.count(b'\n') + int(bool(content) and not content.endswith(b'\n'))


def main() -> int:
    """Report files over the limit and return 1 if any exceed it."""
    paths = check_output(
        ['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
        cwd=ROOT,
    ).decode()
    counts: list[tuple[int, Path]] = []
    for name in sorted(set(paths.split('\0'))):
        path = ROOT / name
        if path.suffix in SOURCE_SUFFIXES and path.is_file() and not path.is_symlink():
            counts.append((physical_lines(path.read_bytes()), path.relative_to(ROOT)))

    over_limit = [(count, name) for count, name in counts if count > LIMIT]
    for count, relative_path in over_limit:
        print(f'{relative_path}: {count} lines (limit: {LIMIT})')
    if not over_limit:
        longest = max((count for count, _ in counts), default=0)
        print(f'{len(counts)} source files checked; longest: {longest}/{LIMIT} lines.')
    return int(bool(over_limit))


if __name__ == '__main__':
    raise SystemExit(main())
