#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#pragma pack(push,1)
struct original_pragma { uint16_t small; uint32_t medium; };
#pragma pack(pop)
struct projected_without_pragma { uint16_t small; uint32_t medium; };
#define __packed __attribute__((aligned(16)))
struct original_macro { uint16_t small; uint32_t medium; } __packed;
#undef __packed
#define __packed __attribute__((packed))
struct projected_redefined_macro { uint16_t small; uint32_t medium; } __packed;
_Static_assert(sizeof(struct original_pragma)==6, "pragma layout");
_Static_assert(sizeof(struct projected_without_pragma)==8, "lost pragma layout");
_Static_assert(sizeof(struct original_macro)==16, "known original macro layout");
_Static_assert(sizeof(struct projected_redefined_macro)==6, "substituted macro layout");
int main(void) {
    printf("{\"original_pragma_size\":%zu,\"projected_without_pragma_size\":%zu,\"original_macro_size\":%zu,\"projected_macro_size\":%zu,\"original_pragma_medium_offset\":%zu,\"projected_pragma_medium_offset\":%zu,\"original_macro_medium_offset\":%zu,\"projected_macro_medium_offset\":%zu}\n",
        sizeof(struct original_pragma),sizeof(struct projected_without_pragma),
        sizeof(struct original_macro),sizeof(struct projected_redefined_macro),
        offsetof(struct original_pragma,medium),offsetof(struct projected_without_pragma,medium),
        offsetof(struct original_macro,medium),offsetof(struct projected_redefined_macro,medium));
    return 0;
}
