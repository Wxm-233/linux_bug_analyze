"""Kimi primary analysis: one request, external credential, explicit timeouts."""
from pathlib import Path
import argparse,importlib.util,json
from kimi_transport import run
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
def main():
 p=argparse.ArgumentParser();p.add_argument('output_directory');p.add_argument('--max-output-tokens',type=int,default=24576);p.add_argument('--connect-timeout',type=float,default=30);p.add_argument('--write-timeout',type=float,default=60);p.add_argument('--read-timeout',type=float,default=600);p.add_argument('--wall-timeout',type=float,default=900);p.add_argument('--proxy-mode',choices=['system','direct'],default='direct');a=p.parse_args();out=Path(a.output_directory).resolve()
 if HERE not in out.parents or not out.is_dir() or (out/'receipt.json').exists():raise RuntimeError('use a new directory under ignored model outputs')
 raw=(out/'prompt.md').read_bytes()
 if a.max_output_tokens<=0:raise ValueError('positive output limit')
 spec=importlib.util.spec_from_file_location('credential_reader',HERE/'2026-10-15/run_claude_code.py');client=importlib.util.module_from_spec(spec);spec.loader.exec_module(client);cred=client.read_credential('kimi-k3-newkey-20261025')
 if cred['model']!='Kimi-K3' or cred['base_url'].rstrip('/')!='https://llmapi.isrc.ac.cn/v1':raise RuntimeError('unexpected credential profile route')
 info=run(out,raw,cred.pop('key'),max_tokens=a.max_output_tokens,connect_timeout=a.connect_timeout,write_timeout=a.write_timeout,read_timeout=a.read_timeout,wall_timeout=a.wall_timeout,proxy_mode=a.proxy_mode)
 print(json.dumps({k:info.get(k) for k in ['status','phase','connect_seconds','response_headers_seconds','elapsed_seconds','actual_models','finish_reasons','done_marker','network_eof','visible_reported_tokens','final_characters','error']}))
if __name__=='__main__':main()
