struct packet { __le32 value; __le32 other; };
int consume(struct packet *p, u32 parameter)
{
if (p->value == parameter) return 1; return 0;
}
