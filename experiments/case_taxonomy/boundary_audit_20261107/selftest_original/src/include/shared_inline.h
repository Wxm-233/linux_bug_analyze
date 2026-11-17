#ifndef TEST_SHARED_INLINE_H
#define TEST_SHARED_INLINE_H
#include "arch_api.h"
static inline int shared_inline(void) { return arch_call(); }
#endif
