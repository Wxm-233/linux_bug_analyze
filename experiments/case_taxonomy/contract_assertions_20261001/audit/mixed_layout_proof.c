#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
struct plain_fields { uint16_t small; uint32_t medium; uint64_t large; };
struct packed_fields { uint16_t small; uint32_t medium; uint64_t large; } __attribute__((packed));
_Static_assert(sizeof(struct packed_fields)==14, "packed mixed width layout");
_Static_assert(sizeof(struct plain_fields)==16, "native plain mixed width layout");
_Static_assert(offsetof(struct packed_fields,medium)==2, "packed medium offset");
_Static_assert(offsetof(struct plain_fields,medium)==4, "plain medium offset");
_Static_assert(offsetof(struct packed_fields,large)==6, "packed large offset");
_Static_assert(offsetof(struct plain_fields,large)==8, "plain large offset");
int main(void) {
    printf("{\"plain_size\":%zu,\"packed_size\":%zu,\"plain_medium_offset\":%zu,\"packed_medium_offset\":%zu,\"plain_large_offset\":%zu,\"packed_large_offset\":%zu}\n",
        sizeof(struct plain_fields),sizeof(struct packed_fields),
        offsetof(struct plain_fields,medium),offsetof(struct packed_fields,medium),
        offsetof(struct plain_fields,large),offsetof(struct packed_fields,large));
    return 0;
}
