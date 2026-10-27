#include <linux/pagemap.h>
#include <linux/huge_mm.h>
extern int printf(const char *, ...);
int main(void) {
printf("PAGE_SHIFT=%lu\n", (unsigned long)(PAGE_SHIFT));
printf("PMD_SHIFT=%lu\n", (unsigned long)(PMD_SHIFT));
printf("HPAGE_PMD_SHIFT=%lu\n", (unsigned long)(HPAGE_PMD_SHIFT));
printf("HPAGE_PMD_ORDER=%lu\n", (unsigned long)(HPAGE_PMD_ORDER));
printf("XA_CHUNK_SHIFT=%lu\n", (unsigned long)(XA_CHUNK_SHIFT));
printf("MAX_XAS_ORDER=%lu\n", (unsigned long)(MAX_XAS_ORDER));
printf("MAX_PAGECACHE_ORDER=%lu\n", (unsigned long)(MAX_PAGECACHE_ORDER));
return 0;
}
