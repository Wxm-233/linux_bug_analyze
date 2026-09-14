"""Source-based leads for review, not vulnerability labels or proofs."""
import re


# Require both a semantic lead in the commit explanation and matching executable
# changes. Directory names and the model's phrasing are deliberately not inputs.
RULES = {
    'page_geometry': (r'page size|64k|page_size|sectorsize', r'page|sector|inline|hd_per'),
    'mapping_permissions': (r'permissions?|write.only|\bWO\b', r'pte|prot|permission'),
    'domain_transition': (r'blocked|bypass|identity', r'ste|attach|detach|domain'),
    'abi_representation': (r'compat|x32|endianness|big.endian', r'compat|bitmap|copy|u32|u64'),
    'topology_lifecycle': (r'topology|hotplug notifier', r'mask|topology|cpu_setup'),
    'capability_description': (r'online.capable|synchroni[sz]|syncroni[sz]|fw_devlink', r'capable|clock|stable|fwnode|link'),
    'unwind_contract': (r'unwind|stack.trace|stack_trace', r'frame|stack|unwind'),
}


def source_signals(commit):
    changed = [line[1:] for line in commit.diff.splitlines()
               if line[:1] in ('+', '-') and not line.startswith(('+++', '---'))]
    # Omit recognizable comment-only lines. This is intentionally a lead detector,
    # not a C parser or a deterministic permission to discard a commit.
    code = '\n'.join(line for line in changed if line.strip()
                     and not line.lstrip().startswith(('/*', '*', '//')))
    explanation = commit.subject + '\n' + commit.body
    found = []
    for family, (lead, change) in RULES.items():
        if code and re.search(lead, explanation, re.I) and re.search(change, code, re.I):
            anchors = [line for line in explanation.splitlines() if re.search(lead, line, re.I)]
            edits = [line for line in code.splitlines() if re.search(change, line, re.I)]
            found.append({'family': family, 'explanation': anchors[:2], 'changed_lines': edits[:2]})
    return found
