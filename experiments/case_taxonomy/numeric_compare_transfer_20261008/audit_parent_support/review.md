# 父版支持预筛：20314bac

审阅者：`/root/numeric_contract_review`。只读本轮协议、父版manifest、冻结规则的支持范围和manifest唯一保存C；未运行规则、读取修复/提交正文、查询Git或调用模型。读取父版是支持预筛曝光，不是完全盲测。

唯一材料为 `prescreen/20314bacd2f9/source_0.c`（父修订3123109284176b1532874591f7c81f3837bbdc17，SHA-256 0310bf04241d497049337252be03ce69746f47ad4f1c9713295c36d72e0233e6），已读完整656行。对应源码路径为drivers/staging/r8188eu/core/rtw_br_ext.c。两个预定quoted header均缺失，不补第三项。冻结rule SHA保持1ca111bf2d10014ceeebfbe8984e14d6ae586ff7160c40c6c2f27401e7b8bbb5。

## 按源顺序的支持边界

以下所有原文均来自上述唯一保存文件，具体绑定与逐条引文见review.json。

| 行 | 原文/站点 | 人工支持判断 |
|---|---|---|
| 57 | `while ((cur_ptr - start_ptr) < ntohs(ph->length)) {` | 先出现的数值循环条件；冻结规则只枚举if，且ntohs、字节指针算术和pppoe_hdr声明不在支持输入范围。 |
| 61 | `if (tagType == type)` | 首个if数值比较；两侧为unsigned short局部/参数，不是直接已声明端序字段，参数值来源未知，不可选为主目标。 |
| 90 | `if ((src+len) > skb_tail_pointer(skb) || skb->len < len)` | 首个if成员数值比较；指针表达式/未知辅助调用，sk_buff声明缺失且len是int参数，不能认证端序或值源。 |
| 159 | `if (icmphdr->icmp6_type == NDISC_ROUTER_SOLICITATION) {` | 外部结构字段与宏比较；同版直接标量声明不可见、宏不是受支持literal，不据名称推断字段域。后续同函数相似分支亦不支持。 |
| 385 | `if (((unsigned char *)(iph) + (iph->ihl << 2)) >= (skb->data + ETH_HLEN + skb->len))` | 多字段、指针/转换/移位与宏，非两侧受限标量比较；结构声明也缺失。 |
| 394 | `if (iph->saddr == 0)` | 零值控制外观，但iphdr声明不在保存材料，保持不足，不能标normal抢占主目标。 |
| 412 | `if (arp->ar_pro != htons(ETH_P_IP))` | 可能涉及格式的直接字段比较，但arphdr声明缺失；htons及ETH_P_IP不在冻结的匹配转换/literal支持范围，不把这种外观判为normal或candidate。 |
| 439 | `if (ph->sid == 0)` | 零值且pppoe_hdr声明不可见；仍不足。443相似。 |
| 444 | `if (ph->code == PADI_CODE || ph->code == PADR_CODE) {` | 外部字段声明/两个宏均不可认证；不按标题或预期candidate挑它。 |
| 553 | `if (iph->nexthdr == IPPROTO_ICMPV6 &&` | 外部ipv6hdr字段声明和宏不可见，不能确定受支持端序数值形状。 |
| 612–613 | udph->source/dest与`__constant_htons(...)`比较 | udphdr声明缺失，辅助转换及宏不在固定规则支持范围。 |
| 618 | `if (cookie == DHCP_MAGIC) { /*  match magic word */` | 虽本文件声明dhcpMessage.cookie为__be32（594），比较仅引用局部cookie而非直接字段；616初始化含__be32 cast、处于嵌套条件，DHCP_MAGIC也是宏。不可用此点替换主目标或认证normal。 |
| 619 | `if (!(dhcph->flags & htons(BROADCAST_FLAG))) {` | flags为同文件__be16（586），但这是掩码谓词而非本轮非零数值比较；htons/宏也不在冻结支持范围。未知不能归normal。 |

另外，本文件73行`data_len = tag->tag_len + TAG_HDR_LEN;`仅为赋值；74行比较skb_tailroom与int局部，既无直接端序字段比较，亦不满足固定值源规则。它们不因提交标题就成为本轮目标，不进行patch推测。

## 停止结论

保存C内仅dhcpMessage具备本地可见__be成员声明（585–594）；其使用点没有受支持的直接非零if数值比较。其余相关字段的结构定义不在允许材料中。按文件顺序读完仍无支持主输入，也无可认证正常控制。

建议本轮记为父版支持尝试1、支持输入0、规则执行0、patch解封0的一次材料/支持范围停止。不扩大导出、不补样、不修改规则；不足不是真阴性或模型/规则假阴性。本轮没有检测输出，不能据此评价准确率、确认故障或增加案例数。
