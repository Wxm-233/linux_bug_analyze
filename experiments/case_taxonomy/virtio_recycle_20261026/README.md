# virtio回收与重投：限定路径证据

## 10月26日 最新进展：virtio普通split回收与重投局部验证

沿用上轮Kimi完整分析和纠正清单，本轮未新增模型调用。固定父版db191ba0c8564ff84877e5b1c9553e991feca239提取9个原函数：unmap资格/单项unmap、两层detach、poll/more_used/get_buf，以及事件queue/recv。原函数体不改。1次成功编译、54次程序执行（9情形×map API开关×used长度0/4/8）；另有1次测试脚手架编译失败，const和符号类型修正后通过，初始脚本及失败记录保留。不是两次成功编译。

普通split、非IN_ORDER、单描述符路径中，观察到unmap回调→token→CPU读→重新add的逐对象顺序；bypass不调用unmap，仍可返回token，所以“回收顺序成立”不能等同“缓存维护完成”。两个预置used事件逐个处理，第一对象被读取时第二对象尚未软件回收；此项反对未经论证的内部事件共享安全结论，不证明真实同时DMA或缓存腐蚀。used项为脚手架预置，不运行设备/发布路径。

add替身分别返回成功、-ENOSPC、-ENOMEM，原事件驱动均继续消费第二事件并kick，确证该调用点忽略返回值；未执行原add失败生成机制，不能断言真实平台的错误触发频率或队列永久单调缩减。used长度0/4/8均读取完整事件字段，证据仅为缺少长度检查，不认定短写是合法设备行为。broken、空队列、越界id、非head和入口ready=false均不消费；ready=false入口也不kick。

回调替身另注入ready由true变false，原循环仍继续重投和处理第二项。源码remove/freeze确有上锁置false再reset/delete等步骤，但尚未核实transport reset/callback同步、input注销与并发可达性；这是构造控制，不是已证实竞态或新缺陷。

新增本轮限定轨迹检查器，按对象验证UNMAP/TOKEN/CPU_READ/ADD的时间顺序，54份记录审核通过；4份早读、缺失add、错对象、bypass却含unmap的篡改控制均拒判。它只接受本轮已登记脚手架语义，不是通用轨迹解析器；CPU可见性、真实设备所有权、whole_path始终insufficient，契约语义及测试条件仍人工提供。累计本轮58次assess调用，控制不算独立样本，独立正例/正常0/0。

下一项：补reset/delete对回调的同步及真实重新add/失败路径，再补实际DMA后端copyback和架构缓存维护边界。packed/IN_ORDER、真实分配基址/平台一致性、合法used长度规范仍缺；不以普通split推及所有布局。将“对象×阶段×后端”的证据要求继续提炼成接口判定方法，暂不建立统一检查器。virtio不结项，SMMU开放缺口、表示接口/R3暂缓、VT-d后置不变；后续主分析仍Kimi。

证据：linux_bug_analyze/experiments/case_taxonomy/virtio_recycle_20261026/（probe、functions、build及build_failed_initial、results、checker、audit、controls、README）。本轮无新模型调用、内核/QEMU启动、真实设备DMA或新Linux缺陷。更新当日日志、待办、进展和交接，三份Windows/WSL镜像以本轮notes_sync.json为准，Word未改。

以下为历史记录，以本节及用户最新指示为准。

