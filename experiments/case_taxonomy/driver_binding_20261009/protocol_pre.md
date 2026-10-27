# 实际声明与构建绑定：三个固定路径的有界核查

日期2026-10-09。沿用已读修订3123109284176b1532874591f7c81f3837bbdc17及已保存 `drivers/staging/r8188eu/core/rtw_br_ext.c`。唯一数据源为WSL Ubuntu现有 `/root/repos/linux` Git，不联网、不取新候选/补丁/模型，不编译或重新执行旧规则、投影/模板。

## 事前固定范围

1. `drivers/staging/r8188eu/include/linux/if_pppox.h`：将原C第10行quoted include按C目录规范化后的首要相对文件位置。
2. `drivers/staging/r8188eu/Makefile`：局部对象和include旗标的源码证据。
3. `drivers/staging/r8188eu/Kconfig`：局部配置声明和依赖证据。

三个路径是相互独立、事前预定的事实项，完成本批即停止；一个missing不触发替代路径或跟随其他include。最多三次文件对象请求。先执行一次 `git cat-file -t` 仅确认指定修订是当前本地仓库的commit；失败则不做文件请求。随后一次 `git cat-file --batch` 通过stdin提交三个固定revision:path，以原始二进制解析每项blob或missing。合计最多两条Git命令，不增加blob rev-parse或搜索全树命令。每个blob从Git响应获得实际oid并与本地Git式blob散列核对，所有stdout/stderr/退出码原样保存。

冻结协议、脚本、原源字节和上阶段闭合清单；独立只读静态核对后才执行。本轮不是盲测，既有案例、条件性布局与source-supported组成关系不改。元数据/文件检索故障与path missing分开，保存部分原物，不重试/替换直到成立。

## 结论边界

首要相对路径missing只表示该修订的该路径不存在，**不证明编译找不到头**。quoted include还可能以相同完整token在其他quote/-I目录搜索，符号链接、生成头及全局编译选项也未取得；不能直接以标准UAPI声明替代实际绑定。保存Makefile含目标对象只证明局部Kbuild文字关系，不证明父级入口、CONFIG取值、实际编译命令或运行到达；Kconfig的局部依赖不等于所有架构/配置受支持。

绑定证据卡须分别记录include文字/归一位置、文件存在与声明、对象列举/聚合/obj-CONFIG关系、局部配置/依赖/include选项、缺失的真实命令及声明链。仍未知的ABI/typedef/CHAR_BIT/packed、完整长度、实际路径和外部契约不得解除，原12项条件维持未证。missing不计真阴性、规则漏检或确认缺陷；新增确认/独立阳性0，原12条6/5/1不变。

完成标志：三项固定路径的存在/缺失原物和两条以内Git收据、有限证据卡/引用、独立协议及源码审阅、只读核验/封存、每日合并日志、Windows/WSL待办。下一项只按本轮具体证据另立协议，不自动扩大本轮文件范围。
