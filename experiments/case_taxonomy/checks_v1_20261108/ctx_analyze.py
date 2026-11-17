"""Check 3-1 (execution context), criteria.md sections 3-4 and amendment 1.

    python3 ctx_analyze.py <cache_dir> <entry_S> <out_json>

Reads the per-unit IR written by ctx_extract.py, computes may_sleep / may_ipi / may_rt_lock closures on the direct
call graph, runs a structured may-dataflow of (irq, raw, spin, preempt) states inside every function, propagates
entry states (trap entries, IPI/stop_machine callbacks, callers) to a fixpoint, and reports S/I/R flags.
"""
import gzip
import json
import re
import sys
from collections import defaultdict, deque
from pathlib import Path

CAP = 2
ZERO = (0, 0, 0, 0, 0)
IRQ, RAW, SPIN, PRE, SIRQ = range(5)  # SIRQ: irqs disabled by a spinlock_t _irq/_irqsave form (amendment 1, item 7)
IRQ_ENTRY = (1, 0, 0, 0, 0)

# ---------------------------------------------------------------- primitive tables (criteria 3.2, amendment 1)
IRQ_OFF = {"arch_local_irq_disable", "arch_local_irq_save", "local_irq_disable", "local_irq_save",
           "raw_local_irq_disable", "raw_local_irq_save"}
IRQ_ON = {"arch_local_irq_enable", "arch_local_irq_restore", "local_irq_enable", "local_irq_restore",
          "raw_local_irq_enable", "raw_local_irq_restore"}
RAW_LOCK = re.compile(r"^(_raw_spin_lock|__raw_spin_lock|raw_spin_lock|do_raw_spin_lock|arch_spin_lock)(_irq|_irqsave|_bh|_nested|_irqsave_nested|_nest_lock)?$")
RAW_TRY = re.compile(r"^(_raw_spin_trylock|__raw_spin_trylock|raw_spin_trylock|do_raw_spin_trylock|arch_spin_trylock)(_irq|_irqsave|_bh)?$")
RAW_UNLOCK = re.compile(r"^(_raw_spin_unlock|__raw_spin_unlock|raw_spin_unlock|do_raw_spin_unlock|arch_spin_unlock)(_irq|_irqrestore|_bh)?$")
SPIN_LOCK = re.compile(r"^(spin_lock|read_lock|write_lock|_raw_read_lock|_raw_write_lock|__raw_read_lock|__raw_write_lock|rt_spin_lock)(_irq|_irqsave|_bh|_nested|_irqsave_nested|_nest_lock)?$")
SPIN_TRY = re.compile(r"^(spin_trylock|read_trylock|write_trylock|_raw_read_trylock|_raw_write_trylock)(_irq|_irqsave|_bh)?$")
SPIN_UNLOCK = re.compile(r"^(spin_unlock|read_unlock|write_unlock|_raw_read_unlock|_raw_write_unlock|__raw_read_unlock|__raw_write_unlock|rt_spin_unlock)(_irq|_irqrestore|_bh)?$")
PRE_INC = {"__preempt_count_add", "preempt_count_add", "__preempt_count_inc", "__local_bh_disable_ip", "local_bh_disable"}
PRE_DEC = {"__preempt_count_sub", "preempt_count_sub", "__preempt_count_dec", "__preempt_count_dec_and_test",
           "__local_bh_enable_ip", "_local_bh_enable", "local_bh_enable"}

SLEEP = re.compile(r"^(__might_sleep|__might_resched|might_fault|__might_fault|schedule|schedule_timeout\w*"
                   r"|schedule_hrtimeout\w*|io_schedule\w*|schedule_preempt_disabled|mutex_lock\w*|down|down_read\w*"
                   r"|down_write\w*|down_interruptible|down_killable|msleep\w*|usleep_range\w*|wait_for_completion\w*"
                   r"|synchronize_rcu\w*|flush_work|cancel_work_sync|vmalloc|vzalloc|copy_from_user|copy_to_user"
                   r"|_copy_from_user|_copy_to_user|get_user|put_user|cond_resched)$")
ALLOC = re.compile(r"^(kmalloc\w*|kzalloc\w*|__get_free_pages|alloc_pages\w*)$")
IPI = re.compile(r"^(smp_call_function\w*|on_each_cpu\w*)$")
CALLBACK_USERS = re.compile(r"^(smp_call_function\w*|on_each_cpu\w*|stop_machine\w*|stop_one_cpu\w*)$")
NO_DESCEND = re.compile(r"^(pr_|printk|dev_|WARN|BUG|panic|dump_stack|trace_|lockdep_|kasan_|kcsan_|kmsan_)")
NO_SLEEP_PROPAGATE = {"might_alloc"}  # amendment 1, item 6: gfp-conditional sleep is judged at the allocation call


def is_trylock(name):
    return "trylock" in name


def is_sleep_prim(name, flags):
    if is_trylock(name):
        return False
    return bool(SLEEP.match(name)) or ("g" in flags and bool(ALLOC.match(name)))


def is_rt_prim(name, flags):
    if is_trylock(name):
        return False
    return bool(SPIN_LOCK.match(name)) or ("s" in flags and RAW_LOCK.match(name) is not None)


def is_primitive(name):
    return (name in IRQ_OFF or name in IRQ_ON or name in PRE_INC or name in PRE_DEC or RAW_LOCK.match(name)
            or RAW_TRY.match(name) or RAW_UNLOCK.match(name) or SPIN_LOCK.match(name) or SPIN_TRY.match(name)
            or SPIN_UNLOCK.match(name))


def is_opaque(name):
    """amendment 3: criteria 3.3 -- primitive functions (3.2, including the sleep and IPI seeds) and NO_DESCEND names
    are not expanded: their bodies give no property, receive no entry state and produce no flag of their own."""
    return bool(is_primitive(name) or SLEEP.match(name) or IPI.match(name) or NO_DESCEND.match(name))


def bump(s, i, d):
    v = list(s)
    v[i] = max(0, min(CAP, v[i] + d))
    return tuple(v)


def transfer(name, flags, s):
    """States after a call to `name`, from state s. Returns a list of states."""
    irqs = name.endswith(("_irq", "_irqsave", "_irqsave_nested"))
    irqr = name.endswith(("_irq", "_irqrestore"))
    bh = name.endswith("_bh")
    if name in IRQ_OFF:
        return [bump(s, IRQ, 1)]
    if name in IRQ_ON:
        return [bump(s, IRQ, -1)]
    if name in PRE_INC:
        return [bump(s, PRE, 1)]
    if name in PRE_DEC:
        return [bump(s, PRE, -1)]
    spinish = SPIN_LOCK.match(name) or ("s" in flags and RAW_LOCK.match(name))
    if spinish:
        t = bump(s, SPIN, 1)
        t = bump(t, SIRQ, 1) if irqs else t
        return [bump(t, PRE, 1) if bh else t]
    if RAW_LOCK.match(name):
        t = bump(s, RAW, 1)
        t = bump(t, IRQ, 1) if irqs else t
        return [bump(t, PRE, 1) if bh else t]
    if SPIN_TRY.match(name) or RAW_TRY.match(name):
        spin = SPIN_TRY.match(name) is not None
        t = bump(s, SPIN if spin else RAW, 1)
        t = bump(t, SIRQ if spin else IRQ, 1) if irqs else t
        return [s, t]
    if SPIN_UNLOCK.match(name) or ("s" in flags and RAW_UNLOCK.match(name)):
        t = bump(s, SPIN, -1)
        t = bump(t, SIRQ, -1) if irqr else t
        return [bump(t, PRE, -1) if bh else t]
    if RAW_UNLOCK.match(name):
        t = bump(s, RAW, -1)
        t = bump(t, IRQ, -1) if irqr else t
        return [bump(t, PRE, -1) if bh else t]
    return [s]


def atomic(s):
    return any(s)


def hard_ipi(s):
    return s[IRQ] > 0 or s[RAW] > 0 or s[SIRQ] > 0


def hard_rt(s):
    return s[IRQ] > 0 or s[RAW] > 0


# ---------------------------------------------------------------- loading
def load(cache):
    funcs, units, status = {}, 0, defaultdict(int)
    for path in sorted((Path(cache) / "units").glob("*.json.gz")):
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            d = json.load(fh)
        units += 1
        status["error" if "error" in d else ("fatal" if d.get("fatal") else "ok")] += 1
        for f in d.get("functions", []):
            funcs.setdefault(f["usr"], f)
    return funcs, units, dict(status)


def calls_of(node, out):
    t = node[0]
    if t == "call":
        out.append(node)
    elif t == "seq":
        for n in node[1]:
            calls_of(n, out)
    elif t == "if":
        for n in node[1:]:
            calls_of(n, out)
    elif t in ("loop",):
        calls_of(node[1], out)
    elif t == "switch":
        calls_of(node[1], out)
        calls_of(node[2], out)
    elif t == "ret":
        calls_of(node[1], out)
    elif t == "label":
        calls_of(node[2], out)
    return out


def count(node, kinds):
    t = node[0]
    kinds[t] += 1  # amendment 2, item 2: the old "if t in kinds" never counted (kinds starts empty)
    for x in node[1:]:
        if isinstance(x, list) and x and isinstance(x[0], str):
            count(x, kinds)
        elif isinstance(x, list):
            for y in x:
                if isinstance(y, list) and y and isinstance(y[0], str):
                    count(y, kinds)


# ---------------------------------------------------------------- intraprocedural dataflow
class Flow:
    """Structured may-analysis of one function body from a set of entry states."""

    def __init__(self, init_fn):
        self.init_fn = init_fn
        self.sites = defaultdict(set)   # (file, line, col, callee_usr) -> pre-states
        self.labels = defaultdict(set)
        self.changed = False

    def run(self, ir, entry):
        for _ in range(10):
            self.changed = False
            self.sites.clear()
            self.walk(ir, frozenset(entry), None)
            if not self.changed:
                break
        return self.sites

    def walk(self, n, S, sw):
        """Returns (out, brk, cont) state sets; return statements end paths."""
        t = n[0]
        E = frozenset()
        if not S and t not in ("label", "case"):
            return E, E, E
        if t == "seq":
            brk = cont = E
            for x in n[1]:
                S, b, c = self.walk(x, S, sw)
                brk |= b
                cont |= c
            return S, brk, cont
        if t == "call":
            _, name, usr, f, line, col, flags, cbs = n
            self.sites[(f, line, col, usr, name, flags)] |= S
            if self.init_fn:
                return S, E, E
            out = set()
            for s in S:
                out.update(transfer(name, flags, s))
            return frozenset(out), E, E
        if t in ("icall", "asm"):
            return S, E, E
        if t == "if":
            c, b0, k0 = self.walk(n[1], S, sw)
            a, b1, k1 = self.walk(n[2], c, sw)
            o, b2, k2 = self.walk(n[3], c, sw)
            return a | o, b0 | b1 | b2, k0 | k1 | k2
        if t == "loop":
            head = S
            out = brk = E
            for _ in range(20):
                o, b, k = self.walk(n[1], head, None)
                nh = head | o | k
                brk |= b
                out = o
                if nh == head:
                    break
                head = nh
            return S | head | brk, E, E
        if t == "switch":
            c, b0, k0 = self.walk(n[1], S, sw)
            o, b, k = self.walk(n[2], c, c)
            return o | b | c, b0, k0 | k
        if t == "case":
            return S | (sw or E), E, E
        if t == "ret":
            self.walk(n[1], S, sw)
            return E, E, E
        if t == "break":
            return E, S, E
        if t == "continue":
            return E, E, S
        if t == "goto":
            if not S <= self.labels[n[1]]:
                self.labels[n[1]] |= S
                self.changed = True
            return E, E, E
        if t == "label":
            return self.walk(n[2], S | self.labels[n[1]], sw)
        return S, E, E


# ---------------------------------------------------------------- whole program
def closures(funcs):
    """may_sleep / may_ipi / may_rt_lock with one shortest witness chain each."""
    callers = defaultdict(set)
    seeds = {"sleep": {}, "ipi": {}, "rt": {}}
    for usr, f in funcs.items():
        if is_opaque(f["name"]):
            continue  # amendment 3
        for c in calls_of(f["ir"], []):
            _, name, cusr, _, line, _, flags, _ = c
            if is_sleep_prim(name, flags):
                seeds["sleep"].setdefault(usr, [name])
            if IPI.match(name):
                seeds["ipi"].setdefault(usr, [name])
            if is_rt_prim(name, flags):
                seeds["rt"].setdefault(usr, [name])
            if cusr in funcs and not is_opaque(name):
                callers[cusr].add(usr)
    result = {}
    for prop, seed in seeds.items():
        chain = {u: [funcs[u]["name"]] + w for u, w in seed.items()}
        q = deque(seed)
        while q:
            u = q.popleft()
            if prop == "sleep" and funcs[u]["name"] in NO_SLEEP_PROPAGATE:
                continue
            for c in callers[u]:
                if c not in chain:
                    chain[c] = [funcs[c]["name"]] + chain[u]
                    q.append(c)
        if prop == "sleep":
            for u in [u for u in chain if funcs[u]["name"] in NO_SLEEP_PROPAGATE]:
                del chain[u]
        result[prop] = chain
    return result, callers


def entry_seeds(funcs, entry_s_text):
    """criteria 3.4 (a): externally linked C functions named in entry.S; (b): callbacks passed by name."""
    text = re.sub(r"/\*.*?\*/", " ", entry_s_text, flags=re.S)
    text = re.sub(r"//[^\n]*", " ", text)
    words = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text))
    trap = {u for u, f in funcs.items() if f["name"] in words and u.startswith("c:@F@")}
    cb = set()
    for f in funcs.values():
        for c in calls_of(f["ir"], []):
            if CALLBACK_USERS.match(c[1]):
                cb.update(x for x in c[7] if x in funcs)
    return trap, cb


def analyse(funcs, entry_s_text):
    clos, callers = closures(funcs)
    trap, cb = entry_seeds(funcs, entry_s_text)
    entry = defaultdict(set)
    for u in funcs:
        if is_opaque(funcs[u]["name"]):
            continue  # amendment 3: bodies of opaque functions are not analysed
        if u in trap or u in cb:
            entry[u].add(IRQ_ENTRY)
        if not callers.get(u) and u not in trap:
            entry[u].add(ZERO)
    done = defaultdict(set)          # usr -> entry states already analysed
    site_states = defaultdict(set)   # (caller_usr, site) -> states
    work = deque(u for u in funcs if entry[u])
    queued = set(work)
    while work:
        u = work.popleft()
        queued.discard(u)
        new = entry[u] - done[u]
        if not new:
            continue
        done[u] |= new
        f = funcs[u]
        sites = Flow(f["init"]).run(f["ir"], new)
        for site, S in sites.items():
            site_states[(u, site)] |= S
            cusr, name = site[3], site[4]
            if cusr in funcs and not is_opaque(name):
                if not S <= entry[cusr]:
                    entry[cusr] |= S
                    if cusr not in queued:
                        work.append(cusr)
                        queued.add(cusr)
    return clos, callers, trap, cb, entry, site_states


def flags_of(funcs, clos, entry, site_states):
    out = []
    for (u, site), S in site_states.items():
        if funcs[u]["name"] in NO_SLEEP_PROPAGATE:
            continue  # amendment 1, item 6: the gfp-conditional might_sleep inside might_alloc is not a site
        f, line, col, cusr, name, cflags = site
        kinds = []
        # the flagged callee property: either the callee is a primitive of that kind, or the closure holds it
        opaque = is_opaque(name)  # amendment 3: an opaque callee only carries its own primitive kind
        sleep_w = [name] if is_sleep_prim(name, cflags) else (None if opaque else clos["sleep"].get(cusr))
        ipi_w = [name] if IPI.match(name) else (None if opaque else clos["ipi"].get(cusr))
        rt_w = [name] if is_rt_prim(name, cflags) else (None if opaque else clos["rt"].get(cusr))
        if sleep_w and any(atomic(s) for s in S):
            kinds.append(("S", sleep_w, sorted(s for s in S if atomic(s))))
        if ipi_w and any(hard_ipi(s) for s in S):
            kinds.append(("I", ipi_w, sorted(s for s in S if hard_ipi(s))))
        if rt_w and any(hard_rt(s) for s in S):
            kinds.append(("R", rt_w, sorted(s for s in S if hard_rt(s))))
        for k, w, states in kinds:
            local = any(atomic(s) for s in Flow(funcs[u]["init"]).run(funcs[u]["ir"], {ZERO}).get(site, ()))
            out.append({"kind": k, "caller": funcs[u]["name"], "caller_usr": u, "caller_file": funcs[u]["file"],
                        "site": [f, line, col], "callee": name, "witness": w[:8], "states": states,
                        "origin": "local" if local else "entry", "caller_entry": sorted(entry[u])})
    return out


def main():
    cache, entry_s, out = sys.argv[1], sys.argv[2], sys.argv[3]
    funcs, units, status = load(cache)
    text = Path(entry_s).read_text(errors="replace")
    clos, callers, trap, cb, entry, site_states = analyse(funcs, text)
    flags = flags_of(funcs, clos, entry, site_states)
    # entry-origin chains: walk back over call sites that reach the caller in an atomic state
    rev = defaultdict(list)
    for (u, site), S in site_states.items():
        rev[site[3]].append((u, site, S))
    for fl in flags:
        if fl["origin"] != "entry":
            continue
        chain, cur, seen = [], fl["caller_usr"], {fl["caller_usr"]}
        for _ in range(8):
            if cur in trap:
                chain.append(["<trap entry>", "arch/riscv/kernel/entry.S", 0])
                break
            if cur in cb:
                chain.append(["<IPI/stop_machine callback>", "", 0])
                break
            step = next(((u, site) for u, site, S in rev.get(cur, ()) if any(atomic(s) for s in S) and u not in seen), None)
            if step is None:
                break
            u, site = step
            chain.append([funcs[u]["name"], site[0], site[1]])
            seen.add(u)
            cur = u
        fl["origin_chain"] = chain
    kinds = defaultdict(int)
    for f in funcs.values():
        count(f["ir"], kinds)
    distinct = {(fl["kind"], tuple(fl["site"][:2])) for fl in flags}
    summary = {
        "units": units, "unit_status": status, "functions": len(funcs),
        "trap_entries": sorted(funcs[u]["name"] for u in trap), "callbacks": len(cb),
        "may_sleep": len(clos["sleep"]), "may_ipi": len(clos["ipi"]), "may_rt_lock": len(clos["rt"]),
        "indirect_calls": kinds.get("icall", 0), "inline_asm": kinds.get("asm", 0),
        "flags": len(flags), "distinct_sites": len(distinct),
        "by_kind": {k: sum(1 for f in flags if f["kind"] == k) for k in "SIR"},
        "by_origin": {o: sum(1 for f in flags if f["origin"] == o) for o in ("local", "entry")},
    }
    Path(out).write_text(json.dumps({"summary": summary, "flags": flags}, ensure_ascii=False, indent=1))
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
