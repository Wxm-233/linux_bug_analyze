/* Exact dw_mmc member declarations; macros and host path excluded.
 * Branch root declarations preserve the reviewed original names and types. */
#include <stdint.h>
typedef uint32_t u32;
typedef uint32_t __le32;
struct idmac_desc_64addr {
	u32		des0;	/* Control Descriptor */
	u32		des1;	/* Reserved */
	u32		des2;	/*Buffer sizes */
	u32		des3;	/* Reserved */
	u32		des4;	/* Lower 32-bits of Buffer Address Pointer 1*/
	u32		des5;	/* Upper 32-bits of Buffer Address Pointer 1*/
	u32		des6;	/* Lower 32-bits of Next Descriptor Address */
	u32		des7;	/* Upper 32-bits of Next Descriptor Address */
};
struct idmac_desc {
	__le32		des0;	/* Control Descriptor */
	__le32		des1;	/* Buffer sizes */
	__le32		des2;	/* buffer 1 physical address */
	__le32		des3;	/* buffer 2 physical address */
};
int scope_projection(int mode) {
    if (mode == 1) {
        struct idmac_desc_64addr *p;
        struct idmac_desc_64addr object = {0};
        p = &object;
        _Static_assert(__builtin_types_compatible_p(__typeof__(p), struct idmac_desc_64addr *), "first p belongs to 64addr declaration");
        _Static_assert(sizeof(p->des0) == 4, "first p scalar width");
        p->des0 = 0;
        p->des1 = 0;
        p->des2 = 0;
        p->des3 = 0;
        return p->des0;
    } else {
        struct idmac_desc *p;
        struct idmac_desc object = {0};
        p = &object;
        _Static_assert(__builtin_types_compatible_p(__typeof__(p), struct idmac_desc *), "second p belongs to 32addr declaration");
        _Static_assert(sizeof(p->des0) == 4, "second p scalar width");
        p->des0 = 0;
        p->des1 = 0;
        return p->des0;
    }
}
/* Additional synthetic nested shadow; not present in the dw_mmc snippet. */
int nested_shadow_projection(void) {
    uint32_t p = 0;
    _Static_assert(sizeof(p)==4,"outer synthetic p");
    {
        uint16_t p = 0;
        _Static_assert(sizeof(p)==2,"inner synthetic p");
        (void)p;
    }
    return (int)p;
}
