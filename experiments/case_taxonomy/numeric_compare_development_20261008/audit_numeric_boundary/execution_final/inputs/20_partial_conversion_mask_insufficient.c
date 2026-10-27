struct packet { __le32 value; __le32 other; };
int consume(struct packet *p, u32 parameter)
{
if (p->value & (cpu_to_le32(1) | MASK_UNKNOWN)) return 1; return 0;
}
