
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/stat.h>
typedef unsigned long pgoff_t;
typedef long long loff_t;
struct shmem_sb_info { int huge; };
struct super_block { struct shmem_sb_info info; };
struct inode { unsigned int i_mode; struct super_block *i_sb; long long size; };
struct mm_struct { unsigned long flags; };
#define SHMEM_SB(sb) (&(sb)->info)
#define SHMEM_HUGE_NEVER 0
#define SHMEM_HUGE_ALWAYS 1
#define SHMEM_HUGE_WITHIN_SIZE 2
#define SHMEM_HUGE_ADVISE 3
#define SHMEM_HUGE_DENY -1
#define SHMEM_HUGE_FORCE -2
#define VM_NOHUGEPAGE 1UL
#define VM_HUGEPAGE 2UL
#define MMF_DISABLE_THP 0
#define test_bit(n,p) (((*(p)) >> (n)) & 1UL)
#define i_size_read(inode) ((inode)->size)
#define round_up(x,y) ((((x) + (y) - 1) / (y)) * (y))
#define fallthrough __attribute__((fallthrough))
#define PAGE_SIZE (1UL << PAGE_SHIFT)
#define HPAGE_PMD_ORDER (HPAGE_PMD_SHIFT - PAGE_SHIFT)
#define HPAGE_PMD_NR (1UL << HPAGE_PMD_ORDER)
#define min(a,b) ((a) < (b) ? (a) : (b))
#define MAX_XAS_ORDER (XA_CHUNK_SHIFT * 2 - 1)
#define PREFERRED_MAX_PAGECACHE_ORDER HPAGE_PMD_ORDER
#define MAX_PAGECACHE_ORDER CERTIFIED_MAX_PAGECACHE_ORDER
static int shmem_huge = SHMEM_HUGE_NEVER;

bool old_shmem_is_huge(struct inode *inode, pgoff_t index, bool shmem_huge_force,
		   struct mm_struct *mm, unsigned long vm_flags)
{
	loff_t i_size;

	if (!S_ISREG(inode->i_mode))
		return false;
	if (mm && ((vm_flags & VM_NOHUGEPAGE) || test_bit(MMF_DISABLE_THP, &mm->flags)))
		return false;
	if (shmem_huge == SHMEM_HUGE_DENY)
		return false;
	if (shmem_huge_force || shmem_huge == SHMEM_HUGE_FORCE)
		return true;

	switch (SHMEM_SB(inode->i_sb)->huge) {
	case SHMEM_HUGE_ALWAYS:
		return true;
	case SHMEM_HUGE_WITHIN_SIZE:
		index = round_up(index + 1, HPAGE_PMD_NR);
		i_size = round_up(i_size_read(inode), PAGE_SIZE);
		if (i_size >> PAGE_SHIFT >= index)
			return true;
		fallthrough;
	case SHMEM_HUGE_ADVISE:
		if (mm && (vm_flags & VM_HUGEPAGE))
			return true;
		fallthrough;
	default:
		return false;
	}
}
static bool __shmem_is_huge(struct inode *inode, pgoff_t index,
			    bool shmem_huge_force, struct mm_struct *mm,
			    unsigned long vm_flags)
{
	loff_t i_size;

	if (!S_ISREG(inode->i_mode))
		return false;
	if (mm && ((vm_flags & VM_NOHUGEPAGE) || test_bit(MMF_DISABLE_THP, &mm->flags)))
		return false;
	if (shmem_huge == SHMEM_HUGE_DENY)
		return false;
	if (shmem_huge_force || shmem_huge == SHMEM_HUGE_FORCE)
		return true;

	switch (SHMEM_SB(inode->i_sb)->huge) {
	case SHMEM_HUGE_ALWAYS:
		return true;
	case SHMEM_HUGE_WITHIN_SIZE:
		index = round_up(index + 1, HPAGE_PMD_NR);
		i_size = round_up(i_size_read(inode), PAGE_SIZE);
		if (i_size >> PAGE_SHIFT >= index)
			return true;
		fallthrough;
	case SHMEM_HUGE_ADVISE:
		if (mm && (vm_flags & VM_HUGEPAGE))
			return true;
		fallthrough;
	default:
		return false;
	}
}
bool shmem_is_huge(struct inode *inode, pgoff_t index,
		   bool shmem_huge_force, struct mm_struct *mm,
		   unsigned long vm_flags)
{
	if (HPAGE_PMD_ORDER > MAX_PAGECACHE_ORDER)
		return false;

	return __shmem_is_huge(inode, index, shmem_huge_force, mm, vm_flags);
}

int main(void) {
    struct super_block sb = { .info = { .huge = SHMEM_HUGE_ALWAYS } };
    struct inode inode = { .i_mode = S_IFREG, .i_sb = &sb, .size = 1LL << 30 };
    struct mm_struct mm = { .flags = 0 };
    struct { const char *name; int policy; bool force; unsigned long flags; } cases[] = {
        {"always", SHMEM_HUGE_ALWAYS, false, 0},
        {"force_argument", SHMEM_HUGE_NEVER, true, 0},
        {"advise", SHMEM_HUGE_ADVISE, false, VM_HUGEPAGE},
        {"never", SHMEM_HUGE_NEVER, false, 0},
        {"nohugepage", SHMEM_HUGE_ALWAYS, false, VM_NOHUGEPAGE},
    };
    for (unsigned int i=0; i<sizeof(cases)/sizeof(cases[0]); i++) {
        sb.info.huge = cases[i].policy;
        printf("%s %d %d\n", cases[i].name,
            old_shmem_is_huge(&inode, 0, cases[i].force, &mm, cases[i].flags),
            shmem_is_huge(&inode, 0, cases[i].force, &mm, cases[i].flags));
    }
    return 0;
}
