#include <linux/pagemap.h>
#include <linux/huge_mm.h>
#include <linux/mmzone.h>
extern int printf(const char *, ...);
#define VALUE(name, expression) printf("\"" name "\":%lu,", (unsigned long)(expression))
int main(void)
{
	printf("{");
	VALUE("PAGE_SHIFT", PAGE_SHIFT);
	VALUE("PMD_SHIFT", PMD_SHIFT);
	VALUE("HPAGE_PMD_ORDER", HPAGE_PMD_ORDER);
	VALUE("MAX_PAGE_ORDER", MAX_PAGE_ORDER);
	VALUE("XA_CHUNK_SHIFT", XA_CHUNK_SHIFT);
	VALUE("MAX_PAGECACHE_ORDER", MAX_PAGECACHE_ORDER);
	VALUE("FOLIO_FLAGS_OFFSET", __builtin_offsetof(struct folio, flags));
	VALUE("FOLIO_FLAGS1_OFFSET", __builtin_offsetof(struct folio, _flags_1));
	VALUE("FOLIO_MAPPING_OFFSET", __builtin_offsetof(struct folio, mapping));
	VALUE("FOLIO_INDEX_OFFSET", __builtin_offsetof(struct folio, index));
	VALUE("FOLIO_HEAD_MASK", 1UL << PG_head);
	VALUE("XAS_SHIFT_OFFSET", __builtin_offsetof(struct xa_state, xa_shift));
	VALUE("XAS_NODE_OFFSET", __builtin_offsetof(struct xa_state, xa_node));
	VALUE("XA_NOMEM_ENCODING", (unsigned long)XA_ERROR(-ENOMEM));
	printf("\"ULONG_BYTES\":%lu}\n", (unsigned long)sizeof(unsigned long));
	return 0;
}
