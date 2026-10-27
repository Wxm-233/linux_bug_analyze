"""Strict model-output ingestion; citation identity is not semantic authority."""
from pathlib import Path
import hashlib
import json
import re

from .contract_protocol import ContractError, validate_contract


class CandidateInputError(ValueError):
    pass


def _need(ok, why):
    if not ok:
        raise CandidateInputError(why)


def _unique(pairs):
    result = {}
    for key, value in pairs:
        _need(key not in result, 'duplicate JSON key: '+key)
        result[key] = value
    return result


def parse_model_candidate(text, documents, *, read_bytes=None):
    """Accept one JSON object, optionally in a sole json fence; no repair.

    documents is a separately pinned registry, including provided line spans.
    Candidate claims cannot set evidence statuses or create review ledgers.
    """
    _need(isinstance(text, str) and 0 < len(text.encode('utf-8')) <= 262144, 'invalid output size')
    body = text.strip()
    fenced = body.startswith('```')
    if fenced:
        match = re.fullmatch(r'```(?:json)?\s*\n([\s\S]*?)\n```', body)
        _need(match is not None, 'unsupported JSON fence or surrounding prose')
        body = match[1]
    try:
        value = json.loads(body, object_pairs_hook=_unique,
                           parse_constant=lambda x: (_ for _ in ()).throw(CandidateInputError('nonfinite number')))
    except (json.JSONDecodeError, RecursionError) as exc:
        raise CandidateInputError('invalid JSON') from exc
    fields = {'schema','interface_id','revision','deadline_event','contract','symbol_bindings','citations','uncertainties'}
    _need(isinstance(value, dict) and set(value) == fields, 'unexpected candidate fields')
    _need(value['schema'] == 'model_interface_candidate_v1', 'unsupported output schema')
    for key in ('interface_id','revision','deadline_event'):
        _need(isinstance(value[key], str) and 0 < len(value[key]) <= 160, 'invalid '+key)
    try:
        validate_contract(value['contract'])
    except (ContractError, TypeError, KeyError) as exc:
        raise CandidateInputError('invalid contract: '+str(exc)) from exc
    _need(value['contract']['revision'] == value['revision'], 'revision mismatch')
    _need(all(v == 'model_proposal' for v in value['contract']['field_origins'].values()), 'model cannot assert reviewed provenance')
    bindings = value['symbol_bindings']
    _need(isinstance(bindings, dict) and set(bindings) == set(value['contract']['symbols']), 'incomplete symbol bindings')
    _need(all(isinstance(v,str) and 0 < len(v) <= 160 for v in bindings.values()), 'invalid semantic role')
    uncertainty = value['uncertainties']
    _need(isinstance(uncertainty,list) and len(uncertainty)<=32 and all(isinstance(v,str) and len(v)<=4096 for v in uncertainty), 'invalid uncertainty list')
    citations = value['citations']
    _need(isinstance(citations,list) and 4 <= len(citations) <= 64, 'invalid citation count')
    support_fields = {'scope','relation','symbol_bindings','deadline_event'}
    covered, snapshots = set(), {}
    read_bytes = read_bytes or (lambda p: Path(p).read_bytes())
    for ref in citations:
        _need(isinstance(ref,dict) and set(ref)=={'supports','document','start_line','end_line','quote'}, 'invalid citation fields')
        _need(isinstance(ref['supports'],str) and ref['supports'] in support_fields, 'unknown supported field')
        covered.add(ref['supports'])
        doc_id = ref['document']
        _need(isinstance(doc_id,str) and doc_id in documents, 'unregistered document')
        doc = documents[doc_id]
        _need(doc.get('revision') == value['revision'], 'citation revision mismatch')
        if doc_id not in snapshots:
            try:
                raw = read_bytes(doc['path'])
                _need(hashlib.sha256(raw).hexdigest()==doc['sha256'], 'source SHA mismatch')
                snapshots[doc_id] = raw.decode('utf-8-sig').splitlines()
            except (OSError, UnicodeError, KeyError) as exc:
                raise CandidateInputError('unreadable registered source') from exc
        lines = snapshots[doc_id]
        lo,hi=ref['start_line'],ref['end_line']
        _need(type(lo) is int and type(hi) is int and 1<=lo<=hi<=len(lines), 'citation outside source')
        _need(any(a<=lo<=hi<=b for a,b in doc['provided_spans']), 'citation outside supplied spans')
        quote=ref['quote']
        _need(isinstance(quote,str) and 0<len(quote.strip())<=8192,'invalid quote')
        normalize=lambda s:' '.join(s.split())
        _need(normalize(quote) in normalize('\n'.join(lines[lo-1:hi])), 'quote not present at cited lines')
    _need(covered==support_fields,'missing field citation')
    return {'candidate':{k:value[k] for k in ('interface_id','deadline_event','contract','symbol_bindings')},
            'citations':citations,'uncertainties':uncertainty,
            'raw_output_sha256':hashlib.sha256(text.encode('utf-8')).hexdigest(),
            'normalization':'outer_json_fence_removed' if fenced else 'JSON_only',
            'citation_identity_verified':True,'citation_semantics_verified':False,
            'human_candidate_rewrite':False}
