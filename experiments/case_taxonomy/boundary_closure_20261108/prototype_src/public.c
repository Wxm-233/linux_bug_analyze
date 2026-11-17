#include "arch/provider.h"
static int same(int x) { return x + 2; }
int public_target(int x) { return x + 3; }
int public_macro_user(void) { return OUTER(2); }
struct ops public_ops = { .run = same };
