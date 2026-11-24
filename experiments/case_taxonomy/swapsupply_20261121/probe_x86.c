/* user-space copy of x86_64 swap macros at df2908090cda (arch/x86/include/asm/pgtable_64.h:211-237), public swapops.h:28-29,85-120, leafops.h:55-65 */
#include <stdio.h>
#define BITS_PER_LONG 64
#define BITS_PER_XA_VALUE (BITS_PER_LONG - 1)
#define MAX_SWAPFILES_SHIFT 5
#define SWP_TYPE_SHIFT (BITS_PER_XA_VALUE - MAX_SWAPFILES_SHIFT)
#define SWP_OFFSET_MASK ((1UL << SWP_TYPE_SHIFT) - 1)
#define _PAGE_BIT_PROTNONE 8
#define SWP_TYPE_BITS 5
#define SWP_OFFSET_FIRST_BIT (_PAGE_BIT_PROTNONE + 1)
#define SWP_OFFSET_SHIFT (SWP_OFFSET_FIRST_BIT+SWP_TYPE_BITS)
typedef struct { unsigned long val; } swp_entry_t;
#define __swp_type(x) ((x).val >> (64 - SWP_TYPE_BITS))
#define __swp_offset(x) (~(x).val << SWP_TYPE_BITS >> SWP_OFFSET_SHIFT)
#define __swp_entry(type, offset) ((swp_entry_t) { (~(unsigned long)(offset) << SWP_OFFSET_SHIFT >> SWP_TYPE_BITS) | ((unsigned long)(type) << (64-SWP_TYPE_BITS)) })
static swp_entry_t swp_entry(unsigned long type, unsigned long offset) { swp_entry_t r; r.val = (type << SWP_TYPE_SHIFT) | (offset & SWP_OFFSET_MASK); return r; }
static unsigned swp_type(swp_entry_t e) { return e.val >> SWP_TYPE_SHIFT; }
static unsigned long swp_offset(swp_entry_t e) { return e.val & SWP_OFFSET_MASK; }
static unsigned long to_pte(swp_entry_t e) { return __swp_entry(swp_type(e), swp_offset(e)).val; }
/* pte_present: P(0)|PROTNONE(8); pte_none: !(pte & ~(_PAGE_DIRTY|_PAGE_ACCESSED)) -- KNL erratum mask, bits 6,5 */
static int present(unsigned long p) { return (p & ((1UL<<0)|(1UL<<8))) != 0; }
static int none(unsigned long p) { return !(p & ~((1UL<<6)|(1UL<<5))); }
static swp_entry_t from_pte(unsigned long p) { swp_entry_t a = {p}; if (present(p) || none(p)) return (swp_entry_t){0}; /* flags clear omitted: SD/F/E bits are 0 here */ return swp_entry(__swp_type(a), __swp_offset(a)); }
int main(void) {
  unsigned long p0 = to_pte(swp_entry(0, ~0UL));
  printf("pte(swp_entry(0,~0)) = %#lx none=%d\n", p0, none(p0));
  unsigned long dbg = swp_offset(from_pte(p0));             /* debug_vm_pgtable.c:1229 */
  swp_entry_t a = {p0}; unsigned long gen = swp_offset(swp_entry(__swp_type(a), __swp_offset(a))) + 1;   /* generic_max_swapfile_size */
  printf("debug_vm_pgtable max_swap_offset = %#lx ; generic_max_swapfile_size = %#lx\n", dbg, gen);
  return 0;
}
