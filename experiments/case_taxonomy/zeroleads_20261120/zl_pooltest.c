// SPDX-License-Identifier: GPL-2.0
/*
 * zeroleads_20261120: boot-time check that dma_alloc_coherent() returns zeroed memory
 * on arm32 for a non-coherent device, atomic (pool) path vs. blocking path.
 * Built in (late_initcall) into a throw-away source copy; never part of the repository tree.
 */
#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/platform_device.h>
#include <linux/dma-mapping.h>
#include <linux/dma-map-ops.h>
#include <linux/string.h>

#define SZ 4096
#define ROUNDS 8

static size_t nonzero(const u8 *p, size_t n)
{
	size_t i, c = 0;

	for (i = 0; i < n; i++)
		c += p[i] != 0;
	return c;
}

static void run(struct device *dev, gfp_t gfp, const char *tag)
{
	void *prev = NULL;
	int r;

	for (r = 0; r < ROUNDS; r++) {
		dma_addr_t h;
		u8 *p = dma_alloc_coherent(dev, SZ, &h, gfp);

		if (!p) {
			pr_info("ZLTEST %s round %d: allocation failed\n", tag, r);
			return;
		}
		pr_info("ZLTEST %s round %d: nonzero=%zu same_addr=%d first=%02x\n",
			tag, r, nonzero(p, SZ), p == prev, p[0]);
		memset(p, 0xA5, SZ);
		prev = p;
		dma_free_coherent(dev, SZ, p, h);
	}
}

static int __init zl_pooltest_init(void)
{
	struct platform_device *pdev;
	struct device *dev;

	pdev = platform_device_register_simple("zl_pooltest", -1, NULL, 0);
	if (IS_ERR(pdev)) {
		pr_info("ZLTEST: platform device failed\n");
		return 0;
	}
	dev = &pdev->dev;
	if (dma_coerce_mask_and_coherent(dev, DMA_BIT_MASK(32))) {
		pr_info("ZLTEST: dma mask failed\n");
		return 0;
	}
	pr_info("ZLTEST start: coherent=%d\n", dev_is_dma_coherent(dev));
	run(dev, GFP_ATOMIC, "atomic");
	run(dev, GFP_KERNEL, "kernel");
	pr_info("ZLTEST done\n");
	return 0;
}
late_initcall(zl_pooltest_init);
