# 独立只读方法审计：真实配置输入的有限适用性门控

结论：**PASS_FOR_BOUNDED_APPLICABILITY_GATE_ONLY**。预先固定两提交与目标路径，不因缺少合格材料改条件或补第三项。记录中只有一次metadata log和一次batch，两份Python原物，冻结候选CLI执行0次。本审计只对本阶段保存流水线负责，不是全局进程历史审计；没有调用Git、旧提取器、候选CLI或C实验。

## 材料与门控

09ea父版/提交版都只取得`tools/testing/kunit/qemu_configs/powerpc.py`，属于Python配置提供材料，不是冻结C模板需要的IS_ENABLED与模式寄存器操作输入。提交版第6行增加`CONFIG_CPU_BIG_ENDIAN=y`到kconfig字符串；这个来源文字不能证明真正生成的autoconf、CPU运行模式、构建可达或设备消费行为。应记`not_C_input_for_frozen_template`。

12b的原始metadata列七个`.S`变更路径，没有协议允许的basename=Kconfig目标，因此没有取得任何该项源码对象。应记`insufficient_material_target_not_in_changed_paths`。这仅说明预定目标在变更路径里未找到，不说明仓库不存在相关Kconfig、汇编没有配置消费，或该提交不涉及研究机制。没有改取汇编是守住冻结范围的正确停止。

已逐字节核对freeze前锁、metadata解析、blob请求、Git收据、两份原物SHA/blob身份与batch边界。详细检查见review.json。两项日期仅为committer元数据，不能转成发现时间或两个缺陷时间间隔。

## 曝露与角色

09ea已在旧选例有metadata/changed-path曝光，此前源码曝光不能认证不存在；本轮两版Python均已读。12b已有标题与模型记录，本轮读标题、父版与changed paths，没有读汇编或Kconfig正文。以后不得把这两项统称完全未读盲样。

两者都未独立建立同机制阳性或真实正常角色。父版/提交版是同一项的版本对照，不是独立正负样本。候选模板根本没有运行，不能把“0次执行”转写成“运行后0候选”，更不能当正常、真阴性、漏报或泛化结果。新增确认/独立阳性0的统计保持。

## 下一步边界

先总结配置提供材料与C模式寄存器模板的范围差距，再为确有配置提供—消费证据的有限接口单独规划适配。新协议需固定材料数、版本、提供者—消费者关联来源、候选角色和事前预期；实际配置与硬件消费缺证就继续保留unknown。不能在本轮结果后放宽Kconfig路径条件、自动适配Python/汇编、补样凑阳性或复用同项版本对照宣称独立检测成功。
