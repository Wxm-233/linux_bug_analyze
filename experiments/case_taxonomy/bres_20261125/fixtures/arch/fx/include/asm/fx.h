#ifndef FX_ARCH_H
#define FX_ARCH_H
#define FX_ARCH_SHIFT 12
int fx_arch_get(int v);
int fx_pte_present(int pte);
unsigned long fx_pte_pfn(int pte);
#endif
