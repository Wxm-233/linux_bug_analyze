#include <asm/fx.h>
#include <fxwrap.h>
#define FX_SIZE (1 << FX_ARCH_SHIFT)
static int fx_helper(int x) { return x * 2; }
int fx_common(int x) { return x - 1; }
int other(void) { return 7; }

int f1(void) { return fx_arch_get(1); }
int f2(int a) { return fx_helper(a); }
int f3(int a, int b) { return fx_arch_get(a) + fx_arch_get(b + 1); }
unsigned long f4(int x)
{
	if (!fx_pte_present(x))
		return 0;
	x = other();
	return fx_pte_pfn(x);
}
int f5(void) { return FX_SIZE; }
int f6(int q) { return fx_wrap(q); }
int f7(int a) { return fx_common(a) + other(); }
int f8(int a)
{
#if 0
	a = fx_arch_get(a);
#endif
	return a;
}
