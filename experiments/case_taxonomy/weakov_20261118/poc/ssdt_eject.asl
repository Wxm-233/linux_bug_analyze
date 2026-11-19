/*
 * Loaded at boot through the initrd table upgrade (kernel/firmware/acpi/).
 * Gives the existing QEMU virt CPU device \_SB.C001 a _STA and an _EJ0, so that
 * Linux marks it ejectable and /sys/bus/acpi/devices/ACPI0007:XX/eject appears.
 * _EJ0 models a firmware that reports the CPU as physically gone after eject:
 * _STA becomes 0 (not present, not enabled), which is the third early-return
 * path of the old arm64 arch_unregister_cpu().
 */
DefinitionBlock ("", "SSDT", 2, "WKOV", "CPUEJ", 1)
{
    External (\_SB.C001, DeviceObj)

    Scope (\_SB.C001)
    {
        Name (STAV, 0x0F)

        Method (_STA, 0, NotSerialized)
        {
            Return (STAV)
        }

        Method (_EJ0, 1, NotSerialized)
        {
            STAV = Zero
        }
    }
}
