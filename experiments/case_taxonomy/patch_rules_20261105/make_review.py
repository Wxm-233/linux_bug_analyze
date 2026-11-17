"""review.json: every issue the model reported in L (criteria.md section 4), grouped into the distinct problems I
checked against the code (README section 3). Grouping is by keywords of the issue text, written after reading all
nine answers; the verdict of each group is the result of that code check. Windows Python; no model calls.
"""
from pathlib import Path
import json
import re

HERE = Path(__file__).resolve().parent
CALLS = HERE.parents[3] / '模型调用测试' / '2026-11-05' / 'patch_rules_20261105'

GROUPS = [  # (key, pattern on 位置+问题, verdict, note)
    ('K1', r'patch_map|fixmap.*抢占', 'real', 'K1'),
    ('text_poke_lockdep', r'bpf_arch_text_poke', 'real',
     'lockdep_assert_held(&text_mutex) then mutex_lock(&text_mutex); common callers do not hold text_mutex'),
    ('K4_ro_insns', r'ro_insns.*(NULL|未赋值|未被设置|从未)|rw_ex', 'real', 'K4'),
    ('K3_rv32_text_copy', r'(RV32|comp32).*(未实现|没有实现).*bpf_arch_text|仅在comp64实现', 'real', 'K3'),
    ('comp32_pc_relative', r'comp32.*(PC|ro_insns)|emit_call', 'not_issue',
     'RV32 emit_call jumps to an absolute address with lui/jalr; comp32 never uses ctx->insns for addresses'),
    ('kzalloc_whole', r'patch_text_set_nosync', 'real', 'kzalloc(len) of up to one pack (2MB); upstream fills page by page'),
    ('icache_before_finalize', r'icache|M3', 'not_issue',
     'finalize copies through bpf_arch_text_copy -> patch_text_nosync, which calls flush_icache_range afterwards'),
    ('finalize_fail_leak', r'bpf_int_jit_compile.*(finalize|out_offset)', 'not_issue',
     'bpf_jit_binary_pack_finalize frees both headers itself on failure'),
    ('kallsyms_verify_off', r'verify_off.*编译|编译失败', 'not_issue', 'bpf_prog_kallsyms_verify_off exists in the base'),
    ('jit_free_finalize', r'bpf_jit_free[^_]|bpf_jit_free$', 'not_issue', 'same pattern as x86 and upstream RISC-V'),
    ('free_pack_size_copy', r'bpf_jit_free_pack', 'not_issue', 'required by the x86 fix 676b2daabaf9'),
    ('trampoline_rx_write', r'trampoline', 'not_issue', 'the trampoline image is still writable while it is prepared'),
    ('free_exec_mismatch', r'bpf_jit_free_exec', 'not_issue', 'arch/riscv/net/bpf_jit_core.c defines bpf_jit_free_exec'),
]


def group(it):
    text = f'{it.get("位置", "")} {it.get("问题", "")}'
    for key, pat, verdict, note in GROUPS:
        if re.search(pat, text):
            return key, verdict
    return 'unmatched', None


def main():
    rows, per = [], {}
    for d in sorted(p for p in CALLS.iterdir() if p.is_dir()):
        text = (d / 'final.md').read_text(encoding='utf-8')
        items = json.loads(re.findall(r'```json\s*(.*?)```', text, re.S)[-1])
        _, series, tag, run = d.name.split('_')
        for it in items:
            key, verdict = group(it)
            rows.append({'call': d.name, 'version': f'{series}_{tag}', 'run': run, 'group': key, 'verdict': verdict,
                         'location': it.get('位置'), 'mechanism': it.get('机制'), 'issue': it.get('问题')})
            per.setdefault(f'{series}_{tag}', {}).setdefault(key, set()).add(run)
    assert not any(r['group'] == 'unmatched' for r in rows), [r for r in rows if r['group'] == 'unmatched']
    verdicts = {k: v for k, _, v, _ in GROUPS}
    summary = {v: {'distinct': len(g), 'real': sum(verdicts[k] == 'real' for k in g),
                   'groups': {k: {'runs': len(r), 'verdict': verdicts[k]} for k, r in sorted(g.items())}}
               for v, g in per.items()}
    out = {'groups': [{'key': k, 'verdict': v, 'note': n} for k, _, v, n in GROUPS], 'summary': summary, 'rows': rows}
    (HERE / 'review.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
