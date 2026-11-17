/* Minimal libc-free /init for the LoongArch boot feasibility test (heldout_prep criteria 三).
 * Generic syscall table: write = 64, reboot = 142. */
static long sys3(long n, long a, long b, long c)
{
	register long a7 __asm__("$a7") = n;
	register long a0 __asm__("$a0") = a;
	register long a1 __asm__("$a1") = b;
	register long a2 __asm__("$a2") = c;
	__asm__ volatile("syscall 0" : "+r"(a0) : "r"(a7), "r"(a1), "r"(a2) : "memory");
	return a0;
}
static long sys4(long n, long a, long b, long c, long d)
{
	register long a7 __asm__("$a7") = n;
	register long a0 __asm__("$a0") = a;
	register long a1 __asm__("$a1") = b;
	register long a2 __asm__("$a2") = c;
	register long a3 __asm__("$a3") = d;
	__asm__ volatile("syscall 0" : "+r"(a0) : "r"(a7), "r"(a1), "r"(a2), "r"(a3) : "memory");
	return a0;
}
void _start(void)
{
	static const char msg[] = "\n@@LA BOOT OK\n";
	sys3(64, 1, (long)msg, sizeof(msg) - 1);
	sys4(142, 0xfee1dead, 672274793, 0x4321fedc, 0); /* LINUX_REBOOT_CMD_POWER_OFF */
	for (;;)
		;
}
