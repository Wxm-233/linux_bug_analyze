"""Metadata-only preflight; no model output or case-level lexical judgment."""
from pathlib import Path
import hashlib
import importlib.util
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTER = ROOT.parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    result_path = HERE / 'packet_preflight.json'
    if result_path.exists():
        raise RuntimeError('preserve first preflight')
    spec = importlib.util.spec_from_file_location('n26_raw', HERE / 'run_raw_candidate_checks.py')
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    baseline = adapter.verify_baseline()
    baseline_sha = sha((HERE / 'adapter_baseline.json').read_bytes())
    selection = json.loads((HERE / 'selection.json').read_text())
    initial = json.loads((HERE / 'initial_material_plan.json').read_text())
    supplement = json.loads((HERE / 'supplement_material_plan.json').read_text())
    rows = []
    for case in ['E', 'F']:
        manifest_path = HERE / ('packet_manifest_' + case + '.json')
        backup = manifest_path.with_name(manifest_path.stem + '.pre_amendment.json')
        old_raw = backup.read_bytes() if backup.exists() else manifest_path.read_bytes()
        old = json.loads(old_raw)
        assert old['adapter_baseline_sha256'] == baseline['collection_baseline_sha256']
        if not backup.exists():
            with backup.open('xb') as stream:
                stream.write(old_raw)
        manifest = dict(old, adapter_baseline_sha256=baseline_sha)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        packet_raw = (HERE / ('documents_' + case + '.json')).read_bytes()
        adapter.old.packet_identity(packet_raw, manifest)
        packet = json.loads(packet_raw)
        material = adapter.validate_material_identity(packet, selection, initial, supplement)
        artifacts = {item['path']: (ROOT / item['path']).read_bytes() for item in packet['input_manifest']}
        for raw in artifacts.values():
            origin = json.loads(raw)
            assert origin['adapter_baseline_sha256'] == baseline['collection_baseline_sha256']
        bound = adapter.bind_documents(packet, artifacts)
        assert len(bound) == 7 and all(row['status'] == 'source_bound' for row in bound.values())
        folder = OUTER / manifest['model_directory']
        # Runner read_text() uses universal-newline normalization before sending.
        # Packet manifest already records those transmitted logical bytes.
        prompt_raw = (folder / 'prompt.md').read_text(encoding='utf-8').encode('utf-8')
        assert sha(prompt_raw) == manifest['prompt_sha256'] and len(prompt_raw) == manifest['prompt_utf8_bytes']
        assert not (folder / 'receipt.json').exists()
        rows.append({'case': case, 'documents_bound': len(bound), 'material_identity': material,
                     'prompt_sha256': sha(prompt_raw), 'prompt_utf8_bytes': len(prompt_raw),
                     'prompt_physical_file_sha256': sha((folder / 'prompt.md').read_bytes()),
                     'packet_manifest_before_sha256': sha(old_raw),
                     'packet_manifest_after_sha256': sha(manifest_path.read_bytes()),
                     'changed_manifest_fields': ['adapter_baseline_sha256']})
    result = {'status': 'PASS', 'scope': 'metadata/source binding only; no actual lexical check or model result',
              'baseline_sha256': baseline_sha, 'collection_baseline_sha256': baseline['collection_baseline_sha256'],
              'cases': rows, 'round_reserved_tokens': 400000, 'round_ceiling': 1000000}
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'documents_bound': sum(x['documents_bound'] for x in rows)}))


if __name__ == '__main__':
    main()
