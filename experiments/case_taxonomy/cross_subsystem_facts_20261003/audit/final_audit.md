# 独立只读收尾审计

2026-10-03，**pass，blockers_found=[]**。仅核对锁定材料与结论，不运行原规则、编译、模型、内核或新输入。138份源码的SHA/Git blob/行数、142条摘录、311条命令的stdout/stderr SHA、725份case manifest成员全部一致；原JSON逐字等于旧开发输出，primary/对照摘要均来自原输出。直接输入SHA、布尔checks及完整输入收据见`final_audit.json`和`mechanical_checks.json`。

ocfs2只纳入`i_flags`一个primary。当前access各只出现一次，零/非零及同表示布尔掩码在这些简单表达式上正常。磁盘声明、主机常量和filecheck修复消费者支持条件性本地表示关系；验证失败、非只读、非journal、有效签名/VALID、I_NEW及缓存/回调条件已保留。未证明大端构建、挂载、真实I/O或损坏。

PWM只纳入get_property的`reg`一个primary。唯一可见static helper caller传入零，故类型candidate不能升级当前请求字节错误。人工核对的payload memcpy/DMA/mailbox链是本地代码证据；远端字段规范、大端设备支持与运行故障仍未知。

旧consumer的整条件转换匹配和掩码/零前缀匹配限制仍在，不批准一般语法soundness。`u32`、`__le32`和按地址传参均不独自证明值源或物理可达；两项人工消费链没有包装为自动dataflow。未审独立外部规范，未求解完整配置或进行运行验证，两项均为已读开发对照，新增病例为0。

执行快照有明确阶段边界：ocfs2准备前后尚无protocol字段，共同工具/直接stdlib字段一致，正式回放前后及最终protocol SHA一致；最终builder SHA与锁定facts一致，初次生成stdout保留为历史。依赖记录不是递归运行时闭包。PWM十个猜测缺失路径没有被当作阴性测试。审计通过仅表示本项材料完整、当前有限结论守界。
