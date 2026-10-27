"""Identity-gated archive association; never infer an unobserved cached value."""
class BindingError(ValueError):pass
def join(source, runtime, facts, mapping):
 for key in ['revision','profile','image_sha256','config_sha256']:
  if source.get(key)!=runtime.get(key) or not source.get(key):raise BindingError('identity mismatch: '+key)
 if source['page_size']!=facts['page_size']:raise BindingError('page configuration mismatch')
 if source['candidate']['field']!=mapping.get('source_field') or mapping.get('origin')!='researcher_authored':raise BindingError('unregistered field mapping')
 if mapping.get('runtime_field')!='sector_size':raise BindingError('unsupported runtime field mapping')
 if source['template']['status']!='conditional_template':raise BindingError('source template insufficient')
 if not source['compiled_definitions_verified']:raise BindingError('missing configured definition')
 if 'cache_at_consumer' in facts:raise BindingError('runtime adapter supplies no direct cache-consumption sample')
 return {'status':'versioned_archive_association','context_id':facts['context_id'],
  'field':source['candidate']['field'],'source_relation':source['candidate']['relation'],
  'disk_geometry':facts[mapping['runtime_field']], 'disk_geometry_origin':'btrfs-progs dump-super decoded text',
  'mapping_origin':mapping['origin'],'effective_limits':facts['effective_limits'],
  'cache_at_consumer':None,'cache_equals_disk_at_consumer':'insufficient',
  'kernel_object_identity':'insufficient','whole_path':'insufficient',
  'reason':'Configuration/revision and archive filesystem identity do not establish fs_info pointer identity or a cached value at consumption.'}
