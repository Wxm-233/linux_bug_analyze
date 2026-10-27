"""Strict projection of the registered single-CPU AArch64 RSP experiment.

This recognizes one bounded collector protocol, not arbitrary GDB sessions.
Trusted artifact identities and semantic scope must be supplied externally.
"""
import re


class WatchEvidenceError(ValueError):
    pass


def require(ok, why):
    if not ok:
        raise WatchEvidenceError(why)


class Cursor:
    def __init__(self, trace):
        require(isinstance(trace, list) and len(trace) <= 10000, 'invalid trace')
        self.trace, self.i = trace, 0

    def get(self, command):
        require(self.i < len(self.trace), 'truncated trace at '+command)
        item = self.trace[self.i]
        self.i += 1
        require(item.get('command') == command, 'unexpected command at row '+str(self.i))
        response = item.get('response')
        require(isinstance(response, str), 'missing response')
        return response

    def ok(self, command):
        require(self.get(command) == 'OK', 'command not acknowledged: '+command)

    def value(self, command, size=8):
        response = self.get(command)
        require(bool(re.fullmatch('[0-9a-f]{'+str(size*2)+'}', response)), 'invalid register/memory width')
        return int.from_bytes(bytes.fromhex(response), 'little')

    def mem(self, address, size):
        return self.value(f'm{address:x},{size:x}', size)

    def reg(self, number):
        return self.value(f'p{number:x}')


def project_watch_intervals(trace, prepared, operands, *, context_id):
    """Emit trace-scoped no-write records only; refuse unsupported sequences."""
    require(bool(re.fullmatch(r'[A-Za-z0-9_.:-]{1,80}', context_id)), 'invalid context')
    for key in ('image_sha256','vmlinux_sha256'):
        require(bool(re.fullmatch(r'[0-9a-f]{64}', prepared.get(key, ''))), 'missing build identity')
    c = Cursor(trace)
    require('qXfer:features:read+' in c.get('qSupported:xmlRegisters=aarch64'), 'missing protocol support')
    require(c.get('?') == 'T05thread:01;', 'unexpected initial thread/stop')
    require('<architecture>aarch64</architecture>' in c.get('qXfer:features:read:target.xml:0,fff'), 'wrong architecture')
    entry, o = prepared['entry'], prepared['offsets']
    c.ok(f'Z0,{entry:x},4')
    rows = []
    # Null options calls are explicitly outside monitored intervals.
    for encounter in range(8):
        start = c.i+1
        require(c.get('c') == 'T05thread:01;', 'entry stop mismatch')
        require(c.reg(32) == entry, 'wrong entry PC')
        info, options, ret, sp = c.reg(0), c.reg(1), c.reg(30), c.reg(31)
        require(info != 0 and ret != entry and ret != 0 and sp != 0, 'invalid identity')
        c.ok(f'z0,{entry:x},4')
        if options == 0:
            require(c.get('s') == 'T05thread:01;', 'null-options step mismatch')
            c.ok(f'Z0,{entry:x},4')
            continue
        raw = c.get(f'm{options:x},40')
        require(bool(re.fullmatch('[0-9a-f]{128}', raw)), 'invalid option read')
        option = bytes.fromhex(raw).split(b'\0')[0].decode('ascii')
        event = operands[len(rows)]
        require(option == 'max_inline='+str(event['request']), 'option/event mismatch')
        superptr = c.mem(info+o['super_pointer'], 8)
        require(superptr and superptr != info, 'invalid super object')
        cache, before = c.mem(info+o['cache'], 4), c.mem(superptr+o['disk_sector'], 4)
        require(int(event['info_pointer'], 16) == info and int(event['super_pointer'], 16) == superptr, 'boot/trace object mismatch')
        require(event['consumed_cache'] == cache and event['adjacent_disk_sample'] == before, 'boot/trace values mismatch')
        target, pointer, positive = superptr+o['disk_sector'], info+o['super_pointer'], info+o['max_inline']
        for address, size in ((target,4),(pointer,8),(positive,8)):
            c.ok(f'Z2,{address:x},{size:x}')
        c.ok(f'Z0,{ret:x},4')
        positives = []
        for _ in range(20):
            reply = c.get('c')
            pc = c.reg(32)
            if pc == ret:
                require(reply == 'T05thread:01;', 'return stop has unexpected reason')
                require(c.reg(31) == sp, 'wrong return stack')
                break
            require(reply == f'T05thread:01;watch:{positive:x};', 'target write or unexpected watch event')
            value = c.mem(positive, 8)
            # Target watchpoints may not be removed, even for positive-control steps.
            c.ok(f'z2,{positive:x},8')
            require(c.get('s') == 'T05thread:01;', 'unexpected single-step stop')
            require(c.reg(32) == pc+4, 'single-step PC mismatch')
            after = c.mem(positive, 8)
            c.ok(f'Z2,{positive:x},8')
            positives.append(dict(pc=pc, before=value, after=after))
        else:
            raise WatchEvidenceError('no bounded return')
        require(len(positives) == 2, 'missing/extra natural-write controls')
        require(positives[0]['after'] == event['request'] and positives[1]['before'] == event['request'] and positives[1]['after'] == event['result'], 'positive-control/operand mismatch')
        require(c.mem(target,4) == before, 'changed endpoint disk value')
        require(c.mem(pointer,8) == superptr, 'changed endpoint pointer')
        require(c.reg(0) == 0, 'parse returned error')
        end = c.i
        for address, size in ((target,4),(pointer,8),(positive,8)):
            c.ok(f'z2,{address:x},{size:x}')
        c.ok(f'z0,{ret:x},4')
        rows.append(dict(interval_id=f'{context_id}:parse{encounter}',context_id=context_id,
            image_sha256=prepared['image_sha256'],vmlinux_sha256=prepared['vmlinux_sha256'],
            object_id=f'{context_id}:parse{encounter}:info{info:x}',info=info,super=superptr,
            entry_pc=entry,return_pc=ret,stack=sp,trace_rows=[start,end],operand_event=event['event_id'],
            fsid=event['fsid'],option=option,cache=cache,disk_sample=before,
            target_virtual_ranges=[[target,4],[pointer,8]],positive_events=positives,
            observed_target_writes=0,coverage='registered_virtual_addresses_single_cpu_tcg',
            interval_evidence='validated_no_target_write_record',
            relation_at_deadline='insufficient',whole_path='insufficient'))
        if len(rows) == len(operands):
            break
        c.ok(f'Z0,{entry:x},4')
    require(len(rows) == len(operands) == 2, 'unexpected interval count')
    c.ok('D')
    require(c.i == len(trace), 'unconsumed trace tail')
    return rows


def assess_interval_claim(record, claim):
    """Bind a projected interval to a limited claim; forbid deadline promotion."""
    result = dict(interval_evidence='insufficient',relation_at_deadline='insufficient',whole_path='insufficient')
    for key in ('context_id','interval_id','object_id','operand_event','coverage','image_sha256','vmlinux_sha256'):
        if claim.get(key) != record.get(key):
            return dict(result,reason='claim binding mismatch: '+key)
    if claim.get('kind') != 'observed_no_target_write':
        return dict(result,reason='unsupported scope or deadline promotion')
    return dict(result,interval_evidence=record['interval_evidence'],
                reason='Only registered virtual ranges and recorded protocol; no alias/DMA/global stability proof.')
