int main(int argc, char **argv)
{
    if (argc != 7) return 2;
    struct acpi_table_madt table = { .header.revision = atoi(argv[3]) };
    acpi_gbl_FADT.header.revision = atoi(argv[1]);
    acpi_gbl_FADT.minor_revision = atoi(argv[2]);
    guest = atoi(argv[4]);
    unsigned flags = atoi(argv[6]);
    determine_support(&table);
    int rc;
    if (atoi(argv[5])) {
        /* No mixed-table duplicate-ID policy is exercised. */
        struct acpi_madt_local_x2apic entry = { .local_apic_id = 256, .uid = 7, .lapic_flags = flags };
        rc = acpi_parse_x2apic((union acpi_subtable_headers *)&entry, sizeof(entry));
    } else {
        struct acpi_madt_local_apic entry = { .id = 7, .processor_id = 7, .lapic_flags = flags };
        rc = acpi_parse_lapic((union acpi_subtable_headers *)&entry, sizeof(entry));
    }
    printf("{\"rc\":%d,\"support\":%d,\"enabled_registered\":%d,\"disabled_registered\":%d,\"accepted\":%d}\n",
           rc, acpi_support_online_capable, num_processors, disabled_cpus,
           num_processors + disabled_cpus);
    return 0;
}
