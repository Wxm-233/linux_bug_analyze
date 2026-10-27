
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <assert.h>
#define PAGE_SIZE (1UL<<PAGE_SHIFT)
#define PAGE_MASK (~(PAGE_SIZE-1))
#define PTRS_PER_PTE (PAGE_SIZE/8)
#define GENMASK_ULL(h,l) ((~0ULL<<(l))&(~0ULL>>(63-(h))))
#define round_down(x,y) ((x)&~((y)-1))
#define round_up(x,y) (((x)+(y)-1)&~((y)-1))
struct mm_struct {int unused;};struct vm_area_struct {struct mm_struct *vm_mm;};
static int cap,calls;static unsigned long got_start,got_end;
#define system_supports_tlb_range() (cap)
#define dsb(x) ((void)0)
#define ASID(mm) ((void)(mm),17UL)
#define __TLBI_VADDR(a,id) ((a)+(id))
#define __TLBI_VADDR_RANGE(a,id,s,n,t) ((a)+(id)+(s)+(n)+(t))
#define __tlbi(op,a) ((void)(a))
#define __tlbi_user(op,a) ((void)(a))
#define __tlbi_level(op,a,l) ((void)(a),(void)(l))
#define __tlbi_user_level(op,a,l) ((void)(a),(void)(l))
static void mmu_notifier_arch_invalidate_secondary_tlbs(struct mm_struct*m,unsigned long a,unsigned long b){(void)m;calls++;got_start=a;got_end=b;}
#define __TLBI_RANGE_PAGES(num, scale)	\
	((unsigned long)((num) + 1) << (5 * (scale) + 1))
#define MAX_TLBI_RANGE_PAGES		__TLBI_RANGE_PAGES(31, 3)
#define TLBI_RANGE_MASK			GENMASK_ULL(4, 0)
#define __TLBI_RANGE_NUM(pages, scale)	\
	((((pages) >> (5 * (scale) + 1)) & TLBI_RANGE_MASK) - 1)
#define MAX_TLBI_OPS	PTRS_PER_PTE
#define __flush_tlb_range_op(op, start, pages, stride,			\
				asid, tlb_level, tlbi_user)		\
do {									\
	int num = 0;							\
	int scale = 0;							\
	unsigned long addr;						\
									\
	while (pages > 0) {						\
		if (!system_supports_tlb_range() ||			\
		    pages % 2 == 1) {					\
			addr = __TLBI_VADDR(start, asid);		\
			__tlbi_level(op, addr, tlb_level);		\
			if (tlbi_user)					\
				__tlbi_user_level(op, addr, tlb_level);	\
			start += stride;				\
			pages -= stride >> PAGE_SHIFT;			\
			continue;					\
		}							\
									\
		num = __TLBI_RANGE_NUM(pages, scale);			\
		if (num >= 0) {						\
			addr = __TLBI_VADDR_RANGE(start, asid, scale,	\
						  num, tlb_level);	\
			__tlbi(r##op, addr);				\
			if (tlbi_user)					\
				__tlbi_user(r##op, addr);		\
			start += __TLBI_RANGE_PAGES(num, scale) << PAGE_SHIFT; \
			pages -= __TLBI_RANGE_PAGES(num, scale);	\
		}							\
		scale++;						\
	}								\
} while (0)
static inline void flush_tlb_mm(struct mm_struct *mm)
{
	unsigned long asid;

	dsb(ishst);
	asid = __TLBI_VADDR(0, ASID(mm));
	__tlbi(aside1is, asid);
	__tlbi_user(aside1is, asid);
	dsb(ish);
	mmu_notifier_arch_invalidate_secondary_tlbs(mm, 0, -1UL);
}
static inline void __flush_tlb_page_nosync(struct mm_struct *mm,
					   unsigned long uaddr)
{
	unsigned long addr;

	dsb(ishst);
	addr = __TLBI_VADDR(uaddr, ASID(mm));
	__tlbi(vale1is, addr);
	__tlbi_user(vale1is, addr);
	mmu_notifier_arch_invalidate_secondary_tlbs(mm, uaddr & PAGE_MASK,
						(uaddr & PAGE_MASK) + PAGE_SIZE);
}
static inline void __flush_tlb_range(struct vm_area_struct *vma,
				     unsigned long start, unsigned long end,
				     unsigned long stride, bool last_level,
				     int tlb_level)
{
	unsigned long asid, pages;

	start = round_down(start, stride);
	end = round_up(end, stride);
	pages = (end - start) >> PAGE_SHIFT;

	/*
	 * When not uses TLB range ops, we can handle up to
	 * (MAX_TLBI_OPS - 1) pages;
	 * When uses TLB range ops, we can handle up to
	 * (MAX_TLBI_RANGE_PAGES - 1) pages.
	 */
	if ((!system_supports_tlb_range() &&
	     (end - start) >= (MAX_TLBI_OPS * stride)) ||
	    pages >= MAX_TLBI_RANGE_PAGES) {
		flush_tlb_mm(vma->vm_mm);
		return;
	}

	dsb(ishst);
	asid = ASID(vma->vm_mm);

	if (last_level)
		__flush_tlb_range_op(vale1is, start, pages, stride, asid, tlb_level, true);
	else
		__flush_tlb_range_op(vae1is, start, pages, stride, asid, tlb_level, true);

	dsb(ish);
	mmu_notifier_arch_invalidate_secondary_tlbs(vma->vm_mm, start, end);
}
int main(int argc,char**argv){assert(argc==5);cap=atoi(argv[1]);unsigned long pages=strtoul(argv[2],0,0),kind=strtoul(argv[3],0,0);struct mm_struct m={0};struct vm_area_struct v={&m};unsigned long start=1UL<<30,end=start+pages*PAGE_SIZE;
if(kind)__flush_tlb_page_nosync(&m,start+7);else __flush_tlb_range(&v,start,end,strtoul(argv[4],0,0),false,0);
assert(calls==1);printf("%lu %lu %lu %lu\n",start,end,got_start,got_end);return 0;}
