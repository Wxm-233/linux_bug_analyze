"""Validate diagnostic additions to the frozen Btrfs RSP collector grammar."""
import re
from .btrfs_watch_facts import WatchEvidenceError, require


def diagnostic_trace(trace, mode, max_inline_offset=648):
    """Return a derived legacy trace plus raw-row mappings and checked steps.

    Only this registered snapshot sequence is accepted; no generic stripping.
    This checks a single selected STR X0,[X19,#offset], not arbitrary instructions.
    """
    require(mode in ('default','explicit'), 'unsupported diagnostic mode')
    require(isinstance(trace,list) and len(trace)<=20000, 'bad diagnostic trace')
    n=3
    def take(command):
        nonlocal n
        require(n<len(trace) and trace[n].get('command')==command, 'diagnostic command/order mismatch at '+str(n+1))
        item=trace[n];n+=1
        require(isinstance(item.get('response'),str), 'missing diagnostic response')
        return item['response']
    def number(command,size=8):
        value=take(command)
        require(bool(re.fullmatch('[0-9a-f]{'+str(size*2)+'}',value)), 'diagnostic value width')
        return int.from_bytes(bytes.fromhex(value),'little')
    require(take('qqemu.sstepbits')=='ENABLE=1,NOIRQ=2,NOTIMER=4','unknown step bits')
    require(take('qqemu.sstep')=='0x7','step mode not established')
    require(take('qqemu.PhyMemMode')=='0','not virtual memory mode')
    if mode=='explicit':
        require(take('Qqemu.sstep=0x7')=='OK','step setting failed')
        require(take('qqemu.sstep')=='0x7','step setting not confirmed')
    output=list(trace[:3]);mapping=[1,2,3];steps=[]
    def snap(pc,address):
        values={key:number(command,4 if key=='pstate' else 8) for key,command in
                [('x0','p0'),('x19','p13'),('sp','p1f'),('pc','p20'),('pstate','p21')]}
        values['instruction']=number(f'm{pc:x},4',4)
        values['memory']=number(f'm{address:x},8')
        require(values['pc']==pc,'snapshot PC inconsistent')
        return values
    while n<len(trace):
        item=trace[n];command=item.get('command','')
        if command.startswith('z2,') and n+1<len(trace) and trace[n+1].get('command')=='p0':
            start=n+1;parts=command.split(',')
            require(len(parts)==3 and parts[2]=='8' and item.get('response')=='OK','bad positive disarm')
            address=int(parts[1],16)
            require(len(output)>=2 and output[-2]['command']=='p20' and output[-1]['command']==f'm{address:x},8','missing preceding positive stop values')
            pc=int.from_bytes(bytes.fromhex(output[-2]['response']),'little')
            old=int.from_bytes(bytes.fromhex(output[-1]['response']),'little')
            output.append(item);mapping.append(n+1);n+=1
            pre=snap(pc,address)
            require(pre['memory']==old,'pre-snapshot memory differs')
            require(pre['x19']+max_inline_offset==address,'snapshot object mismatch')
            # Exact AArch64 STR unsigned immediate encoding for recorded x0/x19.
            expected=0xf9000000 | ((max_inline_offset//8)<<10) | (19<<5)
            require(max_inline_offset%8==0 and pre['instruction']==expected,'unsupported or changed store instruction')
            step_row=n+1
            require(take('s')=='T05thread:01;','unexpected step event or thread')
            output.append(trace[step_row-1]);mapping.append(step_row)
            pc_row=n+1;after=number('p20')
            require(after==pc+4,'single-step PC did not advance exactly one instruction')
            output.append(trace[pc_row-1]);mapping.append(pc_row)
            post=snap(after,address)
            for key in ('x0','x19','sp','pstate'):
                require(pre[key]==post[key],'register/state changed during selected STR: '+key)
            require(post['memory']==pre['x0'],'store outcome not confirmed')
            # Collector's original post-step read must independently agree.
            require(n<len(trace) and trace[n]['command']==f'm{address:x},8','missing collector post-step read')
            require(int.from_bytes(bytes.fromhex(trace[n]['response']),'little')==post['memory'],'post-step read mismatch')
            steps.append(dict(raw_rows=[start,n],pc=pc,address=address,pre=pre,post=post))
        else:
            output.append(item);mapping.append(n+1);n+=1
    require(len(steps)==4,'unexpected diagnostic step count')
    return dict(trace=output,raw_row_for_derived_row=mapping,steps=steps,
                metadata=dict(mode=mode,step_mask='0x7',virtual_memory=True,
                statement='Selected STR step and protocol validated; historical anomaly cause unresolved.'))
