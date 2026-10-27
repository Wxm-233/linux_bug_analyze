# 同版 Btrfs 对象与几何定义：一次有限源码复核

2026-10-12。本稿由独立审阅者手工选择必要定义和局部源码切片，仅复核本阶段材料及 10/11 已读字段链。不执行实验入口、C 代码、编译、Git 或挂载，不访问网络，不新增审计目录。版本和原物身份按 `materials_pre.json` 记录；本次没有独立重算 blob 或校验和。

父版 `0d977e0eba234e01a60bdde27314dc21374201b3` 与修复版 `6f93e834fa7c5faa0372e46828b4b2a966ac61d7` 的 `fs/btrfs/ctree.h` 记录为同一 blob `f07c82fafa046dbba06d04e29b9c920b4f27b04d`，共用 `source/before_ctree.h`（132433 字节）。补存的 `include/asm-generic/unaligned.h` 两版同 blob `1c4242416c9ff6f08d43c1c423d9890bcecbbf92`，共用 `source/before_include__asm-generic__unaligned.h`（2886 字节）。清单记录成功保存两个不同头路径；尝试的 `include/linux/unaligned/le_byteshift.h` 在指定历史版本不存在，记录为缺路径，不计作已读原物。下列同 blob 引用适用于两版；这不代表全部依赖或实际编译配置相同。

## 定义补齐的部分

| 事实 | 手工核对的源码位置 | 能支持的结论 |
| --- | --- | --- |
| `btrfs_sb(sb)` 返回 `sb->s_fs_info` | ctree.h:1035–1038 | 取回函数本身无重新分配或拷贝，连接的是 superblock 当前保存的指针 |
| `fs_info` 的 `nodesize`、`sectorsize` 为 `u32` | ctree.h:982–989 | 缓存使用普通 `u32` 类型标记；未由本轮编译或完整 typedef 树认证 ABI |
| 磁盘结构的 `sectorsize`、`nodesize` 为 `__le32`，结构 packed | ctree.h:224–272，尤其 245–248 | 磁盘字段有 LE 类型标记，与缓存的类型声明不同；packed 表示不能假设每个字段天然对齐 |
| STACK getter 宏返回 `u##bits`，调用 `get_unaligned_le##bits(&s->member)` | ctree.h:1623–1631 | getter 明确调用按位宽命名的 unaligned LE helper；补存 generic 仅给出条件性参考实现 |
| `super_sectorsize` / `super_nodesize` 实例指向各自字段，bits=32 | ctree.h:2401–2404 | 可展开到 `u32 btrfs_super_sectorsize(const struct btrfs_super_block *s)` 及对 `s->sectorsize` 的 `get_unaligned_le32` 调用 |

生成宏和实例是源码中的文字关联。普通 `BTRFS_SETGET_FUNCS` 的 `BUILD_BUG_ON`（1583–1595）不在 STACK 宏中，不能把另一宏的宽度检查移借为当前 getter 已验证的性质。自动入口应核对本次实例的 bits、字段和类型标记，遇到不匹配或缺定义时拒绝认证。

## 局部字段链与对象身份的条件

复用四 C 原物的局部切片可见：super.c:1667 分配 `fs_info`，1672 调用 `btrfs_init_fs_info`；disk-io.c:2977–2981 把 `nodesize`、`sectorsize`、`stripesize` 写为临时 4096。super.c:1709–1710 将该指针交给 `sget`，回调 `btrfs_set_super` 在 `set_anon_super` 返回成功时写 `s->s_fs_info = data`（1549–1554）。`s->s_root` 已存在的分支会释放新建的 `fs_info`；另一分支调用 `btrfs_fill_super`（1716–1726），后者通过 `btrfs_sb(sb)` 取回指针，并把同一 `sb` 交给 `open_ctree`（1334、1359）。`open_ctree` 也通过 `btrfs_sb(sb)` 取得 `fs_info`（disk-io.c:3198）。

因此可以补上“当前 `s_fs_info` 经同版 inline getter 返回”的局部连接；不能仅凭给 `sget` 的实参断言返回 superblock 永远保存本次新建对象。`sget` 的实现、其回调选择、对象生命周期和外部改写没有读取，完整创建到消费的身份仍为条件性路径。

disk-io.c:3236 读取磁盘 superblock；失败、校验算法不支持、初始化校验失败、校验和不通过都会走相应失败出口。通过本次局部路径后，3280 拷贝到 `fs_info->super_copy`，3283 把 `disk_super` 改指向该拷贝；3297 调用的 mount 验证在 2733–2736 转交该拷贝给 `validate_super`。本轮只说明 getter 所用对象与缓存赋值的来源，不能把内存对象模型称为实际磁盘 I/O 或完整格式验证。

父版 `btrfs_parse_options` 调用在 disk-io.c:3317；几何 getter 和缓存写入分别在 3355、3362。修复版分别在 3330、3336、3341。消费者第一形参 `info` 为 `struct btrfs_fs_info *`（super.c:564–565），`max_inline` 分支经 `match_strdup` 成功、`memparse` 得非零值后，使用 `min_t(u64, info->max_inline, info->sectorsize)`（780–795）。这些直接实参/形参和字段表达式支持局部关联；上述行号先后是定位与词法信息，不是 CFG 支配关系或到达定义证明。

检查模板只能表述为：在本次选定 `open_ctree` 的解析调用实际到达非零 `max_inline` 裁剪，且对象绑定、有效 superblock、缓存到消费之间没有未建模改写成立时，裁剪所读缓存应对应这次挂载适用的解码几何。`options` 为空、没有该选项、值为零、字符串分配失败或此前失败出口均不能被计作已发生该字段消费。缓存 `stripesize` 的来源是局部 `stripesize = sectorsize`，不能因同名而自动认成磁盘 `stripesize` getter。

validate_super 的页/扇区分支（disk-io.c:2598–2605）在 4K 页条件下只接受 4K 扇区，在 64K 页条件下接受 4K 或 64K 扇区；其他约束及实际读写适用性仍要满足，不能把任意四字节数学值当受支持配置。`__unused_leafsize` 是独立 `__le32` 字段，2612–2614 的比较通过 `le32_to_cpu`；本轮未补该 helper，不能并入已经认证的 getter链。

## Helper 与运行边界

ctree.h:20 实际写的是 `#include <asm/unaligned.h>`。当前已读材料未提供这个 include 在任何实际架构、配置、生成头目录和编译命令下的解析结果。补存 generic 的 12–15 行定义 `__get_unaligned_t`，通过具有 `__packed` 标记的单字段结构读取指定类型；30–33 行的 `u32 get_unaligned_le32(const void *p)` 返回 `le32_to_cpu(__get_unaligned_t(__le32, p))`。因而这条同版参考路径可明确连到 packed `__le32` 加载与显式 LE→CPU 转换，而非仅依靠 getter 名字。

该版本 generic 没有给本轮 32 位 getter 实现逐字节移位；其 9–10 行还 include `linux/unaligned/packed_struct.h` 和 `asm/byteorder.h`，本轮不继续扩读。不能把 generic 当作真实 `<asm/unaligned.h>` 的已知绑定，也不能把 Python 的四字节 LE 算式称为从此头直接抽出的 C 算式。`le32_to_cpu` 的底层宏、实际架构和配置、`__packed` 属性展开及编译行为保持 unknown。字节模型只能在声明的 LE 表示语义下检验数学解释和与缓存数值关联，不验证该历史内核实际转换实现。缺失的 byteshift 路径已如实记录，不补不存在的原物；无须填满第三个头名额。

必要定义复核已收束；以下入口检查是同一次有限审阅的补段，不另起审计或重跑实验。

## 有限入口的一次静态补核

实现同伴保存最终 `contract.py` / `run.py` 后，审阅者只静态读取两文件一次，并读取事前八项 `expectations_pre.json` 与报告草稿；没有导入或执行入口，没有增加测试。当前冻结范围未发现必改项。

`run.py` 从旧阶段 `source_pairs` 中对应版本的唯一 `facts.records[0]` 取得候选；`derive_template` 的字段、getter 和缓存结构类型来自该记录的 `field`、`source_call.name`、`struct_pointer_type`，而非 `source_expectations`。后者只在派生返回后做观察值对照。它不会重跑旧提取器；手工选择文件、函数、版本、字节输入和模型路径标志仍如实保留。

`contract.py` 核对唯一 STACK 实例、完整生成宏文字形状、由 bits 形成的 `__le<bits>` 磁盘直接字段及 `u<bits>` 缓存直接字段，再核对 generic helper 的显式转换及 packed 加载宏；缺失、歧义或不支持的形状返回 `insufficient`。`btrfs_set_super` 必须匹配完整 `set_anon_super` 调用、`if (!err)` 赋值及返回体，不能只凭同成员命中建立身份。生成结果仍明确实际 arch include、底层端序转换、CFG、外部作用和 `sget` 执行链 unknown，`modeled_object_link` 是手工模型输入，局部 setter/getter 不会自动建立它。

`evaluate_model` 对明确未消费先返回 `not_consumed`；不明消费、未满足前置条件、对象联系未证、模板或字节/数值形式不支持则返回 `insufficient`。两状态的解码、裁剪、缓存失配和行为差异都为 null，不计入数值模型。数值分支分别计算缓存是否等于解码值、`min(requested, cached)` 与 `min(requested, decoded)` 是否不同；小请求可缓存失配但输出相同。`run.py` 分类计数与事前预期对照分列，后验“符合预期”不表示模型通过、行为正确或缺陷标签。

八项预期包含四项数值模型、两项未消费、两项证据不足。两版分别派生候选关联，但共享同 blob 头与旧 setter 参考，并重复使用同一组八项手工输入，预定共 16 次模型求值；这是重复条件性模型检查，不是自动重建两版缓存轨迹、16 个独立样本或真实 C 路径。输出覆写保护、事前输入和恰两个代码文件的哈希门禁可见；本次静态审阅没有运行这些门禁，实际首次执行结果待主任务冻结后取得。

本阶段未独立运行任何代码。实际挂载、硬件 I/O、CPU 架构与 ABI、完整预处理、控制流、外部函数副作用和未知样本泛化均为 unknown。模型通过只能验证人工选定的字节/对象表示及入口行为，不能新增缺陷确认或独立阳性。

既有 12 条保持 6/5/1，新确认 0，独立阳性 0；整体 D2/D3/D4 仍未完成。
