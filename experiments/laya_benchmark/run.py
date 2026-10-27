"""Local Laya screening benchmark on the frozen 100-commit source review.

No API call is made. This experiment does not alter the DeepSeek screener.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

import laya
import torch
from laya.common import build_sequence, serialize_state


ROOT = Path(__file__).resolve().parents[2]
PILOT = ROOT / 'experiments' / 'stratified_review'
DEFAULT_MATERIALS = ROOT / 'analysis_out' / 'stratified-signal-20260923' / 'materials'
DEFAULT_OUT = ROOT / 'analysis_out' / 'laya-stratified-20260923'
DEFAULT_MANIFEST = PILOT / 'pilot_manifest.json'
DEFAULT_NOTES = PILOT / 'review_notes.tsv'
CHECKPOINT = Path('/root/laya-weights/typed-decisions')

CHOICE = {
    'type': 'choice',
    'instructions': 'Classify this Linux commit using only the supplied evidence.',
    'criteria': {
        'related': 'Specific evidence of a shared-kernel versus architecture/platform semantic mismatch, or a cross-architecture regression. A fix can change only one side.',
        'review': 'Plausible architecture or interface boundary clue, but missing evidence about the caller, provider, or trigger.',
        'unrelated': 'Only a feature addition, behavior-preserving cleanup, or local change without a concrete architecture semantic boundary clue.',
    },
}
QUESTIONS = {
    'bugfix': {'type': 'noul', 'instructions': 'Does this commit fix a pre-existing incorrect behavior or regression, rather than only add a feature or clean up code?'},
    'vertical': {'type': 'noul', 'instructions': 'Does the evidence show a mismatch between shared Linux kernel behavior and an architecture or platform implementation? A fix may change only one side.'},
    'horizontal': {'type': 'noul', 'instructions': 'Does the evidence show that a shared behavior change made for one architecture caused a regression on another architecture?'},
    'relevance_choice': CHOICE,
}
TRAILERS = ('Signed-off-by:', 'Reviewed-by:', 'Acked-by:', 'Cc:', 'Link:', 'Tested-by:')


def input_state(item: dict) -> dict:
    body = '\n'.join(line for line in item['body'].splitlines()
                     if line and not line.startswith(TRAILERS))
    changed = [line for line in item['diff'].splitlines()
               if line.startswith(('+', '-')) and not line.startswith(('+++', '---'))]
    selected = changed[:5] + (changed[-5:] if len(changed) > 5 else [])
    return {'subject': item['subject'], 'message': body[:750],
            'files': item['files'][:6], 'changed_lines': '\n'.join(selected)[:420]}


def load_rows(materials: Path, manifest_path: Path, notes_path: Path | None) -> list[dict]:
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    from csv import DictReader
    if notes_path is None:
        notes = [None] * len(manifest['samples'])
    else:
        with notes_path.open(encoding='utf-8', newline='') as stream:
            notes = list(DictReader(stream, delimiter='\t'))
    if not manifest['samples'] or len(notes) != len(manifest['samples']):
        raise ValueError('Sample/label length mismatch')
    result = []
    for index, (sample, note) in enumerate(zip(manifest['samples'], notes), 1):
        path = materials / f"{index:03d}-{sample['hash'][:12]}.json"
        item = json.loads(path.read_text(encoding='utf-8'))
        if item['hash'] != sample['hash'] or (note is not None and int(note['index']) != index):
            raise ValueError(f'Sample/material/label mismatch at {index}')
        result.append({'index': index, 'hash': sample['hash'], 'stratum': sample['stratum'],
                       'reference': note['label'] if note is not None else None, 'state': input_state(item),
                       'source_diff_truncated': item['diff_truncated']})
    return result


def stats(seconds: list[float]) -> dict:
    ordered = sorted(seconds)
    return {'sum_seconds': round(sum(seconds), 3),
            'median_seconds': round(statistics.median(seconds), 4),
            'p95_seconds': round(ordered[int(0.95 * (len(ordered) - 1))], 4),
            'steady_items_per_second': round((len(seconds) - 1) / sum(seconds[1:]), 2)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--materials', type=Path, default=DEFAULT_MATERIALS)
    parser.add_argument('--outdir', type=Path, default=DEFAULT_OUT)
    parser.add_argument('--checkpoint', type=Path, default=CHECKPOINT)
    parser.add_argument('--manifest', type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument('--notes', type=Path, default=DEFAULT_NOTES)
    parser.add_argument('--no-notes', action='store_true')
    parser.add_argument('--modes', choices=('both', 'choice_only', 'four_questions'), default='both')
    args = parser.parse_args()
    rows = load_rows(args.materials, args.manifest, None if args.no_notes else args.notes)
    args.outdir.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    agent = laya.load(str(args.checkpoint), device='cuda' if torch.cuda.is_available() else 'cpu')
    loaded = time.perf_counter() - t0
    result = {'metadata': {'count': len(rows), 'checkpoint': str(args.checkpoint),
                           'laya_version': laya.__version__, 'torch_version': torch.__version__,
                           'device': str(agent.device), 'model_load_seconds': round(loaded, 3),
                           'reference': ('assistant source review, not expert gold'
                                         if not args.no_notes else 'none; score-only validation batch'),
                           'material': 'same short protocol as 16-commit pilot: 750 body chars, 6 paths, 420 changed-line chars'},
              'runs': {}}
    output = args.outdir / 'results.json'
    modes = [('choice_only', {'relevance_choice': CHOICE}), ('four_questions', QUESTIONS)]
    for mode, questions in modes:
        if args.modes not in ('both', mode):
            continue
        mode_rows = []
        result['runs'][mode] = {'rows': mode_rows}
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        for row in rows:
            state = row['state']
            state_tokens = len(agent.tok(serialize_state(state), add_special_tokens=False)['input_ids'])
            rooms = []
            for q in questions.values():
                internal = agent._to_internal(q)
                empty, _ = build_sequence(agent.tok, '', internal, agent.cfg['max_len'], agent.cfg['head_max_len'])
                rooms.append(agent.cfg['max_len'] - len(empty))
            if agent.device.type == 'cuda':
                torch.cuda.synchronize()
            start = time.perf_counter()
            prediction = agent.predict(state, questions)
            if agent.device.type == 'cuda':
                torch.cuda.synchronize()
            mode_rows.append({'index': row['index'], 'hash': row['hash'], 'stratum': row['stratum'],
                              'reference': row['reference'], 'source_diff_truncated': row['source_diff_truncated'],
                              'state_tokens': state_tokens, 'min_state_room': min(rooms),
                              'state_was_token_truncated': state_tokens > min(rooms),
                              'choice': prediction['answers']['relevance_choice'],
                              'binary': {key: prediction['answers'][key]['noul']
                                         for key in ('bugfix', 'vertical', 'horizontal') if key in prediction['answers']},
                              'model_input_tokens': prediction['usage']['input_tokens'],
                              'elapsed_seconds': round(time.perf_counter() - start, 4)})
            if len(mode_rows) % 25 == 0:
                output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
                print(mode, len(mode_rows), flush=True)
        result['runs'][mode]['timing'] = stats([r['elapsed_seconds'] for r in mode_rows])
        result['runs'][mode]['token_truncated_count'] = sum(r['state_was_token_truncated'] for r in mode_rows)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if agent.device.type == 'cuda':
        result['metadata']['gpu_peak_allocated_gib'] = round(torch.cuda.max_memory_allocated(agent.device) / 1024**3, 3)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(output)


if __name__ == '__main__':
    main()
