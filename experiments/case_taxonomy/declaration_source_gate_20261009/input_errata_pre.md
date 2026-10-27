# 首次执行前的输入勘误

2026-10-09，规则尚未执行。原8项输入中的第5项竞争来源构造有误：搜索根shadow加完整token ../include/linux/packet.h仍归一到include/linux/packet.h，不能命中新增的shadow/include/linux/packet.h。根静态复核与独立输入审阅均指出这一点。原fixtures_pre.json、prepare_inputs.py、freeze_inputs_pre.json全部保留，不覆盖；这不是门控运行失败，也不是新源码案例。

仅在fixtures_pre_v2.json修正该fixture的第二搜索根为shadow/include，并同步该项的合成Makefile根表达式和引用/指纹。其余7项及真实回接不变。新的freeze_inputs_v2_pre.json纳入原冻结全部文件及勘误/修订脚本/新fixture。后续runner只接收v2这8项，并记录原freeze与当前freeze；独立审阅v2通过、实现冻结后才能首次执行。
