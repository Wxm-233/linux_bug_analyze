#ifndef COMMON_H
#define COMMON_H
void cpumask_clear_all(void);
void log_only(int v);
void common_reset(void);
int common_alloc(int size, int flags);
#endif
