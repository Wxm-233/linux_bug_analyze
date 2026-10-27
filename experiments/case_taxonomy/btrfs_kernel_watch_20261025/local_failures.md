# 本轮本地准备/核验失败保留

1. prepare.py独立偏移编译成功，但只在旧缓存顶层找initrd而失败。依据旧run.py确认实际路径fix-64k/initrd.gz，finish_prepare.py核原清单SHA后继续；未重新编译或运行内核。
2. verify.py首次在effective_limits比较失败：实时Python字典的request键是int，历史JSON读回为str；两边实际值均2048→2048、8192→4096。将新投影键显式序列化为str后重验，保留原盘导出，不重新运行内核。这是表示比较错误，不是Btrfs差异。
