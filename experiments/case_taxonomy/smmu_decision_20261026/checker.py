"""SMMU NH_VA reserved encoding rule, registered qtest adapter only.
No automatic semantic inference or full-system verdict is implemented here.
"""
def assess(raw, authority_verified, observer_qualified=False):
    out={'encoding':'insufficient','observed_encoding':'insufficient','queue':'insufficient','observer':'not_qualified' if not observer_qualified else 'unverified_claim',
         'sva_runtime':'insufficient','translation_effect':'insufficient','whole_path':'insufficient','reasons':[]}
    words=raw.get('words')
    if not isinstance(words,list) or not all(isinstance(p,list) and len(p)==2 and all(type(w) is int and 0<=w<2**64 for w in p) for p in words):
        out['reasons'].append('missing_or_invalid_command_words');return out
    cmds=[]
    for a,b in words:
        if a&255==0x12:
            tg=(b>>10)&3;ttl=(b>>8)&3;num=(a>>12)&31;scale=(a>>20)&31
            cmds.append({'tg':tg,'ttl':ttl,'num':num,'scale':scale,'reserved':tg!=0 and ttl==num==scale==0})
    out['commands']=cmds
    if authority_verified:
        out['encoding']='violation' if any(c['reserved'] for c in cmds) else 'pass_this_rule_only' if cmds else 'not_applicable'
    else:out['reasons'].append('authority_missing_or_unverified')
    try:
        reqs=raw['requests'];responses=raw['stdout'].splitlines()
        assert len(reqs)==len(responses)
        reads={};writes={}
        for request,response in zip(reqs,responses):
            op,addr,*value=request.split();addr=int(addr,0)
            if op in ['writeq','writel']:
                assert response=='OK';writes[addr]=int(value[0],0)
            else:
                assert op in ['readq','readl'] and response.startswith('OK ')
                reads[addr]=int(response.split()[1],0)
        # Registered layout: test RAM, 64-entry queue, CMDQEN only, appended SYNC.
        pairs=words+[[0x46,0]]
        for i,pair in enumerate(pairs):
            for j,w in enumerate(pair):
                addr=0x40010000+16*i+8*j;assert writes[addr]==reads[addr]==w
        assert writes[0x9050090]==0x40010006 and writes[0x9050020]==reads[0x9050024]==8
        prod=reads[0x9050098];cons=reads[0x905009c];error=(cons>>24)&127
        assert writes[0x9050098]==prod==len(pairs)
        pending=reads[0x9050060]^reads[0x9050064]
        out['queue_fields']={'prod':prod,'cons':cons,'error':error,'pending_error':pending}
        out['queue']='error_observed' if error or pending else 'consumed_in_model' if cons&127==prod else 'not_fully_consumed'
        out['observed_encoding']=out['encoding']
    except (KeyError,AssertionError,ValueError,TypeError,IndexError):
        out['reasons'].append('queue_transcript_incomplete_or_inconsistent')
    return out
