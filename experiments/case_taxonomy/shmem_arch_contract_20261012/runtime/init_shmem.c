#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/falloc.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/klog.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <sys/utsname.h>
#include <unistd.h>
#include "layout.h"

#define RAW_LIMIT (1024 * 1024)
static unsigned int failures;

static void string(const char *p)
{
	putchar('"');
	for (; *p; p++) {
		unsigned char c = *p;
		if (c == '"' || c == '\\') { putchar('\\'); putchar(c); }
		else if (c < 32 || c >= 127) printf("\\u%04x", c);
		else putchar(c);
	}
	putchar('"');
}

static void operation(const char *name, const char *path, long rc, int err)
{
	printf("{\"event\":\"operation\",\"name\":"); string(name);
	printf(",\"path\":"); string(path);
	printf(",\"return\":%ld,\"errno\":%d}\n", rc, err);
	if (rc < 0) failures++;
}

static int write_file(const char *path, const char *value)
{
	int fd = open(path, O_WRONLY);
	ssize_t rc;
	int err;
	if (fd < 0) { operation("open_write", path, fd, errno); return -1; }
	rc = write(fd, value, strlen(value));
	err = rc < 0 ? errno : 0;
	close(fd);
	operation("write", path, rc, err);
	if (rc >= 0 && (size_t)rc != strlen(value)) { failures++; return -1; }
	return rc < 0 ? -1 : 0;
}

static void dump(const char *path)
{
	char *buf = malloc(RAW_LIMIT + 1);
	size_t used = 0;
	int fd = open(path, O_RDONLY), err = fd < 0 ? errno : 0;
	ssize_t rc = 0;
	if (fd >= 0 && buf) {
		while (used < RAW_LIMIT && (rc = read(fd, buf + used, RAW_LIMIT - used)) > 0)
			used += rc;
		if (rc < 0) err = errno;
		close(fd);
	}
	if (!buf) { err = ENOMEM; used = 0; }
	printf("{\"event\":\"file\",\"path\":"); string(path);
	printf(",\"errno\":%d,\"bytes\":%zu,\"truncated\":%s,\"raw\":",
	       err, used, used == RAW_LIMIT ? "true" : "false");
	if (buf) { buf[used] = 0; string(buf); } else string("");
	printf("}\n"); free(buf);
}

static int mount_at(const char *type, const char *path, const char *options)
{
	int rc = mount(type, path, type, MS_NOSUID | MS_NODEV, options);
	operation("mount", path, rc, rc < 0 ? errno : 0); return rc;
}

static int probes(void)
{
	char line[1024];
	const char *defs[] = {
		"p:shmem_contract/partial_in truncate_inode_partial_folio folio=$arg1:x64 start=$arg2:s64 end=$arg3:s64",
		"r128:shmem_contract/partial_out truncate_inode_partial_folio folio=$arg1:x64 rc=$retval:u8\n",
		"p:shmem_contract/split_in split_huge_page_to_list_to_order page=$arg1:x64 new_order=$arg3:u32\n",
		"r128:shmem_contract/split split_huge_page_to_list_to_order page=$arg1:x64 new_order=$arg3:u32 rc=$retval:s32\n",
		"p:shmem_contract/xarray_in xas_split_alloc xas=$arg1:x64 entry=$arg2:x64 order=$arg3:u32",
		"r128:shmem_contract/xarray_out xas_split_alloc xas=$arg1:x64 entry=$arg2:x64 order=$arg3:u32",
		"r128:shmem_contract/punch shmem_fallocate mode=$arg2:u32 offset=$arg3:s64 length=$arg4:s64 rc=$retval:s32\n",
		NULL
	};
	int okay = 1;
	for (int i = 0; defs[i]; i++) {
		if (i == 0)
			snprintf(line, sizeof(line), "%s flags=+%lu($arg1):x64 flags1=+%lu($arg1):x64 fmap=+%lu($arg1):x64 findex=+%lu($arg1):u64\n",
				 defs[i], FOLIO_FLAGS_OFFSET, FOLIO_FLAGS1_OFFSET,
				 FOLIO_MAPPING_OFFSET, FOLIO_INDEX_OFFSET);
		else if (i == 4 || i == 5)
			snprintf(line, sizeof(line), "%s shift=+%lu($arg1):u8 node=+%lu($arg1):x64\n",
				 defs[i], XAS_SHIFT_OFFSET, XAS_NODE_OFFSET);
		else snprintf(line, sizeof(line), "%s", defs[i]);
		printf("{\"event\":\"probe_definition\",\"raw\":"); string(line); printf("}\n");
		if (write_file("/trace/kprobe_events", line)) okay = 0;
	}
	return okay;
}

int main(void)
{
	struct utsname u;
	char ch[2], message[2] = { 0x5a, (char)0xa5 };
	int fd, rc, console;
	off_t size = (off_t)1 << PMD_SHIFT;
	off_t offset = ((off_t)1 << PAGE_SHIFT) * 2 + 17;
	long page_size;
	setvbuf(stdout, NULL, _IONBF, 0);
	if (getpid() != 1) {
		puts("{\"event\":\"end\",\"reason\":\"requires_pid1\",\"executed\":false}"); return 2;
	}
	mkdir("/dev", 0755);
	mount("devtmpfs", "/dev", "devtmpfs", MS_NOSUID, NULL);
	mknod("/dev/console", S_IFCHR | 0600, makedev(5, 1));
	console = open("/dev/console", O_RDWR);
	if (console < 0) for (;;) pause();
	for (int i = 0; i < 3; i++) dup2(console, i);
	if (console > 2) close(console);
	puts("{\"event\":\"begin\",\"schema\":\"shmem_chain_v1\",\"pid\":1}");
	uname(&u);
	printf("{\"event\":\"uname\",\"release\":"); string(u.release);
	printf(",\"machine\":"); string(u.machine); printf("}\n");
	page_size = sysconf(_SC_PAGESIZE);
	printf("{\"event\":\"geometry\",\"runtime_page_size\":%ld,\"page_shift\":%lu,\"pmd_shift\":%lu,\"pmd_order\":%lu,\"max_order\":%lu,\"chunk_shift\":%lu,\"head_mask\":%lu,\"xa_nomem\":%lu}\n",
	       page_size, PAGE_SHIFT, PMD_SHIFT, HPAGE_PMD_ORDER, MAX_PAGE_ORDER,
	       XA_CHUNK_SHIFT, FOLIO_HEAD_MASK, XA_NOMEM_ENCODING);
	mkdir("/proc", 0755); mkdir("/sys", 0755); mkdir("/trace", 0755); mkdir("/work", 0755);
	if (mount_at("proc", "/proc", NULL) || mount_at("sysfs", "/sys", NULL) ||
	    mount_at("tracefs", "/trace", NULL) || mount_at("tmpfs", "/work", "huge=always,size=1G"))
		goto finish;
	dump("/proc/cmdline"); dump("/proc/mounts"); dump("/proc/buddyinfo"); dump("/proc/meminfo");
	dump("/sys/kernel/mm/transparent_hugepage/defrag");
	dump("/sys/kernel/mm/transparent_hugepage/shmem_enabled");
	dump("/sys/devices/system/cpu/online");
	if (page_size != (1L << PAGE_SHIFT)) { failures++; goto finish; }
	if (write_file("/trace/tracing_on", "0\n") ||
	    write_file("/trace/current_tracer", "nop\n") ||
	    write_file("/trace/buffer_size_kb", "1024\n") ||
	    write_file("/trace/set_event_pid", "1\n") || !probes())
		goto capture;
	fd = open("/work/sample", O_RDWR | O_CREAT | O_EXCL, 0600);
	operation("create_sample", "/work/sample", fd, fd < 0 ? errno : 0);
	if (fd < 0) goto capture;
	rc = ftruncate(fd, size);
	operation("ftruncate", "/work/sample", rc, rc < 0 ? errno : 0);
	if (rc < 0) { close(fd); goto capture; }
	printf("{\"event\":\"input\",\"file_size\":%lld,\"offset\":%lld,\"write_hex\":\"5aa5\",\"hole_length\":1,\"mode\":%d}\n",
	       (long long)size, (long long)offset, FALLOC_FL_KEEP_SIZE | FALLOC_FL_PUNCH_HOLE);
	if (write_file("/trace/events/shmem_contract/enable", "1\n") ||
	    write_file("/trace/tracing_on", "1\n")) { close(fd); goto capture; }
	rc = pwrite(fd, message, 2, offset);
	operation("pwrite", "/work/sample", rc, rc < 0 ? errno : 0);
	if (rc == 2) {
		rc = fallocate(fd, FALLOC_FL_KEEP_SIZE | FALLOC_FL_PUNCH_HOLE, offset, 1);
		operation("punch_hole", "/work/sample", rc, rc < 0 ? errno : 0);
		rc = pread(fd, ch, 2, offset);
		operation("pread", "/work/sample", rc, rc < 0 ? errno : 0);
		if (rc == 2) {
			printf("{\"event\":\"readback\",\"hex\":\"%02x%02x\"}\n", (unsigned char)ch[0], (unsigned char)ch[1]);
			if ((unsigned char)ch[0] != 0 || (unsigned char)ch[1] != 0xa5) failures++;
		} else failures++;
	} else failures++;
	write_file("/trace/tracing_on", "0\n");
	close(fd);
capture:
	write_file("/trace/tracing_on", "0\n");
	dump("/trace/kprobe_events"); dump("/trace/kprobe_profile");
	dump("/trace/per_cpu/cpu0/stats"); dump("/trace/trace");
	dump("/proc/buddyinfo"); dump("/proc/meminfo");
finish:
	{
		char *buf = malloc(RAW_LIMIT + 1);
		if (buf) {
			rc = klogctl(3, buf, RAW_LIMIT);
			printf("{\"event\":\"dmesg\",\"errno\":%d,\"raw\":", rc < 0 ? errno : 0);
			buf[rc < 0 ? 0 : rc] = 0; string(buf); puts("}"); free(buf);
		}
	}
	printf("{\"event\":\"end\",\"failures\":%u,\"reached_end\":true,\"contract_verdict\":\"not_evaluated\"}\n", failures);
	fflush(NULL); sync(); reboot(RB_POWER_OFF);
	for (;;) pause();
}
