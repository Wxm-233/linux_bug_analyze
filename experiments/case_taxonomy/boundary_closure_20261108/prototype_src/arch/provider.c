#include "provider.h"
int backing = 5;
int VANISHED = 4;
int CYCLE = 3;
static int same(int x) { return x; }
int compatible(int x) { return x + 1; }
long incompatible(long x) { return x; }
struct ops active_ops = { .run = same, .wide = incompatible };
struct descriptor descriptions[] = { {7, same}, {8, compatible} };
struct ops cast_ops = { .run = (int (*)(int))incompatible };
int (*runtime_slot)(int);
extern int (*external_slot)(int);
void set_slot(int (*input)(int)) { runtime_slot = input; }
int dispatch(int x)
{
    return active_ops.run(x) + descriptions[0].handler(x)
         + runtime_slot(x) + external_slot(x);
}
int macro_user(void)
{
    return OUTER(1) + PARAM(2) + CAT(back, ing) + CHOICE + USE_VANISHED + CYCLE;
}
const char *stringified = STR(INNER(1));
