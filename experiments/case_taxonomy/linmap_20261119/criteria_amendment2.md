# 判据修订 2：只在同一层重新赋值时撤销标记（linmap_20261119）

2026-11-19，Claude。**写于看到修订 1 之后的开发样本结果之后**：btf 修复前报出、修复后不报；zswap 修复前仍然没有报出。

## 原因

`mm/zsmalloc.c` 的 `zs_map_object`（版本 c52eb6db7b7d）：

```c
if (off + class->size <= PAGE_SIZE) {
        area->vm_addr = kmap_atomic(page);   /* 第 1 层 */
        ret = area->vm_addr + off;           /* ret 被标记 */
        goto out;
}
...
ret = __zs_map_object(area, pages, off, class->size);   /* 第 0 层 */
out:
        ...
        return ret;
```

修订 1 规定“在同一层或更外层重新赋值时撤销标记”。第 0 层的这次赋值把 `ret` 的标记撤销了，可内层分支是 `goto out` 跳过它的。所以 `zs_map_object` 没被认成来源函数。

## 修改

“重新赋值撤销标记”只在**同一层**（与设置标记处的花括号层级相同）生效。更外层的重新赋值，可能和设置标记处在不同的执行路径上，所以保留标记（按“可能”处理）。

其余不变。

## 说明

这条修改也是看着 zswap 写的。zswap 只算开发样本，不算独立结果。自测会补一个 goto 跳过外层赋值的样例。
