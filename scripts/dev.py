"""python scripts/dev.py --seed；Ctrl+C 关闭子进程。"""
import os,sys,subprocess,secrets,time,argparse
from pathlib import Path

def load_env():
    path=Path('.env')
    if not path.exists():
        path.write_text('\n'.join([f'AI_SERVICE_TOKEN={secrets.token_urlsafe(32)}',f'ADMIN_INVITE_CODE={secrets.token_urlsafe(16)}',f'TECHNICIAN_INVITE_CODE={secrets.token_urlsafe(16)}',f'DEMO_PASSWORD=Demo-{secrets.token_urlsafe(12)}9','AI_CONFIDENCE_THRESHOLD=0.35','AI_POLL_SECONDS=5'])+'\n',encoding='utf-8')
    for line in path.read_text(encoding='utf-8').splitlines():
        if line and not line.startswith('#') and '=' in line:
            key,value=line.split('=',1);os.environ.setdefault(key,value)

def main():
    os.chdir(Path(__file__).resolve().parents[1])
    parser=argparse.ArgumentParser();parser.add_argument('--seed',action='store_true');args=parser.parse_args()
    load_env()
    if args.seed:subprocess.run([sys.executable,'-m','app.seed'],check=True)
    processes=[]
    try:
        for command in [['-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000'],['-m','uvicorn','ai_service.main:app','--host','127.0.0.1','--port','8001'],['-m','ai_service.worker']]:
            processes.append(subprocess.Popen([sys.executable,*command]))
        print('Open http://127.0.0.1:8000 ; API docs /docs ; local configuration .env',flush=True)
        while all(p.poll() is None for p in processes):time.sleep(1)
    except KeyboardInterrupt:pass
    finally:
        for p in processes:
            if p.poll() is None:p.terminate()
        for p in processes:
            try:p.wait(timeout=10)
            except subprocess.TimeoutExpired:p.kill()

if __name__=='__main__':main()
