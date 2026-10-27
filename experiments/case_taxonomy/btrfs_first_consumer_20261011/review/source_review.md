# 固定源码的同对象字段链复核

2026-10-11；一次独立人工源码复核。输入仅 `protocol_pre.md`、`materials_pre.json`、`source_identity.json` 与固定 before/after 的 disk-io.c、super.c 四份 saved C。四原物共432093字节，低于512KiB；本次仅核对这四份的字节数/SHA256，全部匹配。未调用Git、网页、模型、编译、旧harness或真实挂载，也未读取头文件/其他报告。入口和消费者由人工指定；此为已读开发例，新增确认0、独立阳性0，原12条6/5/1与整体D2/D3/D4未完成口径不变。

版本来源为已给定的 `source_identity.json`：before=`0d977e0eba234e01a60bdde27314dc21374201b3`，after=`6f93e834fa7c5faa0372e46828b4b2a966ac61d7`；本次未再次查询Git，不声称运行内核身份。以下B-D/A-D分别表示固定before/after disk-io.c，B-S/A-S表示固定before/after super.c。

| 材料 | 字节 | SHA256 | Git blob（已给定身份记录） |
| --- | ---: | --- | --- |
| B-D | 142101 | 55e2c1ca63518484f94e4a461d156292d23fbff4582c4f9c961c55fca3814fc7 | 2f9515dccce0b3452513737eb9d4cd81f0bfa0e5 |
| B-S | 73932 | 866f42dbd643afc4ac292a8dbb0157033644ea1e5ee524b0ae2633bffdd9c47a | 537d90bf5d844b094baeab7a1c2f2e3590320e9f |
| A-D | 142128 | 4c5be7ab508f0aec3af738ac9640a79d3ae6d4ee37f0d6ce6055abd401dfbf7e | 355ea88d5c5f72113924e3bb891c89dcbe9d342b |
| A-S | 73932 | 866f42dbd643afc4ac292a8dbb0157033644ea1e5ee524b0ae2633bffdd9c47a | 537d90bf5d844b094baeab7a1c2f2e3590320e9f |

可确认的直接源码链如下；它是局部文本/参数关系证据，不能提升为完整CFG支配证明。

| 环节 | before | after | 有限结论 |
| --- | --- | --- | --- |
| 初始临时值 | B-D:2868、2977–2981 | A-D:2868、2977–2981 | `btrfs_init_fs_info(fs_info)` 写 nodesize/sectorsize/stripesize=4096、sectorsize_bits=ilog2(4096)；注释声明直到真实superblock值被缓存。临时值不等于磁盘几何。 |
| 初始化到新挂载入口的候选关联 | B-S:1667–1675、1549–1554、1709–1726、1329–1362 | A-S同号 | 分配/初始化fs_info；`sget(...,fs_info)` 的set回调成功时写 `s->s_fs_info=data`；无既有s_root分支调用fill_super，后者调用open_ctree。`sget`与`btrfs_sb`实现不在范围内，完整身份关联保持conditional。 |
| open_ctree持有对象 | B-D:3188–3198 | A-D同号 | 局部指针定义为 `struct btrfs_fs_info *fs_info = btrfs_sb(sb)`。 |
| superblock来源 | B-D:3236–3240、3280–3283 | A-D同号 | 从设备读取disk_super；成功路径将其内容复制进`fs_info->super_copy`，释放原disk_super后令`disk_super=fs_info->super_copy`。未验证访问器/释放函数实现。 |
| 几何值派生与缓存 | B-D:3354–3365 | A-D:3329–3339 | nodesize和sectorsize分别取自superblock访问器；stripesize=sectorsize。相关字段为nodesize、sectorsize、sectorsize_bits、csums_per_leaf、stripesize，另重算两个batch值。 |
| 传递到消费者 | B-D:3317，B-S:564–565 | A-D:3341，A-S:564–565 | 调用第一实参正是open_ctree局部`fs_info`，被parser第一形参`info`接收。调用处未按值复制对象；该直接参数关系成立。 |
| 本轮选定的显式字段读取 | B-S:419、594–603、780–797 | A-S同号 | 识别`max_inline=%s`；match_strdup成功且memparse结果非零时，787–789用`info->sectorsize`参与`min_t(u64, info->max_inline, info->sectorsize)`。该字段在parser内的显式出现只有789；这不证明隐藏宏/被调函数或全程序首次读取。 |
| 缓存与调用的文本次序 | 调用3317先于sectorsize缓存3362 | sectorsize缓存3336先于调用3341 | 修复把superblock派生字段缓存移到选项解析前。before若临时值保留到读取，则限制值来自4096；after若新缓存值保留到读取，则限制值来自S。均须注明条件。 |

消费者的数值含义由人工按通常的memparse/min_t语义解释，未读这些定义、未执行模型：设成功解析的非零值为N、磁盘sectorsize为S，且前置准备通过、各相关调用/宏不覆写字段，则before得到`min(N,4096)`，after得到`min(N,S)`。S=4096或N≤4096时两者相同；只有S>4096且N>4096时才可能出现该差异。不能以这个等式证明实际挂载、泛化检测或独立阳性。

前置与失败边界也必须保留：

- B-D/A-D:2554–2555先读superblock几何；2587–2590检查幂次与范围，2598–2604检查PAGE_SIZE对应限制，2725返回ret，2735把super_copy交给validate_super。open_ctree:3297–3301在验证失败时跳fail_alloc，3304–3305在无root时同样退出。因此任意S>4096不是已证明可达；源码在PAGE_SIZE=4K时只接受4K sector，在PAGE_SIZE=64K时该条件只放行4K/64K，具体编译宏/其他准备条件仍unknown。
- open_ctree:3205–3208准备失败跳fail；3218–3220根分配失败、3224–3226inode分配失败跳fail；3237–3239读super失败、3247–3252不支持checksum、3257–3261 hash初始化失败、3268–3272 checksum失败均跳fail_alloc。这些直接分支在选定parser调用之前，不能写成已消费。
- B-S/A-S:594–595空options跳check；597–603是选项循环；781–795字符串复制失败设置ret=-ENOMEM并跳out；783解析为0时786–790跳过sectorsize读取。不存在max_inline选项、之前选项报错、或以上分支均不能声称完成789读取。字符串分配失败会到1033–1047的out收尾，ret也可能被后续检查改写；不单凭795声称最终必为-ENOMEM。
- parser:1047返回ret；caller before:3318–3320/after:3342–3344在ret非零时保存到err并跳fail_alloc。两版fail_alloc:3687–3693清理并return err；成功return 0在3652。789读取属于成功返回前的选项处理，消费成功或parser返回0都不等于完整open_ctree/挂载成功；后续仍有失败入口。

必须保留unknown：完整CFG及支配关系；`btrfs_sb`/sget的完整新对象身份关联；初始化后至消费者的外部函数、宏或别名改写；访问器/宏的真实定义与构建配置；全程序或被调函数中的首次读取；各路径实际可达与真实运行/挂载结果。只能陈述显式同字段直接传参、局部源码形状与带条件的数值预期。

本轮有限提取结果仅作一次复核；无法在固定材料内证明的事项按unknown收束，不扩文件、不重跑旧18格、不增加重复audit。

## 本轮脚本静态复核补充

初次源码复核结束后，按root追加的范围只读本轮`report.md`、`extractor.py`、`run.py`；报告未见源码语义偏差。脚本初次静态复核确认：提取器只接收两份源码文本及两个人工函数名；目标字段、旧新标签/目标行号仅出现在runner的独立冻结验收中，未传给提取器。不同局部对象按声明绑定区分，直接参数重赋值拒绝绑定；候选始终为`lexical_candidate`，没有从顺序推出ready。条件赋值、一跳局部来源是否到达字段写入、外部副作用和CFG均保持unproven。

初次静态意见指出括号包裹的简单名重赋值/字段使用边界；随后仅对`wrapped_use`、`unevaluated_use`、`name_modifications`、`field_uses`及字段RHS/LHS边界的使用作一次受影响函数复核。修正后的匹配括号展开可识别`((input)) = other()`、`++(input)`、`(p)=other()`，并将`(input->unit)=x`分为write、括号外地址/增量使用分别识别；包围字段span的sizeof/typeof括号分为unevaluated_use。固定四材料的源链不受这些变更破坏。复杂C语法、别名、宏和构建配置仍不在认证范围。另指出的一跳局部赋值展示起点由root处理三行修正：赋值记录返回lhs_start，表达式从该起点保留完整括号；审阅者未再扩读代码或新增fixture。

审阅者未执行脚本/测试，六项期望及固定材料不由审阅者修改。仅一次读取root保存的[results.json](../results.json)复核运行数据：父/修复源码各1项sectorsize词法候选，分别为source_write_after_call/source_write_before_call；六项冻结边界预期一致，括号重赋值为insufficient且0候选，条件赋值仍仅lexical_candidate。运行与代码身份由root保存，本段仅引用结果数据，不是审阅者亲自执行，也不构成盲测、独立阳性、CFG证明或挂载验证。本轮在这些unknown处收束。
