/*
 * Focused i386 NUMA input probe.  Requires an x86 kernel with IA32 emulation,
 * NUMA, and MAX_NUMNODES == 1024.  Reuses compat_start.S from numa_entry.
 * Only this process's policy is changed; each case restores MPOL_DEFAULT.
 */
typedef unsigned int u32;
extern int call6(int, int, int, int, int, int, int);

static int sc(int n, int a, int b, int c, int d, int e)
{
	return call6(n, a, b, c, d, e, 0);
}

static void text(const char *s)
{
	int n = 0;
	while (s[n])
		n++;
	sc(4, 1, (int)s, n, 0, 0);
}

static void number(int value)
{
	char b[24];
	u32 v = value < 0 ? -(u32)value : (u32)value;
	int n = 0;
	do {
		b[n++] = '0' + v % 10;
		v /= 10;
	} while (v);
	if (value < 0)
		b[n++] = '-';
	while (n)
		sc(4, 1, (int)&b[--n], 1, 0, 0);
}

static u32 allowed[1024];

int main(void)
{
	/* The current NUMA-node allowance; do not assume node 0 is permitted. */
	int rc = sc(275, 0, (int)allowed, 32768, 0, 4);
	int node = -1;
	u32 mmap_args[] = { 0, 8192, 3, 0x22, (u32)-1, 0 };
	unsigned char *mem;
	const int maxnodes[] = { 1026, 1026, 1026, 1057 };
	const int bytes[] = { 132, 136, 136, 136 };
	const int poison[] = { 0, 0, 1, 1 };

	if (rc)
		return 77;
	for (int i = 0; i < 32768; i++) {
		if (allowed[i / 32] & (1U << (i % 32))) {
			node = i;
			break;
		}
	}
	if (node < 0 || node >= 1024)
		return 78;
	mem = (void *)sc(90, (int)mmap_args, 0, 0, 0, 0);
	if ((u32)mem >= (u32)-4095)
		return 79;
	if (sc(125, (int)(mem + 4096), 4096, 0, 0, 0))
		return 80;

	for (int i = 0; i < 4; i++) {
		unsigned char *p;
		for (int j = 0; j < 4096; j++)
			mem[j] = 0;
		p = mem + 4096 - bytes[i];
		p[node / 8] |= 1U << (node % 8);
		if (poison[i])
			p[132] = 1; /* 34th compat word, outside maxnode=1026. */
		rc = sc(276, 2, (int)p, maxnodes[i], 0, 0);
		text("{\"maxnode\":"); number(maxnodes[i]);
		text(",\"bytes\":"); number(bytes[i]);
		text(",\"poison_word34\":"); number(poison[i]);
		text(",\"first_allowed_node\":"); number(node);
		text(",\"set_rc\":"); number(rc); text("}\n");
		if (sc(276, 0, 0, 0, 0, 0))
			return 81;
	}
	return sc(91, (int)mem, 8192, 0, 0, 0) ? 82 : 0;
}
