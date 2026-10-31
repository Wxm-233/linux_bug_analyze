"""Judgement layer 1: program rules (criteria.md). WSL; no model calls; prints counts only.
Rule 1: candidate still uses a name C removed from all non-arch code (word form, or member form ->x/.x).
Rule 2: C changed the parameter count of a function/macro; candidate calls it, or implements it, with the old count.
Candidates are count_v2's v2 lists (recomputed). Flagged non-target candidates get a survival check at the range end.
Usage: python3 judge_rules.py smoke   (audited yes pairs, prints, writes nothing)
       python3 judge_rules.py         (main, audited and RISC-V pairs -> judge_rules.json, stats.json, survival.json)
"""
from pathlib import Path
import json
import re
import statistics
import sys

HERE = Path(__file__).resolve().parent
C_DIR = HERE.parent
sys.path.insert(0, str(C_DIR / 'ccp_candgen_v2_20261030'))
import count_v2 as CV  # noqa: E402

CC, X, P, WORD, MEMBER = CV.CC, CV.X, CV.P, CV.WORD, CV.MEMBER
END = X.RANGE.split('..')[1]
NOT_DECL = {'return', 'if', 'while', 'for', 'switch', 'sizeof', 'case', 'else', 'do', 'goto', 'typeof', '__typeof__'}
DECL_PREFIX = re.compile(r'^\s*(?:[A-Za-z_]\w*[\s\*]+)+$')
DEFINE = re.compile(r'#\s*define\s+([A-Za-z_]\w*)\(')
CALLSITE = re.compile(r'\b([A-Za-z_]\w*)\s*\(')
NON_ARCH = ('*.c', '*.h', ':!arch/')


def hunk_blocks(commit):
    """[(minus_text, plus_text)] per hunk of C's non-arch .c/.h changes."""
    out, old, path, cur = [], None, None, None
    for line in P['git']('show', '--format=', '-U0', '--no-renames', commit, '--', '*.c', '*.h').splitlines():
        if line.startswith('--- '):
            old = line[6:] if line.startswith('--- a/') else None
            continue
        if line.startswith('+++ '):
            p = line[6:] if line.startswith('+++ b/') else old
            path = p if p and not p.startswith('arch/') else None
            continue
        if line.startswith('@@'):
            cur = [[], []] if path else None
            if cur is not None:
                out.append(cur)
            continue
        if cur is not None and line[:1] in '-+':
            cur[0 if line[0] == '-' else 1].append(line[1:])
    return [('\n'.join(m), '\n'.join(p)) for m, p in out]


def balanced(text, i):
    """Content between the '(' at text[i] and its matching ')', or None if unbalanced."""
    depth = 0
    for j in range(i, len(text)):
        if text[j] == '(':
            depth += 1
        elif text[j] == ')':
            depth -= 1
            if depth == 0:
                return text[i + 1:j], j
    return None, None


def arity(params):
    p = params.strip()
    if not p or p == 'void':
        return 0
    depth, n = 0, 1
    for ch in p:
        if ch in '([{':
            depth += 1
        elif ch in ')]}':
            depth -= 1
        elif ch == ',' and depth == 0:
            n += 1
    return n


def declarations(text):
    """{name: {arity}} for function declarations/definitions and parameterised macros written fully in text."""
    out = {}
    for m in DEFINE.finditer(text):
        params, _ = balanced(text, m.end() - 1)
        if params is not None:
            out.setdefault(m.group(1), set()).add(arity(params))
    for m in CALLSITE.finditer(text):
        name = m.group(1)
        if name in NOT_DECL or name in CC.C_WORDS:
            continue
        start = text.rfind('\n', 0, m.start()) + 1
        prefix = text[start:m.start()]
        if '#' in prefix or not DECL_PREFIX.match(prefix) or set(prefix.split()) & NOT_DECL:
            continue
        params, j = balanced(text, m.end() - 1)
        if params is None:
            continue
        rest = text[j + 1:].lstrip()
        if rest and not (rest[0] in ';{' or rest[0].isalpha() or rest[0] == '_'):
            continue
        out.setdefault(name, set()).add(arity(params))
    return out


def grep_found(commit, names, member):
    """Names (word or member form) still present in non-arch .c/.h at commit."""
    found, names = set(), sorted(names)
    for k in range(0, len(names), 150):
        alt = '|'.join(map(re.escape, names[k:k + 150]))
        args = ['-o', '-E', r'(->|\.)(%s)\b' % alt] if member else ['-o', '-w', '-E', '(%s)' % alt]
        for line in P['git']('grep', *args, commit, '--', *NON_ARCH).splitlines():
            parts = line.split(':', 2)
            if len(parts) == 3:
                found.add(parts[2].lstrip('->.'))
    return found


def rules_of(commit):
    blocks = hunk_blocks(commit)
    minus = '\n'.join(m for m, _ in blocks)
    words = CV.usable(WORD.findall(minus))
    members = CV.usable(MEMBER.findall(minus))
    removed_words = words - grep_found(commit, words, False) if words else set()
    removed_members = members - grep_found(commit, members, True) if members else set()
    old, new = {}, {}
    for m, p in blocks:
        for name, a in declarations(m).items():
            old.setdefault(name, set()).update(a)
        for name, a in declarations(p).items():
            new.setdefault(name, set()).update(a)
    changed = {n: (sorted(old[n]), sorted(new[n])) for n in CV.usable(old) & set(new) if not old[n] & new[n]}
    return {'removed_words': sorted(removed_words), 'removed_members': sorted(removed_members), 'arity_changed': changed}


def func_texts(commit, files):
    """{(file, name): (header_text, body_text)} at commit; same-name spans are concatenated."""
    texts = P['blobs'](['%s:%s' % (commit, f) for f in files])
    out = {}
    for f in files:
        text = texts.get('%s:%s' % (commit, f))
        if not text:
            continue
        lines = text.splitlines()
        for s, e, name in CC.named_spans(text):
            h = CV.header_start(lines, s)
            hd, bd = out.get((f, name), ('', ''))
            out[(f, name)] = (hd + '\n' + '\n'.join(lines[h - 1:s - 1]), bd + '\n' + '\n'.join(lines[s - 1:e]))
    return out


def judge(name, header, body, r):
    """Rule hits for one function: list of (rule, trigger)."""
    hits = []
    rw, rm = set(r['removed_words']), set(r['removed_members'])
    for w in sorted((set(WORD.findall(body)) | {name}) & rw):
        hits.append(('removed_word', w))
    for w in sorted(set(MEMBER.findall(body)) & rm):
        hits.append(('removed_member', w))
    for fn, (old, new) in r['arity_changed'].items():
        if name == fn:
            m = re.search(r'\b%s\s*\(' % re.escape(fn), header)
            if m:
                params, _ = balanced(header, m.end() - 1)
                if params is not None and arity(params) in old:
                    hits.append(('old_arity_impl', fn))
        for m in re.finditer(r'\b%s\s*\(' % re.escape(fn), body):
            params, _ = balanced(body, m.end() - 1)
            if params is not None and arity(params) in old and arity(params) not in new:
                hits.append(('old_arity_call', fn))
                break
    return hits


def survival(f, name, hits, r):
    """Range-end status of a flagged non-target candidate."""
    ft = func_texts(END, [f])
    if (f, name) not in ft:
        return 'changed_or_removed'
    header, body = ft[(f, name)]
    still = {k for k in hits} & set(judge(name, header, body, r))
    return 'still_present' if still else 'changed_or_removed'


def score(p):
    c, tg = p['seed'], {tuple(x) for x in p['targets']}
    keys = CV.keys_of(c)
    cands = CV.candidates_v2(c, keys, set(p['c_arches']))
    r = rules_of(c)
    flagged = []
    if r['removed_words'] or r['removed_members'] or r['arity_changed']:
        ft = func_texts(c, sorted({f for f, _, _ in cands}))
        for i, (f, n, _) in enumerate(cands):
            h = judge(n, *ft.get((f, n), ('', '')), r)
            if h:
                flagged.append({'file': f, 'name': n, 'v2_rank': i + 1, 'target': (f, n) in tg, 'hits': h})
    order = [(x['file'], x['name']) for x in flagged] + [(f, n) for f, n, _ in cands if (f, n) not in {(x['file'], x['name']) for x in flagged}]
    rank = [i for i, k in enumerate(order) if k in tg]
    return {'seed': c, 'target': p['target'], 'rules': r, 'pool_v2': len(cands), 'cov_all_v2': any((f, n) in tg for f, n, _ in cands),
            'flagged': flagged, 'target_flagged': any(x['target'] for x in flagged),
            'rerank_best': rank[0] + 1 if rank else None,
            'v2_best': next((i + 1 for i, (f, n, _) in enumerate(cands) if (f, n) in tg), None)}


def summary(rs):
    cov = [r for r in rs if r['cov_all_v2']]
    fl = [r for r in rs if r['flagged']]
    counts = sorted(len(r['flagged']) for r in fl) or [0]
    tot = sum(len(r['flagged']) for r in rs)
    tgt = sum(1 for r in rs for x in r['flagged'] if x['target'])
    later = sum(1 for r in rs for x in r['flagged'] if not x['target'] and x.get('survival') == 'changed_or_removed')
    by_rule = {k: sum(1 for r in cov if any(x['target'] and any(h[0] == k for h in x['hits']) for x in r['flagged']))
               for k in ('removed_word', 'removed_member', 'old_arity_impl', 'old_arity_call')}
    top = lambda key, n: sum(1 for r in rs if r[key] and r[key] <= n)
    return {'pairs': len(rs), 'covered_v2': len(cov), 'target_flagged_in_covered': sum(r['target_flagged'] for r in cov),
            'rule_recall': round(sum(r['target_flagged'] for r in cov) / len(cov), 3) if cov else None, 'by_rule': by_rule,
            'pairs_with_flags': len(fl), 'flags_per_pair_median': statistics.median(counts), 'flags_per_pair_max': max(counts),
            'flags_total': tot, 'flags_target': tgt, 'flags_nontarget_changed_or_removed': later,
            'flags_nontarget_still_present': tot - tgt - later,
            'precision_strict': round(tgt / tot, 3) if tot else None, 'precision_lenient': round((tgt + later) / tot, 3) if tot else None,
            'top20': {'v2': top('v2_best', 20), 'rerank': top('rerank_best', 20)},
            'top50': {'v2': top('v2_best', 50), 'rerank': top('rerank_best', 50)}}


def riscv_new_code():
    """Descriptive: for RISC-V pairs whose edits are outside existing function bodies, what the rules see in arch/riscv at C."""
    out = []
    for case in json.loads((C_DIR / 'ccp_candgen_v2_20261030' / 'riscv_cases.json').read_text(encoding='utf-8'))['cases']:
        if case['kind'] == 'existing_function':
            continue
        c = case['seed']
        r = rules_of(c)
        files = sorted(l for l in P['git']('ls-tree', '-r', '--name-only', c, '--', 'arch/riscv').splitlines() if l.endswith(('.c', '.h')))
        hits = []
        if r['removed_words'] or r['removed_members'] or r['arity_changed']:
            for (f, n), (hd, bd) in func_texts(c, files).items():
                h = judge(n, hd, bd, r)
                if h:
                    hits.append({'file': f, 'name': n, 'hits': h})
        out.append({'seed': c, 'target': case['target'], 't_subject': case['t_subject'], 'rules': r, 'riscv_flags': hits,
                    't_files_flagged': sorted({x['file'] for x in hits} & set(case['riscv_files']))})
    return out


def main():
    rows_v2 = json.loads((C_DIR / 'ccp_candgen_v2_20261030' / 'v2_pool.json').read_text())['rows']
    pool = {(p['seed'], p['target']): p for p in json.loads((C_DIR / 'ccp_feasibility_20261030' / 'ccp_pool.json').read_text())['pairs']}
    if sys.argv[1:] == ['smoke']:
        for r in rows_v2:
            if r['audit_label'] == 'yes':
                s = score(pool[(r['seed'], r['target'])])
                print(r['target'][:10], 'rules', {k: len(v) for k, v in s['rules'].items()}, 'flags', len(s['flagged']),
                      'target_flagged', s['target_flagged'], 'v2_best', s['v2_best'], 'rerank', s['rerank_best'],
                      [(x['name'], x['hits'][:2]) for x in s['flagged'][:3]], flush=True)
        return
    target = HERE / 'judge_rules.json'
    if target.exists():
        raise SystemExit('preserve')
    rows = []
    for n, r in enumerate(rows_v2, 1):
        s = score(pool[(r['seed'], r['target'])])
        r1 = s['rules']
        for x in s['flagged']:
            if not x['target']:
                x['survival'] = survival(x['file'], x['name'], [tuple(h) for h in x['hits']], r1)
        s.update({k: r[k] for k in ('fresh', 'audited', 'audit_label', 'target_arches')})
        rows.append(s)
        if n % 20 == 0:
            print('progress', n, len(rows_v2), flush=True)
    main_rows = [r for r in rows if r['fresh'] and not r['audited']]
    st = summary(main_rows)
    rr, pl = st['rule_recall'] or 0, st['precision_lenient'] or 0
    stats = {'main_untouched': st, 'reference_audited_yes': summary([r for r in rows if r['audit_label'] == 'yes']),
             'riscv_existing_function_pairs': [{'target': r['target'], 'flagged': len(r['flagged']), 'target_flagged': r['target_flagged'],
                                                'v2_best': r['v2_best'], 'rerank_best': r['rerank_best']} for r in rows if 'riscv' in r['target_arches']],
             'decision': ('program_layer_useful_design_model_layer' if rr >= 0.15 and pl >= 0.30 else
                          'program_layer_low_recall_pilot_model_layer' if rr < 0.15 else 'analyse_false_flags'),
             'kimi_calls': 0}
    surv = [{'seed': r['seed'], 'target': r['target'], **x} for r in main_rows for x in r['flagged'] if x.get('survival') == 'still_present']
    target.write_text(json.dumps({'rows': rows}, indent=1) + '\n')
    (HERE / 'survival.json').write_text(json.dumps({'still_present': surv, 'riscv_new_code': riscv_new_code()}, indent=1) + '\n')
    (HERE / 'stats.json').write_text(json.dumps(stats, indent=1) + '\n')
    print(json.dumps({'main_untouched': st, 'decision': stats['decision']}))


if __name__ == '__main__':
    main()
