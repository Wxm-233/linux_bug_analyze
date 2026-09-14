"""Short-screen wire protocol and conservative exclusion checks."""
import json


def evidence_lines(material):
    # Bound each source unit so resolved quotes satisfy the saved-result protocol.
    return [line[i:i + 300] for line in material.splitlines() if line.strip()
            for i in range(0, len(line), 300) if line[i:i + 300].strip()]


def parse_response(text, lines):
    data = json.loads(text)
    fields = {'relevance', 'reason', 'evidence_ids', 'needs_review',
              'vertical', 'horizontal', 'exclusion_basis'}
    if not isinstance(data, dict) or set(data) != fields:
        raise ValueError('短判定结构字段无效')
    ids = data['evidence_ids']
    if (not isinstance(ids, list) or not 1 <= len(ids) <= 3
            or any(type(i) is not int or not 1 <= i <= len(lines) for i in ids)
            or len(set(ids)) != len(ids)):
        raise ValueError('证据编号无效')
    for name in ('vertical', 'horizontal'):
        if data[name] not in ('present', 'absent', 'unknown'):
            raise ValueError('语义边界状态无效')
    if data['exclusion_basis'] not in ('feature', 'cleanup', 'ordinary_bug',
                                      'insufficient_evidence', 'directory_only',
                                      'no_cross_arch', 'none'):
        raise ValueError('排除依据无效')
    decision = {k: data[k] for k in ('relevance', 'reason', 'needs_review')}
    decision['evidence'] = [lines[i - 1] for i in ids]
    audit = {k: data[k] for k in ('vertical', 'horizontal', 'exclusion_basis', 'evidence_ids')}
    return decision, audit


def exclusion_guard(decision, audit, signals=()):
    """Flag insufficient exclusion; never assert that a commit is related."""
    flags = []
    if decision['relevance'] == 'unrelated':
        if audit['vertical'] != 'absent' or audit['horizontal'] != 'absent':
            flags.append('boundary_not_ruled_out')
        if audit['exclusion_basis'] not in ('feature', 'cleanup', 'ordinary_bug'):
            flags.append('invalid_exclusion_basis')
        if signals:
            flags.append('source_semantic_lead')
        if flags:
            decision = dict(decision, relevance='uncertain', needs_review=True,
                            reason='排除依据需复核：' + decision['reason'][:580])
    return decision, flags
