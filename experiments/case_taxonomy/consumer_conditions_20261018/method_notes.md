# N2.9普通C局部条件原型（冻结前开发说明）

入口为`analyze_consumer(document)`与`evaluate_consumer(analysis, parameters)`。document含id/path/revision/text，只接受原始文本中的一个完整普通C int返回函数；保留原文本摘要及pycparser的本地行列。parameters是**按函数声明顺序列出的名称列表**，有限执行传同名整数dict，不传role、量词、expected或手填效果IR。使用本机pycparser 3.11，不修改旧组件。

## 公开支持形状

参数和局部量只支持int；`const int`也可用但不能写入。volatile、_Atomic等其他qualifier拒绝。数组只支持局部单维int数组，定长1..16；初值可由整数参数、先前局部量或受限纯表达式构成。未初始化成员保持未知，部分显式初始化按C补零。指针、取址、调用、全局、额外定义、重名/遮蔽、不支持表达式或控制均不足。未做删注释、删宏、改写GNU或预处理投影以求解析；原LinuxGNU失败须保留。

顶部声明之后，允许零至多个无else的纯条件早退，然后必须是：搜索for、无见证早退if-return、第二for、尾return。for为局部index=0、index<字面值或未再写局部常量界、index++或++index；两遍界值一致且0..16，允许空域及不同索引名字。界不能引用任一循环索引，以免for隐式写入改变界。循环内可有任意数量简单标量别名赋值或无else的纯if-continue；不支持嵌套循环。别名是普通局部整数值，不是C指针别名分析。

搜索循环最后必须为`if (纯谓词) { witness = 纯值; break; }`，见证有事前可静态求得的常量初值，不能与循环索引或界重合，也不能由其他前置循环赋值重写。紧随的if-return条件只能引用该witness和常量，且对初值求值为真，例如初值-1配`witness<0`或`witness==-1`，初值0配`!witness`。否则不推存在条件。

第二循环保留一个直接或有条件的数组更新，之后必须是无else的if-return检查；更新值和检查须联系同一witness，更新的数组根须出现在搜索谓词和后续检查中。没有证明相同根意味着相同成员，具体索引/对象关系仍在IR中保留，有限执行逐次计算。更新前的别名/skip、写入和检查都保留，不能把后置检查说成前态全称。

## 输出与有限语义边界

输出包含自动从AST转换的受限IR、原坐标、早退条件、两遍迭代界、skip/continue、赋值、break与检查阶段。存在候选只表示**避开指定搜索后出口的必要条件**，保留首个匹配的赋值和后续guard，`sufficiency_proved=false`；赋值后仍等于sentinel时可继续早退，不升级成“有任意匹配就充分”。负return不自动表示bug。早退类别依据源位置为early_bypass/search_absence_exit/member_post_update_check/tail_return。

纯表达式支持整数、标量、局部数组索引、`!/+/-`及`+/-/*/==/!=/</<=/>/>=/&&/||`；短路保留。不使用Python eval。输入、读值与算术限定在保守int范围[-32767,32767]；数组索引在每次实际访问检查。OOB、未初始化、未知值或超范围使该次执行insufficient，保留已到达轨迹但不把未知过滤后求all。

结果记录实际迭代、分支、写入、continue/break和return位置。搜索谓词的存在取实际抵达谓词的次数；逐成员条件只涵盖实际抵达检查的迭代。该谓词使用中性字段`early_return_predicate`，有限结果为`post_update_branches_not_taken`及`all_reached_post_update_branches_not_taken`；它们不是系统契约的通过/失败评分。第二遍未抵达为not_reached；抵达但无检查为vacuous_no_reached_checks，不能冒称完整域验证。早退单成员/其他guard原样记录，不能由`bound==1`或退出码推断整体正确。

11项开发方法测试首次通过，命令及stdout/stderr在`development_tests_initial.json`。冻结前独立审查发现隐式index/bound重叠与语义命名过强后，收紧边界及中性字段，并补充首个bad assignment先break而后有合格者、写后continue缩小检查域、return0出口、qualifier和隐式界写入回归；修后15项一次通过，记录`development_tests_reviewed.json`，初轮不覆盖。测试还覆盖存在而非前态全称、先写再检查、空域、单成员短路、出口后未访问域、重命名、真空检查、OOB/未初始化/未知控制与原IR不变。它们不是持出样本或内核缺陷；独立挑战在方法冻结后才披露，不能围绕其失败修规则。
