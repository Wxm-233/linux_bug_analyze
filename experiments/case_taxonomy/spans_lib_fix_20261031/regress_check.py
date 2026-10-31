import sys, subprocess, json
sys.path.insert(0, '/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze')
sys.path.insert(0, '/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/spans_defect_audit_20261031')
from linux_bug_analyze.sibling_pairs import named_spans
from linux_bug_analyze.candidate_bridge import function_spans
from linux_bug_analyze.check_families import _without_directives
import wide_spans as W
REPO, END = '/root/repos/linux', 'df2908090cda'
files = [f for f in subprocess.run(['git','-C',REPO,'ls-tree','-r','--name-only',END],capture_output=True,text=True).stdout.splitlines() if f.endswith('.c')]
def blobs(paths):
    raw = subprocess.run(['git','-C',REPO,'cat-file','--batch'], input=''.join('%s:%s\n'%(END,p) for p in paths).encode(), capture_output=True).stdout
    out, pos = {}, 0
    for p in paths:
        nl = raw.index(b'\n', pos); h = raw[pos:nl].split(); pos = nl+1
        if len(h) < 3 or h[1] != b'blob': continue
        n = int(h[2]); out[p] = raw[pos:pos+n].decode('utf-8','replace'); pos += n+1
    return out
c = dict.fromkeys(['strict_old','strict_new','strict_audit','strict_lost_vs_old','strict_new_vs_audit_gain','strict_new_vs_audit_loss','bridge_old','bridge_new','bridge_lost_vs_old'], 0)
lost_ex = []
bridge_ex = []
for k in range(0, len(files), 2000):
    for p, t in blobs(files[k:k+2000]).items():
        o = {(s, h) for s, _, h in named_spans(t, window=4)}; n = {(s, h) for s, _, h in named_spans(t)}; a = {(s, h) for s, _, h in W.named_spans(t)}
        c['strict_old'] += len(o); c['strict_new'] += len(n); c['strict_audit'] += len(a)
        lost = {h for _, h in o} - {h for _, h in n}
        c['strict_lost_vs_old'] += len(lost)
        if lost and len(lost_ex) < 12: lost_ex.append((p, sorted(lost)))
        c['strict_new_vs_audit_gain'] += len({s for s, _ in n} - {s for s, _ in a}); c['strict_new_vs_audit_loss'] += len({s for s, _ in a} - {s for s, _ in n})
        pl = _without_directives(t)
        bo = {h for s, _, h in function_spans(pl, window=4) if h}; bn = {h for s, _, h in function_spans(pl) if h}
        c['bridge_old'] += len(bo); c['bridge_new'] += len(bn); c['bridge_lost_vs_old'] += len(bo - bn)
        real = {h for _, h in n} | {h for _, h in o}
        c.setdefault('bridge_lost_real', 0); c['bridge_lost_real'] += len((bo - bn) & real)
        if (bo - bn) & real and len(bridge_ex) < 10: bridge_ex.append((p, sorted((bo - bn) & real)))
print(json.dumps(c)); print(lost_ex); print('bridge real losses', bridge_ex)
