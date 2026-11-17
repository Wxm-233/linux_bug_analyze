"""State-size inventory (criteria.md, sections 2-5): the researcher's manual labels for candidates.json, the grouping,
the development / held-out split, the end-version consumption sites, and the verdict. Labels were written after
reading each commit; reasons are kept next to them. Output: inventory.json.
"""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent

M = {  # commit: (group, arch, function, size source before -> after, state named in the message)
    '935d4f0c6dc8': ('A', 'common', 'set_huge_pte_at', 'interface had no size -> sz parameter', 'swap entries without PFN (PTE markers)'),
    '6f1bace9a9fb': ('A', 'arm64', 'set_huge_pte_at', 'folio of the pte -> sz', 'PTE_MARKER_POISONED / UFFD_WP markers'),
    '1de195dd0e05': ('A', 'riscv', 'set_huge_pte_at', 'pte content (NAPOT order) -> sz', 'swap entry'),
    '02410ac72ac3': ('B', 'common', 'huge_ptep_get_and_clear', 'interface had no size -> sz parameter', 'non-present pte'),
    '49c87f767774': ('B', 'arm64', 'huge_ptep_get_and_clear', 'pte_cont() gate + table walk -> sz, gate removed', 'non-present pte'),
    '83d78ac677b9': ('B', 'riscv', 'huge_ptep_get_and_clear, huge_pte_clear', 'NAPOT order -> sz; pte_napot() gate kept', 'non-present pte'),
    '20156ce2365d': ('C', 'arm64', 'find_num_contig (set_huge_pte_at)', 'present-ness of the PMD slot -> slot position', 'empty (not yet populated) PMD slot'),
}
GROUPS = {
    'A': {'split': 'development', 'why': 'contains 1de195dd (used in the hugetlb rounds); 6f1bace9 and 1de195dd follow 935d4f0c'},
    'B': {'split': 'development', 'why': 'contains 83d78ac6 and 49c87f76 (used in the steps round); 83d78ac6 says the arm64 fix applies to riscv'},
    'C': {'split': 'held-out', 'why': 'arm64 2016, no reference to A or B, not used before'},
}
R = {
    'd3ea79527757': 'arm64 adds WARN_ON(!pte_present) in set_huge_pte_at: states the assumption, fixes no defect (history of group A)',
    'f02ab08afbe7': 'state related, not size: huge_pte_offset did not return poisoned entries',
    'ac8372f3b4e4': 's390 marks an empty converted pte as large; state encoding, size comes from the table level',
    '7cd1f5f77925': 'LoongArch encoding of a cleared huge pte; state, not size',
    'bd51834d1cf6': 'LoongArch invalid PMD read as a swap entry; state, not size',
    '469ed9d823b7': 'arm64 assumed all hugetlb ptes young; state, not size',
    'f73a8edc2ccc': 'arm64 size discovery wrong for unaligned addresses; size, not state',
    'b7d9d2e3a8ab': 'arm64 TLB level hint lacked the entry size; size, not state',
    'eed6bfa8b282': 'arm64 flush level for contiguous sizes; size, not state',
    '6fd44a481b3c': 'sparc64 sun4u TTEs lacked the size bits; size encoding, not state',
    '7ea981070fd9': 'powerpc 8xx passed a size index instead of a size to set_huge_pte_at',
    '1458eb2c9d88': 'riscv NAPOT update without break-before-make',
    '835e5ac3f98e': 'riscv wrprotect did not handle the whole NAPOT group',
    '6966d7988c4f': 'riscv lacked huge_ptep_get gathering A/D bits over the group',
    'a179a4bfb694': 'riscv hugetlb_mask_last_page did not know NAPOT sizes',
    'ce68c035457b': 'riscv migration support check did not know NAPOT sizes',
    '410982303772': 'arm64 break-before-make lost its TLB invalidation',
    '031e6e6b4e12': 'arm64 access flags cleared the range unnecessarily',
    '69d012345a1a': 'arm64 access flags return value over the contiguous group',
    '00de2c9f26b1': 'arm64 page_table_check accounting in clear_flush',
    '59f1183dd368': 'sparc64 size check compared a size with a shift',
    'f2b67ef90b0d': 'powerpc 8xx hugepage table size',
    '7c8d42fdf1a8': 's390 alignment check for 2 GB pages',
    'b6c41cb050d5': 'sparc64 alignment check for 64K pages',
    '544f8f935863': 'sparc64 page-table free range not aligned',
    '2198d4934ee8': 'powerpc free range lost its mask',
    '2e5809a4ddb1': 'arm64 CMA order for gigantic pages',
    '1fdbed657a47': 'x86 pud_huge with 2-level paging; level, not entry state',
}
SITES = [  # end version, size-encoding architectures; class per criteria section 4
    ('arm64', 'huge_ptep_get', 'pte_cont() after pte_present() check', 'G-local', 'hugetlbpage.c:125'),
    ('arm64', 'set_huge_pte_at', 'count from sz', 'G-other', 'hugetlbpage.c:222'),
    ('arm64', 'huge_pte_clear', 'count from sz', 'G-other', 'hugetlbpage.c:375'),
    ('arm64', 'huge_ptep_get_and_clear', 'count from sz, no content gate', 'G-other', 'hugetlbpage.c:387'),
    ('arm64', 'huge_ptep_clear_flush', 'count from hstate', 'G-other', 'hugetlbpage.c:483'),
    ('arm64', 'huge_ptep_set_access_flags', 'pte_cont(new pte) gate', 'G-caller',
     'callers mm/hugetlb.c:4852 (entry from huge_ptep_get of a present pte), :6200 (non-present orig_pte returns at :6075)'),
    ('arm64', 'huge_ptep_set_wrprotect', 'pte_cont(*ptep) gate', 'G-caller', 'caller mm/hugetlb.c:5058, present branch of copy_hugetlb_page_range'),
    ('riscv', 'huge_ptep_get', 'NAPOT order after pte_present() check', 'G-local', 'hugetlbpage.c:12'),
    ('riscv', 'set_huge_pte_at', 'non-present handled first with sz; NAPOT gate only for present', 'G-local', 'hugetlbpage.c:255-266'),
    ('riscv', 'huge_ptep_set_access_flags', 'NAPOT gate and order from new pte', 'G-caller', 'callers as arm64'),
    ('riscv', 'huge_ptep_set_wrprotect', 'NAPOT gate and order from *ptep', 'G-caller', 'caller as arm64'),
    ('riscv', 'huge_ptep_clear_flush', 'NAPOT gate and order from *ptep', 'G-caller',
     'callers mm/hugetlb.c:5641 (pte_same with a present pte), mm/rmap.c:2057, :2624 (page_vma_mapped_walk without PVMW_MIGRATION)'),
    ('riscv', 'huge_ptep_get_and_clear', 'pte_napot(*ptep) gate, count from sz', 'SUSPECT',
     'caller mm/hugetlb.c:5101 move_huge_pte takes any pte, including migration entries and markers'),
    ('riscv', 'huge_pte_clear', 'pte_napot(*ptep) gate, count from sz', 'SUSPECT',
     'callers mm/hugetlb.c:5264 (non-present branch of __unmap_hugepage_range), :5104, :6603 (markers)'),
    ('sparc', '__set_huge_pte_at', 'size from TTE size bits, sz ignored', 'U',
     'a PTE marker (UFFDIO_POISON) gives an 8K size and WARN_ONCE; write and clear both use one entry, harm unclear'),
    ('sparc', 'huge_ptep_get_and_clear', 'size from TTE size bits, sz ignored', 'U', 'same as above'),
    ('powerpc-8xx', '__pte_update cell count', '_PAGE_HUGE of the new value decides 512K vs 16K (4K pages)', 'U',
     'needs deeper reading; outside the RISC-V focus'),
]
NOT_APPLICABLE = {
    's390': 'size from the region/segment table type', 'x86': 'size from the table level', 'loongarch': 'size from the table level',
    'mips': 'size from the table level', 'parisc': 'fixed size', 'powerpc-book3s': 'size from the table level',
}
POST_HOC = [  # wider message search after the labels; not used in the verdict
    ('30f3ac00ad2f', 'arm64 2017: handle swap entries in huge_pte_offset for contiguous hugepages'),
    ('9386fac34c7c', 'common 2017: let architectures override huge_pte_clear (contiguous hugepages)'),
    ('7868a2087ec1', 'common 2017: size parameter for huge_pte_offset'),
]


def main():
    target = HERE / 'inventory.json'
    if target.exists():
        raise SystemExit('preserve')
    cands = json.loads((HERE / 'candidates.json').read_text(encoding='utf-8'))['rows']
    ids = {r['commit'] for r in cands}
    assert set(M) <= ids and set(R) <= ids, 'label for a commit outside the candidates'
    rows = []
    for r in cands:
        c = r['commit']
        if c in M:
            g, arch, fn, src, state = M[c]
            rows.append({**r, 'label': 'M', 'group': g, 'arch': arch, 'function': fn, 'size_source': src, 'state': state})
        else:
            rows.append({**r, 'label': 'R' if c in R else 'N', 'reason': R.get(c, '')})
    held = sorted(g for g, v in GROUPS.items() if v['split'] == 'held-out')
    controls = sum(1 for s in SITES if s[3].startswith('G-'))
    verdict = ('quantitative' if len(held) >= 4 and controls >= 5 else
               'switch mechanism' if len(held) <= 1 else 'descriptive')
    summary = {'candidates': len(rows), 'M': sum(r['label'] == 'M' for r in rows), 'R': sum(r['label'] == 'R' for r in rows),
               'N': sum(r['label'] == 'N' for r in rows), 'groups': len(GROUPS), 'held_out_groups': held,
               'controls_G': controls, 'unknown': sum(s[3] == 'U' for s in SITES),
               'suspect_sites': [f'{s[0]}:{s[1]}' for s in SITES if s[3] == 'SUSPECT'], 'verdict': verdict,
               'post_hoc_possible_instances': len(POST_HOC)}
    out = {'summary': summary, 'groups': GROUPS, 'rows': rows,
           'sites': [dict(zip(('arch', 'function', 'content_use', 'class', 'evidence'), s)) for s in SITES],
           'not_applicable': NOT_APPLICABLE, 'post_hoc': [{'commit': c, 'note': n} for c, n in POST_HOC]}
    target.write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
