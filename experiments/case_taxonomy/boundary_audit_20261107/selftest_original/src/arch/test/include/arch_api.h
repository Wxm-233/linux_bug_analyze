#ifndef TEST_ARCH_API_H
#define TEST_ARCH_API_H
typedef unsigned arch_word;
struct arch_item { int value; };
union arch_value { int i; unsigned u; };
enum { ARCH_LIMIT = 7 };
#define ARCH_INCREMENT(x) ((x) + 1)
extern int arch_data;
int arch_call(void);
#endif
