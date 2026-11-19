/*
 * Loaded at run time through ACPI configfs, after the eject.
 * Module-level code puts the CPU back (_STA = 0x0F) and sends a Device Check
 * notification, which makes Linux rescan \_SB.C001 and hot-add the CPU again.
 */
DefinitionBlock ("", "SSDT", 2, "WKOV", "CPUADD", 1)
{
    External (\_SB.C001, DeviceObj)
    External (\_SB.C001.STAV, IntObj)

    \_SB.C001.STAV = 0x0F
    Notify (\_SB.C001, 0x01)
}
