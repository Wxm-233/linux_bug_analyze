"""review.json: every issue the model reported in L2, grouped into the distinct problems I checked against the code
(README section 3), with three verdicts: real (a defect of the reviewed code), same_as_reference (true of the code
but identical in the upstream RISC-V migration or the x86 reference, so not introduced by this migration) and
not_issue. Also regroups the version-1 answers (patch_rules_20261105) with the same three verdicts, post hoc, for the
comparison. Grouping is by keywords of the issue text, written after reading all answers. Windows Python.
"""
from pathlib import Path
import json
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3] / '模型调用测试' / '2026-11-05'

GROUPS = [  # (key, pattern on 位置+问题, verdict, note)
    ('K1', r'fixmap.*(抢占|迁移|CPU)', 'real', 'K1'),
    ('text_poke_lockdep', r'bpf_arch_text_poke', 'real', 'lockdep_assert_held(&text_mutex) then mutex_lock(&text_mutex)'),
    ('K4_ro_insns', r'ro_insns.*(NULL|未赋值|未被设置|从未)|rw_ex', 'real', 'K4'),
    ('K3_rv32_text_copy', r'(RV32|comp32).*(未实现|没有实现|没有).*bpf_arch_text|仅在comp64实现|只在 bpf_jit_comp64.c 实现'
                          r'|RV32 缺失', 'real', 'K3'),
    ('patch_map_strict_module_rwx', r'STRICT_MODULE_RWX', 'real',
     'patch_map returns addr unless STRICT_MODULE_RWX; the pack is set_memory_rox; arm64 fixed the same (b1480ed230ac)'),
    ('comp32_pc_relative', r'comp32.*(PC|ro_insns)|emit_call', 'not_issue', 'RV32 emit_call uses lui/jalr to an absolute address'),
    ('kzalloc_whole', r'patch_text_set_nosync', 'real', 'kzalloc(len) of up to one pack; upstream fills page by page'),
    ('jited_before_finalize', r'jited', 'same_as_reference', 'upstream 48a8f78c50bd sets jited before finalize too'),
    ('build_body_leak', r'build_body', 'same_as_reference', 'upstream 48a8f78c50bd and the end version also goto out_offset there'),
    ('icache_before_finalize', r'icache|M3', 'not_issue', 'patch_text_nosync calls flush_icache_range after writing'),
    ('finalize_fail_leak', r'bpf_int_jit_compile.*(finalize|out_offset)', 'not_issue', 'finalize frees both headers on failure'),
    ('kallsyms_verify_off', r'verify_off.*编译|编译失败', 'not_issue', 'exists in the base'),
    ('jit_free_finalize', r'bpf_jit_free[^_]|bpf_jit_free$', 'same_as_reference', 'same pattern as x86 and upstream RISC-V'),
    ('free_pack_size_copy', r'bpf_jit_free_pack', 'not_issue', 'required by the x86 fix 676b2daabaf9'),
    ('trampoline_rx_write', r'trampoline', 'not_issue', 'the trampoline image is still writable while it is prepared'),
    ('free_exec_mismatch', r'bpf_jit_free_exec', 'not_issue', 'arch/riscv/net/bpf_jit_core.c defines bpf_jit_free_exec'),
]
VERDICT = {k: v for k, _, v, _ in GROUPS}


def group(it):
    text = f'{it.get("位置", "")} {it.get("问题", "")}'
    for key, pat, _, _ in GROUPS:
        if re.search(pat, text):
            return key
    return 'unmatched'


def collect(folder, prefix):
    rows, per = [], {}
    for d in sorted(p for p in (ROOT / folder).iterdir() if p.is_dir() and p.name.startswith(prefix)):
        items = json.loads(re.findall(r'```json\s*(.*?)```', (d / 'final.md').read_text(encoding='utf-8'), re.S)[-1])
        _, series, tag, run = d.name.split('_')
        for it in items:
            key = group(it)
            rows.append({'call': d.name, 'version': f'{series}_{tag}', 'run': run, 'group': key,
                         'verdict': VERDICT.get(key), 'location': it.get('位置'), 'issue': it.get('问题')})
            per.setdefault(f'{series}_{tag}', {}).setdefault(key, set()).add(run)
    assert not any(r['group'] == 'unmatched' for r in rows), [r for r in rows if r['group'] == 'unmatched']
    summary = {}
    for v, g in per.items():
        counts = {x: sum(VERDICT[k] == x for k in g) for x in ('real', 'same_as_reference', 'not_issue')}
        summary[v] = {'distinct': len(g), **counts,
                      'groups': {k: {'runs': len(r), 'verdict': VERDICT[k]} for k, r in sorted(g.items())}}
    return rows, summary


def main():
    rows2, sum2 = collect('patch_rules_v2_20261105', 'L2_')
    rows1, sum1 = collect('patch_rules_20261105', 'L_')
    out = {'groups': [{'key': k, 'verdict': v, 'note': n} for k, _, v, n in GROUPS],
           'L2': sum2, 'L1_regrouped_post_hoc': sum1, 'rows_L2': rows2}
    (HERE / 'review.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    for name, s in (('L1', sum1), ('L2', sum2)):
        for v, x in s.items():
            print(name, v, x['distinct'], x['real'], x['same_as_reference'], x['not_issue'],
                  {k: g['runs'] for k, g in x['groups'].items()})


if __name__ == '__main__':
    main()
