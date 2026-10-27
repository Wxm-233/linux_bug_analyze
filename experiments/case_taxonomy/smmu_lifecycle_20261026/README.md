# SMMU附着/撤销生命周期有界补证

## 10月26日 最新进展：SMMU组附着事务与解绑前置条件

继续深入SMMU生命周期，未切新接口。固定父版原始group set/remove与PASID attach/detach四函数编译后，9种分支通过：正常附着、三个位置失败、已有映射、插入失败、无group、无set操作、正常解绑。结果保存逐事件映射存在性及模拟锁状态；回滚对全部组成员调用remove，再删除PASID映射。驱动remove通过该映射取得通用SVA对象，因此发布/清理/撤销顺序属于对象可查找性的要求，不能只检查最终返回值。

源码补证：generic SVA复用增加domain->users，仅最后一次unbind触发detach/free；API要求bind调用者持有mm_users引用，unbind前设备不得再发该PASID事务且未完成页请求须已清空。这些是外部生命周期前提，局部函数返回不能补出。SMMU remove在找不到bond时WARN_ON并跳过释放；本轮remove回调是替身，未执行该驱动分支，未把人工三设备组称为真实可达故障或新缺陷。

evidence_packet.json将通用SVA域、设备翻译域、notifier/CD、页粒度、stage与事务/释放义务分开登记。跨轮结果是异构有界证据，不能拼成一次真实运行的同对象事实。事件审核逻辑位于finish.py，从原始事件核set/remove期间映射和锁、全组清理先于erase；全部whole_path仍为insufficient。对象角色/要求由人工选定，非自动N1或统一检查器。

统计：本轮1次成功局部编译、9次程序执行；另2次失败编译（首次提取误匹配API注释且输出GBK解码失败，第二次诊断重现），失败脚本/C/build保留；记录脚本另有2次字面锚点断言失败，未写工作文档，按实际变量名修正；改提取锚点与字节捕获后原函数体不改。无新内核启动、设备、项目模型调用或新缺陷；独立正例/正常0/0。证据linux_bug_analyze/experiments/case_taxonomy/smmu_lifecycle_20261026/。

下一步仍为SMMU：优先核真实mm失效范围来源与可达宽度、编码截断条件；生命周期还缺实际调用者的mm引用、设备静默、并发回调/CD释放及真实合法组配置，不能由上述回放填补。virtio深分析随后，其他扩展暂缓，表示接口/R3暂缓、VT-d后置不变。Word未改。日志、待办、进展、交接同轮维护，WSL三镜像以notes_sync.json为准。

以下为历史记录，以本节及用户最新指示为准。


运行：Windows Python run.py（首轮生成）、finish.py（一次性审核与记录）。保留 run_failed.py/transaction_failed.c/function_manifest.json 为失败材料，采用 function_manifest_fixed.json。设备回调、xarray、锁、列表均为替身，锁状态不是并发证明。
