# 静态事实词表扩展：设计（实现前写定）

2026-10-28。用户同意先扩展静态事实：全局/每CPU对象读写端点、初始化阶段、编译单元内调用可达。依据为桥接试点中“初始化时序/谁在何阶段写读”一类不可表达理由。

## 采集新增（`kernel_facts.collect`）

对每个文件的预处理文本建立**本源文件函数索引**（按`#`行标记只收源自该`.c`的顶层函数，另加所请求函数）：
- `section`：函数头中`__section__("...")`，缺省`.text`；目标文件中的实际段另由反汇编段头记录。
- `writes`/`reads`：预处理正文中的**语法访问**——标识符或`->f`/`.f`字段出现在赋值左侧、复合赋值或`++/--`为写，其余非调用出现为读；取地址`&x`记为`escapes`。
- `calls`：正文中`g(`形式的调用名。
- `initcalls`：预处理文本中`.initcallN.init`段与函数名的对应。

## 新查询

| 查询 | 值 | 语义边界 |
| --- | --- | --- |
| `writes(fn, obj)` / `reads(fn, obj)` | bool | 语法访问；不解析别名、指针所指对象或宏外的间接写 |
| `escapes(fn, obj)` | bool | 正文中出现`&obj` |
| `in_init(fn)` | bool | 函数头含`.init.text`等init段 |
| `initcall_level(fn)` | string | 只在找到对应initcall时给值 |
| `calls(f, g)` / `reachable(f, g)` | bool | 编译单元内文本调用及其传递闭包；函数指针、回调、跨编译单元不可见，reachable=false不证明不可达 |
| `writers_count(obj)` | int | 本源文件函数中写obj的个数 |
| `all_writers_in_init(obj)` / `any_reader_outside_init(obj)` | bool | 仅在本源文件函数范围内；无写者时不答 |

答不了不给值，核心判不足。

## 验证

1. 开发回归：SPARC已读案例上`writes(record_one_cpu, ncpus_probed)`、`in_init(setup_arch)`等与源码对照；记录回调（`of_iterate_over_cpus(record_one_cpu, ...)`）不进入调用图这一已知局限。
2. 试点2：同一组候选在扩展后的词表上再做1次形式化，对照0/5的基线。
3. 新试点：后备池按种子20261028继续取下一个A0通过者，做1次E1和1次形式化，避免只对试点2调优。新试点用后登记接触、不计评价。
