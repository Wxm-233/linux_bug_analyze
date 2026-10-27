# D1 / N2.25：ocfs2 父版来源与消费资格复核

2026-10-23。独立助手的手工研究复核，不是项目主模型输出或人类专家金标准。唯一 primary 为 `ocfs2_dinode_has_extents()` 的 `di->i_flags` 读取。按 `protocol_pre.json/source_reuse.json` 只读九份已归档父版，版本 `390ac56cf0f687de53695648bc6f2259a7eae429`；路径和行号以下均指旧归档 `cross_subsystem_facts_20261003/ocfs2/sources/parent/`。本轮不读修复、不补源、不运行组件、测试、编译、挂载、内核或外部模型。该接口此前已读补丁并开发专用规则，本复核不称盲测或新增案例。

## 1. 本轮可采用的窄契约

在该版本的小端磁盘 inode 格式中，如果该次实际读取仍是格式规定的 `i_flags`，且消费者要判断主机语义的类型标志，那么字段与掩码必须处于可比表示。可以转换字段再与主机掩码比较，也可以把掩码转成字段表示；不能把“未见 `le32_to_cpu`”一概当作错误。

这项要求来自同版格式声明、标志用途和实际消费者，**不以修复代码或多数架构为唯一规范**。完整外部格式标准和实际构建中的有效类型/宏绑定，本轮未认证。

## 2. 字段、实际对象与用途

| 父版原文 | 可支持的关系 | 不能提升的结论 |
| --- | --- | --- |
| `fs/ocfs2/ocfs2_fs.h:660–678` | 明称 `struct ocfs2_dinode` 为 on-disk inode，`i_flags` 声明为 `__le32` | 类型声明不独立证明任意传入 buffer 合法或实际来自磁盘 |
| 同头文件 `:207–221` | 说明该字段的标志，primary 使用的四项为 `0x20/0x40/0x400/0x800` | 标志名称及数值不证明某个实际磁盘块具备这些值 |
| `fs/ocfs2/inode.c:201–206` | `di->i_flags` 与四个普通整数标志的合并掩码作位与；非零直接返回“不含 extent” | 此处是本次唯一 primary，不将其他两类读取或全函数一起计数 |
| `fs/ocfs2/ocfs2_fs.h:726–735` | `id2` 是 extent list、super、local alloc、chain、truncate log、inline data、symlink 等共用 union | 不能任取 union 内容当作 extent list 正常输入 |
| `fs/ocfs2/inode.c:1577–1584,1637–1649` | repair 函数把传入 `bh->b_data` 转成 `di`，传同一个 `di` 给 primary；返回真后才以 `id2.i_list` 比较记录上限，可能赋值，随后计算 ECC/标脏 | 这是同一参数/显式字段链的源码依据，不是磁盘损坏、实际写回或跨过程别名完整证明 |

架构差异是：相同小端存储字节在不同主机端序下成为不同本机整数表示，而上述公共文件系统代码使用相同普通整数掩码。`include/linux/byteorder/generic.h:88–89` 连接转换名称；所给大端头 `:34–35` 经 `__swab32`，小端头 `:34–35` 为表示转换。该材料支持**有端序条件的解释差异**；没有实际编译单元、架构 include 闭合或新运行，不能说本轮已证明某个大端内核触发。

## 3. 来源到该次读取：有条件的真实源码链

- 上游 `fs/ocfs2/filecheck.c:405–443` 的 FIX 入口将 `OCFS2_FI_FLAG_FILECHECK_FIX` 交给 `ocfs2_iget`。`inode.c:145–158` 只有取得 `I_NEW` inode 时才走 `ocfs2_read_locked_inode`；缓存 inode 可绕过。
- `inode.c:520–522,545–595` 按系统文件、orphan recovery、本地挂载及锁结果区分路线。可锁路径的 FIX 分支调用 `ocfs2_filecheck_read_inode_block_full(..., type=1)`；其 `:1671–1675` 把 repair 函数作为 `ocfs2_read_blocks` 的 callback。不可锁路线在同步读取成功、非 journal buffer 等条件下直接调用 repair。
- `buffer_head_io.c:231–245` 将 `bhs[i]` 作为本次 `bh`；`:326–330` 可设置 needs-validate 并提交 READ，`:361–384` 等待/检查后，把同一个 `bh` 传给 `validate(sb,bh)`。这是显式 buffer 参数关系。`:283–312` 的 journal、dirty、readahead 等分支可跳过提交，不能将一次 read 函数调用等同于一次真正磁盘 READ；同步读取 `:89–150` 也有 journal/dirty 跳过。
- repair 对象来自该 callback 的 `bh->b_data`。但它首先调用 validate，验证成功在 `inode.c:1583–1584` 就返回；失败后仍需非只读、非 journal、有效签名及保留 VALID_FL（`:1589–1615`）才能到 primary。因此不是所有读取、所有 filecheck 请求或所有损坏块都消费这个 primary。

**关键值边界：** `ocfs2_filecheck_validate_inode_block:1523–1529` 明确说明 meta-ECC helper 可修复数据。该 helper 体不在九文件内。repair 到 primary 之间没有显式 `i_flags` 赋值，并不证明 ECC 后仍是磁盘最初位值；该字段在 helper 前后的值稳定性未闭合。可保留局部同一 `bh/di` 源码参数链，不能把它升级为“磁盘字节一直不变地流到该运算”的完整效果证明。

## 4. 清单内是否有真正的写入者

不能简单写“清单没有任何写者”：

- `inode.c:710–720,758–767` 的 `ocfs2_remove_inode` 对 `di_bh->b_data` 中的 `i_flags` 执行 `&= cpu_to_le32(~(VALID_FL | ORPHANED_FL))`，然后 journal dirty。这是明确的、与小端表示一致的**局部修改**，不是主机 `struct inode::i_flags`；两者不能混淆。
- `buffer_head_io.c:38–83` 有整块 WRITE 提交；`:428–452` 也有 super/backup 的 ECC 与 WRITE。repair 的 `inode.c:1639,1648–1649` 还写 extent 记录计数、ECC 并标脏。

但是，本清单没有闭合 primary 所涉及特殊类型位的**创建/初始化与编码写者→具体存储块→本次 READ/缓存 buffer→该次 primary**。删除时清除 VALID/ORPHAN、泛型块写入和 repair 的 id2 写入，均不能替代这条来源证明。故“存在局部写操作”可支持，“本次 primary 输入具有完整已证写读链”仍为 insufficient；本轮不再追 writer/helper。

## 5. 合法非空输入与正常边界

语义域并非任意捏造：格式头 `:350–369` 的系统 inode 表给出实际格式类别与 LOCAL_ALLOC、CHAIN、DEALLOC 等标志组合；primary 的注释及 union 定义说明这些位用于区别 `id2` 的解释。这足以支持**非空的局部标志语义域及表示检查开发**，但该表不是写入实现，更不证明某一特殊 inode 确实通过 filecheck 的所有门槛。不能只填写一个非零 flags 值就称完整合法触发。

本轮仅有静态构建范围：`fs/ocfs2/Kconfig:2–11` 定义依赖和选择；`Makefile:4–6,11–44` 把 inode、buffer_head_io、filecheck 纳入同一模块。没有解析完整 Kconfig、实际配置/预处理、有效大端入口、挂载实例或内核执行。

积极正常关系应限于具体读取：同函数 `inode.c:208` 的 `i_size` 非零和 `i_clusters==0` 在合法固定宽度字节置换下保持真值；`inode.c:398–409` 则提供字段与 `cpu_to_le32(MASK)` 同表示相与的源码示例。它们不证明同一个复合条件、整个函数或挂载路径正常；特别 `:208` 另有 `i_mode` 运算，本轮不纳入 primary、也不由零判断正常替它背书。

## 6. 分层准入建议与停止点

| 层级 | 本轮裁定 |
| --- | --- |
| 存储表示→主机整数位判断的局部契约、所选字段/消费位置和非空语义域 | **可用于已读最小迁移设计**，以有效格式与生效端序语义为显式条件 |
| primary 返回值参与同一 `di` 的 union 消费 | 源码支持；路径条件和 helper 效果必须保留 |
| 全函数含义、完整创建写者→存储→该次读取、实际合法 filecheck 非空触发 | **insufficient**，不能为通过而改称完整写读或实际正常实例 |
| 实际大小端内核不对称暴露、完整统一自动检查、独立评价 | **未证明**；本接口已读且经历专用规则开发，不新增独立正/正常分母 |

建议后续仅在冻结最小协议后核对“已有程序从原材料得到哪些事实、人工提供了哪些格式/用途条件、哪些关系仍不足”。历史 endian 专用 checker 的成绩不能替代统一方法迁移；旧缩小原型的运行不算本轮新增。到此完成本工作单元的源码资格审查，不补新源码或扩大挂载/内核实验。
