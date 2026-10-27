/*
 * Read-only PID 1 observations for a historical kernel boot.
 * Build with the target's static glibc toolchain; no shell or BusyBox is used.
 * /dev/console must be directed to the QEMU serial console by the kernel cmdline.
 * This probe emits facts only. Missing topology files are not contract verdicts.
 */
#define _GNU_SOURCE
#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <sys/utsname.h>
#include <unistd.h>

#define MAX_OBSERVED_CPUS 4U
#define MAX_READ_BYTES 16384U

enum read_status { READ_OK, OPEN_ERROR, READ_ERROR };

struct file_read {
	enum read_status status;
	int error;
	size_t length;
	bool truncated;
	unsigned char data[MAX_READ_BYTES + 1];
};

struct operation {
	int result;
	int error;
};

struct cpu_list {
	unsigned int ids[MAX_OBSERVED_CPUS];
	unsigned int selected;
	uint64_t total;
	bool valid;
	const char *error;
};

static unsigned int open_errors, read_errors;

/* Escape bytes, including non-ASCII bytes, so every record is valid JSON.
 * raw_byte_length plus byte_escaped encoding allows byte-for-byte recovery.
 */
static void json_bytes(const unsigned char *bytes, size_t length)
{
	size_t i;
	putchar('"');
	for (i = 0; i < length; i++) {
		unsigned char c = bytes[i];
		switch (c) {
		case '"': fputs("\\\"", stdout); break;
		case '\\': fputs("\\\\", stdout); break;
		case '\b': fputs("\\b", stdout); break;
		case '\f': fputs("\\f", stdout); break;
		case '\n': fputs("\\n", stdout); break;
		case '\r': fputs("\\r", stdout); break;
		case '\t': fputs("\\t", stdout); break;
		default:
			if (c < 0x20 || c >= 0x7f)
				printf("\\u%04x", (unsigned int)c);
			else
				putchar(c);
		}
	}
	putchar('"');
}

static void json_string(const char *s)
{
	json_bytes((const unsigned char *)s, strlen(s));
}

static struct operation make_directory(const char *path)
{
	struct operation op;
	op.result = mkdir(path, 0755);
	op.error = op.result < 0 ? errno : 0;
	return op;
}

static struct operation mount_fs(const char *name, const char *path,
				 unsigned long flags)
{
	struct operation op;
	op.result = mount(name, path, name, flags, NULL);
	op.error = op.result < 0 ? errno : 0;
	return op;
}

static void emit_operation(const char *name, const char *path,
			   struct operation op)
{
	fputs("{\"event\":\"setup\",\"operation\":", stdout);
	json_string(name);
	fputs(",\"path\":", stdout);
	json_string(path);
	printf(",\"return_code\":%d,\"errno\":%d,\"errno_text\":",
	       op.result, op.error);
	json_string(op.error ? strerror(op.error) : "");
	fputs("}\n", stdout);
}

static void read_file(const char *path, struct file_read *r)
{
	int fd;
	memset(r, 0, sizeof(*r));
	r->status = READ_OK;
	fd = open(path, O_RDONLY | O_CLOEXEC);
	if (fd < 0) {
		r->status = OPEN_ERROR;
		r->error = errno;
		open_errors++;
		return;
	}
	while (r->length < MAX_READ_BYTES) {
		ssize_t n = read(fd, r->data + r->length,
				 MAX_READ_BYTES - r->length);
		if (n > 0) {
			r->length += (size_t)n;
			continue;
		}
		if (n == 0)
			break;
		if (errno == EINTR)
			continue;
		r->status = READ_ERROR;
		r->error = errno;
		read_errors++;
		break;
	}
	if (r->status == READ_OK && r->length == MAX_READ_BYTES) {
		unsigned char extra;
		ssize_t n;
		do { n = read(fd, &extra, 1); } while (n < 0 && errno == EINTR);
		if (n > 0)
			r->truncated = true;
		else if (n < 0) {
			r->status = READ_ERROR;
			r->error = errno;
			read_errors++;
		}
	}
	r->data[r->length] = '\0';
	close(fd);
}

static void emit_read(const char *path, bool has_cpu, unsigned int cpu,
		      const struct file_read *r)
{
	const char *status = r->status == READ_OK ? "ok" :
		(r->status == OPEN_ERROR ? "open_error" : "read_error");
	fputs("{\"event\":\"file_read\",\"path\":", stdout);
	json_string(path);
	if (has_cpu)
		printf(",\"cpu\":%u", cpu);
	fputs(",\"status\":", stdout);
	json_string(status);
	printf(",\"errno\":%d,\"errno_text\":", r->error);
	json_string(r->error ? strerror(r->error) : "");
	printf(",\"raw_byte_length\":%zu,\"read_limit_bytes\":%u,"
	       "\"truncated\":%s,\"encoding\":\"byte_escaped\",\"raw\":",
	       r->length, MAX_READ_BYTES, r->truncated ? "true" : "false");
	json_bytes(r->data, r->length);
	fputs("}\n", stdout);
}

static void emit_directory(const char *path, unsigned int cpu)
{
	struct stat st;
	int rc = stat(path, &st);
	int error = rc < 0 ? errno : 0;
	fputs("{\"event\":\"directory_stat\",\"path\":", stdout);
	json_string(path);
	printf(",\"cpu\":%u,\"return_code\":%d,\"errno\":%d,"
	       "\"errno_text\":", cpu, rc, error);
	json_string(error ? strerror(error) : "");
	fputs(",\"exists\":", stdout);
	if (rc == 0)
		fputs("true", stdout);
	else if (error == ENOENT || error == ENOTDIR)
		fputs("false", stdout);
	else
		fputs("null", stdout);
	fputs(",\"is_directory\":", stdout);
	if (rc == 0)
		fputs(S_ISDIR(st.st_mode) ? "true" : "false", stdout);
	else
		fputs("null", stdout);
	fputs("}\n", stdout);
}

static void skip_space(const unsigned char **p, const unsigned char *end)
{
	while (*p < end && isspace((unsigned char)**p))
		(*p)++;
}

static bool parse_cpu_number(const unsigned char **p, const unsigned char *end,
			     unsigned int *value)
{
	unsigned int n = 0;
	const unsigned char *start = *p;
	while (*p < end && **p >= '0' && **p <= '9') {
		unsigned int digit = (unsigned int)(**p - '0');
		if (n > UINT_MAX / 10 ||
		    (n == UINT_MAX / 10 && digit > UINT_MAX % 10))
			return false;
		n = n * 10 + digit;
		(*p)++;
	}
	if (*p == start)
		return false;
	*value = n;
	return true;
}

/* Parse ascending, disjoint Linux cpulist ranges without expanding huge ranges.
 * On malformed/truncated input no CPU subset is presented as authoritative.
 */
static struct cpu_list parse_online(const struct file_read *r)
{
	struct cpu_list list = { .error = "" };
	const unsigned char *p = r->data, *end = r->data + r->length;
	unsigned int previous = 0;
	bool have_previous = false;
	if (r->status != READ_OK || r->truncated) {
		list.error = "online_source_failed_or_truncated";
		return list;
	}
	skip_space(&p, end);
	if (p == end) {
		list.error = "empty_online_list";
		return list;
	}
	for (;;) {
		unsigned int first, last;
		uint64_t id;
		if (!parse_cpu_number(&p, end, &first)) {
			list.error = "invalid_or_out_of_range_cpu_id";
			break;
		}
		last = first;
		skip_space(&p, end);
		if (p < end && *p == '-') {
			p++;
			skip_space(&p, end);
			if (!parse_cpu_number(&p, end, &last)) {
				list.error = "invalid_or_out_of_range_range_end";
				break;
			}
			skip_space(&p, end);
		}
		if (last < first || (have_previous && first <= previous)) {
			list.error = "descending_overlapping_or_unsorted_range";
			break;
		}
		list.total += (uint64_t)last - first + 1;
		for (id = first; id <= (uint64_t)last &&
		     list.selected < MAX_OBSERVED_CPUS; id++)
			list.ids[list.selected++] = (unsigned int)id;
		previous = last;
		have_previous = true;
		if (p == end) {
			list.valid = true;
			return list;
		}
		if (*p != ',') {
			list.error = "invalid_list_separator";
			break;
		}
		p++;
		skip_space(&p, end);
		if (p == end) {
			list.error = "trailing_comma";
			break;
		}
	}
	list.selected = 0;
	list.total = 0;
	return list;
}

static void observe_cpu(unsigned int cpu)
{
	static const char *const attributes[] = {
		"die_id", "die_cpus", "die_cpus_list", "physical_package_id",
		"core_id", "core_cpus_list", "thread_siblings_list"
	};
	char path[160];
	struct file_read r;
	size_t i;
	snprintf(path, sizeof(path), "/sys/devices/system/cpu/cpu%u", cpu);
	emit_directory(path, cpu);
	snprintf(path, sizeof(path), "/sys/devices/system/cpu/cpu%u/topology", cpu);
	emit_directory(path, cpu);
	for (i = 0; i < sizeof(attributes) / sizeof(attributes[0]); i++) {
		snprintf(path, sizeof(path),
			 "/sys/devices/system/cpu/cpu%u/topology/%s", cpu, attributes[i]);
		read_file(path, &r);
		emit_read(path, true, cpu, &r);
	}
}

int main(void)
{
	struct operation dev_dir, dev_mount, console_node, console_open;
	struct utsname uts;
	struct file_read online, r;
	struct cpu_list cpus;
	int fd, rc, error;
	unsigned int i;
	bool truncated;
	setvbuf(stdout, NULL, _IONBF, 0);
	/* Safe native smoke invocation: never mount or power off outside PID 1. */
	if (getpid() != 1) {
		printf("{\"event\":\"probe_begin\",\"schema\":\"die_sysfs_runtime_v1\","
		       "\"pid\":%ld,\"max_cpus\":%u}\n", (long)getpid(), MAX_OBSERVED_CPUS);
		fputs("{\"event\":\"probe_end\",\"reached_end\":true,"
		      "\"setup_skipped\":true,\"reason\":\"requires_pid_1\","
		      "\"contract_verdict\":\"not_evaluated\"}\n", stdout);
		return 2;
	}
	dev_dir = make_directory("/dev");
	dev_mount = mount_fs("devtmpfs", "/dev", MS_NOSUID);
	console_node.result = mknod("/dev/console", S_IFCHR | 0600, makedev(5, 1));
	console_node.error = console_node.result < 0 ? errno : 0;
	fd = open("/dev/console", O_RDWR | O_NOCTTY);
	console_open.result = fd < 0 ? -1 : 0;
	console_open.error = fd < 0 ? errno : 0;
	if (fd >= 0) {
		/* fd can itself be 0/1/2 when inherited descriptors are absent. */
		(void)dup2(fd, STDIN_FILENO);
		(void)dup2(fd, STDOUT_FILENO);
		(void)dup2(fd, STDERR_FILENO);
		if (fd > STDERR_FILENO)
			close(fd);
	}
	printf("{\"event\":\"probe_begin\",\"schema\":\"die_sysfs_runtime_v1\","
	       "\"pid\":1,\"max_cpus\":%u,\"read_limit_bytes\":%u}\n",
	       MAX_OBSERVED_CPUS, MAX_READ_BYTES);
	emit_operation("mkdir", "/dev", dev_dir);
	emit_operation("mount_devtmpfs", "/dev", dev_mount);
	emit_operation("mknod_console", "/dev/console", console_node);
	emit_operation("open_console", "/dev/console", console_open);
	emit_operation("mkdir", "/proc", make_directory("/proc"));
	emit_operation("mount_proc", "/proc",
		       mount_fs("proc", "/proc", MS_NOSUID | MS_NODEV | MS_NOEXEC));
	emit_operation("mkdir", "/sys", make_directory("/sys"));
	emit_operation("mount_sysfs", "/sys",
		       mount_fs("sysfs", "/sys", MS_NOSUID | MS_NODEV | MS_NOEXEC));
	rc = uname(&uts);
	error = rc < 0 ? errno : 0;
	printf("{\"event\":\"uname\",\"return_code\":%d,\"errno\":%d", rc, error);
	if (rc == 0) {
		fputs(",\"release\":", stdout); json_string(uts.release);
		fputs(",\"machine\":", stdout); json_string(uts.machine);
		fputs(",\"version\":", stdout); json_string(uts.version);
		fputs(",\"sysname\":", stdout); json_string(uts.sysname);
	}
	fputs("}\n", stdout);
	read_file("/proc/cmdline", &r);
	emit_read("/proc/cmdline", false, 0, &r);
	read_file("/sys/devices/system/cpu/online", &online);
	emit_read("/sys/devices/system/cpu/online", false, 0, &online);
	read_file("/sys/devices/system/cpu/present", &r);
	emit_read("/sys/devices/system/cpu/present", false, 0, &r);
	read_file("/sys/devices/system/cpu/possible", &r);
	emit_read("/sys/devices/system/cpu/possible", false, 0, &r);
	cpus = parse_online(&online);
	truncated = online.truncated || (cpus.valid && cpus.total > MAX_OBSERVED_CPUS);
	fputs("{\"event\":\"online_selection\",\"parse_ok\":", stdout);
	fputs(cpus.valid ? "true" : "false", stdout);
	fputs(",\"parse_error\":", stdout); json_string(cpus.error);
	fputs(",\"online_cpu_count\":", stdout);
	if (cpus.valid)
		printf("%llu", (unsigned long long)cpus.total);
	else
		fputs("null", stdout);
	printf(",\"truncated\":%s,\"selected_cpu_ids\":[", truncated ? "true" : "false");
	for (i = 0; i < cpus.selected; i++)
		printf("%s%u", i ? "," : "", cpus.ids[i]);
	fputs("]}\n", stdout);
	for (i = 0; i < cpus.selected; i++)
		observe_cpu(cpus.ids[i]);
	/* Sample again so the parent can detect a changed online set, rather than
	 * interpreting files observed at different times as an atomic snapshot. */
	read_file("/sys/devices/system/cpu/online", &r);
	emit_read("/sys/devices/system/cpu/online", false, 0, &r);
	printf("{\"event\":\"probe_end\",\"reached_end\":true,"
	       "\"online_parse_ok\":%s,\"observed_cpus\":%u,\"truncated\":%s,"
	       "\"open_errors\":%u,\"read_errors\":%u,"
	       "\"contract_verdict\":\"not_evaluated\",\"action\":\"poweroff\"}\n",
	       cpus.valid ? "true" : "false", cpus.selected,
	       truncated ? "true" : "false", open_errors, read_errors);
	fflush(NULL);
	sync();
	rc = reboot(RB_POWER_OFF);
	error = rc < 0 ? errno : 0;
	printf("{\"event\":\"poweroff_returned\",\"return_code\":%d,\"errno\":%d}\n",
	       rc, error);
	fflush(NULL);
	/* Returning from PID 1 would panic the kernel if poweroff failed. */
	for (;;)
		pause();
}
