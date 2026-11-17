"""Extract changed declarations from full historical files, not hunk labels."""
from collections import defaultdict
import difflib
import gzip
import re
from common import *
from c_ranges import declarations, changed_lines, scrub

MAPPINGS = [
 ('A019','arch/riscv/kernel/crash_core.c','arch_crash_save_vmcoreinfo','arch/riscv/kernel/vmcore_info.c','arch_crash_save_vmcoreinfo'),
 ('A102','arch/riscv/kernel/sbi.c','__sbi_ecall','arch/riscv/kernel/sbi_ecall.c','__sbi_ecall'),
 ('A102','arch/riscv/kernel/sbi.c','__sbi_base_ecall','arch/riscv/kernel/sbi_ecall.c','__sbi_base_ecall'),
 ('A102','arch/riscv/kernel/sbi.c','sbi_err_map_linux_errno','arch/riscv/include/asm/sbi.h','sbi_err_map_linux_errno'),
 ('A281','arch/riscv/kernel/elf_kexec.c','elf_find_pbase','arch/riscv/kernel/kexec_elf.c','elf_find_pbase'),
 ('A309','arch/riscv/kernel/machine_kexec.c','machine_kexec_mask_interrupts','kernel/irq/kexec.c','machine_kexec_mask_interrupts'),
 ('B414','kernel/crash_core.c','reserve_crashkernel_low','kernel/crash_reserve.c','reserve_crashkernel_low'),
 ('B414','kernel/crash_core.c','reserve_crashkernel_generic','kernel/crash_reserve.c','reserve_crashkernel_generic'),
 ('B435','kernel/bpf/verifier.c','do_misc_fixups','kernel/bpf/fixups.c','bpf_do_misc_fixups'),
]
MAPPINGS += [('A029','arch/riscv/include/asm/pgalloc.h',n,
              'arch/riscv/include/asm/pgalloc.h',n,'macro','function')
             for n in ('__pmd_free_tlb','__pud_free_tlb','__p4d_free_tlb')]

def substantive(text, numbers):
    clean = scrub(text,keep_literals=True).splitlines()
    return [n for n in numbers if 1 <= n <= len(clean) and clean[n-1].strip()]

def align(a, b, numbers):
    wanted = set(numbers)
    result = {}
    for block in difflib.SequenceMatcher(None, a.splitlines(), b.splitlines(), autojunk=False).get_matching_blocks():
        for n in wanted:
            if block.a <= n-1 < block.a+block.size:
                result[n] = block.b + (n-1-block.a) + 1
    return result

def main():
    check_criteria()
    assert git('rev-parse','HEAD').strip() == 'df2908090cda368b01ff43709f51890076c56157'
    audit = {r['id']: r for r in read(AUDIT/'sample_miss_analysis.json')['samples']}
    old = read(OLD/'sample_hits.json')['samples']
    originals = {r['id']: r for r in read(BASE/'cross_arch_sample_set_20261102/labels_v2_1.json')}
    labels = {r['id']: r for r in read(BASE/'boundary_taxonomy_20261106/labels.json')}
    files = {f for r in old for f in r['files']} | {m[3] for m in MAPPINGS}
    current = {}
    for f in sorted(files):
        path = KSRC/f
        if path.is_file() and path.suffix in ('.c','.h'):
            text = path.read_text(encoding='utf-8', errors='replace')
            decl, errors = declarations(text)
            current[f] = {'sha256': sha(path), 'declarations': decl, 'errors': errors}
    # Existing AST extents improve present-day macro-generated declarations only;
    # they cannot be used to guess what a historical hunk changed.
    ast = defaultdict(dict)
    for u in read(AUDIT/'evidence/scopes.json'):
        for r in u['functions']:
            f = r['at'][0]
            if f in current:
                ast[f][(r['name'],r['start'],r['end'])] = {
                    'kind':'function','name':r['name'],'start':r['start'],
                    'end':r['end'],'body_start':r['start'],'method':'existing_libclang_extent'}
    for f, rows in ast.items():
        current[f]['declarations'].extend(rows.values())
        current[f]['declarations'] = list({(r['kind'],r['name'],r['start'],r['end']):r
                                          for r in current[f]['declarations']}.values())
    mapping_rows = []
    for mapping in MAPPINGS:
        ident, of, on, nf, nn = mapping[:5]
        old_kind,new_kind=mapping[5:] if len(mapping)>5 else (None,None)
        targets = [r for r in current.get(nf,{}).get('declarations',[]) if r['name']==nn and (not new_kind or r['kind']==new_kind)]
        assert targets, (ident,nf,nn)
        mapping_rows.append({'id':ident,'old_file':of,'old_name':on,'new_file':nf,'new_name':nn,
                             'old_kind':old_kind,'new_kind':new_kind,
                             'evidence':{'audit_file':'../boundary_audit_20261107/sample_miss_analysis.json',
                                         'audit_id':ident,'judgment':audit[ident]['judgment'],
                                         'current_sha256':current[nf]['sha256'],
                                         'current_declarations':targets,
                                         'additional_evidence':'evidence/history_probe.json' if old_kind else None},
                             'kind':'macro_to_inline_function' if old_kind else ('name_rename_and_move' if on!=nn else 'file_move')})
    write('history_mappings.json', mapping_rows)
    rows=[]
    for index, s in enumerate(old):
        ident, commit = s['id'], s['commit']
        patch_path = AUDIT/f'evidence/patches/{ident}.patch'
        patch = patch_path.read_text(encoding='utf-8') if patch_path.exists() else git('show','--format=fuller','--find-renames','-U3',commit)
        (HERE/'evidence/patches').mkdir(parents=True,exist_ok=True)
        (HERE/f'evidence/patches/{ident}.patch').write_text(patch, encoding='utf-8')
        entities = {}
        file_rows=[]
        for f in changed_lines(patch):
            fr = f | {'versions':[]}
            for version, path, ns in [('parent',f['old_path'],f['old_lines']),('fixed',f['new_path'],f['new_lines'])]:
                if Path(path).suffix not in ('.c','.h'):
                    if ns: fr['versions'].append({'version':version,'path':path,'status':'unsupported_file_domain','changed_lines':ns})
                    continue
                rev = commit+'^' if version=='parent' else commit
                text = git('show', f'{rev}:{path}', optional=True)
                if text is None:
                    fr['versions'].append({'version':version,'path':path,'status':'file_absent','changed_lines':ns})
                    continue
                decl, errors = declarations(text)
                meaningful = substantive(text, ns)
                covered = set()
                matched=[]
                for r in decl:
                    overlap = [n for n in meaningful if r['start']<=n<=r['end']]
                    if overlap:
                        covered.update(overlap)
                        ent = entities.setdefault((path,r['kind'],r['name']), {'file':path,'kind':r['kind'],'name':r['name'],'historical_ranges':[]})
                        ev = r | {'version':version,'revision':rev,'changed_lines':overlap}
                        ent['historical_ranges'].append(ev)
                        matched.append(ev)
                now_path = path
                # Exact line alignment uses only proven file moves, no renamed function heuristic.
                specific = [m for m in mapping_rows if m['id']==ident and m['old_file']==path]
                if not (KSRC/now_path).is_file() and len({m['new_file'] for m in specific})==1:
                    now_path=specific[0]['new_file']
                now = (KSRC/now_path).read_text(encoding='utf-8',errors='replace') if (KSRC/now_path).is_file() else None
                aligned = align(text, now, meaningful) if now is not None else {}
                fr['versions'].append({'version':version,'path':path,'status':'ok',
                    'source_sha256':hashlib.sha256(text.encode()).hexdigest(),
                    'changed_lines':ns,'substantive_changed_lines':meaningful,'modified_declarations':matched,
                    'unassigned_changed_lines':sorted(set(meaningful)-covered), 'parser_diagnostics':errors,
                    'alignment_current_path':now_path,'aligned_changed_lines':[{'historical':k,'current':v} for k,v in sorted(aligned.items())]})
            file_rows.append(fr)
        rows.append({'id':ident,'commit':commit,'check':labels[ident]['check'],'subject':originals[ident]['subject'],
                     'legacy_functions':s['functions'],'legacy_hit':s['hit'],'patch':f'evidence/patches/{ident}.patch',
                     'audit_primary_category':audit.get(ident,{}).get('primary_category'),
                     'audit_judgment':audit.get(ident,{}).get('judgment'),
                     'entities':list(entities.values()),'files':file_rows})
        if (index+1)%20==0: print(f'history {index+1}/120', flush=True)
    write('evidence/current_ranges.json',current)
    write('evidence/sample_entities.json',rows)
    paths=[OLD/'sample_hits.json',BASE/'boundary_taxonomy_20261106/labels.json',BASE/'cross_arch_sample_set_20261102/labels_v2_1.json',
           AUDIT/'sample_miss_analysis.json',AUDIT/'revised_stats.json',AUDIT/'evidence/scopes.json']
    write('evidence/sample_input_manifest.json', inputs_manifest(paths))
    print('extracted',len(rows),'samples',sum(len(s['entities']) for s in rows),'entities')

if __name__=='__main__': main()
