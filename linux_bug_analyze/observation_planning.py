"""Bounded observation coverage and min-clamp probes; no semantic approval."""


def assess_observability(required, available):
    """Required roles are externally reviewed, never inferred from role names."""
    if (not isinstance(required,list) or not required or
            not all(isinstance(x,str) and x for x in required) or
            len(required)!=len(set(required)) or not isinstance(available,dict)):
        return dict(status='invalid_input',missing=[],semantic_authority_established=False)
    missing=[]
    for role in required:
        fact=available.get(role,{})
        if (not isinstance(fact,dict) or fact.get('status')!='available' or
                fact.get('origin')!='reviewed_adapter' or
                not isinstance(fact.get('references'),list) or not fact['references']):
            missing.append(role)
    return dict(status='observable_under_registered_adapter' if not missing else 'insufficient',
                missing=missing,semantic_authority_established=False)


def plan_clamp_probes(requests, cache_hypotheses):
    """Plan min(request,cache) distinctions in a supplied legal request pool.

    Legal inputs and alternative cache hypotheses are external declarations.
    Predicted arithmetic is not actual readiness, a defect label or an oracle.
    """
    valid=lambda xs:isinstance(xs,list) and 0<len(xs)<=128 and all(type(x)is int and 0<=x<2**64 for x in xs) and len(xs)==len(set(xs))
    if not valid(requests) or not valid(cache_hypotheses) or len(cache_hypotheses)<2:
        return dict(status='invalid_input',rows=[])
    rows=[]
    for request in sorted(requests):
        values=[min(request,x) for x in cache_hypotheses]
        rows.append(dict(request=request,hypothetical_results=values,
                         role='discriminating_probe' if len(set(values))>1 else 'behavior_control'))
    return dict(status='planned',rows=rows,readiness_truth='not_evaluated',legality='externally_supplied')
