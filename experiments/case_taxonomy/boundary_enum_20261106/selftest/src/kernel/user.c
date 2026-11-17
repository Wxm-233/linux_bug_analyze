#include "arch_api.h"
#include "asm-generic/fallback.h"
#include "asm/generated_api.h"
#include "shared.h"
#include "shared_inline.h"

__attribute__((weak)) int hook(void) { return 1; }
int shared_data;
int shared_call(void) { return shared_data; }

int user(struct arch_item *item, union arch_value *value)
{
    arch_word word = ARCH_LIMIT;
    arch_data = 4;
    arch_data += 2;
    int *address = &arch_data;
    int (*callback)(void) = arch_call;
    return word + item->value + value->i + arch_data + *address + callback()
        + arch_call() + fallback() + hook() + shared_inline() + GENERATED_CONSTANT
        + ARCH_INCREMENT(1);
}
