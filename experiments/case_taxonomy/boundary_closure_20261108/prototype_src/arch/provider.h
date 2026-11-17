#ifndef CLOSURE_PROVIDER_H
#define CLOSURE_PROVIDER_H
extern int backing;
#define BASE_ADDR backing
#define INNER(p) (BASE_ADDR + (p))
#define OUTER(p) INNER(p)
#define PARAM(INNER) (INNER)
#define STR(x) #x
#define CAT(a, b) a ## b
#define CYCLE CYCLE
#define CHOICE 1
#undef CHOICE
#define CHOICE 2
#define VANISHED 9
#undef VANISHED
#define USE_VANISHED VANISHED
struct ops { int (*run)(int); long (*wide)(long); };
struct descriptor { int code; int (*handler)(int); };
#endif
