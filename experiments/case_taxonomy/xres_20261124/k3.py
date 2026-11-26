import gzip, json
for b in ("riscv", "arm64", "x86_64"):
    S = json.load(gzip.open(f"/root/work/xres/sites_{b}.json.gz", "rt"))
    for s in S:
        if s["F"] == "insert_page_into_pte_locked" and s["G"] in ("pte_pfn",):
            print(b, s["line"], s["G_kind"], json.dumps(s["resources"], ensure_ascii=False))
    for s in S:
        if s["G"] == "PAGE_NONE" and s["F"] == "remove_migration_pte":
            print(b, "D4", s["line"], s["G_file"], s["G_kind"]); break
