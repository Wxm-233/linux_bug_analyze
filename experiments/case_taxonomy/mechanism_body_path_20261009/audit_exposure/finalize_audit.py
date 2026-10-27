from pathlib import Path
import hashlib, json, collections

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
ROOT = STAGE.parent

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def load(p):
    return json.loads(p.read_text(encoding='utf-8'))

scope = load(HERE/'scope_search.json')
pool = load(STAGE/'metadata_pool.json')
matches = load(HERE/'matches.json')
assert scope['metadata_pool_sha256'] == sha(STAGE/'metadata_pool.json')
for f in scope['searched_files']:
    assert sha(ROOT/f['path']) == f['sha256'], f['path']

evidence_map = {
    '95b087f87b780daafad1dbb2c84e81b729d5d33f': [
        ('case_reviews.md', 15, 'prior_source_patch_review', '该复核给出 __be32/CPU/__le32 传递问题及发送/完成路径修复，属于已审阅源案例；范围外结论不消除曝光。'),
        ('final_synthesis_repr_v2_selection_pre.json', 12, 'explicit_prior_source_exposure_record', '此前选样协议已明确固定组源码读过。'),
        ('final_synthesis_repr_selection_pre.json', 9, 'explicit_prior_source_exposure_record', '此前选样协议明确固定12组已审阅源码。')],
    '09f688f0718f57f9cf68ee1aa94490f641e759ba': [
        ('endian_producer_single_revision_review.md', 3, 'prior_rule_development', '明确以先前已读PWM父版开发生产侧规则并以修复版回放。'),
        ('endian_producer_single_revision_review.md', 11, 'prior_source_review_and_detector_result', '已读父版给出 get_property 第69行直接赋值候选与同文件转换对照，足以确认机制与源码曝光。'),
        ('endian_consumer_holdout_review.md', 7, 'prior_source_patch_review', '给出具体字段/旧初始化/修复转换并指出消费者规则范围未覆盖。')],
}
records=[]
for row in pool['records']:
    commit=row['commit']
    refs=[m for m in matches if m['commit']==commit]
    direct=[]
    for path,line,kind,reason in evidence_map.get(commit,[]):
        source=ROOT/path
        quote=source.read_text(encoding='utf-8').splitlines()[line-1]
        assert commit in quote or commit[:12] in quote, (path,line)
        assert any(m['path']==path and m['line']==line for m in refs), (path,line)
        direct.append({'path':path,'line':line,'sha256':sha(source),'text':quote,'evidence_type':kind,'reason':reason})
    exposed=bool(direct)
    if refs and not exposed:
        raise AssertionError('Unclassified references: '+commit)
    metadata_only=[]
    for ref in refs:
        if ref['path'] in {'pilot_500_20260926.tsv','2026-09-28_endian_holdout_metadata_pre.json'}:
            metadata_only.append(ref)
    records.append({'commit':commit,'pool_order':row['pool_order'],'representation_order':row['representation_order'],
        'status':'source_exposure_confirmed' if exposed else 'no_evidence_in_defined_scope',
        'source_exposure_confirmed':exposed,'reference_count':len(refs),
        'actual_source_evidence':direct,'metadata_only_reference_examples':metadata_only,
        'all_references':refs,
        'interpretation':'已存在具体源码/补丁审阅或规则开发证据，不能作为此机制未曝光样本。' if exposed else '仅在固定研究记录定义域未发现该完整提交或前12位引用；不是全球盲样，也不能保证旧短判定从未见过材料。'})
assert len(records)==32
result={'schema_version':1,'date':'2026-10-09','auditor':'/root/body_path_exposure',
    'metadata_pool_sha256':sha(STAGE/'metadata_pool.json'),'scope_search_sha256':sha(HERE/'scope_search.json'),
    'matches_sha256':sha(HERE/'matches.json'),'search_receipts_sha256':sha(HERE/'search_receipts.json'),
    'pool_count':len(records),'searched_file_count':len(scope['searched_files']),
    'searched_files':scope['searched_files'],
    'search_terms':'每条commit全40位与前12位；固定字符串rg，完整32项，既有case_taxonomy md/json/tsv，排除完整mechanism_body_path_20261009目录。',
    'new_git_source_patch_or_model_read':False,
    'status_counts':dict(collections.Counter(r['status'] for r in records)),
    'limitation':'审计域不包含项目旧模型输出目录、聊天历史、所有Python/C或全部外部来源；不存在域内引用不等于无历史曝光。',
    'records':records}
(HERE/'exposure_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
summary='''# 固定32项独立曝光审计

2026-10-09。仅检索此前 case_taxonomy 的 md/json/tsv 记录，排除完整本轮目录。使用 rg 固定字符串检索每条完整 commit 与前12位；范围、命令、原始输出、匹配全文均保留。没有访问新 Git、源码、补丁或模型结果。

范围共752个文件，32项池对应222条引用。30项在定义域无证据；2项确认已审阅源码或参与规则开发；无未决项。范围文件指纹在写结论前逐条复核未变化。这里的“无证据”不代表全球盲样，旧短判定也可能已读取材料。

- bnxt_re `95b087f87b78`：case_reviews.md 第15行明确描述 encoded/CPU/硬件表示传递及修复路径；此前两个选样协议明确标记固定12组源码已读。pilot TSV 是元数据引用，不单独作为源码曝光依据。
- PWM `09f688f0718f`：endian_producer_single_revision_review.md 第3行明确已读父版用于开发，第11行给出字段赋值候选和实际规则输出；endian_consumer_holdout_review.md 第7行也已描述旧/修复写入语义。旧元数据文件引用本身不单独证明源码读过。
- i3c `7a2bccd1a27f`：全40位及前12位在上述定义范围都没有引用；允许按协议进入有限取证，但不称独立阳性或全球未知案例。

与标题REP匹配相交后：3项标题命中，2项已曝光被排除，唯一未有定义域源码曝光证据的项是 i3c。此处不解释其缺陷原因，也不预测正文是否有长度机制。

metadata_pool SHA-256：`POOL`。
exposure_audit SHA-256：`AUDIT`。
scope_search SHA-256：`SCOPE`。
'''.replace('POOL',sha(STAGE/'metadata_pool.json')).replace('AUDIT',sha(HERE/'exposure_audit.json')).replace('SCOPE',sha(HERE/'scope_search.json'))
(HERE/'review.md').write_text(summary,encoding='utf-8')
print(json.dumps({'audit_sha256':sha(HERE/'exposure_audit.json'),'scope_sha256':sha(HERE/'scope_search.json'),'records':len(records),'status_counts':result['status_counts']},ensure_ascii=False))
