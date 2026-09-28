// SPDX-License-Identifier: GPL-2.0
#include <kunit/test.h>
#include <linux/cpu.h>

static void fixture_installed(struct kunit *test)
{
	KUNIT_ASSERT_GE(test, lba_scenario, 0);
	KUNIT_EXPECT_TRUE(test, lba_injected);
	KUNIT_EXPECT_EQ(test, acpi_support_online_capable, lba_scenario == 0);
}

static void actual_cpu_masks(struct kunit *test)
{
	KUNIT_ASSERT_TRUE(test, lba_injected);
	kunit_info(test, "possible=%*pbl present=%*pbl online=%*pbl",
		cpumask_pr_args(cpu_possible_mask), cpumask_pr_args(cpu_present_mask),
		cpumask_pr_args(cpu_online_mask));
	KUNIT_EXPECT_EQ(test, num_possible_cpus(), lba_expected);
	KUNIT_EXPECT_EQ(test, num_present_cpus(), 1U);
	KUNIT_EXPECT_EQ(test, num_online_cpus(), 1U);
}

static void actual_apic_membership(struct kunit *test)
{
	u32 seen = 0;
	unsigned int cpu;
	u32 expected = lba_scenario == 0 ? 0xb : lba_scenario == 1 ? 1 : 0xf;
	KUNIT_ASSERT_TRUE(test, lba_injected);
	for_each_possible_cpu(cpu) {
		u32 id = cpuid_to_apicid[cpu];
		kunit_info(test, "cpu=%u apic=%u", cpu, id);
		KUNIT_ASSERT_LT(test, id, 4U);
		KUNIT_EXPECT_EQ(test, seen & BIT(id), 0UL);
		seen |= BIT(id);
	}
	KUNIT_EXPECT_EQ(test, seen, expected);
}

static struct kunit_case lba_acpi_cases[] = {
	KUNIT_CASE(fixture_installed),
	KUNIT_CASE(actual_cpu_masks),
	KUNIT_CASE(actual_apic_membership),
	{}
};
static struct kunit_suite lba_acpi_suite = {
	.name = "acpi-boot-contract", .test_cases = lba_acpi_cases,
};
kunit_test_suite(lba_acpi_suite);
