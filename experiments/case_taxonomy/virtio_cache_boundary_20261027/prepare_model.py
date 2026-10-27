from pathlib import Path
import json,hashlib
H=Path(__file__).resolve().parent;R=H.parents[3];out=R/'模型调用测试/2026-10-27/virtio_cache_boundaries'
out.mkdir(parents=True,exist_ok=False)
paths=[H/'source'/n for n in ['arch__arm64__mm__cache.S','arch__arm64__include__asm__assembler.h','arch__arm64__include__asm__cache.h','arch__arm64__include__asm__cacheflush.h']]
old=H.parent/'virtio_dma_chain_20261026/source'
paths += [old/n for n in ['arch__arm64__mm__dma-mapping.c','kernel__dma__direct.h','kernel__dma__swiotlb.c','drivers__virtio__virtio_input.c','Documentation__core-api__dma-api-howto.rst']]
text='''任务：对固定Linux父版db191ba0c8564ff84877e5b1c9553e991feca239做限定源码分析，作为virtio_input DMA接口契约的下一阶段。本次是新材料补证任务，不请求恢复任何历史拒绝内容。
只依据下列完整固定源码，解释ARM64 clean/invalidate操作的地址范围、首尾部分行、顺序及clean-cache workaround；明确dcache_line_size的CTR字段、CWG、ARCH_DMA_MINALIGN和kmalloc对齐分别承担什么，不能把它们混同。特别核8字节区间全部位于同一未对齐行时是否重复维护同一行。对direct与bounce区别，指出缓存操作对象是原缓冲还是bounce，CPU copyback触及什么；勿从单向映射、CPU不写事件或对齐宏就推出安全。
我们已有的是原函数局部执行/模拟设备与低端内存拷贝，尚无实际设备DMA、真实平台一致性、cache效果或并发证明。请保留这些缺口，不自行断言ARM64真实损坏。不要扩展成整个子系统审计。输出：1)带文件行号的机制；2)可检验的有限关系、合法输入前提和对照；3)direct/bounce/未知平台的判定边界；4)需补来源。最后给JSON数组，逐项包含id、requirement、authority、conditions、objects、phase、test、unknown。候选不是证明，不预设互斥Pattern或新增缺陷。请控制篇幅，避免凭记忆补未提供的规范。
'''
manifest=[]
for p in paths:
 b=p.read_bytes();name=p.name.replace('__','/');text+='\n\nFILE '+name+'\n'+''.join(f'{i}: {s}\n' for i,s in enumerate(b.decode().splitlines(),1));manifest.append(dict(file=name,sha256=hashlib.sha256(b).hexdigest()))
(out/'prompt.md').write_text(text,encoding='utf-8')
(H/'model_request.json').write_text(json.dumps(dict(output=str(out.relative_to(R)),scope='new fixed source cache boundary analysis',model='Kimi-K3',sources=manifest,automatic_retries=0,prompt_sha256=hashlib.sha256((out/'prompt.md').read_bytes()).hexdigest()),indent=2),encoding='utf-8')
print(str(out))
