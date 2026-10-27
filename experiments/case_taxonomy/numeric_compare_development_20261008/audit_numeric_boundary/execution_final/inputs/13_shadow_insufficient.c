struct packet { __le32 value; __le32 other; };
int consume(struct packet *p, u32 parameter)
{
u32 n = 7; { u32 n = 8; if (p->value == n) return 1; } return 0;
}
