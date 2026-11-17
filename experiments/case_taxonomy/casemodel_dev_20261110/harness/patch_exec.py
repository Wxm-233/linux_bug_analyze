"""Patch the round-1 executor copy into sh_init2.c (casemodel criteria 三). Run once:  python patch_exec.py sh_init2.c
Each replacement must find its anchor exactly once, otherwise the script stops without writing."""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()


def rep(old, new):
    global s
    if s.count(old) != 1:
        raise SystemExit("ANCHOR count %d:\n%s" % (s.count(old), old[:300]))
    s = s.replace(old, new)


rep('/* 同一份 64 位小端源码用于三个架构；仅在 QEMU 的 initramfs 中运行。 */',
    '/* 同一份 64 位小端源码用于三个架构；仅在 QEMU 的 initramfs 中运行。\n'
    ' * 版本 2（casemodel_dev_20261110，Claude 扩展）：结构化缓冲区 t:<k>（用例行 " | " 之后定义）、资源 x:<名>、\n'
    ' * 新 fd 种类；每个用例后清理 SysV IPC 与消息队列。原有记号的含义与输出不变。 */')
rep('#include <sys/eventfd.h>\n',
    '#include <sys/eventfd.h>\n#include <sys/epoll.h>\n#include <sys/timerfd.h>\n#include <sys/signalfd.h>\n'
    '#include <sys/inotify.h>\n#include <sys/ipc.h>\n#include <sys/msg.h>\n#include <sys/sem.h>\n#include <sys/shm.h>\n'
    '#include <mqueue.h>\n#include <linux/perf_event.h>\n')
rep('enum kind { INTEGER, BUFFER, OR_BUFFER, FD, PATH, SELF };',
    'enum kind { INTEGER, BUFFER, OR_BUFFER, FD, PATH, SELF, STRUCTBUF, RES };')
rep('''	F_EVENTFD, F_MEMFD, F_UDP, F_NEG, F_UNOPEN, F_ATCWD, F_PIPEBLOCKRD };
static const char *const fd_names[] = { "file", "dir", "piperd", "pipewr", "ustream",
	"udgram", "eventfd", "memfd", "udp", "neg", "unopen", "atcwd", "pipeblockrd" };''',
    '''	F_EVENTFD, F_MEMFD, F_UDP, F_NEG, F_UNOPEN, F_ATCWD, F_PIPEBLOCKRD,
	F_EPOLL, F_TIMERFD, F_SIGNALFD, F_INOTIFY, F_PIDFD, F_PERFSW, F_MQ };
static const char *const fd_names[] = { "file", "dir", "piperd", "pipewr", "ustream",
	"udgram", "eventfd", "memfd", "udp", "neg", "unopen", "atcwd", "pipeblockrd",
	"epoll", "timerfd", "signalfd", "inotify", "pidfd", "perfsw", "mq" };
enum res_kind { R_MSQ, R_SEM, R_SHM, R_TIMER, R_AIO };
static const char *const res_names[] = { "msq", "sem", "shm", "timer", "aio" };
#define MAXSB 16
#define MAXW 48''')
rep('''struct test_case {
	uint64_t id;
	long nr;
	enum template tmpl;
	int ai, li;
	struct token a[6];
};''', '''struct swrite { uint32_t off; int width; char kind; uint64_t val; };
struct sdef { size_t size; char fill; int off; int nw; struct swrite w[MAXW]; };
struct test_case {
	uint64_t id;
	long nr;
	enum template tmpl;
	int ai, li;
	struct token a[6];
	int nsd;
	struct sdef sd[MAXSB];
};''')
rep('''struct result {
	uint32_t magic;
	char r[64];
	struct delta b[6], pool;
};''', '''struct result {
	uint32_t magic;
	char r[64];
	struct delta b[6], pool, sb[MAXSB];
};''')
rep('''struct memory {
	unsigned char *b[6], *snap[6], *pool, *pool_snap;
	unsigned long args[6];
};''', '''struct memory {
	unsigned char *b[6], *snap[6], *pool, *pool_snap;
	unsigned char *sbase[MAXSB], *ssnap[MAXSB];
	unsigned long args[6];
};''')
rep('''	case 's':
		t->kind = SELF;
		return strcmp(s + 2, "self") ? -1 : 0;''', '''	case 's':
		t->kind = SELF;
		return strcmp(s + 2, "self") ? -1 : 0;
	case 't':
		t->kind = STRUCTBUF;
		if (uint_value(s + 2, 10, &n) || n >= MAXSB)
			return -1;
		t->sub = (int)n;
		return 0;
	case 'x':
		t->kind = RES;
		t->sub = name_index(s + 2, res_names, sizeof(res_names) / sizeof(res_names[0]));
		return t->sub < 0 ? -1 : 0;''')
rep('''static int parse_case(char *line, struct test_case *c)
{
	char *v[10], *save, *p, *end;
	int n = 0;
	memset(c, 0, sizeof(*c));''', '''/* 结构化缓冲区定义：k:size:fill:off[:offset/width/val]*，多个定义以 ';' 分隔；
 * val 为 i<hex>（整数）、t<j>（缓冲区 j 的地址）、l<j>（缓冲区 j 的长度 size）。 */
static int parse_sdefs(char *s, struct test_case *c)
{
	char *save1, *d;
	for (d = strtok_r(s, ";", &save1); d; d = strtok_r(NULL, ";", &save1)) {
		char *save2, *f;
		uint64_t k, v;
		while (*d == ' ')
			d++;
		if (!*d || *d == '\\n' || *d == '\\r')
			continue;
		f = strtok_r(d, ":", &save2);
		if (!f || uint_value(f, 10, &k) || k >= MAXSB)
			return -1;
		struct sdef *sd = &c->sd[k];
		if (!(f = strtok_r(NULL, ":", &save2)) || uint_value(f, 10, &v) || v == 0 || v > (1u << 20))
			return -1;
		sd->size = v;
		if (!(f = strtok_r(NULL, ":", &save2)) || (*f != 'z' && *f != 'a'))
			return -1;
		sd->fill = *f;
		if (!(f = strtok_r(NULL, ":\\r\\n", &save2)) || uint_value(f, 10, &v) || v > 4095)
			return -1;
		sd->off = (int)v;
		while ((f = strtok_r(NULL, ":\\r\\n", &save2))) {
			char *a = strchr(f, '/'), *b = a ? strchr(a + 1, '/') : NULL;
			uint64_t off, w;
			if (!a || !b || sd->nw >= MAXW)
				return -1;
			*a = 0;
			*b = 0;
			if (uint_value(f, 10, &off) || uint_value(a + 1, 10, &w) ||
			    !(w == 1 || w == 2 || w == 4 || w == 8) || off + w > sd->size)
				return -1;
			struct swrite *x = &sd->w[sd->nw++];
			x->off = (uint32_t)off;
			x->width = (int)w;
			x->kind = b[1];
			if ((x->kind != 'i' && x->kind != 't' && x->kind != 'l') ||
			    uint_value(b + 2, x->kind == 'i' ? 16 : 10, &x->val) || (x->kind != 'i' && x->val >= MAXSB))
				return -1;
		}
		if ((int)k + 1 > c->nsd)
			c->nsd = (int)k + 1;
	}
	for (int k = 0; k < c->nsd; k++)
		for (int j = 0; j < c->sd[k].nw; j++)
			if (c->sd[k].w[j].kind != 'i' && !c->sd[c->sd[k].w[j].val].size)
				return -1;
	return 0;
}

static int parse_case(char *line, struct test_case *c)
{
	char *v[10], *save, *p, *end;
	int n = 0;
	memset(c, 0, sizeof(*c));
	char *bar = strstr(line, " | ");
	if (bar) {
		*bar = 0;
		if (parse_sdefs(bar + 3, c))
			return -1;
	}''')
rep('''	case F_NEG: return -1;
	case F_UNOPEN: return 1000;
	case F_ATCWD: return AT_FDCWD;''', '''	case F_NEG: return -1;
	case F_UNOPEN: return 1000;
	case F_ATCWD: return AT_FDCWD;
	case F_EPOLL: {
		struct epoll_event ev = { .events = EPOLLIN };
		fd = epoll_create1(0);
		if (fd < 0 || pipe2(p, O_NONBLOCK))
			return -1;
		ev.data.fd = p[0];
		return epoll_ctl(fd, EPOLL_CTL_ADD, p[0], &ev) ? -1 : fd;
	}
	case F_TIMERFD: return timerfd_create(CLOCK_MONOTONIC, TFD_NONBLOCK);
	case F_SIGNALFD: {
		sigset_t set;
		sigemptyset(&set);
		sigaddset(&set, SIGUSR1);
		return signalfd(-1, &set, SFD_NONBLOCK);
	}
	case F_INOTIFY:
		fd = inotify_init1(IN_NONBLOCK);
		if (fd >= 0 && inotify_add_watch(fd, "/tmp", IN_ALL_EVENTS) < 0)
			return -1;
		return fd;
	case F_PIDFD: return (int)syscall(SYS_pidfd_open, getpid(), 0);
	case F_PERFSW: {
		struct perf_event_attr pa;
		memset(&pa, 0, sizeof(pa));
		pa.type = PERF_TYPE_SOFTWARE;
		pa.size = sizeof(pa);
		pa.config = PERF_COUNT_SW_CPU_CLOCK;
		pa.disabled = 1;
		return (int)syscall(SYS_perf_event_open, &pa, 0, -1, -1, 0);
	}
	case F_MQ: return (int)mq_open("/shq", O_RDWR | O_CREAT | O_NONBLOCK, 0600, NULL);''')
rep('''static int16_t slot_of(uint64_t word, const unsigned char *pool)''', '''static int make_res(int kind, unsigned long *out)
{
	long r;
	switch (kind) {
	case R_MSQ: r = msgget(IPC_PRIVATE, IPC_CREAT | 0600); break;
	case R_SEM: r = semget(IPC_PRIVATE, 1, IPC_CREAT | 0600); break;
	case R_SHM: r = shmget(IPC_PRIVATE, 4096, IPC_CREAT | 0600); break;
	case R_TIMER: {
		int tid = -1;
		r = syscall(SYS_timer_create, CLOCK_MONOTONIC, NULL, &tid);
		if (r == 0)
			r = tid;
		break;
	}
	case R_AIO: {
		unsigned long ctx = 0;
		r = syscall(SYS_io_setup, 8, &ctx);
		if (r == 0) {
			*out = ctx;
			return 0;
		}
		break;
	}
	default: errno = EINVAL; return -1;
	}
	if (r < 0)
		return -1;
	*out = (unsigned long)r;
	return 0;
}

static int16_t slot_of(uint64_t word, const unsigned char *pool)''')
rep('''	for (int i = 0; i < 6; i++) {
		const struct token *t = &c->a[i];
		if (is_buffer(t)) {''', '''	/* 结构化缓冲区：每个单独映射，数据区末尾紧贴一页不可访问页；起点再按 off 错开（off 字节，使地址不对齐） */
	for (int k = 0; k < c->nsd; k++) {
		const struct sdef *sd = &c->sd[k];
		if (!sd->size)
			continue;
		size_t need = sd->size + 8 + sd->off;
		size_t len = (need + PAGE - 1) & ~(PAGE - 1);
		unsigned char *m0 = mmap(NULL, len + PAGE, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
		if (m0 == MAP_FAILED || mprotect(m0, len, PROT_READ | PROT_WRITE))
			return setup_error(s, "struct_mmap");
		memset(m0, sd->fill == 'z' ? 0 : 0xaa, len);
		uintptr_t start = ((uintptr_t)(m0 + len - sd->size - sd->off) & ~(uintptr_t)7) + sd->off;
		m->sbase[k] = (unsigned char *)start;
	}
	for (int k = 0; k < c->nsd; k++) {
		const struct sdef *sd = &c->sd[k];
		for (int j = 0; j < sd->nw; j++) {
			const struct swrite *x = &sd->w[j];
			uint64_t v = x->val;
			if (x->kind == 't')
				v = (uint64_t)(uintptr_t)m->sbase[x->val];
			else if (x->kind == 'l')
				v = c->sd[x->val].size;
			memcpy(m->sbase[k] + x->off, &v, x->width);
		}
	}
	for (int i = 0; i < 6; i++) {
		const struct token *t = &c->a[i];
		if (t->kind == STRUCTBUF) {
			if (t->sub >= c->nsd || !m->sbase[t->sub]) {
				errno = EINVAL;
				return setup_error(s, "struct_ref");
			}
			m->args[i] = (unsigned long)m->sbase[t->sub];
			continue;
		}
		if (t->kind == RES) {
			if (make_res(t->sub, &m->args[i]))
				return setup_error(s, res_names[t->sub]);
			continue;
		}
		if (is_buffer(t)) {''')
rep('''	if (m->pool) {
		m->pool_snap = mmap(NULL, POOL_SIZE, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);''', '''	for (int k = 0; k < c->nsd; k++) {
		if (!m->sbase[k])
			continue;
		m->ssnap[k] = mmap(NULL, c->sd[k].size, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
		if (m->ssnap[k] == MAP_FAILED)
			return setup_error(s, "struct_snapshot_mmap");
		memcpy(m->ssnap[k], m->sbase[k], c->sd[k].size);
	}
	if (m->pool) {
		m->pool_snap = mmap(NULL, POOL_SIZE, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);''')
rep('''	if (m.pool)
		result.pool = changed(m.pool, m.pool_snap, POOL_SIZE);''', '''	if (m.pool)
		result.pool = changed(m.pool, m.pool_snap, POOL_SIZE);
	for (int k = 0; k < c->nsd; k++)
		if (m.sbase[k])
			result.sb[k] = changed(m.sbase[k], m.ssnap[k], c->sd[k].size);''')
rep('''	else
		emit_delta(&obs->pool);
	printf("}\\n");''', '''	else
		emit_delta(&obs->pool);
	if (c->nsd) {  /* 只有带结构化缓冲区的用例才输出 "s"，旧用例的输出不变 */
		printf(",\\"s\\":");
		if (!obs) {
			printf("null");
		} else {
			putchar('[');
			for (int k = 0; k < c->nsd; k++)
				printf("%s[%d,%" PRIu32 ",\\"%08" PRIx32 "\\"]", k ? "," : "", k, obs->sb[k].count, obs->sb[k].hash);
			putchar(']');
		}
	}
	printf("}\\n");''')
rep('''static uint64_t run_case(const struct test_case *c, int casesfd, int debug)
{''', '''/* 用例之间清理 SysV IPC 与消息队列（判据 C3），返回删除的对象数 */
static int cleanup_ipc(void)
{
	static const char *const files[] = { "/proc/sysvipc/msg", "/proc/sysvipc/sem", "/proc/sysvipc/shm" };
	char line[512];
	int removed = 0;
	for (int t = 0; t < 3; t++) {
		FILE *f = fopen(files[t], "r");
		if (!f)
			continue;
		if (!fgets(line, sizeof(line), f)) {
			fclose(f);
			continue;
		}
		while (fgets(line, sizeof(line), f)) {
			long key, id;
			if (sscanf(line, "%ld %ld", &key, &id) != 2)
				continue;
			int r = t == 0 ? msgctl((int)id, IPC_RMID, NULL) : t == 1 ? semctl((int)id, 0, IPC_RMID) :
				shmctl((int)id, IPC_RMID, NULL);
			removed += r == 0;
		}
		fclose(f);
	}
	removed += mq_unlink("/shq") == 0;
	return removed;
}

static uint64_t run_case(const struct test_case *c, int casesfd, int debug)
{''')
rep('''	emit_result(c, name, s->t, obs);
	if (debug)
		emit_debug(c, s, elapsed);''', '''	emit_result(c, name, s->t, obs);
	int removed = cleanup_ipc();
	if (debug) {
		emit_debug(c, s, elapsed);
		printf("{\\"selftest_ipc_removed\\":%" PRIu64 ",\\"n\\":%d}\\n", c->id, removed);
		fflush(stdout);
	}''')
open(p, "w", encoding="utf-8").write(s)
print("patched")
