"""swapcmp: why the native pmd_softleaf_tests fails on loongarch (clang-folded; not part of the frozen checker). WSL."""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "swapsym_20261121"))
import swaparch as A
S = A.S
A.register("loongarch")
src = r'''
#include <linux/mm.h>
#include <linux/pgtable.h>
#include <linux/swapops.h>
#include <linux/leafops.h>
static inline pmd_t m_of(unsigned long pfn) { return softleaf_to_pmd(make_writable_migration_entry(pfn)); }
unsigned long long L_native_val(void) { return pmd_val(m_of(~0UL)); }
unsigned long L_native_present(void) { return !!pmd_present(m_of(~0UL)); }
unsigned long L_native_valid(void) { return pmd_is_valid_softleaf(m_of(~0UL)); }
unsigned long L_pfnbits(void) { return SWP_PFN_BITS; }
unsigned long long L_legalmax_val(void) { return pmd_val(m_of((1UL << SWP_PFN_BITS) - 1)); }
unsigned long L_legalmax_present(void) { return !!pmd_present(m_of((1UL << SWP_PFN_BITS) - 1)); }
unsigned long L_legalmax_ad_present(void) { return !!pmd_present(softleaf_to_pmd(make_migration_entry_dirty(make_migration_entry_young(make_writable_migration_entry((1UL << SWP_PFN_BITS) - 1))))); }
unsigned long L_first_bad_pfn_bit(void) { for (int i = 0; i < 58; i++) if (pmd_present(m_of(1UL << i))) return i; return 99; }
'''
names = ["L_native_val", "L_native_present", "L_native_valid", "L_pfnbits", "L_legalmax_val", "L_legalmax_present", "L_legalmax_ad_present", "L_first_bad_pfn_bit"]
got = S.clang_consts("loongarch", src, names)
out = {n: (hex(v) if v is not None and n.endswith("_val") else v) for n, v in got.items()}
(HERE / "loong_probe.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
