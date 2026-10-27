#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define CMD_HDR_FORCE_PHY_OFF 17
#define CMD_HDR_FORCE_PHY_MSK (0x1U << CMD_HDR_FORCE_PHY_OFF)
static uint32_t to_le32(uint32_t x) {
#if __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
return __builtin_bswap32(x);
#else
return x;
#endif
}
int main(void) {
 uint32_t init[]={0,0x100U};
 for(unsigned i=0;i<2;i++) {
   uint32_t old=to_le32(init[i]),fix=old;
   old |= CMD_HDR_FORCE_PHY_MSK;
   fix |= to_le32(CMD_HDR_FORCE_PHY_MSK);
   uint32_t expected=init[i]|CMD_HDR_FORCE_PHY_MSK;
   unsigned char bytes[4];
   for(unsigned b=0;b<4;b++) bytes[b]=(expected>>(8*b))&255;
   printf("{\"initial\":%u,\"mask\":%u,\"old_matches_le_contract\":%s,\"fixed_matches_le_contract\":%s}\n",init[i],CMD_HDR_FORCE_PHY_MSK,
    memcmp(&old,bytes,4)?"false":"true",memcmp(&fix,bytes,4)?"false":"true");
 }
 return 0;
}
