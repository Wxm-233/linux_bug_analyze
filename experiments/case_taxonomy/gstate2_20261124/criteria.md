# 判据：收紧“全局状态”性质检查（gstate2_20261124，师兄流程第四轮）

2026-11-24，Claude。用户：“先收紧全局状态”。写于任何实现和运行之前。接 `xprop_20261124`（第三轮）。第三轮的文件只读不改。

## 一、第三轮的问题

第一版报出 9 条“运行时可变”候选，全部审为不可能。误报来自三类问题：
1. 把取地址 `&X` 算成了写入；
2. 没带 `__init`、但只在启动阶段被调用的辅助函数，被当成运行时写入；
3. 公共代码自己的变量（`init_mm`、`execmem` 缓存、`elfcorehdr_addr`、`nr_cpu_ids`）被当成了架构状态。

另外，第一版的写入识别不认每 CPU 变量的写法（`this_cpu_write` 等）和 `WRITE_ONCE`，会漏掉真正的运行时写入。

## 二、新规则

输入与第三轮相同：边界上的架构函数 G 读写的全局变量（`/root/work/xprop/sites_*.json.gz`，角色“全局”）；范围、构建不变。

1. **只看架构状态**：变量 X 在 `arch/` 下有声明或定义（`extern`、`DECLARE_PER_CPU`、`DEFINE_PER_CPU`，或文件作用域的定义），才算架构状态；否则记为“公共状态”，不出候选。
2. **写入**只认下面几种（都要在该构建实际编进去的行上）：
   - 对 X 本身、它的字段或数组元素直接赋值，或做复合赋值、自增、自减；
   - `WRITE_ONCE(X…)`；
   - 每 CPU 写操作：`this_cpu_*`、`__this_cpu_*`、`raw_cpu_*` 这一族里的 `write/add/sub/inc/dec/or/and/xchg/cmpxchg`，第一个参数是 X 或 X 的字段；
   - `memset/memcpy/memmove(X 或 &X…)`；
   - `set_bit/clear_bit/__set_bit/__clear_bit/change_bit(…, X 或 &X)`；
   - `atomic*/atomic_long*` 的写操作（`set/inc/dec/add/sub/xchg/cmpxchg` 等），作用在 `&X` 上。

   单纯取地址 `&X` 不算写入。
3. **启动时**：写入所在的函数 w 满足下面任一条，就算启动时写入：
   - w 带 `__init`、`__ref`、`__meminit`、`__head`、`__init_or_module`；
   - w 被 `*_initcall(w)`、`early_param(…, w)`、`__setup(…, w)` 登记；
   - 沿直接调用关系往上找（按名字、只看该构建编进去的代码，最多 4 层），w 的每个直接调用者都是启动时的。

   w 没有直接调用者、但它的地址被取用（作为回调登记），算**运行时**；既没有直接调用者、也没被取用，算“调用者未知”，也按运行时处理（保守）。
4. **分类**：常量 / 启动时设定 / 运行时可变 / 没找到写入 / 公共状态。**候选** = 被边界上的架构函数读写的、“运行时可变”的架构状态。

## 三、核对与关口（写于运行之前）

### G1 校准（直接对指定变量跑分类，不要求它被边界函数读到）

| 变量 | 构建 | 预期 |
|---|---|---|
| `tlb_single_page_flush_ceiling` | x86_64 | 运行时可变（写在 debugfs 写处理函数 `tlbflush_write_file` 里，是回调） |
| `cpu_tlbstate` | x86_64 | 运行时可变（`switch_mm_irqs_off` 里 `this_cpu_write`） |
| `pgtable_l4_enabled` | riscv | 启动时设定 |
| `page_offset_base` | x86_64 | 启动时设定 |
| `memstart_addr` | arm64 | 启动时设定 |

**关口：5/5 全对。** 不对就停下查原因、写修订，不改预期。

### G2 候选审查

候选全部由我逐条审完，给出结论：可能 / 不可能 / 说不清，附理由。本轮不设命中门槛。另外报告：
- 第三轮那 9 条误报在新规则下各落到哪一类，并说明原因；
- 各分类的数量；
- 只在部分架构存在的架构状态（例如 riscv 的 `pgtable_l4_enabled`）。

## 四、不做的事

不改第三轮及更早的文件；不对外报告；不推 GitHub，结束后在本地另存。中间产物放 WSL `/root/work/gstate2/`。
