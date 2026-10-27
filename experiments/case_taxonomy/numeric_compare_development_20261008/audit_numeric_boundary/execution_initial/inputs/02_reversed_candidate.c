struct packet { __le32 value; __le32 other; };
int consume(struct packet *p, u32 parameter)
{
u32 n = 7; if (n == p->value) return 1; return 0;
}
