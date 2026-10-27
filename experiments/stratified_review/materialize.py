"""Read the frozen pilot's commit messages and patch excerpts from local Git."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from linux_bug_analyze.git_repository import GitRepository


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--linux-dir', type=Path, required=True)
    parser.add_argument('--outdir', type=Path, required=True)
    parser.add_argument('--max-diff-chars', type=int, default=10000)
    args = parser.parse_args()
    if args.max_diff_chars < 0:
        parser.error('--max-diff-chars must be nonnegative')
    manifest = json.loads((args.outdir / 'manifest.json').read_text(encoding='utf-8'))
    repo = GitRepository(args.linux_dir)
    repo.validate()
    materials = args.outdir / 'materials'
    materials.mkdir(exist_ok=True)
    for index, row in enumerate(manifest['samples'], 1):
        path = materials / f"{index:03d}-{row['hash'][:12]}.json"
        if path.exists():
            continue
        commit = repo.get_commit(row['hash'], args.max_diff_chars)
        item = {
            'sample_index': index, 'hash': commit.hash, 'stratum': row['stratum'],
            'subject': commit.subject, 'body': commit.body, 'files': commit.files,
            'diff': commit.diff, 'diff_truncated': commit.diff_truncated,
            'original_diff_chars': commit.original_diff_chars,
            'source': 'local-linux-git',
        }
        path.write_text(json.dumps(item, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        if index % 10 == 0:
            print(f'materialized {index}/{len(manifest["samples"])}', flush=True)


if __name__ == '__main__':
    main()
