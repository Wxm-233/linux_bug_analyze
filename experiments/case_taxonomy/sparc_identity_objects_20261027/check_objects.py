"""Decide O1-O4 from extracted disassembly/.i text; constructed tampering controls in memory."""
from pathlib import Path
import copy
import json
import re

HERE = Path(__file__).resolve().parent
A = HERE / 'analysis'
VARIANTS = ['parent-default', 'parent-nr64', 'fixed-default', 'fixed-nr64']


def lines(variant, name):
    path = A / f'{variant}.{name}.dis.txt'
    return path.read_text(encoding='utf-8').splitlines() if path.exists() else None


def load_ld_into(lines_, i, reg, symbol, window):
    """True if within `window` lines before i an `ld [..], reg` is relocated against symbol."""
    for j in range(max(0, i - window), i):
        if re.search(r'\bld\s+\[ %\w+ \], ' + re.escape(reg) + r'$', lines_[j]) and j + 1 < len(lines_) \
                and re.search(r'R_SPARC_LO10\s+' + re.escape(symbol) + r'$', lines_[j + 1]):
            return True
    return False


def call_index(lines_, symbol):
    return [i for i, l in enumerate(lines_) if re.search(r'R_SPARC_WDISP30\s+' + re.escape(symbol) + r'$', l)]


def o1(dis, nr):
    """IRQ-stack loop bound: runtime nr_cpu_ids (4096) or constant 64 word (64).

    attempt2: the loop region is [first softirq/hardirq_stack base relocation,
    last memblock_alloc_try_nid call + 15 lines]; compilers may rotate the loop so
    the bound test sits after the body. Exactly one bound construct must be inside.
    """
    bases = [i for i, l in enumerate(dis) if re.search(r'R_SPARC_(HI22|LO10)\s+(softirq|hardirq)_stack$', l)]
    allocs = call_index(dis, 'memblock_alloc_try_nid')
    if not bases or len(allocs) < 2:
        return 'insufficient', 'IRQ-stack allocation loop not located'
    lo, hi = min(bases), max(allocs) + 15
    region = dis[lo:hi + 1]
    stores = [l for l in region if re.search(r'stx\s+%o0, \[ %i[23] \+ %i\d \]$', l)]
    if len(stores) < 2:
        return 'insufficient', 'per-CPU softirq/hardirq stack stores not shown in region'
    if nr == 4096:
        calls = [i for i in call_index(dis, '_find_next_bit') if lo <= i <= hi]
        sized = [i for i in calls if load_ld_into(dis, i, '%o1', 'nr_cpu_ids', 8)]
        exit_cmp = [i for i in sized if any(re.search(r'R_SPARC_LO10\s+nr_cpu_ids$', dis[k]) for k in range(i, i + 4))]
        return ('runtime_nr_cpu_ids', 'size arg %o1 loaded from nr_cpu_ids into _find_next_bit; loop exit compares nr_cpu_ids')             if len(calls) == 1 and exit_cmp else ('insufficient', f'bounded find-bit calls in region: {len(calls)}/{len(sized)}')
    if any('nr_cpu_ids' in l for l in dis):
        return 'insufficient', 'nr64 setup_arch unexpectedly references nr_cpu_ids'
    const = [l for l in region if re.search(r'cmp\s+%\w+, 0x40$', l)]
    return ('constant_64', 'single-word scan bounded by constant 0x40, no nr_cpu_ids') if len(const) == 1         else ('insufficient', f'constant 0x40 bound constructs in region: {len(const)}')


def o2(dis, nr, version):
    """Possible-weight width inside record_one_cpu (fixed) / smp_fill_in_cpu_possible_map (parent)."""
    if dis is None:
        return 'insufficient', 'function absent'
    if nr == 4096:
        calls = [i for i in call_index(dis, '__bitmap_weight') if load_ld_into(dis, i, '%o1', 'nr_cpu_ids', 6)]
        return ('runtime_nr_cpu_ids', '__bitmap_weight size %o1 loaded from nr_cpu_ids') if calls \
            else ('insufficient', 'nr_cpu_ids-sized weight not shown')
    if call_index(dis, '__bitmap_weight'):
        return 'insufficient', 'nr64 unexpectedly calls __bitmap_weight'
    return ('constant_64', 'full-word __arch_hweight64') if call_index(dis, '__arch_hweight64') \
        else ('insufficient', 'constant-width weight not shown')


def o3(facts, nr):
    text = facts['setup_64.i:alloc_irqstack_bootmem'] or ''
    expected = '(nr_cpu_ids)' if nr == 4096 else '(((unsigned int)64))'
    m = re.search(r'find_next_bit\(.*?, (\(.+?\)), \(\(i\)\)\), \(\(i\)\) < (\(.+?\)); \(\(i\)\)\+\+\)', text)
    if not m:
        return 'insufficient', 'loop expansion not found'
    return ('matches', m.group(1)) if m.group(1) == m.group(2) == expected else ('insufficient', m.groups())


def o4(facts, version):
    smp_funcs = facts['smp_64.o.defined_functions']
    has_fill = 'smp_fill_in_cpu_possible_map' in smp_funcs
    rec = facts.get('prom_64.o:record_one_cpu', {}).get('relocation_symbols', [])
    guard = 'nr_cpu_ids' in rec
    ok = (has_fill and not guard) if version == 'parent' else (guard and not has_fill)
    return ('matches_version', {'smp_fill_in_present': has_fill, 'record_guard_reads_nr_cpu_ids': guard}) if ok \
        else ('insufficient', {'smp_fill_in_present': has_fill, 'record_guard_reads_nr_cpu_ids': guard})


def decide(variant, facts, dis_setup, dis_weight):
    version, cfg = variant.split('-')
    nr = int(facts['config_NR_CPUS'])
    if nr != (4096 if cfg == 'default' else 64):
        return {k: ('insufficient', 'configuration label/NR_CPUS mismatch') for k in ['O1', 'O2', 'O3', 'O4']}
    return {'O1': o1(dis_setup, nr), 'O2': o2(dis_weight, nr, version), 'O3': o3(facts, nr), 'O4': o4(facts, version)}


def main():
    facts = json.loads((A / 'object_facts.json').read_text(encoding='utf-8'))
    results = {}
    for v in VARIANTS:
        weight_fn = 'record_one_cpu' if v.startswith('fixed') else 'smp_fill_in_cpu_possible_map'
        results[v] = decide(v, facts[v], lines(v, 'setup_arch'), lines(v, weight_fn))
    controls = []
    fd = facts['fixed-default']
    base_setup, base_rec = lines('fixed-default', 'setup_arch'), lines('fixed-default', 'record_one_cpu')

    def ctl(name, variant, f, setup, rec, key, expected):
        got = decide(variant, f, setup, rec)[key][0]
        controls.append({'control': name, 'check': key, 'expected': expected, 'got': got, 'as_expected': got == expected})

    ctl('nr_cpu_ids_reloc_removed_from_loop', 'fixed-default', fd,
        [l for l in base_setup if not re.search(r'R_SPARC_LO10\s+nr_cpu_ids$', l)], base_rec, 'O1', 'insufficient')
    ctl('irq_stack_stores_removed', 'fixed-default', fd,
        [l for l in base_setup if 'irq_stack' not in l], base_rec, 'O1', 'insufficient')
    ctl('weight_helper_swapped_to_hweight64', 'fixed-default', fd, base_setup,
        [l.replace('__bitmap_weight', '__arch_hweight64') for l in base_rec], 'O2', 'insufficient')
    swapped = copy.deepcopy(fd); swapped['config_NR_CPUS'] = '64'
    ctl('default_objects_labelled_nr64_config', 'fixed-default', swapped, base_setup, base_rec, 'O1', 'insufficient')
    nr64_as_default = copy.deepcopy(facts['fixed-nr64']); nr64_as_default['config_NR_CPUS'] = '4096'
    ctl('nr64_objects_claimed_as_4096', 'fixed-default', nr64_as_default, lines('fixed-nr64', 'setup_arch'),
        lines('fixed-nr64', 'record_one_cpu'), 'O1', 'insufficient')
    ctl('parent_objects_claimed_fixed', 'fixed-default', facts['parent-default'], lines('parent-default', 'setup_arch'),
        lines('parent-default', 'record_one_cpu'), 'O4', 'insufficient')
    bad_i = copy.deepcopy(fd); bad_i['setup_64.i:alloc_irqstack_bootmem'] = fd['setup_64.i:alloc_irqstack_bootmem'].replace('(nr_cpu_ids)', '(((unsigned int)4096))')
    ctl('preprocessed_bound_replaced_by_constant', 'fixed-default', bad_i, base_setup, base_rec, 'O3', 'insufficient')
    summary = {'decisions': results, 'controls': controls,
               'controls_as_expected': sum(c['as_expected'] for c in controls),
               'object_checks': 16, 'tier': 'actual sparc64 compiler objects and preprocessed units; no link/boot/runtime'}
    (HERE / 'object_results.json').write_text(json.dumps(summary, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    for v, d in results.items():
        print(v, {k: x[0] for k, x in d.items()})
    print('controls', summary['controls_as_expected'], '/', len(controls))
    for c in controls:
        if not c['as_expected']:
            print('UNEXPECTED', c)


if __name__ == '__main__':
    main()
