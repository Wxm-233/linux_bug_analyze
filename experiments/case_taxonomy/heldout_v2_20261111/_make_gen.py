"""One-off: build gen_holdout2.py from fieldhint2_dev_20261111/gen_field2.py (only paths and the G3f branch change)."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
s = (HERE.parent / "fieldhint2_dev_20261111" / "gen_field2.py").read_text(encoding="utf8")
head, body = s[:s.index("def main():")], s[s.index("def main():"):]
core = body[body.index('        lay = json.loads((xg / f"layouts_{g}.json").read_text())'):body.index('    (HERE / "field_stats.json")')]
R = [
    ('        fv = json.loads((HERE / "static" / f"fieldvocab_{g}.json").read_text())["vocab"]\n', ''),
    ('''        for G, rule, fvp, tag in (("G3f", 1, HERE.parent / "fieldhint_dev_20261111" / "static", "field"),
                                  ("G3g", 2, HERE / "static", "field2")):
            fv = json.loads((fvp / f"fieldvocab_{g}.json").read_text())["vocab"]''',
     '''        for G, rule, tag in (("G3g", 2, "field2"),):  # heldout_v2: only the frozen main method's variants
            fv = json.loads(Path(a.fieldvocab).read_text())["vocab"]'''),
    ('        out = HERE / "run" / g', '        out = ws / "run"'),
    ('        for kname, a in kernels(g).items():', '        slot = a.slot_name or "riscv"\n        for kname, arch in kernels(g).items():'),
    ('TR.translate_cases([c], table, [a])', 'TR.translate_cases([c], table, [arch])'),
    ('vs.append(t1[a][0])', 'vs.append(t1[arch][0])'),
    ('meta["NR_syscalls"])[a]', 'meta["NR_syscalls"])[arch]'),
    ('(xg / f"cases_{g}_{a}.txt")', '(xg / f"cases_{g}_{arch}.txt")'),
    ('(out / f"cases_{kname}.txt")', '(out / f"cases_{kname.replace(\'riscv\', slot)}.txt")'),
    ('        allstats[g] = allst\n', ''),
]
for a, b in R:
    assert core.count(a) == 1, a[:60]
    core = core.replace(a, b)
main = '''def main():
    import argparse
    ap = argparse.ArgumentParser()
    for x in ("ws", "group", "S", "fieldvocab"):
        ap.add_argument(x)
    ap.add_argument("--slot-name", default=None)
    a = ap.parse_args()
    g = a.group
    ws = Path(a.ws).resolve()
    xg, cg = ws / "diverse_dev_20261110" / "gen", ws / "merge_dev_20261111" / "gen"
    cg.mkdir(parents=True, exist_ok=True)
    generate_x.B = 2000
    generate_x.HERE = calib.HERE = generate_c.DG = xg
    generate_c.CT, generate_c.HERE = ws, cg
    generate_x.ML.BG.KERNELS[g] = list(kernels(g))
    generate_c.S[g] = [int(x, 16) for x in a.S.split(",") if x]
    probes = json.loads((ws / "rtprobe_dev_20261110" / "probes.json").read_text())
    consts, vn, _, _, _, bases = TR.load()
    fam, _ = TR.families(consts, vn, bases)
    table = TR.table_of(fam, json.loads((CT / "anyarch_dev_20261110/gen/confirmed.json").read_text())["confirmed"])
    sys.argv = ["generate_x.py", g]
    generate_x.main()
    sys.argv = ["generate_c.py", g]
    generate_c.main()
    if True:
''' + core + '''    (ws / "run" / "field_stats.json").write_text(json.dumps(allst, indent=1))


if __name__ == "__main__":
    main()
'''
head = head.replace('"""(fieldhint2_dev_20261111:', '"""(heldout_v2_20261111: built by _make_gen.py from fieldhint2_dev_20261111/gen_field2.py: only G3g, inputs\nfrom a workspace prepared like heldout_run_20261111/prep_ws.py; criteria 三.3.\n    python gen_holdout2.py <ws> <group> <S hex,...> <fieldvocab.json> [--slot-name loongarch])\n(fieldhint2_dev_20261111:', 1)
(HERE / "gen_holdout2.py").write_text(head + main, encoding="utf8", newline="\n")
print("written")
