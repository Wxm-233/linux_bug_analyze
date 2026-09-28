// SPDX-License-Identifier: GPL-2.0
/* Included in iommu.c: exercise the helper used by __domain_mapping(). */
#include <kunit/test.h>

static void expect_permissions(struct kunit *test, bool first, int prot, u64 expected)
{
	u64 attr = intel_iommu_encode_pte_attr(first, prot);

	KUNIT_EXPECT_EQ(test, attr & (DMA_PTE_READ | DMA_PTE_WRITE), expected);
}

static void first_level_read_only(struct kunit *test)
{
	expect_permissions(test, true, DMA_PTE_READ, DMA_PTE_READ);
}

static void first_level_read_write(struct kunit *test)
{
	expect_permissions(test, true, DMA_PTE_READ | DMA_PTE_WRITE,
			   DMA_PTE_READ | DMA_PTE_WRITE);
}

static void first_level_wo_not_representable(struct kunit *test)
{
	/* Characterize existing behavior, not a claim that WO is supported. */
	expect_permissions(test, true, DMA_PTE_WRITE, DMA_PTE_READ | DMA_PTE_WRITE);
}

static void second_level_read_only(struct kunit *test)
{
	expect_permissions(test, false, DMA_PTE_READ, DMA_PTE_READ);
}

static void second_level_write_only(struct kunit *test)
{
	expect_permissions(test, false, DMA_PTE_WRITE, DMA_PTE_WRITE);
}

static void second_level_read_write(struct kunit *test)
{
	expect_permissions(test, false, DMA_PTE_READ | DMA_PTE_WRITE,
			   DMA_PTE_READ | DMA_PTE_WRITE);
}

static void contract_free_domain(void *ptr)
{
	domain_exit(ptr);
}

static void contract_free_data(void *ptr)
{
	free_pages((unsigned long)ptr, 1);
}

/* Detached domain: real page tables and ops, explicitly supplied capabilities.
 * No device probing, hardware page walker, or IOTLB target is exercised.
 */
static void expect_installed(struct kunit *test, bool first, int prot,
			     u64 expected, bool cross_boundary)
{
	struct dmar_domain *d = kzalloc(sizeof(*d), GFP_KERNEL);
	unsigned long iova = cross_boundary ? SZ_2M - PAGE_SIZE : PAGE_SIZE;
	size_t size = cross_boundary ? 2 * PAGE_SIZE : PAGE_SIZE;
	struct dma_pte *pte;
	void *data;
	phys_addr_t pa;
	int large = 0, ret;
	size_t off;

	KUNIT_ASSERT_NOT_NULL(test, d);
	INIT_LIST_HEAD(&d->devices);
	INIT_LIST_HEAD(&d->dev_pasids);
	INIT_LIST_HEAD(&d->cache_tags);
	spin_lock_init(&d->lock);
	spin_lock_init(&d->cache_lock);
	xa_init(&d->iommu_array);
	d->nid = NUMA_NO_NODE;
	d->gaw = 48;
	d->agaw = width_to_agaw(48);
	d->use_first_level = first;
	d->iommu_coherency = true;
	d->domain.type = IOMMU_DOMAIN_UNMANAGED;
	d->domain.ops = intel_iommu_ops.default_domain_ops;
	d->domain.pgsize_bitmap = SZ_4K;
	KUNIT_ASSERT_EQ(test, kunit_add_action_or_reset(test, contract_free_domain, d), 0);
	d->pgd = iommu_alloc_page_node(d->nid, GFP_KERNEL);
	KUNIT_ASSERT_NOT_NULL(test, d->pgd);
	data = (void *)__get_free_pages(GFP_KERNEL | __GFP_ZERO, 1);
	KUNIT_ASSERT_NOT_NULL(test, data);
	KUNIT_ASSERT_EQ(test, kunit_add_action_or_reset(test, contract_free_data, data), 0);
	pa = virt_to_phys(data);
	ret = iommu_map(&d->domain, iova, pa, size, prot, GFP_KERNEL);
	if (!prot) {
		KUNIT_EXPECT_EQ(test, ret, -EINVAL);
		KUNIT_EXPECT_FALSE(test, d->has_mappings);
		KUNIT_EXPECT_EQ(test, iommu_iova_to_phys(&d->domain, iova), (phys_addr_t)0);
		return;
	}
	KUNIT_ASSERT_EQ(test, ret, 0);
	for (off = 0; off < size; off += PAGE_SIZE) {
		pte = dma_pfn_level_pte(d, (iova + off) >> VTD_PAGE_SHIFT, 1, &large);
		KUNIT_ASSERT_NOT_NULL(test, pte);
		KUNIT_EXPECT_EQ(test, pte->val & (DMA_PTE_READ | DMA_PTE_WRITE), expected);
		KUNIT_EXPECT_EQ(test, (phys_addr_t)dma_pte_addr(pte), pa + off);
		KUNIT_EXPECT_EQ(test, iommu_iova_to_phys(&d->domain, iova + off + 37), pa + off + 37);
	}
	KUNIT_EXPECT_EQ(test, iommu_unmap(&d->domain, iova, size), size);
	for (off = 0; off < size; off += PAGE_SIZE) {
		pte = dma_pfn_level_pte(d, (iova + off) >> VTD_PAGE_SHIFT, 1, &large);
		KUNIT_EXPECT_TRUE(test, !pte || !dma_pte_present(pte));
		KUNIT_EXPECT_EQ(test, iommu_iova_to_phys(&d->domain, iova + off), (phys_addr_t)0);
	}
}

#define INSTALLED_CASE(name, first, prot, expected, cross) \
	static void name(struct kunit *test) \
	{ expect_installed(test, first, prot, expected, cross); }

INSTALLED_CASE(map_first_ro, true, IOMMU_READ, DMA_PTE_READ, false)
INSTALLED_CASE(map_first_rw, true, IOMMU_READ | IOMMU_WRITE, DMA_PTE_READ | DMA_PTE_WRITE, false)
INSTALLED_CASE(map_first_wo_characterization, true, IOMMU_WRITE, DMA_PTE_READ | DMA_PTE_WRITE, false)
INSTALLED_CASE(map_second_ro, false, IOMMU_READ, DMA_PTE_READ, false)
INSTALLED_CASE(map_second_rw, false, IOMMU_READ | IOMMU_WRITE, DMA_PTE_READ | DMA_PTE_WRITE, false)
INSTALLED_CASE(map_second_wo, false, IOMMU_WRITE, DMA_PTE_WRITE, false)
INSTALLED_CASE(map_second_wo_cross_boundary, false, IOMMU_WRITE, DMA_PTE_WRITE, true)
INSTALLED_CASE(map_second_no_permissions, false, 0, 0, false)

static struct kunit_case intel_iommu_pte_contract_cases[] = {
	KUNIT_CASE(map_first_ro),
	KUNIT_CASE(map_first_rw),
	KUNIT_CASE(map_first_wo_characterization),
	KUNIT_CASE(map_second_ro),
	KUNIT_CASE(map_second_rw),
	KUNIT_CASE(map_second_wo),
	KUNIT_CASE(map_second_wo_cross_boundary),
	KUNIT_CASE(map_second_no_permissions),
	KUNIT_CASE(first_level_read_only),
	KUNIT_CASE(first_level_read_write),
	KUNIT_CASE(first_level_wo_not_representable),
	KUNIT_CASE(second_level_read_only),
	KUNIT_CASE(second_level_write_only),
	KUNIT_CASE(second_level_read_write),
	{}
};

static struct kunit_suite intel_iommu_pte_contract_suite = {
	.name = "intel-iommu-pte-contract",
	.test_cases = intel_iommu_pte_contract_cases,
};

kunit_test_suite(intel_iommu_pte_contract_suite);
