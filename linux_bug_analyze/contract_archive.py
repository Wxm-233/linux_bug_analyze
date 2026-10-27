"""Integrity gate for a pinned external-review archive, not semantic approval."""
import hashlib
import json
from pathlib import Path


class ArchiveError(ValueError):
    pass


def load_verified_archive(path, expected_sha256, *, read_bytes=None):
    """Return bundles and hashes of the exact byte snapshots checked.

    The caller supplies a trusted digest outside the archive. This does not
    authenticate the reviewer or prove any claim. An injected reader is for
    deterministic corruption controls; it is never a runtime observation.
    """
    reader = read_bytes or (lambda p: Path(p).read_bytes())
    try:
        raw = reader(str(path))
        if hashlib.sha256(raw).hexdigest() != expected_sha256:
            raise ArchiveError('review archive digest mismatch')
        bundles = json.loads(raw)
        if not isinstance(bundles, list) or not bundles:
            raise ArchiveError('empty or malformed archive')
        snapshots = {}
        for bundle in bundles:
            ledger = bundle['ledger']
            revision = bundle['contract']['revision']
            for doc in ledger['documents'].values():
                p = doc['path']
                if not isinstance(p, str) or not Path(p).is_absolute():
                    raise ArchiveError('document path must be absolute')
                if p not in snapshots:
                    content = reader(p)
                    snapshots[p] = dict(sha256=hashlib.sha256(content).hexdigest(),
                                        lines=len(content.decode('utf-8').splitlines()))
                actual = snapshots[p]
                if actual['sha256'] != doc.get('sha256'):
                    raise ArchiveError('document digest mismatch: '+p)
                if doc['context_revision'] != revision:
                    raise ArchiveError('document revision mismatch: '+p)
                lo, hi = doc['start_line'], doc['end_line']
                if type(lo) is not int or type(hi) is not int or not 1 <= lo <= hi <= actual['lines']:
                    raise ArchiveError('document range outside actual snapshot: '+p)
            for claim in ledger['claims'].values():
                for ref in claim['references']:
                    doc = ledger['documents'][ref['document']]
                    lo, hi = ref['start_line'], ref['end_line']
                    if type(lo) is not int or type(hi) is not int or not doc['start_line'] <= lo <= hi <= doc['end_line']:
                        raise ArchiveError('claim range outside document')
        return bundles, snapshots
    except ArchiveError:
        raise
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
        raise ArchiveError('unreadable or malformed evidence: '+str(exc)) from exc
