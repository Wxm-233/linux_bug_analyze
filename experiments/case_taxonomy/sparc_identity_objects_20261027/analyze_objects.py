"""Per-symbol relocation facts from the four sparc64 objects, plus preprocessed excerpts (run in WSL)."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

HERE = Path(__file__).resolve().parent
OBJ = HERE / 'attempt1'
VARIANTS = ['parent-default', 'parent-nr64', 'fixed-default', 'fixed-nr64']
OBJDUMP = 'sparc64-linux-gnu-objdump'
NM = 'sparc64-linux-gnu-nm'
INTEREST = {'nr_cpu_ids', '__cpu_possible_mask', '__cpu_present_mask', '__bitmap_weight', '_find_next_bit',
            '_find_next_and_bit', 'find_next_bit', 'hardirq_stack', 'softirq_stack', 'memblock_alloc_try_nid',
            '__sw_hweight64', '__arch_hweight64', '__popcountdi2'}


def run(argv):
    return subprocess.run(argv, capture_output=True, text=True, check=True).stdout


def functions(obj):
    """Split objdump -dr output into {symbol: [lines]}."""
    out, current = {}, None
    for line in run([OBJDUMP, '-dr', '--no-show-raw-insn', str(obj)]).splitlines():
        m = re.match(r'^[0-9a-f]+ <([^>]+)>:$', line)
        if m:
            current = m.group(1)
            out[current] = []
        elif current and line.strip():
            out[current].append(line.rstrip())
    return out


def relocs(lines):
    syms = []
    for line in lines:
        m = re.search(r'R_SPARC_\w+\s+([A-Za-z_.$][\w.$]*)', line)
        if m:
            syms.append(m.group(1))
    return syms


def excerpt_i(path, header_re, limit=40):
    text = path.read_text(encoding='utf-8', errors='replace').splitlines()
    for i, line in enumerate(text):
        if re.search(header_re, line):
            body = []
            for j in range(i, min(i + 400, len(text))):
                if text[j].startswith('#'):
                    continue
                body.append(text[j])
                if text[j].startswith('}'):
                    break
            joined = '\n'.join(body)
            return joined[:6000]
    return None


def main():
    out = HERE / 'analysis'
    out.mkdir(exist_ok=False)
    rows = {}
    for variant in VARIANTS:
        d = OBJ / variant
        row = {'config_NR_CPUS': re.search(r'^CONFIG_NR_CPUS=(\d+)$', (d / 'config').read_text(), re.M).group(1)}
        for obj in ['prom_64.o', 'setup_64.o', 'smp_64.o']:
            path = d / obj
            row[obj + '.sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
            funcs = functions(path)
            symbols = run([NM, str(path)])
            row[obj + '.defined_functions'] = sorted(funcs)
            row[obj + '.alloc_irqstack_bootmem_symbol'] = ' alloc_irqstack_bootmem' in symbols
            for name in ['record_one_cpu', 'setup_arch', 'alloc_irqstack_bootmem', 'smp_fill_in_cpu_possible_map',
                         'setup_per_cpu_areas']:
                if name in funcs:
                    rel = relocs(funcs[name])
                    row[f'{obj}:{name}'] = {
                        'instructions': len(funcs[name]),
                        'relocation_symbols': sorted(set(rel)),
                        'interesting_counts': {s: rel.count(s) for s in sorted(INTEREST) if s in rel}}
                    (out / f'{variant}.{name}.dis.txt').write_text('\n'.join(funcs[name]) + '\n', encoding='utf-8')
        row['setup_64.i:alloc_irqstack_bootmem'] = excerpt_i(d / 'setup_64.i', r'void __attribute__.*alloc_irqstack_bootmem\(void\)|alloc_irqstack_bootmem\(void\)$')
        row['prom_64.i:record_one_cpu'] = excerpt_i(d / 'prom_64.i', r'\*record_one_cpu\(struct device_node')
        rows[variant] = row
    (out / 'object_facts.json').write_text(json.dumps(rows, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    for variant, row in rows.items():
        print(variant, 'NR_CPUS', row['config_NR_CPUS'])
        for key, value in row.items():
            if isinstance(value, dict):
                print('  ', key, value['instructions'], value['interesting_counts'])
        print('   alloc_irqstack symbol:', row['setup_64.o.alloc_irqstack_bootmem_symbol'])


if __name__ == '__main__':
    main()
