# 独立数值比较边界审阅：最终回归

原事前20项合成输入以 `run_probes.py --label final` 重跑，20/20符合预期，退出码0。最终根规则 SHA-256 为 `1ca111bf2d10014ceeebfbe8984e14d6ae586ff7160c40c6c2f27401e7b8bbb5`，与 `freeze_code_closeout_pre.json` 一致；执行前后规则、旧依赖、探针和runner哈希均未改变。

首轮结果保存在 `execution_initial/`，最终回归另存 `execution_final/`，没有覆盖。探针规格 SHA-256 始终为 `c4849121b4f9686468c6c1f1aae41186b1ad4312a2ead16e87f5cc51978cfae5`。**这是同20个合成case的两次执行，不是40个独立case。**审阅者没有添加第21项、修改根代码或旧材料，也没有访问新Git源码、WSL、模型或运行内核实验。

先前静态提出的sizeof普通变量/参数类型名阴影风险，已在最终实现中看到保守ordinary-name shadow guard；该新增形状的测试由root维护，不另记为本审阅的第21项已执行探针。完整预处理、任意C声明/作用域和CFG仍未认证。

20项只检查协议支持的局部表示形状与拒判边界；normal不等于真实运行正确，candidate不等于确认缺陷。没有独立同机制阳性、新增确认案例或总体准确率结论，原固定12条分母不变。
