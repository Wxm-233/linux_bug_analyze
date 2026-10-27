### {"id": "D01", "profile": "old_s390", "kind": "configured_function", "function": "smp_start_secondary", "path": "/root/.cache/linux-bug-analyze/s390-contract-20261013/runtime/old/linux/arch/s390/kernel/smp.c", "configuration_sha256": "ba935721b43a3187db05c24b74f5694180be0e816368efbc0155a507ace1f11e", "source_identity_note": "instrumented current preprocessing; local packet lines are not original C lines"}
```c
1 | static void smp_start_secondary(void *cpuvoid)
2 | {
3 |  int cpu = ((*((struct lowcore *) 0)).cpu_nr);
4 | 
5 |  (*((struct lowcore *) 0)).last_update_clock = get_tod_clock();
6 |  (*((struct lowcore *) 0)).restart_stack = (unsigned long)restart_stack;
7 |  (*((struct lowcore *) 0)).restart_fn = (unsigned long)do_restart;
8 |  (*((struct lowcore *) 0)).restart_data = 0;
9 |  (*((struct lowcore *) 0)).restart_source = -1U;
10 |  (*((struct lowcore *) 0)).restart_flags = 0;
11 |  restore_access_regs((*((struct lowcore *) 0)).access_regs_save_area);
12 |  cpu_init();
13 |  rcu_cpu_starting(cpu);
14 |  init_cpu_timer();
15 |  vtime_init();
16 |  vdso_getcpu_init();
17 |  ({-1;});
18 |  r4_note("arch_before_notify", cpu, 0, -1, -1, -1, 0);
19 |  notify_cpu_starting(cpu);
20 |  r4_note("arch_after_notify", cpu, 0, -1, -1, -1, 0);
21 |  if ((cpu_topology[cpu].dedicated))
22 |   set_cpu_flag(7);
23 |  else
24 |   clear_cpu_flag(7);
25 |  set_cpu_online(cpu, true);
26 |  update_cpu_masks();
27 |  r4_note("arch_online_ready", cpu, 0, -1, -1, -1, 0);
28 |  inc_irq_stat(CPU_RST);
29 |  do { arch_local_irq_enable(); } while (0);
30 |  cpu_startup_entry(CPUHP_AP_ONLINE_IDLE);
31 | }
```

### {"id": "D02", "profile": "old_s390", "kind": "configured_function", "function": "cpu_thread_map", "path": "/root/.cache/linux-bug-analyze/s390-contract-20261013/runtime/old/linux/arch/s390/kernel/topology.c", "configuration_sha256": "ba935721b43a3187db05c24b74f5694180be0e816368efbc0155a507ace1f11e", "source_identity_note": "instrumented current preprocessing; local packet lines are not original C lines"}
```c
1 | static void cpu_thread_map(cpumask_t *dst, unsigned int cpu)
2 | {
3 |  static cpumask_t mask;
4 |  int i;
5 | 
6 |  cpumask_clear(&mask);
7 |  if (!cpu_online(cpu))
8 |   goto out;
9 |  cpumask_set_cpu(cpu, &mask);
10 |  if (topology_mode != TOPOLOGY_MODE_HW)
11 |   goto out;
12 |  cpu -= cpu % (smp_cpu_mtid + 1);
13 |  for (i = 0; i <= smp_cpu_mtid; i++)
14 |   if (cpu_present(cpu + i))
15 |    cpumask_set_cpu(cpu + i, &mask);
16 |  cpumask_and(&mask, &mask, ((const struct cpumask *)&__cpu_online_mask));
17 | out:
18 |  cpumask_copy(dst, &mask);
19 | }
```

### {"id": "D03", "profile": "old_s390", "kind": "configured_function", "function": "update_cpu_masks", "path": "/root/.cache/linux-bug-analyze/s390-contract-20261013/runtime/old/linux/arch/s390/kernel/topology.c", "configuration_sha256": "ba935721b43a3187db05c24b74f5694180be0e816368efbc0155a507ace1f11e", "source_identity_note": "instrumented current preprocessing; local packet lines are not original C lines"}
```c
1 | void update_cpu_masks(void)
2 | {
3 |  struct cpu_topology_s390 *topo, *topo_package, *topo_sibling;
4 |  int cpu, sibling, pkg_first, smt_first, id;
5 | 
6 |  for (((cpu)) = -1; ((cpu)) = cpumask_next(((cpu)), (((const struct cpumask *)&__cpu_possible_mask))), ((cpu)) < nr_cpu_ids;) {
7 |   topo = &cpu_topology[cpu];
8 |   cpu_thread_map(&topo->thread_mask, cpu);
9 |   cpu_group_map(&topo->core_mask, &socket_info, cpu);
10 |   cpu_group_map(&topo->book_mask, &book_info, cpu);
11 |   cpu_group_map(&topo->drawer_mask, &drawer_info, cpu);
12 |   topo->booted_cores = 0;
13 |   if (topology_mode != TOPOLOGY_MODE_HW) {
14 |    id = topology_mode == TOPOLOGY_MODE_PACKAGE ? 0 : cpu;
15 |    topo->thread_id = cpu;
16 |    topo->core_id = cpu;
17 |    topo->socket_id = id;
18 |    topo->book_id = id;
19 |    topo->drawer_id = id;
20 |   }
21 |  }
22 |  for (((cpu)) = -1; ((cpu)) = cpumask_next(((cpu)), (((const struct cpumask *)&__cpu_online_mask))), ((cpu)) < nr_cpu_ids;) {
23 |   topo = &cpu_topology[cpu];
24 |   pkg_first = cpumask_first(&topo->core_mask);
25 |   topo_package = &cpu_topology[pkg_first];
26 |   if (cpu == pkg_first) {
27 |    for ((sibling) = -1; (sibling) = cpumask_next((sibling), (&topo->core_mask)), (sibling) < nr_cpu_ids;) {
28 |     topo_sibling = &cpu_topology[sibling];
29 |     smt_first = cpumask_first(&topo_sibling->thread_mask);
30 |     if (sibling == smt_first)
31 |      topo_package->booted_cores++;
32 |    }
33 |   } else {
34 |    topo->booted_cores = topo_package->booted_cores;
35 |   }
36 |  }
37 | }
```

### {"id": "D04", "profile": "old_s390", "kind": "configured_function", "function": "cpu_smt_mask", "path": "/root/.cache/linux-bug-analyze/s390-contract-20261013/runtime/old/linux/include/linux/topology.h", "configuration_sha256": "ba935721b43a3187db05c24b74f5694180be0e816368efbc0155a507ace1f11e", "source_identity_note": "instrumented current preprocessing; local packet lines are not original C lines"}
```c
1 | static inline __attribute__((__gnu_inline__)) __attribute__((__unused__)) __attribute__((__no_instrument_function__)) const struct cpumask *cpu_smt_mask(int cpu)
2 | {
3 |  return (&cpu_topology[cpu].thread_mask);
4 | }
```

### {"id": "D05", "profile": "old_s390", "kind": "configured_function", "function": "sched_core_cpu_starting", "path": "/root/.cache/linux-bug-analyze/s390-contract-20261013/runtime/old/linux/kernel/sched/core.c", "configuration_sha256": "ba935721b43a3187db05c24b74f5694180be0e816368efbc0155a507ace1f11e", "source_identity_note": "instrumented current preprocessing; local packet lines are not original C lines"}
```c
1 | static void sched_core_cpu_starting(unsigned int cpu)
2 | {
3 |  const struct cpumask *smt_mask = cpu_smt_mask(cpu);
4 |  struct rq *rq = (&(*({ do { const void *__vpp_verify = (typeof((&(runqueues)) + 0))((void *)0); (void)__vpp_verify; } while (0); ({ unsigned long __ptr; __asm__ ("" : "=r"(__ptr) : "0"((typeof(*((&(runqueues)))) *)((&(runqueues))))); (typeof((typeof(*((&(runqueues)))) *)((&(runqueues))))) (__ptr + (((__per_cpu_offset[((cpu))])))); }); }))), *core_rq = ((void *)0);
5 |  unsigned long flags;
6 |  int t;
7 | 
8 |  (*({ do { const void *__vpp_verify = (typeof((&(r4_lock_observation)) + 0))((void *)0); (void)__vpp_verify; } while (0); ({ unsigned long __ptr; __asm__ ("" : "=r"(__ptr) : "0"((typeof(*((&(r4_lock_observation)))) *)((&(r4_lock_observation))))); (typeof((typeof(*((&(r4_lock_observation)))) *)((&(r4_lock_observation))))) (__ptr + (((__per_cpu_offset[(cpu)])))); }); })).active = true;
9 |  r4_note("core_enter", cpu, 0, -1, -1, -1, 0);
10 |  sched_core_lock(cpu, &flags);
11 | 
12 |  ({ int __ret_warn_on = !!(rq->core != rq); if (__builtin_expect(!!(__ret_warn_on), 0)) do { do { asm __inline volatile( "0:	mc	0,0\n" ".section .rodata.str,\"aMS\",@progbits,1\n" "1:	.asciz	\"""kernel/sched/core.c""\"\n" ".previous\n" ".section __bug_table,\"awM\",@progbits,%2\n" "2:	.long	0b-2b,1b-2b\n" "	.short	%0,%1\n" "	.org	2b+%2\n" ".previous\n" : : "i" (5786), "i" ((1 << 0)|((1 << 1) | ((9) << 8))), "i" (sizeof(struct bug_entry))); } while (0); } while (0); __builtin_expect(!!(__ret_warn_on), 0); });
13 | 
14 | 
15 |  if (cpumask_weight(smt_mask) == 1)
16 |   goto unlock;
17 | 
18 | 
19 |  for ((t) = -1; (t) = cpumask_next((t), (smt_mask)), (t) < nr_cpu_ids;) {
20 |   if (t == cpu)
21 |    continue;
22 |   rq = (&(*({ do { const void *__vpp_verify = (typeof((&(runqueues)) + 0))((void *)0); (void)__vpp_verify; } while (0); ({ unsigned long __ptr; __asm__ ("" : "=r"(__ptr) : "0"((typeof(*((&(runqueues)))) *)((&(runqueues))))); (typeof((typeof(*((&(runqueues)))) *)((&(runqueues))))) (__ptr + (((__per_cpu_offset[((t))])))); }); })));
23 |   if (rq->core == rq) {
24 |    core_rq = rq;
25 |    break;
26 |   }
27 |  }
28 | 
29 |  if (({ int __ret_warn_on = !!(!core_rq); if (__builtin_expect(!!(__ret_warn_on), 0)) do { do { asm __inline volatile( "0:	mc	0,0\n" ".section .rodata.str,\"aMS\",@progbits,1\n" "1:	.asciz	\"""kernel/sched/core.c""\"\n" ".previous\n" ".section __bug_table,\"awM\",@progbits,%2\n" "2:	.long	0b-2b,1b-2b\n" "	.short	%0,%1\n" "	.org	2b+%2\n" ".previous\n" : : "i" (5803), "i" ((1 << 0)|((1 << 1) | ((9) << 8))), "i" (sizeof(struct bug_entry))); } while (0); } while (0); __builtin_expect(!!(__ret_warn_on), 0); }))
30 |   goto unlock;
31 | 
32 | 
33 |  for ((t) = -1; (t) = cpumask_next((t), (smt_mask)), (t) < nr_cpu_ids;) {
34 |   rq = (&(*({ do { const void *__vpp_verify = (typeof((&(runqueues)) + 0))((void *)0); (void)__vpp_verify; } while (0); ({ unsigned long __ptr; __asm__ ("" : "=r"(__ptr) : "0"((typeof(*((&(runqueues)))) *)((&(runqueues))))); (typeof((typeof(*((&(runqueues)))) *)((&(runqueues))))) (__ptr + (((__per_cpu_offset[((t))])))); }); })));
35 | 
36 |   if (t == cpu)
37 |    rq->core = core_rq;
38 | 
39 |   ({ int __ret_warn_on = !!(rq->core != core_rq); if (__builtin_expect(!!(__ret_warn_on), 0)) do { do { asm __inline volatile( "0:	mc	0,0\n" ".section .rodata.str,\"aMS\",@progbits,1\n" "1:	.asciz	\"""kernel/sched/core.c""\"\n" ".previous\n" ".section __bug_table,\"awM\",@progbits,%2\n" "2:	.long	0b-2b,1b-2b\n" "	.short	%0,%1\n" "	.org	2b+%2\n" ".previous\n" : : "i" (5813), "i" ((1 << 0)|((1 << 1) | ((9) << 8))), "i" (sizeof(struct bug_entry))); } while (0); } while (0); __builtin_expect(!!(__ret_warn_on), 0); });
40 |  }
41 | 
42 | unlock:
43 |  sched_core_unlock(cpu, &flags);
44 |  {
45 |   struct r4_lock_observation *o = &(*({ do { const void *__vpp_verify = (typeof((&(r4_lock_observation)) + 0))((void *)0); (void)__vpp_verify; } while (0); ({ unsigned long __ptr; __asm__ ("" : "=r"(__ptr) : "0"((typeof(*((&(r4_lock_observation)))) *)((&(r4_lock_observation))))); (typeof((typeof(*((&(r4_lock_observation)))) *)((&(r4_lock_observation))))) (__ptr + (((__per_cpu_offset[(cpu)])))); }); }));
46 |   o->active = false;
47 |   printk("\001" "6" "R4 phase=lock_snapshot cpu=%u current=%u seq=%u mask=%lx self=%u weight=%u locks=%u rq_self=%u online=%u printed_after_unlock=1\n", cpu, ((*((struct lowcore *) 0)).cpu_nr), o->seq, o->mask, o->self, o->weight, o->count, o->rq_self, o->online)
48 |                                                                                                      ;
49 |  }
50 |  r4_note("core_exit", cpu, 0, -1, -1, -1, 0);
51 | }
```

### {"id": "D06", "profile": "old_s390", "kind": "configured_function", "function": "sched_core_lock", "path": "/root/.cache/linux-bug-analyze/s390-contract-20261013/runtime/old/linux/kernel/sched/core.c", "configuration_sha256": "ba935721b43a3187db05c24b74f5694180be0e816368efbc0155a507ace1f11e", "source_identity_note": "instrumented current preprocessing; local packet lines are not original C lines"}
```c
1 | static void sched_core_lock(int cpu, unsigned long *flags)
2 | {
3 |  const struct cpumask *smt_mask = cpu_smt_mask(cpu);
4 |  int t, i = 0;
5 |  struct r4_lock_observation *o = &(*({ do { const void *__vpp_verify = (typeof((&(r4_lock_observation)) + 0))((void *)0); (void)__vpp_verify; } while (0); ({ unsigned long __ptr; __asm__ ("" : "=r"(__ptr) : "0"((typeof(*((&(r4_lock_observation)))) *)((&(r4_lock_observation))))); (typeof((typeof(*((&(r4_lock_observation)))) *)((&(r4_lock_observation))))) (__ptr + (((__per_cpu_offset[(cpu)])))); }); }));
6 | 
7 |  if (o->active) {
8 |   o->seq = r4_next_seq(cpu);
9 |   o->mask = ((smt_mask)->bits)[0];
10 |   o->self = cpumask_test_cpu(cpu, smt_mask);
11 |   o->weight = cpumask_weight(smt_mask);
12 |   o->rq_self = (&(*({ do { const void *__vpp_verify = (typeof((&(runqueues)) + 0))((void *)0); (void)__vpp_verify; } while (0); ({ unsigned long __ptr; __asm__ ("" : "=r"(__ptr) : "0"((typeof(*((&(runqueues)))) *)((&(runqueues))))); (typeof((typeof(*((&(runqueues)))) *)((&(runqueues))))) (__ptr + (((__per_cpu_offset[((cpu))])))); }); })))->core == (&(*({ do { const void *__vpp_verify = (typeof((&(runqueues)) + 0))((void *)0); (void)__vpp_verify; } while (0); ({ unsigned long __ptr; __asm__ ("" : "=r"(__ptr) : "0"((typeof(*((&(runqueues)))) *)((&(runqueues))))); (typeof((typeof(*((&(runqueues)))) *)((&(runqueues))))) (__ptr + (((__per_cpu_offset[((cpu))])))); }); })));
13 |   o->online = cpu_online(cpu);
14 |   o->count = 0;
15 |  }
16 |  do { do { ({ unsigned long __dummy; typeof(*flags) __dummy2; (void)(&__dummy == &__dummy2); 1; }); *flags = arch_local_irq_save(); } while (0); } while (0);
17 |  for ((t) = -1; (t) = cpumask_next((t), (smt_mask)), (t) < nr_cpu_ids;) {
18 |   __raw_spin_lock(((void)(i++), (&(&(*({ do { const void *__vpp_verify = (typeof((&(runqueues)) + 0))((void *)0); (void)__vpp_verify; } while (0); ({ unsigned long __ptr; __asm__ ("" : "=r"(__ptr) : "0"((typeof(*((&(runqueues)))) *)((&(runqueues))))); (typeof((typeof(*((&(runqueues)))) *)((&(runqueues))))) (__ptr + (((__per_cpu_offset[((t))])))); }); })))->__lock)));
19 |   if (o->active)
20 |    o->count++;
21 |  }
22 | }
```

### {"id": "D07", "profile": "old_x86", "kind": "configured_function", "function": "set_cpu_sibling_map", "path": "/root/.cache/linux-bug-analyze/s390-contract-20261013/runtime/old/linux/arch/x86/kernel/smpboot.c", "configuration_sha256": "a9264c98fd293799f8a3aced3642bd3bc8e5def1ed6f12884f96056695aba318", "source_identity_note": "instrumented current preprocessing; local packet lines are not original C lines"}
```c
1 | void set_cpu_sibling_map(int cpu)
2 | {
3 |  bool has_smt = smp_num_siblings > 1;
4 |  bool has_mp = has_smt || boot_cpu_data.x86_max_cores > 1;
5 |  struct cpuinfo_x86 *c = &(*({ do { const void *__vpp_verify = (typeof((&(cpu_info)) + 0))((void *)0); (void)__vpp_verify; } while (0); ({ unsigned long __ptr; __asm__ ("" : "=r"(__ptr) : "0"((typeof(*((&(cpu_info)))) *)((&(cpu_info))))); (typeof((typeof(*((&(cpu_info)))) *)((&(cpu_info))))) (__ptr + (((__per_cpu_offset[(cpu)])))); }); }));
6 |  struct cpuinfo_x86 *o;
7 |  int i, threads;
8 | 
9 |  cpumask_set_cpu(cpu, cpu_sibling_setup_mask);
10 | 
11 |  if (!has_mp) {
12 |   cpumask_set_cpu(cpu, ((*({ do { const void *__vpp_verify = (typeof((&(cpu_sibling_map)) + 0))((void *)0); (void)__vpp_verify; } while (0); ({ unsigned long __ptr; __asm__ ("" : "=r"(__ptr) : "0"((typeof(*((&(cpu_sibling_map)))) *)((&(cpu_sibling_map))))); (typeof((typeof(*((&(cpu_sibling_map)))) *)((&(cpu_sibling_map))))) (__ptr + (((__per_cpu_offset[(cpu)])))); }); }))));
13 |   cpumask_set_cpu(cpu, cpu_llc_shared_mask(cpu));
14 |   cpumask_set_cpu(cpu, ((*({ do { const void *__vpp_verify = (typeof((&(cpu_core_map)) + 0))((void *)0); (void)__vpp_verify; } while (0); ({ unsigned long __ptr; __asm__ ("" : "=r"(__ptr) : "0"((typeof(*((&(cpu_core_map)))) *)((&(cpu_core_map))))); (typeof((typeof(*((&(cpu_core_map)))) *)((&(cpu_core_map))))) (__ptr + (((__per_cpu_offset[(cpu)])))); }); }))));
15 |   cpumask_set_cpu(cpu, ((*({ do { const void *__vpp_verify = (typeof((&(cpu_die_map)) + 0))((void *)0); (void)__vpp_verify; } while (0); ({ unsigned long __ptr; __asm__ ("" : "=r"(__ptr) : "0"((typeof(*((&(cpu_die_map)))) *)((&(cpu_die_map))))); (typeof((typeof(*((&(cpu_die_map)))) *)((&(cpu_die_map))))) (__ptr + (((__per_cpu_offset[(cpu)])))); }); }))));
16 |   c->booted_cores = 1;
17 |   return;
18 |  }
19 | 
20 |  for ((i) = -1; (i) = cpumask_next((i), (cpu_sibling_setup_mask)), (i) < nr_cpu_ids;) {
21 |   o = &(*({ do { const void *__vpp_verify = (typeof((&(cpu_info)) + 0))((void *)0); (void)__vpp_verify; } while (0); ({ unsigned long __ptr; __asm__ ("" : "=r"(__ptr) : "0"((typeof(*((&(cpu_info)))) *)((&(cpu_info))))); (typeof((typeof(*((&(cpu_info)))) *)((&(cpu_info))))) (__ptr + (((__per_cpu_offset[(i)])))); }); }));
22 | 
23 |   if (match_pkg(c, o) && !topology_same_node(c, o))
24 |    x86_has_numa_in_package = true;
25 | 
26 |   if ((i == cpu) || (has_smt && match_smt(c, o)))
27 |    do { cpumask_set_cpu((cpu), ((*({ do { const void *__vpp_verify = (typeof((&(cpu_sibling_map)) + 0))((void *)0); (void)__vpp_verify; } while (0); ({ unsigned long __ptr; __asm__ ("" : "=r"(__ptr) : "0"((typeof(*((&(cpu_sibling_map)))) *)((&(cpu_sibling_map))))); (typeof((typeof(*((&(cpu_sibling_map)))) *)((&(cpu_sibling_map))))) (__ptr + (((__per_cpu_offset[(i)])))); }); })))); cpumask_set_cpu((i), ((*({ do { const void *__vpp_verify = (typeof((&(cpu_sibling_map)) + 0))((void *)0); (void)__vpp_verify; } while (0); ({ unsigned long __ptr; __asm__ ("" : "=r"(__ptr) : "0"((typeof(*((&(cpu_sibling_map)))) *)((&(cpu_sibling_map))))); (typeof((typeof(*((&(cpu_sibling_map)))) *)((&(cpu_sibling_map))))) (__ptr + (((__per_cpu_offset[(cpu)])))); }); })))); } while (0);
28 | 
29 |   if ((i == cpu) || (has_mp && match_llc(c, o)))
30 |    do { cpumask_set_cpu((cpu), cpu_llc_shared_mask(i)); cpumask_set_cpu((i), cpu_llc_shared_mask(cpu)); } while (0);
31 | 
32 |   if ((i == cpu) || (has_mp && match_die(c, o)))
33 |    do { cpumask_set_cpu((cpu), ((*({ do { const void *__vpp_verify = (typeof((&(cpu_die_map)) + 0))((void *)0); (void)__vpp_verify; } while (0); ({ unsigned long __ptr; __asm__ ("" : "=r"(__ptr) : "0"((typeof(*((&(cpu_die_map)))) *)((&(cpu_die_map))))); (typeof((typeof(*((&(cpu_die_map)))) *)((&(cpu_die_map))))) (__ptr + (((__per_cpu_offset[(i)])))); }); })))); cpumask_set_cpu((i), ((*({ do { const void *__vpp_verify = (typeof((&(cpu_die_map)) + 0))((void *)0); (void)__vpp_verify; } while (0); ({ unsigned long __ptr; __asm__ ("" : "=r"(__ptr) : "0"((typeof(*((&(cpu_die_map)))) *)((&(cpu_die_map))))); (typeof((typeof(*((&(cpu_die_map)))) *)((&(cpu_die_map))))) (__ptr + (((__per_cpu_offset[(cpu)])))); }); })))); } while (0);
34 |  }
35 | 
36 |  threads = cpumask_weight(((*({ do { const void *__vpp_verify = (typeof((&(cpu_sibling_map)) + 0))((void *)0); (void)__vpp_verify; } while (0); ({ unsigned long __ptr; __asm__ ("" : "=r"(__ptr) : "0"((typeof(*((&(cpu_sibling_map)))) *)((&(cpu_sibling_map))))); (typeof((typeof(*((&(cpu_sibling_map)))) *)((&(cpu_sibling_map))))) (__ptr + (((__per_cpu_offset[(cpu)])))); }); }))));
37 |  if (threads > __max_smt_threads)
38 |   __max_smt_threads = threads;
39 | 
40 | 
41 | 
42 | 
43 | 
44 |  for ((i) = -1; (i) = cpumask_next((i), (cpu_sibling_setup_mask)), (i) < nr_cpu_ids;) {
45 |   o = &(*({ do { const void *__vpp_verify = (typeof((&(cpu_info)) + 0))((void *)0); (void)__vpp_verify; } while (0); ({ unsigned long __ptr; __asm__ ("" : "=r"(__ptr) : "0"((typeof(*((&(cpu_info)))) *)((&(cpu_info))))); (typeof((typeof(*((&(cpu_info)))) *)((&(cpu_info))))) (__ptr + (((__per_cpu_offset[(i)])))); }); }));
46 | 
47 |   if ((i == cpu) || (has_mp && match_pkg(c, o))) {
48 |    do { cpumask_set_cpu((cpu), ((*({ do { const void *__vpp_verify = (typeof((&(cpu_core_map)) + 0))((void *)0); (void)__vpp_verify; } while (0); ({ unsigned long __ptr; __asm__ ("" : "=r"(__ptr) : "0"((typeof(*((&(cpu_core_map)))) *)((&(cpu_core_map))))); (typeof((typeof(*((&(cpu_core_map)))) *)((&(cpu_core_map))))) (__ptr + (((__per_cpu_offset[(i)])))); }); })))); cpumask_set_cpu((i), ((*({ do { const void *__vpp_verify = (typeof((&(cpu_core_map)) + 0))((void *)0); (void)__vpp_verify; } while (0); ({ unsigned long __ptr; __asm__ ("" : "=r"(__ptr) : "0"((typeof(*((&(cpu_core_map)))) *)((&(cpu_core_map))))); (typeof((typeof(*((&(cpu_core_map)))) *)((&(cpu_core_map))))) (__ptr + (((__per_cpu_offset[(cpu)])))); }); })))); } while (0);
49 | 
50 | 
51 | 
52 | 
53 |    if (threads == 1) {
54 | 
55 | 
56 | 
57 | 
58 |     if (cpumask_first(
59 |         ((*({ do { const void *__vpp_verify = (typeof((&(cpu_sibling_map)) + 0))((void *)0); (void)__vpp_verify; } while (0); ({ unsigned long __ptr; __asm__ ("" : "=r"(__ptr) : "0"((typeof(*((&(cpu_sibling_map)))) *)((&(cpu_sibling_map))))); (typeof((typeof(*((&(cpu_sibling_map)))) *)((&(cpu_sibling_map))))) (__ptr + (((__per_cpu_offset[(i)])))); }); })))) == i)
60 |      c->booted_cores++;
61 | 
62 | 
63 | 
64 | 
65 |     if (i != cpu)
66 |      (*({ do { const void *__vpp_verify = (typeof((&(cpu_info)) + 0))((void *)0); (void)__vpp_verify; } while (0); ({ unsigned long __ptr; __asm__ ("" : "=r"(__ptr) : "0"((typeof(*((&(cpu_info)))) *)((&(cpu_info))))); (typeof((typeof(*((&(cpu_info)))) *)((&(cpu_info))))) (__ptr + (((__per_cpu_offset[(i)])))); }); })).booted_cores++;
67 |    } else if (i != cpu && !c->booted_cores)
68 |     c->booted_cores = (*({ do { const void *__vpp_verify = (typeof((&(cpu_info)) + 0))((void *)0); (void)__vpp_verify; } while (0); ({ unsigned long __ptr; __asm__ ("" : "=r"(__ptr) : "0"((typeof(*((&(cpu_info)))) *)((&(cpu_info))))); (typeof((typeof(*((&(cpu_info)))) *)((&(cpu_info))))) (__ptr + (((__per_cpu_offset[(i)])))); }); })).booted_cores;
69 |   }
70 |  }
71 | }
```

### {"id": "D08", "profile": "old_x86", "kind": "configured_function", "function": "start_secondary", "path": "/root/.cache/linux-bug-analyze/s390-contract-20261013/runtime/old/linux/arch/x86/kernel/smpboot.c", "configuration_sha256": "a9264c98fd293799f8a3aced3642bd3bc8e5def1ed6f12884f96056695aba318", "source_identity_note": "instrumented current preprocessing; local packet lines are not original C lines"}
```c
1 | static void __attribute__((no_instrument_function)) start_secondary(void *unused)
2 | {
3 | 
4 | 
5 | 
6 | 
7 | 
8 |  cr4_init();
9 | 
10 | 
11 | 
12 | 
13 | 
14 | 
15 |  cpu_init_secondary();
16 |  rcu_cpu_starting(({ typeof(cpu_number) pscr_ret__; do { const void *__vpp_verify = (typeof((&(cpu_number)) + 0))((void *)0); (void)__vpp_verify; } while (0); switch(sizeof(cpu_number)) { case 1: pscr_ret__ = ({ u8 pfo_val__; asm volatile ("mov" "b " "%%""gs"":" "%" "[var]" ", " "%[val]" : [val] "=" "q" (pfo_val__) : [var] "m" (cpu_number)); (typeof(cpu_number))(unsigned long) pfo_val__; }); break; case 2: pscr_ret__ = ({ u16 pfo_val__; asm volatile ("mov" "w " "%%""gs"":" "%" "[var]" ", " "%[val]" : [val] "=" "r" (pfo_val__) : [var] "m" (cpu_number)); (typeof(cpu_number))(unsigned long) pfo_val__; }); break; case 4: pscr_ret__ = ({ u32 pfo_val__; asm volatile ("mov" "l " "%%""gs"":" "%" "[var]" ", " "%[val]" : [val] "=" "r" (pfo_val__) : [var] "m" (cpu_number)); (typeof(cpu_number))(unsigned long) pfo_val__; }); break; case 8: pscr_ret__ = ({ u64 pfo_val__; asm volatile ("mov" "q " "%%""gs"":" "%" "[var]" ", " "%[val]" : [val] "=" "r" (pfo_val__) : [var] "m" (cpu_number)); (typeof(cpu_number))(unsigned long) pfo_val__; }); break; default: __bad_size_call_parameter(); break; } pscr_ret__; }));
17 |  x86_cpuinit.early_percpu_clock_init();
18 |  smp_callin();
19 | 
20 |  enable_start_cpu0 = 0;
21 | 
22 | 
23 |  __asm__ __volatile__("": : :"memory");
24 | 
25 | 
26 | 
27 |  check_tsc_sync_target();
28 | 
29 |  speculative_store_bypass_ht_init();
30 | 
31 | 
32 | 
33 | 
34 | 
35 | 
36 | 
37 |  lock_vector_lock();
38 |  set_cpu_online(({ __this_cpu_preempt_check("read"); ({ typeof(cpu_number) pscr_ret__; do { const void *__vpp_verify = (typeof((&(cpu_number)) + 0))((void *)0); (void)__vpp_verify; } while (0); switch(sizeof(cpu_number)) { case 1: pscr_ret__ = ({ u8 pfo_val__; asm ("mov" "b " "%%""gs"":" "%" "[var]" ", " "%[val]" : [val] "=" "q" (pfo_val__) : [var] "m" (cpu_number)); (typeof(cpu_number))(unsigned long) pfo_val__; }); break; case 2: pscr_ret__ = ({ u16 pfo_val__; asm ("mov" "w " "%%""gs"":" "%" "[var]" ", " "%[val]" : [val] "=" "r" (pfo_val__) : [var] "m" (cpu_number)); (typeof(cpu_number))(unsigned long) pfo_val__; }); break; case 4: pscr_ret__ = ({ u32 pfo_val__; asm ("mov" "l " "%%""gs"":" "%" "[var]" ", " "%[val]" : [val] "=" "r" (pfo_val__) : [var] "m" (cpu_number)); (typeof(cpu_number))(unsigned long) pfo_val__; }); break; case 8: pscr_ret__ = ({ u64 pfo_val__; asm ("mov" "q " "%%""gs"":" "%" "[var]" ", " "%[val]" : [val] "=" "r" (pfo_val__) : [var] "m" (cpu_number)); (typeof(cpu_number))(unsigned long) pfo_val__; }); break; default: __bad_size_call_parameter(); break; } pscr_ret__; }); }), true);
39 |  lapic_online();
40 |  unlock_vector_lock();
41 |  cpu_set_state_online(({ __this_cpu_preempt_check("read"); ({ typeof(cpu_number) pscr_ret__; do { const void *__vpp_verify = (typeof((&(cpu_number)) + 0))((void *)0); (void)__vpp_verify; } while (0); switch(sizeof(cpu_number)) { case 1: pscr_ret__ = ({ u8 pfo_val__; asm ("mov" "b " "%%""gs"":" "%" "[var]" ", " "%[val]" : [val] "=" "q" (pfo_val__) : [var] "m" (cpu_number)); (typeof(cpu_number))(unsigned long) pfo_val__; }); break; case 2: pscr_ret__ = ({ u16 pfo_val__; asm ("mov" "w " "%%""gs"":" "%" "[var]" ", " "%[val]" : [val] "=" "r" (pfo_val__) : [var] "m" (cpu_number)); (typeof(cpu_number))(unsigned long) pfo_val__; }); break; case 4: pscr_ret__ = ({ u32 pfo_val__; asm ("mov" "l " "%%""gs"":" "%" "[var]" ", " "%[val]" : [val] "=" "r" (pfo_val__) : [var] "m" (cpu_number)); (typeof(cpu_number))(unsigned long) pfo_val__; }); break; case 8: pscr_ret__ = ({ u64 pfo_val__; asm ("mov" "q " "%%""gs"":" "%" "[var]" ", " "%[val]" : [val] "=" "r" (pfo_val__) : [var] "m" (cpu_number)); (typeof(cpu_number))(unsigned long) pfo_val__; }); break; default: __bad_size_call_parameter(); break; } pscr_ret__; }); }));
42 |  x86_platform.nmi_init();
43 | 
44 | 
45 |  do { arch_local_irq_enable(); } while (0);
46 | 
47 |  x86_cpuinit.setup_percpu_clockev();
48 | 
49 |  asm volatile("sfence" ::: "memory");
50 |  cpu_startup_entry(CPUHP_AP_ONLINE_IDLE);
51 | }
```

### {"id": "D09", "profile": "old_x86", "kind": "configured_function", "function": "cpu_smt_mask", "path": "/root/.cache/linux-bug-analyze/s390-contract-20261013/runtime/old/linux/include/linux/topology.h", "configuration_sha256": "a9264c98fd293799f8a3aced3642bd3bc8e5def1ed6f12884f96056695aba318", "source_identity_note": "instrumented current preprocessing; local packet lines are not original C lines"}
```c
1 | static inline __attribute__((__gnu_inline__)) __attribute__((__unused__)) __attribute__((no_instrument_function)) const struct cpumask *cpu_smt_mask(int cpu)
2 | {
3 |  return ((*({ do { const void *__vpp_verify = (typeof((&(cpu_sibling_map)) + 0))((void *)0); (void)__vpp_verify; } while (0); ({ unsigned long __ptr; __asm__ ("" : "=r"(__ptr) : "0"((typeof(*((&(cpu_sibling_map)))) *)((&(cpu_sibling_map))))); (typeof((typeof(*((&(cpu_sibling_map)))) *)((&(cpu_sibling_map))))) (__ptr + (((__per_cpu_offset[(cpu)])))); }); })));
4 | }
```

### {"id": "D10", "profile": "old_x86", "kind": "configured_function", "function": "sched_core_cpu_starting", "path": "/root/.cache/linux-bug-analyze/s390-contract-20261013/runtime/old/linux/kernel/sched/core.c", "configuration_sha256": "a9264c98fd293799f8a3aced3642bd3bc8e5def1ed6f12884f96056695aba318", "source_identity_note": "instrumented current preprocessing; local packet lines are not original C lines"}
```c
1 | static void sched_core_cpu_starting(unsigned int cpu)
2 | {
3 |  const struct cpumask *smt_mask = cpu_smt_mask(cpu);
4 |  struct rq *rq = (&(*({ do { const void *__vpp_verify = (typeof((&(runqueues)) + 0))((void *)0); (void)__vpp_verify; } while (0); ({ unsigned long __ptr; __asm__ ("" : "=r"(__ptr) : "0"((typeof(*((&(runqueues)))) *)((&(runqueues))))); (typeof((typeof(*((&(runqueues)))) *)((&(runqueues))))) (__ptr + (((__per_cpu_offset[((cpu))])))); }); }))), *core_rq = ((void *)0);
5 |  unsigned long flags;
6 |  int t;
7 | 
8 |  (*({ do { const void *__vpp_verify = (typeof((&(r4_lock_observation)) + 0))((void *)0); (void)__vpp_verify; } while (0); ({ unsigned long __ptr; __asm__ ("" : "=r"(__ptr) : "0"((typeof(*((&(r4_lock_observation)))) *)((&(r4_lock_observation))))); (typeof((typeof(*((&(r4_lock_observation)))) *)((&(r4_lock_observation))))) (__ptr + (((__per_cpu_offset[(cpu)])))); }); })).active = true;
9 |  r4_note("core_enter", cpu, 0, -1, -1, -1, 0);
10 |  sched_core_lock(cpu, &flags);
11 | 
12 |  ({ int __ret_warn_on = !!(rq->core != rq); if (__builtin_expect(!!(__ret_warn_on), 0)) do { do { } while(0); do { asm __inline volatile("1:\t" ".byte 0x0f, 0x0b" "\n" ".pushsection __bug_table,\"aw\"\n" "2:\t" ".long " "1b" " - 2b" "\t# bug_entry::bug_addr\n" "\t" ".long " "%c0" " - 2b" "\t# bug_entry::file\n" "\t.word %c1" "\t# bug_entry::line\n" "\t.word %c2" "\t# bug_entry::flags\n" "\t.org 2b+%c3\n" ".popsection" : : "i" ("kernel/sched/core.c"), "i" (5786), "i" ((1 << 0)|((1 << 1) | ((9) << 8))), "i" (sizeof(struct bug_entry))); } while (0); ({ asm volatile("492" ":\n\t" ".pushsection .discard.reachable\n\t" ".long " "492" "b - .\n\t" ".popsection\n\t"); }); do { } while(0); } while (0); __builtin_expect(!!(__ret_warn_on), 0); });
13 | 
14 | 
15 |  if (cpumask_weight(smt_mask) == 1)
16 |   goto unlock;
17 | 
18 | 
19 |  for ((t) = -1; (t) = cpumask_next((t), (smt_mask)), (t) < nr_cpu_ids;) {
20 |   if (t == cpu)
21 |    continue;
22 |   rq = (&(*({ do { const void *__vpp_verify = (typeof((&(runqueues)) + 0))((void *)0); (void)__vpp_verify; } while (0); ({ unsigned long __ptr; __asm__ ("" : "=r"(__ptr) : "0"((typeof(*((&(runqueues)))) *)((&(runqueues))))); (typeof((typeof(*((&(runqueues)))) *)((&(runqueues))))) (__ptr + (((__per_cpu_offset[((t))])))); }); })));
23 |   if (rq->core == rq) {
24 |    core_rq = rq;
25 |    break;
26 |   }
27 |  }
28 | 
29 |  if (({ int __ret_warn_on = !!(!core_rq); if (__builtin_expect(!!(__ret_warn_on), 0)) do { do { } while(0); do { asm __inline volatile("1:\t" ".byte 0x0f, 0x0b" "\n" ".pushsection __bug_table,\"aw\"\n" "2:\t" ".long " "1b" " - 2b" "\t# bug_entry::bug_addr\n" "\t" ".long " "%c0" " - 2b" "\t# bug_entry::file\n" "\t.word %c1" "\t# bug_entry::line\n" "\t.word %c2" "\t# bug_entry::flags\n" "\t.org 2b+%c3\n" ".popsection" : : "i" ("kernel/sched/core.c"), "i" (5803), "i" ((1 << 0)|((1 << 1) | ((9) << 8))), "i" (sizeof(struct bug_entry))); } while (0); ({ asm volatile("493" ":\n\t" ".pushsection .discard.reachable\n\t" ".long " "493" "b - .\n\t" ".popsection\n\t"); }); do { } while(0); } while (0); __builtin_expect(!!(__ret_warn_on), 0); }))
30 |   goto unlock;
31 | 
32 | 
33 |  for ((t) = -1; (t) = cpumask_next((t), (smt_mask)), (t) < nr_cpu_ids;) {
34 |   rq = (&(*({ do { const void *__vpp_verify = (typeof((&(runqueues)) + 0))((void *)0); (void)__vpp_verify; } while (0); ({ unsigned long __ptr; __asm__ ("" : "=r"(__ptr) : "0"((typeof(*((&(runqueues)))) *)((&(runqueues))))); (typeof((typeof(*((&(runqueues)))) *)((&(runqueues))))) (__ptr + (((__per_cpu_offset[((t))])))); }); })));
35 | 
36 |   if (t == cpu)
37 |    rq->core = core_rq;
38 | 
39 |   ({ int __ret_warn_on = !!(rq->core != core_rq); if (__builtin_expect(!!(__ret_warn_on), 0)) do { do { } while(0); do { asm __inline volatile("1:\t" ".byte 0x0f, 0x0b" "\n" ".pushsection __bug_table,\"aw\"\n" "2:\t" ".long " "1b" " - 2b" "\t# bug_entry::bug_addr\n" "\t" ".long " "%c0" " - 2b" "\t# bug_entry::file\n" "\t.word %c1" "\t# bug_entry::line\n" "\t.word %c2" "\t# bug_entry::flags\n" "\t.org 2b+%c3\n" ".popsection" : : "i" ("kernel/sched/core.c"), "i" (5813), "i" ((1 << 0)|((1 << 1) | ((9) << 8))), "i" (sizeof(struct bug_entry))); } while (0); ({ asm volatile("494" ":\n\t" ".pushsection .discard.reachable\n\t" ".long " "494" "b - .\n\t" ".popsection\n\t"); }); do { } while(0); } while (0); __builtin_expect(!!(__ret_warn_on), 0); });
40 |  }
41 | 
42 | unlock:
43 |  sched_core_unlock(cpu, &flags);
44 |  {
45 |   struct r4_lock_observation *o = &(*({ do { const void *__vpp_verify = (typeof((&(r4_lock_observation)) + 0))((void *)0); (void)__vpp_verify; } while (0); ({ unsigned long __ptr; __asm__ ("" : "=r"(__ptr) : "0"((typeof(*((&(r4_lock_observation)))) *)((&(r4_lock_observation))))); (typeof((typeof(*((&(r4_lock_observation)))) *)((&(r4_lock_observation))))) (__ptr + (((__per_cpu_offset[(cpu)])))); }); }));
46 |   o->active = false;
47 |   printk("\001" "6" "R4 phase=lock_snapshot cpu=%u current=%u seq=%u mask=%lx self=%u weight=%u locks=%u rq_self=%u online=%u printed_after_unlock=1\n", cpu, ({ typeof(cpu_number) pscr_ret__; do { const void *__vpp_verify = (typeof((&(cpu_number)) + 0))((void *)0); (void)__vpp_verify; } while (0); switch(sizeof(cpu_number)) { case 1: pscr_ret__ = ({ u8 pfo_val__; asm volatile ("mov" "b " "%%""gs"":" "%" "[var]" ", " "%[val]" : [val] "=" "q" (pfo_val__) : [var] "m" (cpu_number)); (typeof(cpu_number))(unsigned long) pfo_val__; }); break; case 2: pscr_ret__ = ({ u16 pfo_val__; asm volatile ("mov" "w " "%%""gs"":" "%" "[var]" ", " "%[val]" : [val] "=" "r" (pfo_val__) : [var] "m" (cpu_number)); (typeof(cpu_number))(unsigned long) pfo_val__; }); break; case 4: pscr_ret__ = ({ u32 pfo_val__; asm volatile ("mov" "l " "%%""gs"":" "%" "[var]" ", " "%[val]" : [val] "=" "r" (pfo_val__) : [var] "m" (cpu_number)); (typeof(cpu_number))(unsigned long) pfo_val__; }); break; case 8: pscr_ret__ = ({ u64 pfo_val__; asm volatile ("mov" "q " "%%""gs"":" "%" "[var]" ", " "%[val]" : [val] "=" "r" (pfo_val__) : [var] "m" (cpu_number)); (typeof(cpu_number))(unsigned long) pfo_val__; }); break; default: __bad_size_call_parameter(); break; } pscr_ret__; }), o->seq, o->mask, o->self, o->weight, o->count, o->rq_self, o->online)
48 |                                                                                                      ;
49 |  }
50 |  r4_note("core_exit", cpu, 0, -1, -1, -1, 0);
51 | }
```

### {"id": "D11", "profile": "old_x86", "kind": "configured_function", "function": "sched_core_lock", "path": "/root/.cache/linux-bug-analyze/s390-contract-20261013/runtime/old/linux/kernel/sched/core.c", "configuration_sha256": "a9264c98fd293799f8a3aced3642bd3bc8e5def1ed6f12884f96056695aba318", "source_identity_note": "instrumented current preprocessing; local packet lines are not original C lines"}
```c
1 | static void sched_core_lock(int cpu, unsigned long *flags)
2 | {
3 |  const struct cpumask *smt_mask = cpu_smt_mask(cpu);
4 |  int t, i = 0;
5 |  struct r4_lock_observation *o = &(*({ do { const void *__vpp_verify = (typeof((&(r4_lock_observation)) + 0))((void *)0); (void)__vpp_verify; } while (0); ({ unsigned long __ptr; __asm__ ("" : "=r"(__ptr) : "0"((typeof(*((&(r4_lock_observation)))) *)((&(r4_lock_observation))))); (typeof((typeof(*((&(r4_lock_observation)))) *)((&(r4_lock_observation))))) (__ptr + (((__per_cpu_offset[(cpu)])))); }); }));
6 | 
7 |  if (o->active) {
8 |   o->seq = r4_next_seq(cpu);
9 |   o->mask = ((smt_mask)->bits)[0];
10 |   o->self = cpumask_test_cpu(cpu, smt_mask);
11 |   o->weight = cpumask_weight(smt_mask);
12 |   o->rq_self = (&(*({ do { const void *__vpp_verify = (typeof((&(runqueues)) + 0))((void *)0); (void)__vpp_verify; } while (0); ({ unsigned long __ptr; __asm__ ("" : "=r"(__ptr) : "0"((typeof(*((&(runqueues)))) *)((&(runqueues))))); (typeof((typeof(*((&(runqueues)))) *)((&(runqueues))))) (__ptr + (((__per_cpu_offset[((cpu))])))); }); })))->core == (&(*({ do { const void *__vpp_verify = (typeof((&(runqueues)) + 0))((void *)0); (void)__vpp_verify; } while (0); ({ unsigned long __ptr; __asm__ ("" : "=r"(__ptr) : "0"((typeof(*((&(runqueues)))) *)((&(runqueues))))); (typeof((typeof(*((&(runqueues)))) *)((&(runqueues))))) (__ptr + (((__per_cpu_offset[((cpu))])))); }); })));
13 |   o->online = cpu_online(cpu);
14 |   o->count = 0;
15 |  }
16 |  do { do { ({ unsigned long __dummy; typeof(*flags) __dummy2; (void)(&__dummy == &__dummy2); 1; }); *flags = arch_local_irq_save(); } while (0); } while (0);
17 |  for ((t) = -1; (t) = cpumask_next((t), (smt_mask)), (t) < nr_cpu_ids;) {
18 |   _raw_spin_lock(((void)(i++), (&(&(*({ do { const void *__vpp_verify = (typeof((&(runqueues)) + 0))((void *)0); (void)__vpp_verify; } while (0); ({ unsigned long __ptr; __asm__ ("" : "=r"(__ptr) : "0"((typeof(*((&(runqueues)))) *)((&(runqueues))))); (typeof((typeof(*((&(runqueues)))) *)((&(runqueues))))) (__ptr + (((__per_cpu_offset[((t))])))); }); })))->__lock)));
19 |   if (o->active)
20 |    o->count++;
21 |  }
22 | }
```

### {"id": "D12", "profile": "old_x86", "kind": "configured_function", "function": "smp_callin", "path": "/root/.cache/linux-bug-analyze/s390-contract-20261013/runtime/old/linux/arch/x86/kernel/smpboot.c", "configuration_sha256": "a9264c98fd293799f8a3aced3642bd3bc8e5def1ed6f12884f96056695aba318", "source_identity_note": "instrumented current preprocessing; local packet lines are not original C lines"}
```c
1 | static void smp_callin(void)
2 | {
3 |  int cpuid;
4 | 
5 | 
6 | 
7 | 
8 | 
9 | 
10 | 
11 |  cpuid = ({ __this_cpu_preempt_check("read"); ({ typeof(cpu_number) pscr_ret__; do { const void *__vpp_verify = (typeof((&(cpu_number)) + 0))((void *)0); (void)__vpp_verify; } while (0); switch(sizeof(cpu_number)) { case 1: pscr_ret__ = ({ u8 pfo_val__; asm ("mov" "b " "%%""gs"":" "%" "[var]" ", " "%[val]" : [val] "=" "q" (pfo_val__) : [var] "m" (cpu_number)); (typeof(cpu_number))(unsigned long) pfo_val__; }); break; case 2: pscr_ret__ = ({ u16 pfo_val__; asm ("mov" "w " "%%""gs"":" "%" "[var]" ", " "%[val]" : [val] "=" "r" (pfo_val__) : [var] "m" (cpu_number)); (typeof(cpu_number))(unsigned long) pfo_val__; }); break; case 4: pscr_ret__ = ({ u32 pfo_val__; asm ("mov" "l " "%%""gs"":" "%" "[var]" ", " "%[val]" : [val] "=" "r" (pfo_val__) : [var] "m" (cpu_number)); (typeof(cpu_number))(unsigned long) pfo_val__; }); break; case 8: pscr_ret__ = ({ u64 pfo_val__; asm ("mov" "q " "%%""gs"":" "%" "[var]" ", " "%[val]" : [val] "=" "r" (pfo_val__) : [var] "m" (cpu_number)); (typeof(cpu_number))(unsigned long) pfo_val__; }); break; default: __bad_size_call_parameter(); break; } pscr_ret__; }); });
12 | 
13 | 
14 | 
15 | 
16 | 
17 | 
18 | 
19 |  apic_ap_setup();
20 | 
21 | 
22 | 
23 | 
24 | 
25 |  smp_store_cpu_info(cpuid);
26 | 
27 | 
28 | 
29 | 
30 | 
31 |  set_cpu_sibling_map(({ typeof(cpu_number) pscr_ret__; do { const void *__vpp_verify = (typeof((&(cpu_number)) + 0))((void *)0); (void)__vpp_verify; } while (0); switch(sizeof(cpu_number)) { case 1: pscr_ret__ = ({ u8 pfo_val__; asm volatile ("mov" "b " "%%""gs"":" "%" "[var]" ", " "%[val]" : [val] "=" "q" (pfo_val__) : [var] "m" (cpu_number)); (typeof(cpu_number))(unsigned long) pfo_val__; }); break; case 2: pscr_ret__ = ({ u16 pfo_val__; asm volatile ("mov" "w " "%%""gs"":" "%" "[var]" ", " "%[val]" : [val] "=" "r" (pfo_val__) : [var] "m" (cpu_number)); (typeof(cpu_number))(unsigned long) pfo_val__; }); break; case 4: pscr_ret__ = ({ u32 pfo_val__; asm volatile ("mov" "l " "%%""gs"":" "%" "[var]" ", " "%[val]" : [val] "=" "r" (pfo_val__) : [var] "m" (cpu_number)); (typeof(cpu_number))(unsigned long) pfo_val__; }); break; case 8: pscr_ret__ = ({ u64 pfo_val__; asm volatile ("mov" "q " "%%""gs"":" "%" "[var]" ", " "%[val]" : [val] "=" "r" (pfo_val__) : [var] "m" (cpu_number)); (typeof(cpu_number))(unsigned long) pfo_val__; }); break; default: __bad_size_call_parameter(); break; } pscr_ret__; }));
32 | 
33 |  init_freq_invariance(true, false);
34 | 
35 | 
36 | 
37 | 
38 | 
39 | 
40 | 
41 |  calibrate_delay();
42 |  (*({ do { const void *__vpp_verify = (typeof((&(cpu_info)) + 0))((void *)0); (void)__vpp_verify; } while (0); ({ unsigned long __ptr; __asm__ ("" : "=r"(__ptr) : "0"((typeof(*((&(cpu_info)))) *)((&(cpu_info))))); (typeof((typeof(*((&(cpu_info)))) *)((&(cpu_info))))) (__ptr + (((__per_cpu_offset[(cpuid)])))); }); })).loops_per_jiffy = loops_per_jiffy;
43 |  ({ if (0) printk("\001" "7" "smpboot" ": " "Stack at about %p\n", &cpuid); 0; });
44 | 
45 |  asm volatile("sfence" ::: "memory");
46 | 
47 |  r4_note("arch_before_notify", cpuid, 1, cpumask_test_cpu(cpuid, cpu_sibling_setup_mask), -1, -1, 0);
48 |  notify_cpu_starting(cpuid);
49 |  r4_note("arch_after_notify", cpuid, 1, cpumask_test_cpu(cpuid, cpu_sibling_setup_mask), -1, -1, 0);
50 | 
51 | 
52 | 
53 | 
54 |  cpumask_set_cpu(cpuid, cpu_callin_mask);
55 | }
```

### {"id": "D13", "profile": "old_s390", "kind": "selected_config_facts", "function": null, "path": "experiments/case_taxonomy/s390_arch_contract_20261013/runtime/profiles/old_s390/kernel.config", "configuration_sha256": "ba935721b43a3187db05c24b74f5694180be0e816368efbc0155a507ace1f11e", "source_identity_note": "only selected explicit config records; missing keys are unknown"}
```c
1 | CONFIG_SCHED_CORE=y
2 | CONFIG_S390=y
3 | CONFIG_64BIT=y
4 | CONFIG_SMP=y
5 | CONFIG_NR_CPUS=4
6 | CONFIG_HOTPLUG_CPU=y
7 | CONFIG_SCHED_SMT=y
8 | CONFIG_SCHED_TOPOLOGY=y
9 | CONFIG_SYSFS=y
```

### {"id": "D14", "profile": "old_x86", "kind": "selected_config_facts", "function": null, "path": "experiments/case_taxonomy/s390_arch_contract_20261013/runtime/profiles/old_x86/kernel.config", "configuration_sha256": "a9264c98fd293799f8a3aced3642bd3bc8e5def1ed6f12884f96056695aba318", "source_identity_note": "only selected explicit config records; missing keys are unknown"}
```c
1 | CONFIG_SCHED_CORE=y
2 | CONFIG_64BIT=y
3 | CONFIG_X86_64=y
4 | CONFIG_SMP=y
5 | CONFIG_NR_CPUS=4
6 | CONFIG_SCHED_SMT=y
7 | CONFIG_HOTPLUG_CPU=y
8 | CONFIG_SYSFS=y
```
