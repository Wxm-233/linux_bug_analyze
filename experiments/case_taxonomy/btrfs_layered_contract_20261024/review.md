# 外部语义登记与稳定性复核

## 1. 范围

本登记仅针对两版已验证64K页/64K盘、正2048/8192请求、已保存观测变换的四条事件。主智能体研究侧审核，复用10/24 observation_review.md；不是独立专家/模型自动发现。原函数名、判据、适用范围和观察位置均有人工作用。

## 2. A：记录中的运算一致性

super.observed.c正max_inline分支保留u64请求、u32缓存，并用min_t(u64,lba_request,lba_cache)计算lba_result，再赋给info->max_inline。日志打印这些局部量。关系可用核心已有lt/le/eq/and/or表达，无需扩核心。A只验证记录符合该运算，不证明缓存准备正确或本来就应该执行该运算。前轮解析器已预验min关系，A通过也不能算新增检测能力；合成错误负控制另列。

## 3. B：跨时刻记录比较

cached_operand是用于min的局部量；adjacent_disk是之后从同info->super_copy读取的磁盘sectorsize。程序可在同一归档记录中比较两个实际值是否相等，因此B可判观察满足/违反，但它是显式跨时刻诊断，非消费期限条件。缓存/磁盘访问的局部对象关联来自同一info表达式与观测补丁，不证明完整root/文件对象链。

## 4. C：真正准备条件未准入

实际接口准备候选需要缓存与消费时适用几何相符。当前只取得消费缓存和后采样磁盘，没有同刻磁盘值。局部顺序复核：缓存读取→局部min→写max_inline→读super_copy→getter；在可见区域没有写sectorsize，也没有在磁盘getter前新增外部日志调用，但此词法事实并不排除其他CPU/中断/共享writer。单CPU、单线程用户请求也不自动排除中断/内核执行。super_copy对象从何时可达、是否在区间有其他写者、相关同步均未作完整证明。

故C的consumer_requirement保持候选，消费参考绑定/稳定性审核状态insufficient，事实disk_at_deadline不填入，不借UUID、静态无写或输出相同代替证据。整项不足的原因必须保留。

## 5. 事件、对象、来源

统一核心以archived_runtime容纳已存运行档案，额外metadata明确instrumented_runtime_operand_capture，不能丢失观测变换层级。sample_event为clamp日志记录，deadline_event为此前min的消费，二者不同；sample_kind=sample。A/B对象是当前boot+mount的info及其保存值，不能因地址复用合并。事实来自program_projection；语义、适用范围及绑定审核为researcher_review。引用同时登记运行日志、完整观测源码和本说明的对应节。

核心reference边界校验不是语义证明：所有supported只针对A/B的限定档案关系、所选局部来源与明确事件定位。不得借此将C或whole_path标supported。
