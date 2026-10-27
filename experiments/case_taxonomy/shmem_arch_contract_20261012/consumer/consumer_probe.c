// SPDX-License-Identifier: GPL-2.0
/* Run the unchanged historical xas_split_alloc() through its official shim. */
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include "test.h"
#include <linux/xarray.h>

int main(int argc, char **argv)
{
	char *end;
	unsigned long order;
	int before, after, error, after_cleanup;
	DEFINE_XARRAY(array);
	XA_STATE_ORDER(xas, &array, 0, 0);

	if (argc != 2)
		return 2;
	errno = 0;
	order = strtoul(argv[1], &end, 10);
	if (errno || *end || order > 63)
		return 2;

	rcu_register_thread();
	radix_tree_init();
	before = nr_allocated;
	xas_split_alloc(&xas, xa_mk_value(123), (unsigned int)order, GFP_KERNEL);
	error = xas_error(&xas);
	after = nr_allocated;
	xas_destroy(&xas);
	radix_tree_cpu_dead(1);
	rcu_barrier();
	after_cleanup = nr_allocated;
	printf("{\"order\":%lu,\"new_order\":0,\"xa_shift\":%u,"
	       "\"xa_chunk_shift\":%u,\"xas_error\":%d,"
	       "\"nodes_before\":%d,\"nodes_after_alloc\":%d,"
	       "\"nodes_after_cleanup\":%d}\n",
	       order, (unsigned int)xas.xa_shift, (unsigned int)XA_CHUNK_SHIFT, error,
	       before, after, after_cleanup);
	rcu_unregister_thread();
	return after_cleanup == before ? 0 : 1;
}
