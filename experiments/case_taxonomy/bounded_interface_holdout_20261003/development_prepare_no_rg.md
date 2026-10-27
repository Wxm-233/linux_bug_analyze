# 冻结前准备环境记录

首轮prepare在`rg --version`前发现WSL没有rg，FileNotFoundError退出1。此前只保存git/python版本输出，位于`commands/prepare/001–002`；尚未查询HEAD、提交池、选择、新源码或补丁，未执行检测器。

保留原输出，不删除或覆写。冻结前将runner改为先查可用搜索程序，rg不可用用现有grep；完整准备记录另存`commands/prepare_complete/`。这属于冻结前编排修正，原consumer/producer不改。后续freeze才界定正式规则、选择与执行，不把这次环境错误计入样本结果。
