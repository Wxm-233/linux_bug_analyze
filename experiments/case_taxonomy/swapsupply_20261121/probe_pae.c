/* user-space copy of i386 PAE swap macros (arch/x86/include/asm/pgtable-3level.h:164-202, df2908090cda); unsigned long is 32-bit there */
#include <stdio.h>
#include <stdint.h>
typedef uint32_t ul;
typedef uint64_t pteval_t;
#define BITS_PER_XA_VALUE 31
#define SWP_TYPE_SHIFT_PUB (BITS_PER_XA_VALUE - 5)
#define SWP_OFFSET_MASK (((ul)1 << SWP_TYPE_SHIFT_PUB) - 1)
#define SWP_TYPE_BITS 5
#define _SWP_TYPE_MASK ((1U << SWP_TYPE_BITS) - 1)
#define SWP_OFFSET_SHIFT (9 + SWP_TYPE_BITS)
typedef struct { ul val; } swp_entry_t;
#define __swp_type(x) (((x).val) & _SWP_TYPE_MASK)
#define __swp_offset(x) ((x).val >> SWP_TYPE_BITS)
#define __swp_entry(type, offset) ((swp_entry_t){((type) & _SWP_TYPE_MASK) | (offset) << SWP_TYPE_BITS})
#define __swp_pteval_entry(type, offset) ((pteval_t)((~(pteval_t)(offset) << SWP_OFFSET_SHIFT >> SWP_TYPE_BITS) | ((pteval_t)(type) << (64 - SWP_TYPE_BITS))))
int main(void) {
  ul off = (~(ul)0) & SWP_OFFSET_MASK;            /* swp_entry(0, ~0UL) */
  swp_entry_t a = __swp_entry(0, off);
  pteval_t p = __swp_pteval_entry(__swp_type(a), __swp_offset(a));
  printf("PAE pte(swp_entry(0,~0)) = %#llx (none if 0)\n", (unsigned long long)p);
  return 0;
}
