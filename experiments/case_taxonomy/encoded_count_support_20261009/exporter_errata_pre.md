# 新Git取证前的导出脚本修订

原元数据选择/规则冻结12b521c4…92be4a保留，尚未执行新Git。独立方法审阅指出：原prepare.py用fullmatch读取quoted include，会跳过带尾部注释的literal include，进而可能错误取第三条。此偏差修为捕获literal前缀的match，计数仍为原顺序前两条，不推断预处理条件。其他词法/头适用性限制保留。

原prepare.py及原freeze不覆盖。另存prepare_v2.py，仅修改此匹配方法并让export核对新的元数据/code锁及方法审阅身份；v2在执行前同时校验原锁和新锁。选择队列、16元数据、父路径排序/3文件/4命令额度、无C和missing停止规则不变。新freeze_metadata_v2_pre.json纳入原全部冻结项、原冻结自身、v2脚本与本勘误。独立方法v1拒批记录保留，v2重新审阅后才允许唯一导出。本勘误不是失败Git/规则运行。
