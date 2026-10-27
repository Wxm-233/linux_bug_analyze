"""Produce bounded local source excerpts for held-out shadow candidates."""
import argparse
import csv
from pathlib import Path
import subprocess


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--candidates', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    with a.candidates.open(encoding='utf-8', newline='') as f:
        rows = [r for r in csv.DictReader(f, delimiter='\t') if r['dataset'] == 'batch2']
    grouped = {}
    for row in rows:
        grouped.setdefault(row['hash'], row)
    with a.output.open('w', encoding='utf-8') as f:
        for h, row in grouped.items():
            result = subprocess.run(['git', '-C', str(a.repo), 'show', '--format=medium',
                                     '--stat', '--no-renames', h], check=True, text=True,
                                    capture_output=True)
            patch = subprocess.run(['git', '-C', str(a.repo), 'show', '--format=',
                                    '--no-renames', '--unified=3', h], check=True,
                                   text=True, capture_output=True)
            f.write(f'\n=== {h[:12]} {row["stratum"]} {row["rule"]} ===\n')
            f.write(result.stdout[:1800] + '\nPATCH:\n' + patch.stdout[:2500] + '\n')


if __name__ == '__main__':
    main()
