struct packet { __le32 value; __le32 other; };
int consume(struct packet *p, u32 parameter)
{
if (p->value == 0) return 1; return 0;
}
