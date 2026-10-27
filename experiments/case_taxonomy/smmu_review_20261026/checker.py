"""Version 3: strict, ordered adapter for the registered qtest fixture.
Manual rule and fixture; not a general SMMU or transcript validator.
"""
def assess(raw, authority_verified):
    out=dict(encoding='insufficient',observed_encoding='insufficient',queue='insufficient',observer='not_qualified',sva_runtime='insufficient',translation_effect='insufficient',whole_path='insufficient',reasons=[])
    words=raw.get('words')
    if not isinstance(words,list) or len(words)>62 or not all(isinstance(p,list) and len(p)==2 and all(type(w) is int and 0<=w<2**64 for w in p) for p in words):
        out['reasons'].append('unsupported_words_or_queue_size');return out
    decoded=[]
    for a,b in words:
        if a&255==0x12:
            tg=(b>>10)&3;ttl=(b>>8)&3;num=(a>>12)&31;scale=(a>>20)&31
            decoded.append(dict(tg=tg,ttl=ttl,num=num,scale=scale,reserved=tg!=0 and ttl==num==scale==0))
    out['commands']=decoded
    if authority_verified is True:
        out['encoding']='violation' if any(c['reserved'] for c in decoded) else 'pass_this_rule_only' if decoded else 'not_applicable'
    else:out['reasons'].append('authority_missing_or_unverified')
    pairs=words+[[0x46,0]];expected=[];values=[]
    for i,p in enumerate(pairs):
        for j,w in enumerate(p):expected.append(('writeq',0x40010000+i*16+j*8,w));values.append(None)
    for i,p in enumerate(pairs):
        for j,w in enumerate(p):expected.append(('readq',0x40010000+i*16+j*8));values.append(w)
    expected.extend([('writeq',0x9050090,0x40010006),('writel',0x9050020,8),('readl',0x9050024),('writel',0x9050098,len(pairs)),('readl',0x9050098),('readl',0x905009c),('readl',0x9050060),('readl',0x9050064)])
    values.extend([None,None,8,None,len(pairs),'cons','ge','gn'])
    try:
        requests=[tuple([parts[0]]+[int(x,0) for x in parts[1:]]) for parts in (r.split() for r in raw['requests'])]
        responses=raw['stdout'].splitlines()
        if requests!=expected or len(responses)!=len(expected):raise ValueError('unsupported_order_or_transcript_shape')
        regs={}
        for op,v,response in zip(expected,values,responses):
            fields=response.split()
            if v is None:
                if fields!=['OK']:raise ValueError('write_reply_invalid')
            else:
                if len(fields)!=2 or fields[0]!='OK':raise ValueError('read_reply_invalid')
                actual=int(fields[1],0)
                if not 0<=actual<2**(64 if op[0]=='readq' else 32):raise ValueError('read_width_invalid')
                if isinstance(v,int):
                    if actual!=v:raise ValueError('readback_mismatch')
                else:regs[v]=actual
        cons=regs['cons'];idx=cons&127;error=(cons>>24)&127;pending=regs['ge']^regs['gn']
        if cons & ~((127<<24)|127) or idx>len(pairs):raise ValueError('unsupported_consumer_state')
        out['queue_fields']=dict(prod=len(pairs),cons=cons,error=error,pending_error=pending)
        out['queue']='error_observed' if error or pending else 'consumed_in_model' if idx==len(pairs) else 'not_fully_consumed'
        out['observed_encoding']=out['encoding']
    except (KeyError,TypeError,ValueError,IndexError,AttributeError) as err:
        out['reasons'].append(str(err))
    return out
