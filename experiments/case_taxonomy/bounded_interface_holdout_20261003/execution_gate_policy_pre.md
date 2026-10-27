# 父版执行与解封门控补充

在prepare完成、父版规则尚未运行前，独立静态审阅发现原编排器允许CLI失败/无JSON后继续解封，并且重复执行的拒绝发生在subprocess之后。原runner处于prepare运行中，保持不改；增加单独门控，须事前封`execution_gate_lock_pre.json`。

正式parents/unseal只经`execution_gate_pre.py`进入，不直接调用原runner。parents先拒绝已有开始标记、锁、命令或raw，写一次性开始标记再执行；发生失败保留，不重试。空选停止。

unseal先校验规则/选择/gate/父版锁，核对所有父版CLI为0、JSON存在、SHA和revision/source身份/计数一致，再写允许与开始标记。任何缺失或失败均停止，不开补丁；零站点但完整成功JSON可继续。解封已有产物也事先拒绝。这只保证程序顺序，不赋予语义正确性或人类金标准。

这一补充发生在父版输出前，不修改选样标准、原consumer/producer或已形成freeze_pre。门控文件、策略和原freeze的哈希作为额外前置锁单列。本轮每项旧版/修复仍各一次，不按结果修改规则或换例。
