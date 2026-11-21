cd /root/repos/linux; R=df2908090cda
git show $R:arch/x86/pci/amd_bus.c | sed -n 50,62p
git show $R:arch/x86/pci/amd_bus.c | sed -n 68,110p | grep -n "found\|return\|for (\|read_pci_config\|hb_probes\|vendor\|device"
git show $R:arch/x86/pci/amd_bus.c | sed -n 400,425p
which qemu-system-i386 >/dev/null 2>&1 && echo "qemu-system-i386 present" || echo "no qemu-system-i386"
