# 类型角色与复合候选的完整保留

本轮为已读模型输出的开发回放，不新调用模型。新组件为`linux_bug_analyze/candidate_parts.py`，原model_candidate/interface_intent/contract_protocol不改。

## 输入与输出

- 输入：上一轮未经改写的1份模型JSON、单独登记的类型角色清单、已有原始运行/磁盘/配置材料。
- 程序展开顶层及嵌套AND，保留每项原树路径；OR和NOT不拆开。不是删除不通过的子句，也不是把OR分支误作多个必须条件。
- 依每个符号声明的角色检查类型与configuration/observation类别，不通过变量名字猜角色，不给旧错误映射自动改名。
- 根据适配器已核的原始事实对每项计算局部值关系；缺值、错类型、错上下文、模型自报事实均不能作为已核事实。角色清单及适配器字段对应由研究者提供，不是自动语义发现。

## 真实回放结果

原候选7个scope叶、5个relation叶全部保留。原5配置变量仍混用selected_profile（bool），因此7项scope条件均不足。
两个旧父版观测中，每个均有3项算术关系满足、2项含disk_at_deadline的关系不足。未将后采样值或磁盘配置值填成消费时刻参考。

事实适配器取得页面大小65536、磁盘扇区65536、设备数1、原请求集合及各事件request/cache/result/adjacent_disk；每项保留上下文、原文件SHA和行号。mount_flags、selected_profile及disk_at_deadline均未伪造。新类型词表有可供后续新候选使用的page_size/disk_sector_size/device_count等独立角色；这不回溯修复旧候选。

3项算术关系已经被旧操作数解析器检查，故本轮不算新增检测能力；新增作用是保留整个复合候选、细化角色问题、显示每项事实依赖。scope失败时局部计算不批准整条候选，原C/whole_path保持不足，也没有新执行正式契约核心。

## 运行

外层工作区：`python linux_bug_analyze/experiments/case_taxonomy/btrfs_typed_parts_20261025/run.py --output <新的JSON路径>`。
输入、原代码和方法哈希由frozen_inputs.json保护；输出不覆盖。新组件10项边界测试加原53项共63通过。

## 下一步

将有类型的角色清单交给下一次模型生成，保留它的原始候选，再执行相同的完整分解及事实绑定。新版本结果与旧拒判分别记录；不以人工修好的旧JSON充模型成功。随后只针对仍未获得证据的接口关系安排有限审核，保持“接口分析→自动程序”主线。
