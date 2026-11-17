#include "arch_api.h"
#include "shared.h"

int arch_data;
int arch_call(void) { return shared_call() + shared_data; }
int hook(void) { return 2; }
