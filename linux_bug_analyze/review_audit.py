"""Reproducible stratified sampling and explicitly scoped quality estimates."""
import math
import random


def wilson(successes, total):
    if not total:
        return None
    z = 1.959963984540054
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    radius = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return [max(0, center - radius), min(1, center + radius)]


def make_audit_plan(records, selection, results, human_labels, *, rate, minimum, boundary, seed):
    groups = {name: [] for name in ('related', 'unrelated', 'uncertain')}
    for h in selection:
        result = results.get(h)
        if not result or result['status'] != 'success':
            raise ValueError('LLM 清单尚未全部成功完成；请先续跑或处理失败，不能把未完成结果当作负例。')
        groups[result['decision']['relevance']].append(h)
    total = sum(map(len, groups.values()))
    target = min(total, max(math.ceil(total * rate), minimum))
    # Give each nonempty stratum at least one sample, then allocate proportionally.
    sizes = {k: int(bool(v)) for k, v in groups.items()}
    target = max(target, sum(sizes.values()))
    while sum(sizes.values()) < target:
        k = max((k for k in groups if sizes[k] < len(groups[k])),
                key=lambda k: len(groups[k]) * target / max(total, 1) - sizes[k])
        sizes[k] += 1
    rng = random.Random(seed)
    samples = []
    populations = {}
    for k, group in groups.items():
        populations[k] = len(group)
        for h in rng.sample(sorted(group), sizes[k]):
            samples.append(dict(hash=h, stratum=k, population=len(group), sample_size=sizes[k],
                                inclusion_probability=sizes[k] / len(group)))
    selected = set(selection)
    for name, pool in (
        ('below_threshold', [r['hash'] for r in records if r['candidate'] and r['hash'] not in selected
                             and r['hash'] not in human_labels]),
        ('regex_rejected', [r['hash'] for r in records if not r['candidate']
                            and r['hash'] not in human_labels]),
    ):
        populations[name] = len(pool)
        count = min(boundary, len(pool))
        for h in rng.sample(sorted(pool), count):
            samples.append(dict(hash=h, stratum=name, population=len(pool), sample_size=count,
                                inclusion_probability=count / len(pool)))
    rng.shuffle(samples)  # Do not reveal predicted classes through review order.
    return dict(seed=seed, rate=rate, minimum=minimum, boundary=boundary,
                populations=populations, samples=samples)


def audit_statistics(plan, labels):
    groups = {}
    for name, population in plan['populations'].items():
        sample = [r for r in plan['samples'] if r['stratum'] == name]
        reviewed = [labels[r['hash']]['label'] for r in sample if r['hash'] in labels]
        binary = [v for v in reviewed if v != 'uncertain']
        positives = binary.count('related')
        # Incomplete samples and unresolved human judgments must not quietly
        # disappear from the denominator of an advertised accuracy estimate.
        complete = bool(sample) and len(binary) == len(sample)
        groups[name] = dict(population=population, sampled=len(sample), reviewed=len(reviewed),
                            resolved=len(binary), human_related=positives,
                            human_uncertain=reviewed.count('uncertain'),
                            complete=complete,
                            related_fraction=positives / len(binary) if binary else None,
                            related_fraction_ci95=wilson(positives, len(binary)))
    active = [k for k in ('related', 'unrelated') if groups[k]['population']]
    accuracy = None
    if active and all(groups[k]['complete'] for k in active):
        numerator = sum(groups[k]['population'] * (
            groups[k]['related_fraction'] if k == 'related' else 1 - groups[k]['related_fraction'])
            for k in active)
        accuracy = numerator / sum(groups[k]['population'] for k in active)
    return dict(strata=groups, weighted_binary_accuracy=accuracy,
                scope='Only this frozen LLM batch; excludes LLM uncertain/failures. Not pipeline recall.',
                warning='Stratum fractions/intervals are descriptive until every sampled item is resolved; '
                        'Wilson intervals ignore finite-population correction. Boundary checks do not prove recall.')
