struct packet { __le32 value[2]; __le32 other; };
int consume(struct packet *p, u32 parameter)
{
u32 n = 7; if (p->value[0] == n) return 1; return 0;
}
