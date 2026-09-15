/* SPDX-License-Identifier: GPL-2.0 */
/* Test-only early-boot fixture. Only used in isolated QEMU kernels. */
static int lba_scenario = -1;
static bool lba_x2, lba_injected;
static unsigned int lba_expected;

static int __init lba_parse_option(char *str)
{
	/* 0 modern, 1 legacy native-policy, 2 legacy guest-policy, 3 MADT45 guest */
	int mode;
	if (!str || kstrtoint(str, 10, &mode) || mode < 0 || mode > 7)
		return -EINVAL;
	lba_scenario = mode / 2;
	lba_x2 = mode & 1;
	lba_expected = lba_scenario == 0 ? 3 : lba_scenario == 1 ? 1 : 4;
	return 0;
}
early_param("lba_acpi", lba_parse_option);

static bool __init lba_native_policy(void)
{
	if (lba_scenario >= 0)
		return lba_scenario == 1;
	return hypervisor_is_type(X86_HYPER_NATIVE);
}

static void __init lba_prepare_madt(struct acpi_table_madt *madt)
{
	u8 *start = (u8 *)(madt + 1), *end = (u8 *)madt + madt->header.length;
	u8 *first = NULL, *last = NULL, *p;
	unsigned int count = 0, i;
	u8 checksum = 0;

	if (lba_scenario < 0 || lba_injected)
		return;
	/* Require exactly the expected contiguous 8 LAPIC records from QEMU. */
	for (p = start; p + sizeof(struct acpi_subtable_header) <= end;) {
		struct acpi_subtable_header *h = (void *)p;
		if (h->length < sizeof(*h) || p + h->length > end)
			return;
		if (h->type == ACPI_MADT_TYPE_LOCAL_APIC) {
			if (h->length != sizeof(struct acpi_madt_local_apic) ||
			    (last && last != p))
				return;
			if (!first)
				first = p;
			count++;
			last = p + h->length;
		}
		p += h->length;
	}
	if (count != 8 || !first || last - first != 64)
		return;
	/* Preserve total MADT length and all non-CPU records. */
	memset(first, 0, 64);
	for (i = 0; i < (lba_x2 ? 4 : 8); i++) {
		u32 flags = i == 0 ? ACPI_MADT_ENABLED :
			(lba_scenario == 0 && (i == 1 || i == 3) ? ACPI_MADT_ONLINE_CAPABLE : 0);
		if (lba_x2) {
			struct acpi_madt_local_x2apic *e = (void *)(first + i * 16);
			e->header.type = ACPI_MADT_TYPE_LOCAL_X2APIC;
			e->header.length = sizeof(*e);
			e->local_apic_id = i;
			e->uid = i;
			e->lapic_flags = flags;
		} else {
			struct acpi_madt_local_apic *e = (void *)(first + i * 8);
			e->header.type = ACPI_MADT_TYPE_LOCAL_APIC;
			e->header.length = sizeof(*e);
			e->id = i < 4 ? i : 0xff;
			e->processor_id = i;
			e->lapic_flags = flags;
		}
	}
	acpi_gbl_FADT.header.revision = 6;
	acpi_gbl_FADT.minor_revision = lba_scenario == 0 ? 3 : 2;
	madt->header.revision = lba_scenario == 0 ? 5 : lba_scenario == 3 ? 45 : 4;
	madt->header.checksum = 0;
	for (p = (u8 *)madt; p < end; p++)
		checksum += *p;
	madt->header.checksum = -checksum;
	lba_injected = true;
	pr_info("LBA fixture scenario=%d x2=%d expected=%u bytes=%u\n",
		lba_scenario, lba_x2, lba_expected, madt->header.length);
}
