# SMB 固定输入解封后人工审阅

2026-10-03。修复 `6d44a780635b9b3fb6e20f366ee7750a9adfa884` 的真正目标是 `fs/smb/client/reparse.c:679`：`parse_reparse_wsl_symlink()` 把 `symname_utf16` 作为 `utf8s_to_utf16s()` 的第四个参数时，加上 `(wchar_t *)` 指针强转。父版为 `fac04efc5c793dccbd07e2d59af9f90b7fc0dca4`。提交说明称其用于消除编译警告；补丁没有改变已经显式传入的 `UTF16_LITTLE_ENDIAN`、输入/长度、分配或后续消费者。新增确认案例为 **0**。

两版原 consumer 输出都为 0 candidate / 1 normal / 2 insufficient。工具没有输出 `:679` 的真实补丁目标，因为它是局部输出指针的函数参数，超出“if 条件中的直接结构体小端标量字段读取”规则。候选为零不能写成“目标被诊断正常”、真阴性或整个文件安全；本项也不构成目标 candidate→normal 的独立命中。

| 原输出位置 | 原标签 | 人工核对的含义 |
| --- | --- | --- |
| `parse_reparse_posix():485`，`len < sizeof(buf->InodeType)` | insufficient | 固定大小标量的 `sizeof` 操作数不求值，引用其类型/大小，不读取字段值。附近实际值在 switch 中显式 `le64_to_cpu`，不在原工具 if-only 范围内。 |
| `parse_reparse_wsl_symlink():659`，`len <= sizeof(buf->Flags)` | insufficient | 同样是不求值的大小引用；虽处于目标函数，也没有读取 Flags 或检查 `:679` 输出指针类型。 |
| `parse_reparse_point():722`，`le16_to_cpu(buf->ReparseDataLength) != 0` | normal | 该条件只有一个对应 access，局部显式转换有源码支持。它位于其他 reparse tag 的长度验证分支，与补丁调用点不同，不能扩成整个函数正确。 |

类型诊断与数据表示须分开。目标局部指针声明为 `__le16 *`；同版 `include/linux/nls.h:19` 定义 `wchar_t` 为 `u16`，`:57–58` 的 API 原型要求 `wchar_t *pwcs`，并另接收 `enum utf16_endian`。补丁显式承认这条指针接口的参数类型。提交报告的警告与这些源码声明相符，但具体 compiler/checker、选项和实际警告输出没有重现，不能替提交补出某种诊断机制。

本地 API 实现才是此转换调用的数据格式语义依据。`fs/nls/nls_base.c:117–129` 的 `put_utf16()` 在 `UTF16_LITTLE_ENDIAN` 分支写 `__cpu_to_le16(c)`；`:132–170` 的转换函数按该参数写每个 UTF16 单元，并返回单元数。因此第四参的指针拼写不决定端序；父版已有显式小端选择。该实现和 selector 在两版保持相同，源码没有支持本补丁改变字节格式或修复此前大小端数据失配的链条。这里审阅的是本地 API 格式权威，独立 SMB 外部规范未读取。

值源与消费链是解封后的人工事实，不是原工具自动数据流。已有 `smb2pdu.h:1555–1562` 把 WSL PathBuffer 声明为无 nul 结尾的 UTF-8 字节串。`smb2_parse_reparse_point():736–748` 从调用者提供的 IOCTL `rsp_iov` 及 OutputOffset/OutputCount 取得 buffer；`parse_reparse_point():714–717` 在 LX_SYMLINK tag 分支转入目标。目标转换 ReparseDataLength、扣除 Flags 大小、拒绝嵌入 nul、分配临时输出、处理转换错误，将返回单元数乘二后传给 `cifs_strndup_from_utf16(..., true, ...)`。

补充的 `cifs_unicode.c:334–364` 显示该消费者按 `__le16` 处理 Unicode 输入并调用 `cifs_from_utf16()`；`:195–204` 以 `get_unaligned_le16` 取单元。于是转换端显式选择小端，消费端也解释小端，在补丁前后均有局部源码支持。`smb2ops.c` 的 ops binding 进一步保存了本地入口绑定；没有追完整网络调用、真实服务器 payload、部署配置或设备执行，也不能用“WSL-style”格式名称证明 Linux 正运行在 WSL。

| 五维初码 | 当前支持与未知 |
| --- | --- |
| 时间 | 解封 patch 的 committer 日期为 2024-12-09；发现日、故障引入日与相关间隔未知。`Fixes: 06a7adf318a3` 只保留为提交声明，未扩历史审查。 |
| 架构/平台 | SMB WSL-style symlink 格式上下文；未支持某个 CPU 架构触发，构建诊断环境未知。 |
| 子系统/接口 | `fs/smb/client` 调用共享 NLS UTF8/UTF16 API；边界是输出指针类型、独立格式参数和本地消费者。 |
| 纵向/横向 | 有软件层调用，未确认跨架构纵向或横向故障；分层调用本身不作失配证据。 |
| 引入侧 | SMB 调用点类型注释的警告修复；行为故障引入仍未知，不计确认缺陷。 |

分类为“补丁目标不在原规则覆盖范围，且当前源码不支持它属于行为端序失配机制”。这是对固定输入原输出与解封目标的诚实对照，不计算准确率、总体频率或提速，也不改选其他文件/样本。

本轮每版仅补四份同版源码：`include/linux/nls.h`、`fs/nls/nls_base.c`、`fs/smb/client/cifs_unicode.c`、`fs/smb/client/smb2ops.c`，合计八份；未递归扩配置或追发现日期。`source_manifest_extra.json` 保存原字节 SHA、Git blob、stage 相对路径；`review.json` 的 34 个 source quotes 均含约定的 revision/source_path/saved_path/start_line/end_line/text/sha256/blob_sha1。所有新增 Git stdout/stderr 和准确命令见 `commands_extra.json`。未重跑原 CLI、规则、模型、编译或内核；旧 ocfs2 与本项已锁父输出、协议、选择和原 source/raw 均未修改。
