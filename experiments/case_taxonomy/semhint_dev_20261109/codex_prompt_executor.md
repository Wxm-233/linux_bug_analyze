你在 linux_bug_analyze 项目里接一个编码任务，由 Claude 派给你。用中文写日志和最终回复。

## 背景（先读）
- `../交接文档.md` 第一、三、六节（规则、WSL 用法、禁止事项）；
- 本轮判据：`experiments/case_taxonomy/semhint_dev_20261109/criteria.md` 第五、六节（用例怎么执行、观测什么）；
- 上一轮的测试程序可参考、可复制代码：`experiments/case_taxonomy/difftest_known_20261109/harness/`（`dt_init2.c` 的探测段 probe、JSON 输出、关机；`mk_initramfs2.sh`、`run_qemu2.sh`）。

这是防御性研究：内核只在 WSL 里的 QEMU 虚拟机中运行，比较 riscv 与 arm64、x86_64 对同一系统调用的答复。

## 要写的文件（都放在 `experiments/case_taxonomy/semhint_dev_20261109/harness/`）

### 1. `sh_init.c`：initramfs 的 /init，同一份源码静态编译到 riscv64、aarch64、x86_64
启动后：
1. 挂载 proc、sysfs、devtmpfs（/dev）、tmpfs（/tmp）。
2. 输出 `@@SH BEGIN`，然后照抄 `dt_init2.c` 的探测段（PMU 列表、PMU 事件、cpuinfo），JSON 每行一条。
3. 记下 `/proc/sys/kernel/tainted`。
4. 读 `/cases.txt`，逐行执行用例（格式见下），每个用例输出一行 JSON。
5. 输出 `{"taint_changed": 0|1}`、`@@SH END`，`sync`，`reboot(RB_POWER_OFF)`。
每行输出后 fflush。

### 用例文件格式（`/cases.txt`，每行一个用例，空格分隔）
```
<id> <nr> <tmpl> <a0> <a1> <a2> <a3> <a4> <a5>
```
- `id`：十进制编号；`nr`：本架构的系统调用号（十进制，可为负）。
- `tmpl`：`none`，或 `occ:<ai>:<li>`，或 `adj:<ai>:<li>`（ai、li 为参数下标 0–5）。在参数全部解析成数值之后、发起调用之前：
  - `occ`：在 `addr & ~4095` 处用 `mmap(MAP_FIXED_NOREPLACE|MAP_PRIVATE|MAP_ANONYMOUS, PROT_READ)` 映射 1 页，addr 为第 ai 个参数的数值；
  - `adj`：在 `(addr + len + 4095) & ~4095` 处同样映射 1 页，len 为第 li 个参数的数值；
  - 映射失败或返回的地址不等于请求的地址，记 `"t":0`，否则 `"t":1`；`none` 记 `"t":-1`。不管成败都继续发起调用。
- 每个参数一个记号：
  - `i:<十六进制>`：64 位整数，原样传入；
  - `b:<fill>:<off>`：新建一个“主缓冲区”，传入其起始地址加 off（十进制，可为 0 到 8191）。主缓冲区为 2 页可读写，后接 1 页 PROT_NONE（越界即出错）。fill 为 `z`（全 0）、`a`（全 0xAA）、`g`（指针图，见下）；
  - `o:<fill>:<bit>`：同上新建主缓冲区，传入 `起始地址 | (1UL << bit)`（bit 为 0–63）；
  - `f:<kind>`：文件描述符，kind 为
    - `file`：O_RDWR 打开 `/tmp/f`；`dir`：O_RDONLY|O_DIRECTORY 打开 `/tmp/d`；
    - `piperd`：pipe2(O_NONBLOCK) 的读端，事先往写端写 16 字节；`pipewr`：另一个 pipe2(O_NONBLOCK) 的写端；
    - `ustream`：socketpair(AF_UNIX, SOCK_STREAM|SOCK_NONBLOCK) 的一端，对端已发送 16 字节；
    - `udgram`：socketpair(AF_UNIX, SOCK_DGRAM|SOCK_NONBLOCK) 的一端，该端先开 SO_PASSCRED，对端再用 sendmsg 发送 16 字节，附带一个 SCM_RIGHTS（传 `/tmp/f` 的 fd）；
    - `eventfd`：eventfd(0, EFD_NONBLOCK)；`memfd`：memfd_create("m", 0) 并 ftruncate 到 4096；`udp`：socket(AF_INET, SOCK_DGRAM|SOCK_NONBLOCK, 0)，不绑定；
    - `neg`：-1；`unopen`：1000；`atcwd`：AT_FDCWD；
  - `p:<kind>`：路径字符串指针，kind 为 `f`（"/tmp/f"）、`d`（"/tmp/d"）、`nx`（"/tmp/nonexist"）、`empty`（""）、`null`（NULL）。字符串放在单独的缓冲区里；
  - `s:self`：子进程自己的 pid。
- **指针图 `g`**：用以用例 id 为种子的 xorshift64 伪随机数（种子 = id * 0x9E3779B97F4A7C15 + 1，三个架构必须得到完全相同的序列）。主缓冲区先全部填 0xAA，再把前 8 个 8 字节字逐个决定：随机数最低位为 1 时填“池”里某个槽的地址，否则填 64。池：每个用例一个 64 页的区域（各页可读写），槽 k 为第 k 页；第 0–31 槽的前 8 个字同样按指针图规则填（只能指向第 32–63 槽），其余字节 0xAA；第 32–63 槽全 0xAA。槽号用随机数取模。只在用到 `g` 的用例里建池。

### 每个用例的执行
1. 父进程 fork；子进程：把 0、1、2 重定向到 /dev/null；chdir("/tmp")；重建 `/tmp/f`（4096 字节 'x'）和目录 `/tmp/d`（已存在则保留）；建所需的 fd、缓冲区、池、模板；
2. 调用前，给每个主缓冲区（3 页中前 2 页）和池做快照；
3. `long r = syscall(nr, a0..a5)`，立刻保存 errno；
4. 观测：每个主缓冲区，统计与快照不同的字节**位置**，输出位置数和这些位置（4 字节小端无符号数序列）的 FNV-1a 32 位哈希；池整体也统计一次（位置按池内偏移）；
5. 子进程把结果写进与父进程之间的管道后 `_exit(0)`。父进程最多等 500 毫秒（轮询 waitpid WNOHANG，每次 1 毫秒），超时就 SIGKILL 并记 `timeout`；子进程被信号终止记 `SIG<名>`（用 sigabbrev_np）；子进程正常退出但没写结果记 `noresult`。
- **返回值规整**：r == -1 时记 errno 名（strerrorname_np）；r ≥ 0 时，若等于某个参数的数值，记 `argK`（K 取最小下标）；否则小于 65536 记十进制数，大于等于记 `big`；其他负值记 `neg`。
- **输出**：`{"id":12,"r":"ENOENT","t":-1,"b":[[0,8,"1a2b3c4d"],[3,0,"811c9dc5"]],"pool":[0,"811c9dc5"]}`，`b` 只列主缓冲区参数，按参数下标；没有池时 `"pool":null`。

### 2. `mk_initramfs.sh <riscv|arm64|x86_64> <cases.txt 的路径> <输出 cpio>`
交叉编译 `sh_init.c`（`riscv64-linux-gnu-gcc`、`aarch64-linux-gnu-gcc`、`x86_64-linux-gnu-gcc`，`-static -O2 -Wall`），与用例文件一起打包成 newc cpio（含 dev、proc、sys、tmp 目录），旁边写 `.init.sha256`。

### 3. `run_qemu.sh <arch> <内核镜像> <initramfs> <日志>`
同 `run_qemu2.sh` 的 QEMU 参数（riscv `-cpu rv64,sscofpmf=true -bios default`，arm64 `-cpu max`，x86_64 `-M q35 -cpu max`，单核，512M，`panic=-1 quiet`），超时 3600 秒，结束打印退出码和 JSON 行数。

### 4. `parse_log.py <日志>`
解析日志，输出 JSON：`{"probe": {...}, "cases": {"<id>": [r, t, b, pool], ...}, "taint_changed": ..., "complete": true|false}`，`complete` 表示看到了 `@@SH END`。

### 5. 自测 `harness/selftest/`
- 手写一份小用例文件 `selftest_cases_<arch>.txt`（三个架构的系统调用号各不相同，请从各自的 unistd 头文件取），覆盖每一种记号、三种 fill、三种模板，至少包括：getpid（`argK` 不应出现，应为数字）、read 从 `f:piperd` 读到 `b:a:0`（应改写 16 个位置）、`syscall(-1)`、一个会超时的调用（例如在 `f:pipewr` 的另一端……请自己选一个确定会阻塞的，如对空的阻塞管道 read——可以加一种你需要的方式，但不要改上面已定的记号含义）、一个会 SIGSEGV 的调用不好造就算了；mmap 配 `occ` 模板；recvmsg 在 `f:udgram` 上配 `b:g:0`；
- 在当前版本三个内核上各跑一次（WSL 中：`/root/work/boundary_build/riscv_defconfig/arch/riscv/boot/Image`、`/root/work/boundary_build/arm64_defconfig/arch/arm64/boot/Image`、`/root/work/boundary_build/x86_64_defconfig/arch/x86/boot/bzImage`），产物放 `/root/work/semhint/selftest/`；
- 检查：三个架构都 `complete`；同一用例 id 在三个架构上的指针图内容一致（可以加一个只在自测时打开的调试输出，例如环境变量或用例文件第一行的开关，打印主缓冲区前 64 字节里哪些字是指针——正式运行不打开）；把检查结果写进 `harness/selftest/selftest_result.md`，并报告每个用例的平均耗时（毫秒），我要用它估算预算。

## 限制
- 只写上面列出的文件，不改本轮其他文件（`criteria.md`、`static/`、`gen/` 由 Claude 写），不改旧轮次；
- 不运行正式用例（`gen/` 下的文件），不构建内核，不安装软件，不联网；
- WSL 命令按交接文档第三节：写成 `.sh` 再用 `wsl -u root -- bash /mnt/d/...` 运行，第一行 `source .../tools/wsl_env.sh`；
- 不读密钥和配置文件（`~/.codex/`、`~/.claude/`、`settings.toml`）；
- 在 `experiments/codex_worklog.md` 末尾追加你的工作记录；不 git commit。

## 最终回复
列出写了哪些文件、自测结果（每个架构是否 complete、哪些检查没通过）、每个用例的平均耗时、你对格式或做法的疑问（例如你觉得规格里有不合理的地方，请指出，但不要自行改变已定的记号含义）。
