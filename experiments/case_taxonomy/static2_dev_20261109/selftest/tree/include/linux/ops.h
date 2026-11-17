struct ops { int (*op)(int a); int (*op2)(int a); };
#define EINVAL 22
int impl_op2(int a);
