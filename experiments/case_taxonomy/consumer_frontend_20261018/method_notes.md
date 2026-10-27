# N2.10实现与开发边界

新模块`linux_bug_analyze.consumer_obligations_v2`保留`analyze_consumer(document)`、`evaluate_consumer(analysis, parameters)`接口；参数名称列表按源码声明顺序输出。调用方不传role、量词、expected或手工效果IR。只读复用冻结v1的普通C表达式/语句转换与有限整数运算，不修改v1或N2.9结果。

## 前端与原文身份

scanner输出原text SHA、解析视图SHA、注释字符跨度与恒等字符坐标映射。注释非CR/LF字符替换成等长空格；CRLF、tab与非ASCII注释的字符位置保留。列定义为Unicode字符列，tab计一个字符，非屏幕可视列或UTF-8字节列。字符串/字符字面量及转义原样保留，内部注释标记不作为注释；这不表示后续int表达式模块支持string/char值。

拒绝未终止注释/引号、引号内真实换行、NUL、指令、反斜线LF/CRLF续行、裸CR与所有`??`（保守拒绝三字符组）。不删GNU语句、asm、宏或不支持的控制来获得解析。完整原文与视图身份均保留，未进行Linux投影。

首14项开发测试发现pycparser 3.11还拒绝CRLF中的CR。原失败记录保留；按`scope_amendment_pre.json`登记，在本新模块本地用`CRLFLexer`仅跳过紧邻LF前的CR，原文本和pos不改，LF仍完成行计数。不改安装包、C语法或旧lexer。该桥依赖已记录的pycparser 3.11接口。

## 受限结构与作用域

只支持完整普通C int函数、int参数和局部量、只读const、固定局部一维int数组1..16；数组可由scalar参数初始化。volatile/_Atomic、指针、取址、调用、全局、不支持控制/表达式均不足。参数`void`形式以及char/string值不在当前语义子集中。

两遍for保持index=0、index<静态可求且未再写的局部界或字面值、++步进，界0..16且不依赖任一循环index。顶层及每个循环体顺序验证声明。循环体int别名必须显式初始化、不得shadow活动名称；两个不同循环体可声明同名别名，属于不重叠作用域。每轮重新初始化，continue/break/return及异常退出都清理；循环局部数组、嵌套分支声明、额外词法作用域和嵌套循环不支持。

保留搜索skip、最后的条件赋witness+break、紧随的sentinel早退出口。初始witness使出口guard为真；赋值是否真正消除该guard仍由首个实际匹配及后续guard决定，不称任意exists足够。第二遍最多一个直接/条件数组写入及一个检查，检查可在写入前后，不重排。零检查不生成全称候选。

检查可为直接if-return，或单调flag：顶层初值0、仅指定检查分支置1、无其他写入，循环后if-return只引用该flag且对0假/1真。不能用“代码返回0”推断正常或缺陷。IR保留所有条件、目标、索引、写入与出口位置。

## 有限观察与证据层级

`check_observations`每条恰为`{iteration, predicate_value, writes_before}`：iteration是第二遍for规范0起始迭代序号；predicate_value是原if guard的bool真值；writes_before只数本轮在检查前实际执行的数组赋值。新一轮重置，未执行的条件写入不计，continue/早退不补造未抵达检查。

trace另保存数组目标IR、实际索引和值；计数本身不证明写入和检查是同一对象。静态`before_potential_array_write/after_potential_array_write`仅说明源位置，具体是否写入以有限轨迹为准。实际未到达、真空检查域、源中没有检查分别标记。OOB、未初始化、未知值或保守int算术范围外导致insufficient，不过滤这些路径后求all。不使用任意eval，不证明全输入内存合法或架构规范。

## 开发验证与下一步

首14项测试13过1个CRLF失败，保存在`development_tests_initial.json`；CRLF桥后14项通过，记录`development_tests_crlf.json`。独立预审补一项const写法/参数禁写及不支持值类型回归，最终15项记录单独保存，不覆盖前轮。

`run_known_development.py`只读核对旧N2.9九份原始字节与参考摘要、v1 baseline不变，输出新stage的`known_development_results.json`。7份提取、2份保持不足，2754个source/args记录全部求值且返回值2754/2754相同；跨源码891个唯一args。它们已读且参与本轮开发，**不是独立成绩**。旧参考只验证return，不验证新check_observations；不能将Python生成字段称原生观测。

新独立源码/参考始终隔离，方法冻结后由root执行。普通C组件成功不代表原GNU Linux成功；下一阶段应核对真实源编译器前端与架构提供条件，不能持续把增加合成形状或测试数量作为研究主成果。
