/* SPDX-License-Identifier: GPL-2.0 */
/* Logical test doubles: not a binary ACPI table parser or topology allocator. */
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
typedef uint8_t u8;
typedef uint32_t u32;
#define __init
#define CONFIG_X86_X2APIC 1
#define MAX_LOCAL_APIC 1024
#define X86_HYPER_NATIVE 0
#define pr_info(...) ((void)0)
#define pr_warn(...) ((void)0)
#define BAD_MADT_ENTRY(p, end) ((void)(p), (void)(end), false)
#define acpi_table_print_madt_entry(p) ((void)(p))
#define early_per_cpu(name, cpu) name[cpu]
struct acpi_madt_local_apic { u8 id, processor_id; u32 lapic_flags; };
struct acpi_madt_local_x2apic { u32 local_apic_id, uid, lapic_flags; };
union acpi_subtable_headers { int common; };
struct table_header { unsigned revision; };
struct acpi_table_madt { struct table_header header; };
static struct { struct table_header header; unsigned minor_revision; } acpi_gbl_FADT;
static bool acpi_support_online_capable, guest;
static bool has_lapic_cpus;
static int disabled_cpus, num_processors;
static unsigned boot_cpu_physical_apicid = -1U, boot_cpu_apic_version;
static u32 x86_cpu_to_acpiid[4];
static bool apic_id_valid(u32 id) { return id < MAX_LOCAL_APIC; }
static struct { bool (*apic_id_valid)(u32); } apic_ops = { apic_id_valid };
static typeof(apic_ops) *apic = &apic_ops;
static bool hypervisor_is_type(int type) { (void)type; return !guest; }
static int generic_processor_info(int id, unsigned ver)
{ (void)id; (void)ver; return num_processors++; }
static void topology_register_apic(u32 id, u32 uid, bool enabled)
{ (void)id; (void)uid; if (enabled) num_processors++; else disabled_cpus++; }
