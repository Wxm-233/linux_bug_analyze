/* 同一份 64 位小端源码用于三个架构；仅在 QEMU 的 initramfs 中运行。
 * 版本 2（casemodel_dev_20261110，Claude 扩展）：结构化缓冲区 t:<k>（用例行 " | " 之后定义）、资源 x:<名>、
 * 新 fd 种类；每个用例后清理 SysV IPC 与消息队列。原有记号的含义与输出不变。 */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <limits.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/eventfd.h>
#include <sys/epoll.h>
#include <sys/timerfd.h>
#include <sys/signalfd.h>
#include <sys/inotify.h>
#include <sys/ipc.h>
#include <sys/msg.h>
#include <sys/sem.h>
#include <sys/shm.h>
#include <mqueue.h>
#include <linux/perf_event.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <netinet/in.h>
#include <time.h>
#include <unistd.h>

#ifndef MAP_FIXED_NOREPLACE
#define MAP_FIXED_NOREPLACE 0x100000
#endif

#define PAGE 4096UL
#define MAIN_SIZE (2 * PAGE)
#define POOL_SIZE (64 * PAGE)
#define FNV_INIT UINT32_C(2166136261)
#define RESULT_MAGIC UINT32_C(0x53485231)
_Static_assert(sizeof(unsigned long) == 8, "64-bit ABI required");

static void json_str(const char *s)
{
	putchar('"');
	for (; *s; s++) {
		if (*s == '"' || *s == '\\')
			putchar('\\');
		if ((unsigned char)*s >= 0x20)
			putchar(*s);
	}
	putchar('"');
}

/* 以下探测段来自 dt_init2.c；仅补上逐行 fflush。 */
static int is_hw_pmu(const char *n)
{
	return !strcmp(n, "cpu") || !strcmp(n, "cpu_core") || !strcmp(n, "cpu_atom") ||
	       !strncmp(n, "armv8", 5) || !strncmp(n, "armv9", 5);
}

static void probe_pmus(void)
{
	DIR *d = opendir("/sys/bus/event_source/devices");
	struct dirent *e;
	char path[512];
	int first = 1;

	printf("{\"probe\": \"pmu_devices\", \"value\": [");
	if (d) {
		while ((e = readdir(d))) {
			if (e->d_name[0] == '.')
				continue;
			if (!first)
				printf(", ");
			json_str(e->d_name);
			first = 0;
		}
		closedir(d);
	}
	printf("]}\n");
	fflush(stdout);
	d = opendir("/sys/bus/event_source/devices");
	if (!d)
		return;
	while ((e = readdir(d))) {
		DIR *ev;
		struct dirent *x;
		if (e->d_name[0] == '.' || !is_hw_pmu(e->d_name))
			continue;
		snprintf(path, sizeof(path), "/sys/bus/event_source/devices/%s/events", e->d_name);
		ev = opendir(path);
		printf("{\"probe\": \"pmu_events\", \"pmu\": ");
		json_str(e->d_name);
		if (!ev) {
			printf(", \"value\": null}\n");
			fflush(stdout);
			continue;
		}
		printf(", \"value\": [");
		first = 1;
		while ((x = readdir(ev))) {
			if (x->d_name[0] == '.')
				continue;
			if (!first)
				printf(", ");
			json_str(x->d_name);
			first = 0;
		}
		closedir(ev);
		printf("]}\n");
		fflush(stdout);
	}
	closedir(d);
}

static void probe_cpuinfo(void)
{
	FILE *f = fopen("/proc/cpuinfo", "r");
	char line[4096];
	int seen_isa = 0, seen_mmu = 0, seen_feat = 0, seen_flags = 0;
	if (!f)
		return;
	while (fgets(line, sizeof(line), f)) {
		char *colon = strchr(line, ':');
		int *seen = NULL;
		const char *key = NULL;
		if (!colon)
			continue;
		if (!strncmp(line, "isa", 3) && !strncmp(line, "isa\t", 4)) { seen = &seen_isa; key = "isa"; }
		else if (!strncmp(line, "mmu", 3)) { seen = &seen_mmu; key = "mmu"; }
		else if (!strncmp(line, "Features", 8)) { seen = &seen_feat; key = "Features"; }
		else if (!strncmp(line, "flags", 5)) { seen = &seen_flags; key = "flags"; }
		if (!seen || *seen)
			continue;
		*seen = 1;
		line[strcspn(line, "\n")] = 0;
		colon++;
		while (*colon == ' ' || *colon == '\t')
			colon++;
		printf("{\"probe\": \"cpuinfo\", \"key\": \"%s\", \"value\": ", key);
		json_str(colon);
		printf("}\n");
		fflush(stdout);
	}
	fclose(f);
}

static long read_long(const char *path)
{
	FILE *f = fopen(path, "r");
	long v = -1;
	if (f) {
		if (fscanf(f, "%ld", &v) != 1)
			v = -1;
		fclose(f);
	}
	return v;
}

enum kind { INTEGER, BUFFER, OR_BUFFER, FD, PATH, SELF, STRUCTBUF, RES };
enum template { NONE, OCC, ADJ };
enum fd_kind { F_FILE, F_DIR, F_PIPERD, F_PIPEWR, F_USTREAM, F_UDGRAM,
	F_EVENTFD, F_MEMFD, F_UDP, F_NEG, F_UNOPEN, F_ATCWD, F_PIPEBLOCKRD,
	F_EPOLL, F_TIMERFD, F_SIGNALFD, F_INOTIFY, F_PIDFD, F_PERFSW, F_MQ };
static const char *const fd_names[] = { "file", "dir", "piperd", "pipewr", "ustream",
	"udgram", "eventfd", "memfd", "udp", "neg", "unopen", "atcwd", "pipeblockrd",
	"epoll", "timerfd", "signalfd", "inotify", "pidfd", "perfsw", "mq" };
enum res_kind { R_MSQ, R_SEM, R_SHM, R_TIMER, R_AIO };
static const char *const res_names[] = { "msq", "sem", "shm", "timer", "aio" };
#define MAXSB 16
#define MAXW 48
static const char *const path_names[] = { "f", "d", "nx", "empty", "null" };
static const char *const paths[] = { "/tmp/f", "/tmp/d", "/tmp/nonexist", "", NULL };

struct token { enum kind kind; uint64_t value; char fill; int sub; };
struct swrite { uint32_t off; int width; char kind; uint64_t val; };
struct sdef { size_t size; char fill; int off; int nw; struct swrite w[MAXW]; };
struct test_case {
	uint64_t id;
	long nr;
	enum template tmpl;
	int ai, li;
	struct token a[6];
	int nsd;
	struct sdef sd[MAXSB];
};
struct delta { uint32_t count, hash; };
struct result {
	uint32_t magic;
	char r[64];
	struct delta b[6], pool, sb[MAXSB];
};
/* 只把模板状态和自测信息放在共享内存；正式观测结果仍须经过管道。 */
struct shared {
	volatile int t, prepared;
	char error[128];
	int fd_ok[6], memory_ok[6];
	int16_t graph[6][8], pool_graph[32][8];
	uint32_t pool_hash;
	int graph_ok;
};
struct memory {
	unsigned char *b[6], *snap[6], *pool, *pool_snap;
	unsigned char *sbase[MAXSB], *ssnap[MAXSB];
	unsigned long args[6];
};

static int uint_value(const char *s, int base, uint64_t *v)
{
	char *end;
	if (!*s || *s == '-' || *s == '+')
		return -1;
	errno = 0;
	*v = strtoull(s, &end, base);
	return errno || *end ? -1 : 0;
}

static int name_index(const char *s, const char *const *names, size_t n)
{
	for (size_t i = 0; i < n; i++)
		if (!strcmp(s, names[i]))
			return (int)i;
	return -1;
}

static int parse_token(const char *s, struct token *t)
{
	uint64_t n;
	if (strlen(s) < 3 || s[1] != ':')
		return -1;
	switch (*s) {
	case 'i':
		t->kind = INTEGER;
		return uint_value(s + 2, 16, &t->value);
	case 'b': case 'o':
		if (strlen(s) < 5 || !strchr("zag", s[2]) || s[3] != ':' ||
		    uint_value(s + 4, 10, &n) || n > (*s == 'b' ? 8191 : 63))
			return -1;
		t->kind = *s == 'b' ? BUFFER : OR_BUFFER;
		t->fill = s[2];
		t->sub = (int)n;
		return 0;
	case 'f':
		t->kind = FD;
		t->sub = name_index(s + 2, fd_names, sizeof(fd_names) / sizeof(fd_names[0]));
		return t->sub < 0 ? -1 : 0;
	case 'p':
		t->kind = PATH;
		t->sub = name_index(s + 2, path_names, sizeof(path_names) / sizeof(path_names[0]));
		return t->sub < 0 ? -1 : 0;
	case 's':
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
		return t->sub < 0 ? -1 : 0;
	default: return -1;
	}
}

/* 结构化缓冲区定义：k:size:fill:off[:offset/width/val]*，多个定义以 ';' 分隔；
 * val 为 i<hex>（整数）、t<j>（缓冲区 j 的地址）、l<j>（缓冲区 j 的长度 size）。 */
static int parse_sdefs(char *s, struct test_case *c)
{
	char *save1, *d;
	for (d = strtok_r(s, ";", &save1); d; d = strtok_r(NULL, ";", &save1)) {
		char *save2, *f;
		uint64_t k, v;
		while (*d == ' ')
			d++;
		if (!*d || *d == '\n' || *d == '\r')
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
		if (!(f = strtok_r(NULL, ":\r\n", &save2)) || uint_value(f, 10, &v) || v > 4095)
			return -1;
		sd->off = (int)v;
		while ((f = strtok_r(NULL, ":\r\n", &save2))) {
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
	}
	for (p = strtok_r(line, " \t\r\n", &save); p && n < 10;
	     p = strtok_r(NULL, " \t\r\n", &save))
		v[n++] = p;
	if (n != 9 || uint_value(v[0], 10, &c->id))
		return -1;
	errno = 0;
	c->nr = strtol(v[1], &end, 10);
	if (errno || *end)
		return -1;
	if (!strcmp(v[2], "none")) {
		c->tmpl = NONE;
	} else {
		if (strlen(v[2]) != 7 || (strncmp(v[2], "occ:", 4) && strncmp(v[2], "adj:", 4)) ||
		    v[2][4] < '0' || v[2][4] > '5' || v[2][5] != ':' || v[2][6] < '0' || v[2][6] > '5')
			return -1;
		c->tmpl = v[2][0] == 'o' ? OCC : ADJ;
		c->ai = v[2][4] - '0';
		c->li = v[2][6] - '0';
	}
	for (int i = 0; i < 6; i++)
		if (parse_token(v[i + 3], &c->a[i]))
			return -1;
	return 0;
}

static int is_buffer(const struct token *t)
{
	return t->kind == BUFFER || t->kind == OR_BUFFER;
}

static int has_pool(const struct test_case *c)
{
	for (int i = 0; i < 6; i++)
		if (is_buffer(&c->a[i]) && c->a[i].fill == 'g')
			return 1;
	return 0;
}

static uint64_t next_random(uint64_t *state)
{
	*state ^= *state << 13;
	*state ^= *state >> 7;
	*state ^= *state << 17;
	return *state;
}

static void graph_words(unsigned char *dst, unsigned char *pool, uint64_t *rng, int nested)
{
	for (int w = 0; w < 8; w++) {
		uint64_t r = next_random(rng);
		uint64_t value = r & 1 ? (uintptr_t)(pool + (nested ? 32 + r % 32 : r % 64) * PAGE) : 64;
		memcpy(dst + 8 * w, &value, 8);
	}
}

static uint32_t fnv_byte(uint32_t h, unsigned char b)
{
	return (h ^ b) * UINT32_C(16777619);
}

static struct delta changed(const unsigned char *b, const unsigned char *snapshot, size_t size)
{
	struct delta d = { 0, FNV_INIT };
	for (uint32_t pos = 0; pos < size; pos++) {
		if (b[pos] == snapshot[pos])
			continue;
		d.count++;
		for (int byte = 0; byte < 4; byte++)
			d.hash = fnv_byte(d.hash, (unsigned char)(pos >> (8 * byte)));
	}
	return d;
}

static int setup_error(struct shared *s, const char *stage)
{
	const char *name = strerrorname_np(errno);
	snprintf(s->error, sizeof(s->error), "%s:%s", stage, name ? name : "E?");
	return -1;
}

static int write_all(int fd, const void *buf, size_t size)
{
	const unsigned char *p = buf;
	while (size) {
		ssize_t n = write(fd, p, size);
		if (n < 0 && errno == EINTR)
			continue;
		if (n <= 0)
			return -1;
		p += n;
		size -= (size_t)n;
	}
	return 0;
}

static int rebuild_files(struct shared *s)
{
	char x[4096];
	int fd;
	if (chdir("/tmp"))
		return setup_error(s, "chdir");
	if (unlink("/tmp/f") && errno != ENOENT)
		return setup_error(s, "unlink_f");
	fd = open("/tmp/f", O_CREAT | O_TRUNC | O_RDWR, 0600);
	if (fd < 0)
		return setup_error(s, "create_f");
	memset(x, 'x', sizeof(x));
	if (write_all(fd, x, sizeof(x))) {
		close(fd);
		return setup_error(s, "fill_f");
	}
	close(fd);
	if (mkdir("/tmp/d", 0700) && errno != EEXIST)
		return setup_error(s, "mkdir_d");
	return 0;
}

static int make_fd(int kind)
{
	int p[2], fd, one = 1;
	char data[16];
	memset(data, 'p', sizeof(data));
	switch (kind) {
	case F_FILE: return open("/tmp/f", O_RDWR);
	case F_DIR: return open("/tmp/d", O_RDONLY | O_DIRECTORY);
	case F_PIPERD: case F_PIPEWR: case F_PIPEBLOCKRD:
		if (pipe2(p, kind == F_PIPEBLOCKRD ? 0 : O_NONBLOCK))
			return -1;
		/* 两端均保留到子进程结束；空管道不会因写端关闭而返回 EOF。 */
		if (kind == F_PIPERD && write_all(p[1], data, sizeof(data)))
			return -1;
		return kind == F_PIPEWR ? p[1] : p[0];
	case F_USTREAM:
		if (socketpair(AF_UNIX, SOCK_STREAM | SOCK_NONBLOCK, 0, p) ||
		    write_all(p[1], data, sizeof(data)))
			return -1;
		return p[0];
	case F_UDGRAM: {
		union { struct cmsghdr align; unsigned char bytes[CMSG_SPACE(sizeof(int))]; } control;
		struct iovec iov = { data, sizeof(data) };
		struct msghdr msg = { 0 };
		struct cmsghdr *cm;
		if (socketpair(AF_UNIX, SOCK_DGRAM | SOCK_NONBLOCK, 0, p) ||
		    setsockopt(p[0], SOL_SOCKET, SO_PASSCRED, &one, sizeof(one)))
			return -1;
		fd = open("/tmp/f", O_RDWR);
		if (fd < 0)
			return -1;
		memset(&control, 0, sizeof(control));
		msg.msg_iov = &iov;
		msg.msg_iovlen = 1;
		msg.msg_control = control.bytes;
		msg.msg_controllen = sizeof(control.bytes);
		cm = CMSG_FIRSTHDR(&msg);
		cm->cmsg_level = SOL_SOCKET;
		cm->cmsg_type = SCM_RIGHTS;
		cm->cmsg_len = CMSG_LEN(sizeof(fd));
		memcpy(CMSG_DATA(cm), &fd, sizeof(fd));
		if (sendmsg(p[1], &msg, 0) != sizeof(data)) {
			close(fd);
			return -1;
		}
		close(fd);
		return p[0];
	}
	case F_EVENTFD: return eventfd(0, EFD_NONBLOCK);
	case F_MEMFD:
		fd = memfd_create("m", 0);
		if (fd >= 0 && ftruncate(fd, PAGE)) {
			close(fd);
			return -1;
		}
		return fd;
	case F_UDP: return socket(AF_INET, SOCK_DGRAM | SOCK_NONBLOCK, 0);
	case F_NEG: return -1;
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
	case F_MQ: return (int)mq_open("/shq", O_RDWR | O_CREAT | O_NONBLOCK, 0600, NULL);
	default: errno = EINVAL; return -1;
	}
}

/* 自测只窥看数据；SCM_RIGHTS 的 MSG_PEEK 副本及时关闭，原消息保持排队。 */
static int check_fd(int fd, int kind)
{
	struct stat st;
	int flags, n;
	char data[16];
	if (kind == F_NEG || kind == F_ATCWD)
		return fd == (kind == F_NEG ? -1 : AT_FDCWD);
	if (kind == F_UNOPEN)
		return fcntl(fd, F_GETFD) == -1 && errno == EBADF;
	flags = fcntl(fd, F_GETFL);
	if (flags < 0 || fstat(fd, &st))
		return 0;
	switch (kind) {
	case F_FILE: return S_ISREG(st.st_mode) && st.st_size == 4096 && (flags & O_ACCMODE) == O_RDWR;
	case F_DIR: return S_ISDIR(st.st_mode) && (flags & O_ACCMODE) == O_RDONLY;
	case F_MEMFD: return S_ISREG(st.st_mode) && st.st_size == 4096;
	case F_PIPERD: return (flags & O_NONBLOCK) && !ioctl(fd, FIONREAD, &n) && n == 16;
	case F_PIPEWR: return (flags & O_NONBLOCK) && (flags & O_ACCMODE) == O_WRONLY;
	case F_PIPEBLOCKRD: return !(flags & O_NONBLOCK) && !ioctl(fd, FIONREAD, &n) && n == 0;
	case F_EVENTFD: return (flags & O_NONBLOCK) != 0;
	case F_USTREAM: return (flags & O_NONBLOCK) && recv(fd, data, sizeof(data), MSG_PEEK | MSG_DONTWAIT) == 16;
	case F_UDP: {
		struct sockaddr_in addr;
		socklen_t len = sizeof(addr);
		return (flags & O_NONBLOCK) && !getsockname(fd, (struct sockaddr *)&addr, &len) &&
		       addr.sin_family == AF_INET && addr.sin_port == 0;
	}
	case F_UDGRAM: {
		union { struct cmsghdr align; unsigned char bytes[256]; } control;
		struct iovec iov = { data, sizeof(data) };
		struct msghdr msg = { 0 };
		struct cmsghdr *cm;
		int rights = 0, creds = 0;
		msg.msg_iov = &iov;
		msg.msg_iovlen = 1;
		msg.msg_control = control.bytes;
		msg.msg_controllen = sizeof(control.bytes);
		if (!(flags & O_NONBLOCK) || recvmsg(fd, &msg, MSG_PEEK | MSG_DONTWAIT) != 16)
			return 0;
		for (cm = CMSG_FIRSTHDR(&msg); cm; cm = CMSG_NXTHDR(&msg, cm)) {
			if (cm->cmsg_level != SOL_SOCKET)
				continue;
			if (cm->cmsg_type == SCM_CREDENTIALS && cm->cmsg_len == CMSG_LEN(sizeof(struct ucred)))
				creds++;
			if (cm->cmsg_type == SCM_RIGHTS && cm->cmsg_len == CMSG_LEN(sizeof(int))) {
				int received;
				memcpy(&received, CMSG_DATA(cm), sizeof(received));
				rights += !fstat(received, &st) && S_ISREG(st.st_mode) && st.st_size == 4096;
				close(received);
			}
		}
		return rights == 1 && creds == 1 && !(msg.msg_flags & MSG_CTRUNC);
	}
	default: return 0;
	}
}

static int make_res(int kind, unsigned long *out)
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

static int16_t slot_of(uint64_t word, const unsigned char *pool)
{
	uint64_t base = (uintptr_t)pool;
	if (word == 64)
		return -1;  /* -1 表示常量 64；非负数表示池的槽号。 */
	if (word >= base && word - base < POOL_SIZE && !((word - base) % PAGE))
		return (int16_t)((word - base) / PAGE);
	return -2;
}

static void debug_memory(const struct test_case *c, struct memory *m, struct shared *s)
{
	s->graph_ok = 1;
	for (int i = 0; i < 6; i++) {
		if (!m->b[i])
			continue;
		unsigned char fill = c->a[i].fill == 'z' ? 0 : 0xaa;
		s->memory_ok[i] = 1;
		for (size_t p = c->a[i].fill == 'g' ? 64 : 0; p < MAIN_SIZE; p++)
			if (m->b[i][p] != fill)
				s->memory_ok[i] = 0;
		for (int w = 0; c->a[i].fill == 'g' && w < 8; w++) {
			uint64_t value;
			memcpy(&value, m->b[i] + 8 * w, 8);
			s->graph[i][w] = slot_of(value, m->pool);
			if (s->graph[i][w] == -2)
				s->graph_ok = 0;
		}
		unsigned long expected = (unsigned long)m->b[i];
		expected = c->a[i].kind == BUFFER ? expected + c->a[i].sub : expected | (1UL << c->a[i].sub);
		if (m->args[i] != expected)
			s->memory_ok[i] = 0;
	}
	if (!m->pool)
		return;
	/* 整个池逐字节哈希，前 8 字中的地址先还原成可比较的槽号/64。 */
	s->pool_hash = FNV_INIT;
	for (int k = 0; k < 64; k++) {
		for (size_t p = 0; p < PAGE; p++) {
			unsigned char byte = m->pool[k * PAGE + p];
			if (k < 32 && p < 64) {
				uint64_t word;
				memcpy(&word, m->pool + k * PAGE + (p / 8) * 8, 8);
				int16_t slot = slot_of(word, m->pool);
				s->pool_graph[k][p / 8] = slot;
				if (slot != -1 && (slot < 32 || slot > 63))
					s->graph_ok = 0;
				uint64_t normalized = slot < 0 ? 64 : (uint64_t)slot;
				byte = (unsigned char)(normalized >> ((p % 8) * 8));
			} else if (byte != 0xaa) {
				s->graph_ok = 0;
			}
			s->pool_hash = fnv_byte(s->pool_hash, byte);
		}
	}
}

static int prepare(const struct test_case *c, struct memory *m, struct shared *s, int debug)
{
	uint64_t rng = c->id * UINT64_C(0x9e3779b97f4a7c15) + 1;
	if (rebuild_files(s))
		return -1;
	if (has_pool(c)) {
		m->pool = mmap(NULL, POOL_SIZE, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
		if (m->pool == MAP_FAILED)
			return setup_error(s, "pool_mmap");
		memset(m->pool, 0xaa, POOL_SIZE);
	}
	/* 结构化缓冲区：每个单独映射，数据区末尾紧贴一页不可访问页；起点再按 off 错开（off 字节，使地址不对齐） */
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
		if (is_buffer(t)) {
			m->b[i] = mmap(NULL, 3 * PAGE, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
			if (m->b[i] == MAP_FAILED || mprotect(m->b[i], MAIN_SIZE, PROT_READ | PROT_WRITE))
				return setup_error(s, "buffer_mmap");
			memset(m->b[i], t->fill == 'z' ? 0 : 0xaa, MAIN_SIZE);
			m->args[i] = t->kind == BUFFER ? (unsigned long)m->b[i] + t->sub :
				(unsigned long)m->b[i] | (1UL << t->sub);
		} else if (t->kind == INTEGER) {
			m->args[i] = t->value;
		} else if (t->kind == SELF) {
			m->args[i] = (unsigned long)getpid();
		} else if (t->kind == PATH) {
			if (!paths[t->sub]) {
				m->args[i] = 0;
				continue;
			}
			char *p = mmap(NULL, PAGE, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
			if (p == MAP_FAILED)
				return setup_error(s, "path_mmap");
			strcpy(p, paths[t->sub]);
			m->args[i] = (unsigned long)p;
		} else if (t->kind == FD) {
			int fd = make_fd(t->sub);
			if (fd == -1 && t->sub != F_NEG)
				return setup_error(s, fd_names[t->sub]);
			m->args[i] = (unsigned long)(long)fd;
			if (debug)
				s->fd_ok[i] = check_fd(fd, t->sub);
		}
	}
	/* 所有地址确定后才填图；主缓冲区在前，池在后，次序不依赖地址。 */
	for (int i = 0; i < 6; i++)
		if (m->b[i] && c->a[i].fill == 'g')
			graph_words(m->b[i], m->pool, &rng, 0);
	for (int k = 0; m->pool && k < 32; k++)
		graph_words(m->pool + k * PAGE, m->pool, &rng, 1);
	if (c->tmpl != NONE) {
		unsigned long addr = m->args[c->ai];
		if (c->tmpl == ADJ)
			addr += m->args[c->li] + PAGE - 1; /* uint64 模 2^64 运算。 */
		addr &= ~(PAGE - 1);
		void *p = mmap((void *)addr, PAGE, PROT_READ,
			MAP_FIXED_NOREPLACE | MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
		s->t = p != MAP_FAILED && (unsigned long)p == addr;
		if (p != MAP_FAILED && (unsigned long)p != addr)
			munmap(p, PAGE);
	}
	if (debug)
		debug_memory(c, m, s);
	for (int i = 0; i < 6; i++) {
		if (!m->b[i])
			continue;
		m->snap[i] = mmap(NULL, MAIN_SIZE, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
		if (m->snap[i] == MAP_FAILED)
			return setup_error(s, "snapshot_mmap");
		memcpy(m->snap[i], m->b[i], MAIN_SIZE);
	}
	for (int k = 0; k < c->nsd; k++) {
		if (!m->sbase[k])
			continue;
		m->ssnap[k] = mmap(NULL, c->sd[k].size, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
		if (m->ssnap[k] == MAP_FAILED)
			return setup_error(s, "struct_snapshot_mmap");
		memcpy(m->ssnap[k], m->sbase[k], c->sd[k].size);
	}
	if (m->pool) {
		m->pool_snap = mmap(NULL, POOL_SIZE, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
		if (m->pool_snap == MAP_FAILED)
			return setup_error(s, "pool_snapshot_mmap");
		memcpy(m->pool_snap, m->pool, POOL_SIZE);
	}
	s->prepared = 1;
	return 0;
}

static void normalize(char *out, size_t size, long r, int e, const unsigned long args[6])
{
	if (r == -1) {
		const char *name = strerrorname_np(e);
		snprintf(out, size, "%s", name ? name : "E?");
	} else if (r >= 0) {
		for (int i = 0; i < 6; i++)
			if ((unsigned long)r == args[i]) {
				snprintf(out, size, "arg%d", i);
				return;
			}
		if (r < 65536)
			snprintf(out, size, "%ld", r);
		else
			snprintf(out, size, "big");
	} else {
		snprintf(out, size, "neg");
	}
}

static void child_run(const struct test_case *c, int pipefd, struct shared *s, int debug)
{
	struct memory m = { 0 };
	struct result result = { .magic = RESULT_MAGIC };
	int fd = open("/dev/null", O_RDWR);
	if (fd < 0) {
		setup_error(s, "dev_null");
		_exit(1);
	}
	for (int i = 0; i < 3; i++)
		if (dup2(fd, i) < 0) {
			setup_error(s, "dup2");
			_exit(1);
		}
	if (fd > 2)
		close(fd);
	if (prepare(c, &m, s, debug))
		_exit(1);
	errno = 0;
	long r = syscall(c->nr, m.args[0], m.args[1], m.args[2], m.args[3], m.args[4], m.args[5]);
	int saved_errno = errno;
	normalize(result.r, sizeof(result.r), r, saved_errno, m.args);
	for (int i = 0; i < 6; i++)
		if (m.b[i])
			result.b[i] = changed(m.b[i], m.snap[i], MAIN_SIZE);
	if (m.pool)
		result.pool = changed(m.pool, m.pool_snap, POOL_SIZE);
	for (int k = 0; k < c->nsd; k++)
		if (m.sbase[k])
			result.sb[k] = changed(m.sbase[k], m.ssnap[k], c->sd[k].size);
	write_all(pipefd, &result, sizeof(result));
	_exit(0);
}

static uint64_t now_ns(void)
{
	struct timespec t;
	if (clock_gettime(CLOCK_MONOTONIC, &t))
		return 0;
	return (uint64_t)t.tv_sec * UINT64_C(1000000000) + (uint64_t)t.tv_nsec;
}

static void emit_delta(const struct delta *d)
{
	printf("[%" PRIu32 ",\"%08" PRIx32 "\"]", d->count, d->hash);
}

static void emit_result(const struct test_case *c, const char *r, int t, const struct result *obs)
{
	printf("{\"id\":%" PRIu64 ",\"r\":", c->id);
	json_str(r);
	printf(",\"t\":%d,\"b\":", t);
	if (!obs) {
		printf("null");
	} else {
		int first = 1;
		putchar('[');
		for (int i = 0; i < 6; i++) {
			if (!is_buffer(&c->a[i]))
				continue;
			printf("%s[%d,%" PRIu32 ",\"%08" PRIx32 "\"]", first ? "" : ",", i,
				obs->b[i].count, obs->b[i].hash);
			first = 0;
		}
		putchar(']');
	}
	printf(",\"pool\":");
	if (!has_pool(c))
		printf("null");
	else if (!obs)
		printf("[null,null]");
	else
		emit_delta(&obs->pool);
	if (c->nsd) {  /* 只有带结构化缓冲区的用例才输出 "s"，旧用例的输出不变 */
		printf(",\"s\":");
		if (!obs) {
			printf("null");
		} else {
			putchar('[');
			for (int k = 0; k < c->nsd; k++)
				printf("%s[%d,%" PRIu32 ",\"%08" PRIx32 "\"]", k ? "," : "", k, obs->sb[k].count, obs->sb[k].hash);
			putchar(']');
		}
	}
	printf("}\n");
	fflush(stdout);
}

static void emit_debug(const struct test_case *c, const struct shared *s, uint64_t elapsed)
{
	printf("{\"selftest\":%" PRIu64 ",\"elapsed_ms\":%.6f,\"prepared\":%d,\"setup_error\":",
		c->id, (double)elapsed / 1000000.0, s->prepared);
	if (*s->error)
		json_str(s->error);
	else
		printf("null");
	printf(",\"fd_checks\":{");
	int first = 1;
	for (int i = 0; i < 6; i++)
		if (c->a[i].kind == FD) {
			printf("%s\"%d\":%d", first ? "" : ",", i, s->fd_ok[i]);
			first = 0;
		}
	printf("},\"memory_checks\":{");
	first = 1;
	for (int i = 0; i < 6; i++)
		if (is_buffer(&c->a[i])) {
			printf("%s\"%d\":%d", first ? "" : ",", i, s->memory_ok[i]);
			first = 0;
		}
	printf("},\"graph_ok\":%d,\"graph\":{", s->graph_ok);
	first = 1;
	for (int i = 0; i < 6; i++) {
		if (!is_buffer(&c->a[i]) || c->a[i].fill != 'g')
			continue;
		printf("%s\"%d\":[", first ? "" : ",", i);
		for (int w = 0; w < 8; w++)
			printf("%s%d", w ? "," : "", s->graph[i][w]);
		putchar(']');
		first = 0;
	}
	printf("},\"pool_graph\":");
	if (!has_pool(c)) {
		printf("null,\"pool_hash\":null");
	} else {
		putchar('[');
		for (int k = 0; k < 32; k++) {
			printf("%s[", k ? "," : "");
			for (int w = 0; w < 8; w++)
				printf("%s%d", w ? "," : "", s->pool_graph[k][w]);
			putchar(']');
		}
		printf("],\"pool_hash\":\"%08" PRIx32 "\"", s->pool_hash);
	}
	printf("}\n");
	fflush(stdout);
}

/* 用例之间清理 SysV IPC 与消息队列（判据 C3），返回删除的对象数 */
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
{
	int p[2], status = 0, timed_out = 0;
	pid_t child;
	uint64_t start, elapsed;
	struct result result;
	struct shared *s = mmap(NULL, sizeof(*s), PROT_READ | PROT_WRITE, MAP_SHARED | MAP_ANONYMOUS, -1, 0);
	if (s == MAP_FAILED || pipe2(p, O_NONBLOCK | O_CLOEXEC)) {
		emit_result(c, "setup_failed", c->tmpl == NONE ? -1 : 0, NULL);
		printf("{\"harness_error\":\"parent_ipc\"}\n");
		fflush(stdout);
		if (s != MAP_FAILED)
			munmap(s, sizeof(*s));
		return 0;
	}
	s->t = c->tmpl == NONE ? -1 : 0;
	/* Claude 补：每个用例前换一个干净的 /tmp，避免上一个用例建的文件影响下一个（判据第五节“彼此独立”）。 */
	if (umount2("/tmp", MNT_DETACH) || mount("tmpfs", "/tmp", "tmpfs", 0, "mode=1777"))
		snprintf(s->error, sizeof(s->error), "tmp_reset_failed");
	start = now_ns();
	child = fork();
	if (child == 0) {
		close(p[0]);
		close(casesfd);
		child_run(c, p[1], s, debug);
	}
	close(p[1]);
	if (child < 0) {
		snprintf(s->error, sizeof(s->error), "fork_failed");
	} else {
		for (;;) {
			pid_t waited = waitpid(child, &status, WNOHANG);
			if (waited == child)
				break;
			if (waited < 0 && errno != EINTR) {
				snprintf(s->error, sizeof(s->error), "waitpid_failed");
				break;
			}
			if (now_ns() - start >= UINT64_C(500000000)) {
				timed_out = 1;
				kill(child, SIGKILL);
				while (waitpid(child, &status, 0) < 0 && errno == EINTR) {}
				break;
			}
			struct timespec pause = { 0, 1000000 };
			nanosleep(&pause, NULL);
		}
	}
	elapsed = now_ns() - start;
	/* 非阻塞读取：调用可能复制了结果管道 fd，不能依赖 EOF。结果小于 PIPE_BUF。 */
	ssize_t n;
	do { n = read(p[0], &result, sizeof(result)); } while (n < 0 && errno == EINTR);
	close(p[0]);
	const struct result *obs = NULL;
	char name[64];
	if (*s->error) {
		snprintf(name, sizeof(name), "setup_failed");
		printf("{\"harness_error\":");
		json_str(s->error);
		printf(",\"id\":%" PRIu64 "}\n", c->id);
		fflush(stdout);
	} else if (timed_out) {
		snprintf(name, sizeof(name), "timeout");
	} else if (WIFSIGNALED(status)) {
		const char *sig = sigabbrev_np(WTERMSIG(status));
		snprintf(name, sizeof(name), "SIG%s", sig ? sig : "?");
	} else if (n != sizeof(result) || result.magic != RESULT_MAGIC) {
		snprintf(name, sizeof(name), "noresult");
	} else {
		snprintf(name, sizeof(name), "%s", result.r);
		obs = &result;
	}
	emit_result(c, name, s->t, obs);
	int removed = cleanup_ipc();
	if (debug) {
		emit_debug(c, s, elapsed);
		printf("{\"selftest_ipc_removed\":%" PRIu64 ",\"n\":%d}\n", c->id, removed);
		fflush(stdout);
	}
	munmap(s, sizeof(*s));
	return elapsed;
}

int main(void)
{
	FILE *cases;
	char *line = NULL;
	size_t capacity = 0;
	unsigned long lineno = 0, count = 0;
	uint64_t elapsed = 0;
	int debug = 0, failed = 0, fd;
	long taint0, taint1;
	if (getpid() != 1) {
		fprintf(stderr, "sh_init must run as PID 1 in a QEMU initramfs\n");
		return 2;
	}
	int mount_error = mount("devtmpfs", "/dev", "devtmpfs", 0, NULL);
	fd = open("/dev/console", O_WRONLY);
	if (fd >= 0) {
		dup2(fd, 1);
		dup2(fd, 2);
		if (fd > 2)
			close(fd);
	}
	setvbuf(stdout, NULL, _IONBF, 0);
	mount_error |= mount("proc", "/proc", "proc", 0, NULL);
	mount_error |= mount("sysfs", "/sys", "sysfs", 0, NULL);
	mount_error |= mount("tmpfs", "/tmp", "tmpfs", 0, "mode=1777");
	printf("\n@@SH BEGIN\n");
	fflush(stdout);
	if (mount_error) {
		printf("{\"harness_error\":\"mount_failed\"}\n");
		goto poweroff;
	}
	probe_pmus();
	probe_cpuinfo();
	taint0 = read_long("/proc/sys/kernel/tainted");
	cases = fopen("/cases.txt", "r");
	if (!cases) {
		printf("{\"harness_error\":\"open_cases_failed\"}\n");
		goto poweroff;
	}
	while (getline(&line, &capacity, cases) >= 0) {
		struct test_case c;
		lineno++;
		if (lineno == 1 && (!strcmp(line, "# SH_SELFTEST\n") || !strcmp(line, "# SH_SELFTEST\r\n"))) {
			debug = 1;
			continue;
		}
		char *p = line;
		while (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n')
			p++;
		if (!*p || *p == '#')
			continue;
		if (parse_case(p, &c)) {
			printf("{\"harness_error\":\"invalid_case\",\"line\":%lu}\n", lineno);
			fflush(stdout);
			failed = 1;
			break;
		}
		elapsed += run_case(&c, fileno(cases), debug);
		count++;
	}
	if (ferror(cases)) {
		printf("{\"harness_error\":\"read_cases_failed\"}\n");
		failed = 1;
	}
	free(line);
	fclose(cases);
	taint1 = read_long("/proc/sys/kernel/tainted");
	if (taint0 < 0 || taint1 < 0) {
		printf("{\"harness_error\":\"read_taint_failed\"}\n");
		printf("{\"taint_changed\":null}\n");
		failed = 1;
	} else {
		printf("{\"taint_changed\":%d}\n", taint0 != taint1);
	}
	fflush(stdout);
	if (debug) {
		printf("{\"selftest_summary\":{\"cases\":%lu,\"elapsed_ms\":%.6f,\"mean_ms\":%.6f}}\n",
			count, (double)elapsed / 1000000.0, count ? (double)elapsed / (1000000.0 * count) : 0.0);
		fflush(stdout);
	}
	if (!failed)
		printf("@@SH END\n");
poweroff:
	fflush(stdout);
	sync();
	reboot(RB_POWER_OFF);
	return 0;
}
