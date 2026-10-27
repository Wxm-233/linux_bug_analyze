struct packet { __le32 value; __le32 other; };
int consume(struct packet *p, u32 parameter)
{
u32 n; if (parameter) n = 7; if (p->value == n) return 1; return 0;
}
