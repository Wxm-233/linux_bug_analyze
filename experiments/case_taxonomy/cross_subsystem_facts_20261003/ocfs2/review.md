# 已读 ocfs2 接口：事实—契约—消费清单

2026-10-03。本清单只纳入 `ocfs2_dinode_has_extents()` 的 `i_flags` 读取；它是以前读过的开发接口，新增案例为 **0**。未修改的原 CLI 回放仍得到父版全文件 3 candidate / 10 normal / 0 insufficient、修复版 0 / 13 / 0。该总数只作背景；`i_mode`、`i_dyn_features` 不升级为这轮 primary，不把一次修订中的多个读取当成多个独立案例。

父版解析为 `390ac56cf0f687de53695648bc6f2259a7eae429`，修复版为 `c9dff86eb78a4b6b02b1e407993c946ccaf9bfb4`。目标源码全文 SHA 分别为 `3984db38126ebc1d0066baec311a456b36561eb884ec3281d093e0b02a901dea` 和 `fcfdc2956191ebd8498e9a7be6d8442aeb475d5d8f36e828dc6a9f0b6132feb6`。同版保存的 `ocfs2_fs.h` SHA 为 `2c5ef8d4e9096064c95321b6fff9cb909954d7bdffb47db7bfc075baf3d80942`；每份全文的 Git blob、SHA 和路径见 `source_manifest.json`，每项审阅的行号、原文片段及相同标识见 `facts.json` 的 R1–R13。

| 固定站点 | 父版原输出 | 修复版原输出 | 本轮解释 |
| --- | --- | --- | --- |
| primary：`inode.c:204`，`di->i_flags` | candidate，直接位掩码 | normal，`le32_to_cpu(di->i_flags)` | 局部表示契约在假定大端实现适用时得到源码支持；实际大端运行未知 |
| 正常对照：同函数 `i_size` | `:208` 非零/存在性读取，normal | `:209` 显式转换，normal | 零与非零不受字节交换影响，该次读取在父版已正常 |
| 辅助对照：同条件 `i_clusters` | `:208 == 0`，normal | `:210 !le32_to_cpu(...)`，normal | 同样只证明这次零判断的局部正常 |
| 已有上下文：`ocfs2_populate_inode()` 的 `i_flags` | `:398 & cpu_to_le32(OCFS2_SYSTEM_FL)`，normal | `:400` 同表达式，normal | 掩码与磁盘字段采用相同表示，不另计 primary/案例 |

原工具确实提取的是结构体参数和字段声明（`ocfs2_fs.h:678` 的直接 `__le32 i_flags`）、条件原文、读取所在函数/行号、受限语法分类及理由、两层 quoted includes 的实际读取清单与 SHA。它没有展开宏、求取值域、追踪 buffer 赋值、调用者或磁盘 I/O，也没有证明配置、ABI、外部规范或运行故障。两版的 `raw/parent.json`、`raw/fix.json` 完整保留原 stdout；并未替换 getter、导入算法后改写行为或把审阅信息塞进原工具输出。

人工核对了当前 primary 和所选正常对照的实际 access occurrence：每个对应条件中的 `di->i_flags`、`di->i_size`、`di->i_clusters` 各出现一次。原工具通过整个条件中的同文本匹配转换而不是对每个 occurrence 作完整语义绑定，这个一般边界仍保留；本轮三个简单读取没有触发重复同文本的混淆。父版正常对照所在的同一条件还有单独的 `i_mode` 候选，因此不能把局部 normal 扩大成整个条件或函数正确。

人工契约依据有三层。首先，同版 `ocfs2_fs.h:660–678` 明确称此结构为磁盘 inode，`i_flags` 是小端 32 位字段。其次，`:215–221` 的四个宏为普通整数常量 `0x20`、`0x40`、`0x400`、`0x800`，合并为 `0x00000c60`；该数值和这些常量的解释是人工阅读结果，原检查器只认出位掩码模式。最后，同版 `generic.h:88–89` 及 UAPI 大/小端 byteorder 头说明 `le32_to_cpu` 在大端实现中交换字节、在小端实现中只作表示转换。因而大端条件下，父版对磁盘原字直接取 host mask 的关系与其本地契约不符；修复版在该读取明确转换。这里的结论不依赖最终补丁决定父版标签，也不通过增加非零合成输入来演示结果。

真正的消费者不是通常 inode 读取完成后的任意路径。同版 `git grep` 在 `fs/ocfs2` 仅找到函数定义和一个直接调用：父版 `inode.c:1637`，修复版 `:1639`，位于 `ocfs2_filecheck_repair_inode_block()`。它先在 `bh->b_data` 上取得 `di`。验证成功立即返回；验证失败后，还须非硬/软只读、非 journal buffer、有效签名、保留 `OCFS2_VALID_FL` 才到 primary。块号和 fs generation 可在此前修复，`i_flags` 未在这段路径先转换或重写。

返回真时，调用者把 `id2` 当作 extent list 比较 `l_next_free_rec` 和 `l_count`，可能改写前者，然后重新计算 ECC 并标脏。`ocfs2_fs.h:726–735` 说明同一个 `id2` 是 `i_super/i_lab/i_chain/i_list/i_dealloc/i_data/i_symlink` 共用的联合体，目标函数注释也明确要排除其他 `id2` 表示。这个消费动作使表示关系具有实际本地意义，但未观察到磁盘损坏，也未证明某种真实特殊 inode 经过所有门槛。

磁盘值源也由人工审阅取得。`ocfs2_filecheck_read_inode_block_full()` 在 repair type 分支把 repair 函数作为 callback 传给 `ocfs2_read_blocks()`。后者在 `buffer_head_io.c:231–245` 获取 inode block buffer，按缓存/脏/journal 条件决定读；`:326–331` 提交 READ，`:361–384` 等待成功并在 needs-validation 时调用 `validate(sb, bh)`。它存在缓存或跳过路径，所以保存的是有条件的磁盘→buffer→修复读取链，不能把函数名或 `__le32` 当成实际 I/O 的证明。

上游局部入口为 filecheck 的 fix sysfs 操作：`filecheck.c:405–443` 传 `OCFS2_FI_FLAG_FILECHECK_FIX` 给 `ocfs2_iget()`；只有 `I_NEW` inode 才到 `ocfs2_read_locked_inode()`。后者按 `can_lock` 选择 callback 路径或同步读后直接 repair 路径。缓存 inode 可绕过这个修复链；真实设备、挂载、sysfs 调用、验证失败及 callback 到达都未执行。本轮仅保存这些本地源码与必要注册证据，不执行 filecheck。

配置范围也限于源码。`OCFS2_FS` 是 tristate，依赖 `INET && SYSFS && CONFIGFS_FS`；Makefile 把 `inode.o`、`buffer_head_io.o`、`filecheck.o` 纳入 ocfs2。当前目标和 caller 没有 `CONFIG_OCFS2_DEBUG_FS` 包围。保存的 PowerPC endian choice 与 `asm/byteorder.h` 说明存在相应源码实现分支；没有求解完整 Kconfig、运行预处理、编译大端内核、挂载或验证硬件执行。因此 support flags 把“本地表示/掩码/消费者链/源码配置范围支持”与“真实大端路径、外部格式规范、实际 flags 和损坏未知”明确分开。磁盘格式的独立外部规范未审阅，不能说它已由类型声明自动认证。

执行命令、cwd、返回码、stdout/stderr 文件及字节 SHA 完整保存在 `commands.json`。`runner.py` 在 Ubuntu WSL 使用原脚本的原 CLI，原脚本 SHA 前后均为 `71e50604221ff0b68ac44039ca64606253e32e6b0a136206aea768e329bd467c`；根事前协议 SHA 前后均为 `1177e42163992884eed62023cab877e636f2e137d4664c0f0fbbfc795d21b44f`。脚本仅直接导入标准库，直接导入模块来源的哈希前后一致；这不是递归依赖闭包。原工具实际读取的每份源码 SHA 都与保存的同版全文一致。WSL localhost/NAT 的含 NUL transport 提示不参与 Git stdout 或 SHA 识别。

未修改旧脚本、旧 JSON、freeze、Word、TODO 或日志；未新增模型、编译、运行验证、样本或输入网格。本轮锁定后等待独立只读方法审阅，综合冻结与日志由根任务负责。

锁定前完整性检查通过：86 份源码的全文 SHA 和 Git blob（按保存的原字节重算对象 ID）、190 条命令的 stdout/stderr SHA、64 个人工审阅摘录的行号/原文绑定、两版自动摘要在原输出中的身份，以及旧脚本/协议运行前后一致性。两份回放原 JSON 还逐项等于已有开发 JSON。`verify_artifacts.py` 只验证这些材料完整性，没有新增检测规则、内核样本或执行实验。
