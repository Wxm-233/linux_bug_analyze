"""Freeze this round's scope and working-note identities before experiments."""
from pathlib import Path
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
OUTER = HERE.parents[3]
NAMES = ['当前代办.md', '当前研究方向与进展.md', '项目研究与文档写作交接说明.md']

def save(name, value):
    with (HERE / name).open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')

def main():
    before = {}
    for name in NAMES:
        raw = (OUTER / name).read_bytes()
        before[name] = hashlib.sha256(raw).hexdigest()
        (HERE / ('before_' + name)).write_bytes(raw)
    save('notes_before.json', {'before_sha256': before})
    (HERE / 'plan_before.md').write_bytes((OUTER / '接口验证后续规划.md').read_bytes())
    shutil.copyfile(HERE.parent / 'virtio_platform_qualification_20261027/sync_work_notes.py', HERE / 'sync_work_notes.py')
    save('frozen_plan.json', {
        'date': '2026-10-27', 'purpose': 'effective source origin at die attribute compilation, with versioned export policy',
        'profiles': ['old_x86_64', 'fixed_x86_64', 'old_s390', 'fixed_s390'],
        'new_work': ['full translation-unit preprocessing using each archived runtime build command and configuration',
                     'effective macro definition timeline and compiled attribute projection',
                     'versioned source-qualification adapter using the unchanged generic contract evaluator',
                     'identity, unknown-origin, policy and definition-order controls'],
        'historical_gap': 'N2.16 only reviewed direct-source candidates; did not expand the runtime translation unit',
        'evidence_tier': 'new reconstruction of archived compilation context; not historical compiler-time evidence or new boot',
        'policy': 'fixed dual-native export policy; parent application explicitly counterfactual',
        'not_claimed': ['old fallback violated old ABI', 'physical die topology truth', 'runtime first consumption or stable lifecycle',
                        'new Linux defect', 'independent detection sample', 'automatic semantic policy inference'],
        'paid_model_calls_planned': 0, 'kernel_builds_planned': 0, 'boots_planned': 0,
        'preserve_historical_unknowns': True, 'independent_positive': 0, 'independent_normal': 0,
    })
    print(json.dumps({'status': 'frozen', 'notes': len(before)}))

if __name__ == '__main__':
    main()
