/*
 * /init for the patch_map verification (criteria.md section 2): enable the BPF JIT, load a trivial socket filter
 * three times, print jited_prog_len of each, close them, wait, power off.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/bpf.h>
#include <stdio.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/syscall.h>
#include <unistd.h>

static long sys_bpf(int cmd, union bpf_attr *attr)
{
	return syscall(__NR_bpf, cmd, attr, sizeof(*attr));
}

int main(void)
{
	struct bpf_insn prog[] = {
		{ .code = BPF_ALU64 | BPF_MOV | BPF_K, .dst_reg = BPF_REG_0, .imm = 0 },
		{ .code = BPF_JMP | BPF_EXIT },
	};
	char log[256] = "";
	int fds[3], k, fd;

	setvbuf(stdout, NULL, _IONBF, 0);
	mount("proc", "/proc", "proc", 0, NULL);
	fd = open("/proc/sys/net/core/bpf_jit_enable", O_WRONLY);
	if (fd >= 0) {
		printf("BPF-TEST jit_enable write=%zd\n", write(fd, "1", 1));
		close(fd);
	} else {
		printf("BPF-TEST jit_enable open failed errno=%d\n", errno);
	}
	for (k = 0; k < 3; k++) {
		union bpf_attr attr;
		struct bpf_prog_info info;

		memset(&attr, 0, sizeof(attr));
		attr.prog_type = BPF_PROG_TYPE_SOCKET_FILTER;
		attr.insns = (unsigned long)prog;
		attr.insn_cnt = 2;
		attr.license = (unsigned long)"GPL";
		attr.log_buf = (unsigned long)log;
		attr.log_size = sizeof(log);
		attr.log_level = 1;
		fds[k] = sys_bpf(BPF_PROG_LOAD, &attr);
		if (fds[k] < 0) {
			printf("BPF-TEST load %d failed errno=%d log=%s\n", k, errno, log);
			continue;
		}
		memset(&info, 0, sizeof(info));
		memset(&attr, 0, sizeof(attr));
		attr.info.bpf_fd = fds[k];
		attr.info.info_len = sizeof(info);
		attr.info.info = (unsigned long)&info;
		if (sys_bpf(BPF_OBJ_GET_INFO_BY_FD, &attr) < 0)
			printf("BPF-TEST info %d failed errno=%d\n", k, errno);
		else
			printf("BPF-TEST load %d fd=%d jited_prog_len=%u xlated_prog_len=%u\n", k, fds[k],
			       info.jited_prog_len, info.xlated_prog_len);
	}
	for (k = 0; k < 3; k++)
		if (fds[k] >= 0)
			close(fds[k]);
	printf("BPF-TEST closed\n");
	sleep(1);
	printf("BPF-TEST done\n");
	sync();
	reboot(RB_POWER_OFF);
	return 0;
}
