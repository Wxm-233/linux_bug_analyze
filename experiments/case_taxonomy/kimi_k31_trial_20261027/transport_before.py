"""One-attempt Kimi transport; explicit TLS/upload/header/SSE phases.

DC/network credentials and reasoning text never enter saved artifacts.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,http.client,json,queue,ssl,threading,time,urllib.parse,urllib.request

class StreamState:
 def __init__(self,key):
  self.key=key;self.models=set();self.stops=set();self.text=[];self.usage=None
  self.done=False;self.eof=False;self.error=False;self.refused=False;self.tools=False
 def data(self,data):
  if data=='[DONE]':self.done=True;return dict(kind='done')
  if self.done:raise ValueError('data after DONE')
  obj=json.loads(data)
  if not isinstance(obj,dict):raise ValueError('SSE object')
  model=obj.get('model');model=model.replace(self.key,'[REDACTED]') if isinstance(model,str) else None
  if model:self.models.add(model)
  if isinstance(obj.get('usage'),dict):self.usage=obj['usage']
  if obj.get('error'):self.error=True
  safe=dict(kind='event',model=model,choices=[])
  if obj.get('error'):safe['api_error_present']=True
  for c in obj.get('choices',[]):
   d=c.get('delta') or {};item=dict(index=c.get('index'),finish_reason=c.get('finish_reason'))
   if c.get('index',0)!=0:self.error=True
   if isinstance(d.get('content'),str):
    text=d['content'].replace(self.key,'[REDACTED]');self.text.append(text);item['content']=text
   if d.get('refusal'):self.refused=True;item['refusal_present']=True
   if d.get('tool_calls'):self.tools=True;item['tool_calls_present']=True
   if c.get('finish_reason'):self.stops.add(c['finish_reason'])
   safe['choices'].append(item)
  return safe
 def complete(self):
  return bool(''.join(self.text).strip()) and self.models=={'Kimi-K3'} and self.stops=={'stop'} and self.done and self.eof and not(self.error or self.refused or self.tools)

def run(out,raw,key,*,max_tokens=24576,connect_timeout=30,write_timeout=60,read_timeout=600,wall_timeout=900,proxy_mode='direct',connection_factory=None):
 out=Path(out)
 if (out/'receipt.json').exists():raise RuntimeError('preserve prior receipt')
 if min(connect_timeout,write_timeout,read_timeout,wall_timeout)<=0:raise ValueError('positive timeouts required')
 if proxy_mode not in ('system','direct'):raise ValueError('proxy mode')
 endpoint='https://llmapi.isrc.ac.cn/v1/chat/completions';u=urllib.parse.urlsplit(endpoint)
 payload=dict(model='Kimi-K3',messages=[dict(role='user',content=raw.decode('utf-8'))],max_tokens=max_tokens,stream=True,stream_options=dict(include_usage=True))
 wire=json.dumps(payload,ensure_ascii=False).encode('utf-8');proxy=None
 if proxy_mode=='system' and not urllib.request.proxy_bypass(u.hostname):
  value=urllib.request.getproxies().get('https')
  if value:
   proxy=urllib.parse.urlsplit(value if '://' in value else 'http://'+value)
   if proxy.scheme!='http' or proxy.username or proxy.password:raise ValueError('unsupported proxy configuration; no automatic fallback')
 plan=dict(model='Kimi-K3',endpoint=endpoint,protocol='OpenAI compatible Chat Completions SSE',credential_profile='kimi-k3-newkey-20261025',prompt_sha256=hashlib.sha256(raw).hexdigest(),payload_sha256=hashlib.sha256(wire).hexdigest(),request_bytes=len(wire),max_output_tokens=max_tokens,connect_timeout_seconds=connect_timeout,write_timeout_seconds=write_timeout,read_idle_timeout_seconds=read_timeout,wall_clock_seconds=wall_timeout,automatic_retries=0,per_call_allowance=1000000,historical_usage_deducted=False,default_route_changed=False,proxy_mode=proxy_mode,proxy_present=proxy is not None,transport_version=2)
 def save(n,v):(out/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 save('call_plan.json',plan);started=time.monotonic();info=dict(plan,status='started',started_at=datetime.now(timezone.utc).isoformat(),phase='connect',actual_models=[],visible_reported_tokens=None,usage_known=False);save('receipt.json',info)
 q=queue.Queue();state=StreamState(key)
 def worker():
  conn=None;phase='connect'
  def emit(**e):q.put(dict(e,elapsed_seconds=round(time.monotonic()-started,3)))
  try:
   emit(kind='phase',phase=phase)
   if connection_factory:conn=connection_factory()
   else:
    host=proxy.hostname if proxy else u.hostname;port=(proxy.port or 80) if proxy else (u.port or 443)
    conn=http.client.HTTPSConnection(host,port,timeout=connect_timeout,context=ssl.create_default_context())
    if proxy:conn.set_tunnel(u.hostname,u.port or 443)
   conn.connect();emit(kind='connected');phase='request_upload';emit(kind='phase',phase=phase);conn.sock.settimeout(write_timeout)
   conn.request('POST',u.path,body=wire,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json','Accept':'text/event-stream'})
   phase='response_headers';emit(kind='phase',phase=phase,request_bytes_sent=len(wire));conn.sock.settimeout(read_timeout)
   response=conn.getresponse();emit(kind='http',status=response.status,content_type=response.getheader('Content-Type'))
   if response.status!=200:emit(kind='error',phase=phase,error_type='HTTPStatus',status=response.status);return
   phase='sse_read';emit(kind='phase',phase=phase);pending=[]
   while True:
    line=response.readline()
    if not line:
     if pending:emit(kind='data',data='\n'.join(pending))
     emit(kind='eof');break
    line=line.decode('utf-8').rstrip('\r\n')
    if not line:
     if pending:emit(kind='data',data='\n'.join(pending));pending=[]
     else:emit(kind='keepalive')
    elif line.startswith('data:'):pending.append(line[5:].lstrip())
    elif line.startswith(':'):emit(kind='keepalive')
  except Exception as e:
   # Exception text, raw headers and error bodies can expose secrets: omit them.
   emit(kind='error',phase=phase,error_type=type(e).__name__,errno=getattr(e,'errno',None))
  finally:
   if conn:
    try:conn.close()
    except Exception:pass
 threading.Thread(target=worker,daemon=True).start();last_save=started
 with (out/'events.jsonl').open('w',encoding='utf-8',buffering=1) as events,(out/'partial_text.md').open('w',encoding='utf-8',buffering=1) as partial:
  while time.monotonic()-started<wall_timeout:
   try:e=q.get(timeout=min(.3,max(.01,wall_timeout-(time.monotonic()-started))))
   except queue.Empty:
    if time.monotonic()-last_save>=5:
     info['elapsed_seconds']=round(time.monotonic()-started,3);save('receipt.json',info);last_save=time.monotonic()
    continue
   if e['kind']=='data':
    try:e=dict(state.data(e['data']),elapsed_seconds=e['elapsed_seconds'])
    except Exception as err:e=dict(kind='error',phase='sse_parse',error_type=type(err).__name__,elapsed_seconds=e['elapsed_seconds'])
    if 'first_sse_seconds' not in info:info['first_sse_seconds']=e['elapsed_seconds']
    for c in e.get('choices',[]):
     if c.get('content'):partial.write(c['content'])
   if e['kind']=='phase':info['phase']=e['phase']
   elif e['kind']=='connected':info['connect_seconds']=e['elapsed_seconds']
   elif e['kind']=='http':info['http_status']=e['status'];info['response_headers_seconds']=e['elapsed_seconds']
   elif e['kind']=='error':state.error=True;info['error']=e
   elif e['kind']=='eof':state.eof=True
   events.write(json.dumps(e,ensure_ascii=False)+'\n');info.update(event_elapsed_seconds=e['elapsed_seconds'],elapsed_seconds=round(time.monotonic()-started,3),actual_models=sorted(state.models),finish_reasons=sorted(state.stops),text_characters=sum(map(len,state.text)))
   save('receipt.json',info);last_save=time.monotonic()
   if e['kind'] in ('error','eof'):break
  else:
   state.error=True;info['wall_clock_limit_reached']=True;info['error']=dict(kind='error',error_type='WallTimeout',phase=info['phase']);events.write(json.dumps(info['error'])+'\n')
 complete=state.complete()
 if complete:(out/'final.md').write_text(''.join(state.text),encoding='utf-8')
 info.update(status='complete_final_received' if complete else 'incomplete_or_error',elapsed_seconds=round(time.monotonic()-started,3),actual_models=sorted(state.models),finish_reasons=sorted(state.stops),done_marker=state.done,network_eof=state.eof,refusal_observed=state.refused,usage=state.usage,visible_reported_tokens=(state.usage or {}).get('total_tokens'),usage_known=False,usage_note='Provider counters retained; complete billing not independently established.',final_characters=sum(map(len,state.text)) if complete else 0,semantic_review_allowed=complete)
 save('receipt.json',info);return info
