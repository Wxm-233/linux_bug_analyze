"""Three-class labels of the 60 development items (criteria.md section 4), mapped from
llm_review_expand_20261103/labels.json, which stays unchanged. No git, no model. Output: labels3.json."""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'llm_review_expand_20261103' / 'labels.json'
CONVENTION_A = {24: 'regs_irqs_disabled是static inline，几乎总会被内联进调用者，LoongArch也不做noinstr的objtool校验，'
                    '所以不会造成实际错误；上游后来（bb0511d59db9）把它改为__always_inline，属于写法上的完善'}


def main():
    if (HERE / 'labels3.json').exists():
        raise SystemExit('preserve')
    out = []
    for r in json.loads(OLD.read_text(encoding='utf-8'))['rows']:
        k, lab = r['cand'], r['label']
        if lab == 'a' and k in CONVENTION_A:
            new, basis, why = 'convention', 'first_annotator', CONVENTION_A[k]
        elif lab == 'a':
            new, basis, why = 'bug', 'fixed_upstream', r['label_reason']
        elif lab == 'a2':
            new, basis, why = 'bug', 'first_annotator_nofix', r['label_reason']
        elif r['kind'] == 'noinstr':  # the 25 b items of the noinstr kind and the c item on_thread_stack
            new, basis, why = 'convention', 'first_annotator', r['label_reason']
        elif lab == 'b':
            new, basis, why = 'not_issue', 'first_annotator', r['label_reason']
        else:
            raise SystemExit(f'unmapped {k} {lab}')
        out.append({**{x: r[x] for x in r if x not in ('label', 'basis', 'label_reason')},
                    'old_label': lab, 'label3': new, 'basis3': basis, 'reason3': why})
    note = '三类标签（criteria.md第四节），由llm_review_expand_20261103/labels.json按规则映射，调用之前写定。'
    (HERE / 'labels3.json').write_text(json.dumps({'note': note, 'rows': out}, indent=1, ensure_ascii=False) + '\n',
                                       encoding='utf-8')
    from collections import Counter
    print(Counter((r['label3'], r['basis3']) for r in out))


if __name__ == '__main__':
    main()
