
#include <stdio.h>
#include <stdint.h>
typedef uint64_t u64;
#define GENMASK_ULL(h,l) ((~0ULL << (l)) & (~0ULL >> (63-(h))))
#define FIELD_PREP(m,v) ((((u64)(v)) << __builtin_ctzll(m)) & (m))
#define fallthrough __attribute__((fallthrough))
struct entry {unsigned opcode;struct {unsigned long asid,vmid,addr,ttl,num,scale,tg,leaf;} tlbi;};
#define CMDQ_0_OP GENMASK_ULL(7, 0)
#define CMDQ_OP_TLBI_EL2_VA 0x22
#define CMDQ_OP_TLBI_NH_VA 0x12
#define CMDQ_OP_TLBI_S2_IPA 0x2a
#define CMDQ_TLBI_0_ASID GENMASK_ULL(63, 48)
#define CMDQ_TLBI_0_NUM GENMASK_ULL(16, 12)
#define CMDQ_TLBI_0_SCALE GENMASK_ULL(24, 20)
#define CMDQ_TLBI_0_VMID GENMASK_ULL(47, 32)
#define CMDQ_TLBI_1_IPA_MASK GENMASK_ULL(51, 12)
#define CMDQ_TLBI_1_LEAF (1UL << 0)
#define CMDQ_TLBI_1_TG GENMASK_ULL(11, 10)
#define CMDQ_TLBI_1_TTL GENMASK_ULL(9, 8)
#define CMDQ_TLBI_1_VA_MASK GENMASK_ULL(63, 12)
static void encode(u64 *cmd,struct entry *ent){cmd[0]=FIELD_PREP(CMDQ_0_OP,ent->opcode);cmd[1]=0;switch(ent->opcode){
	case CMDQ_OP_TLBI_NH_VA:
		cmd[0] |= FIELD_PREP(CMDQ_TLBI_0_VMID, ent->tlbi.vmid);
		fallthrough;
	case CMDQ_OP_TLBI_EL2_VA:
		cmd[0] |= FIELD_PREP(CMDQ_TLBI_0_NUM, ent->tlbi.num);
		cmd[0] |= FIELD_PREP(CMDQ_TLBI_0_SCALE, ent->tlbi.scale);
		cmd[0] |= FIELD_PREP(CMDQ_TLBI_0_ASID, ent->tlbi.asid);
		cmd[1] |= FIELD_PREP(CMDQ_TLBI_1_LEAF, ent->tlbi.leaf);
		cmd[1] |= FIELD_PREP(CMDQ_TLBI_1_TTL, ent->tlbi.ttl);
		cmd[1] |= FIELD_PREP(CMDQ_TLBI_1_TG, ent->tlbi.tg);
		cmd[1] |= ent->tlbi.addr & CMDQ_TLBI_1_VA_MASK;
		break;
	case CMDQ_OP_TLBI_S2_IPA:
		cmd[0] |= FIELD_PREP(CMDQ_TLBI_0_NUM, ent->tlbi.num);
		cmd[0] |= FIELD_PREP(CMDQ_TLBI_0_SCALE, ent->tlbi.scale);
		cmd[0] |= FIELD_PREP(CMDQ_TLBI_0_VMID, ent->tlbi.vmid);
		cmd[1] |= FIELD_PREP(CMDQ_TLBI_1_LEAF, ent->tlbi.leaf);
		cmd[1] |= FIELD_PREP(CMDQ_TLBI_1_TTL, ent->tlbi.ttl);
		cmd[1] |= FIELD_PREP(CMDQ_TLBI_1_TG, ent->tlbi.tg);
		cmd[1] |= ent->tlbi.addr & CMDQ_TLBI_1_IPA_MASK;
		break;

default:break;}}
int main(void){struct entry e;u64 cmd[2];while(scanf("%u %lu %lu %lu %lu %lu %lu %lu %lu",&e.opcode,&e.tlbi.asid,&e.tlbi.vmid,&e.tlbi.addr,&e.tlbi.ttl,&e.tlbi.num,&e.tlbi.scale,&e.tlbi.tg,&e.tlbi.leaf)==9){encode(cmd,&e);printf("%llx %llx\n",(unsigned long long)cmd[0],(unsigned long long)cmd[1]);}return 0;}
