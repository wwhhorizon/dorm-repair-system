"""独立推理进程：轮询待分类工单，调用分类 API，提交结果；失败指数退避。"""
import os,time,logging,argparse
from datetime import datetime,timezone
import httpx

logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
BACKEND=os.getenv('BACKEND_URL','http://127.0.0.1:8000')
AI_URL=os.getenv('AI_URL','http://127.0.0.1:8001')

def run_once(client):
    headers={'X-Service-Token':os.environ['AI_SERVICE_TOKEN'],'X-Requested-With':'RepairApp'}
    res=client.get(BACKEND+'/api/ai/pending',headers=headers);res.raise_for_status()
    for ticket in res.json():
        inferred=client.post(AI_URL+'/predict',json={'text':ticket['description']},headers=headers)
        inferred.raise_for_status()
        result=client.post(BACKEND+'/api/ai/results',headers=headers,json={**inferred.json(),'ticket_id':ticket['id'],'timestamp':datetime.now(timezone.utc).isoformat()})
        result.raise_for_status()
        logging.info('ticket=%s accepted=%s',ticket['id'],result.json().get('accepted'))
    return len(res.json())

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--once',action='store_true');args=parser.parse_args()
    if not os.getenv('AI_SERVICE_TOKEN'):raise SystemExit('AI_SERVICE_TOKEN is required')
    interval=max(1,float(os.getenv('AI_POLL_SECONDS','5')));backoff=1
    with httpx.Client(timeout=15) as client:
        while True:
            try:
                run_once(client);backoff=1
                if args.once:return
                time.sleep(interval)
            except (httpx.HTTPError,ValueError,KeyError) as exc:
                logging.error('AI pipeline failed: %s',type(exc).__name__)
                if args.once:raise
                time.sleep(min(60,backoff));backoff=min(60,backoff*2)

if __name__=='__main__':main()
