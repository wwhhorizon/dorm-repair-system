"""启动独立录制环境，不修改日常使用的数据库。Ctrl+C 停止。"""
import os
import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.dev import load_env


def main():
    os.chdir(ROOT)
    load_env()
    target = ROOT / 'artifacts' / ('demo-session-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.db')
    os.environ['DATABASE_URL'] = 'sqlite:///' + target.as_posix()
    os.environ['AI_POLL_SECONDS'] = '1'
    # Legacy account names remain available to the browser verification script.
    from app.seed import seed
    from contextlib import redirect_stdout
    import io
    with redirect_stdout(io.StringIO()):
        seed()
    from app.models import SessionLocal, User
    with SessionLocal() as db:
        for old, new in [('student', '袁谦朗'), ('student2', '另一同学'), ('admin', '宿管值班'), ('repair', '维修值班')]:
            user = db.query(User).filter_by(username=old).one()
            user.username = new
        db.commit()
    children = []
    try:
        for command in [
            ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000'],
            ['-m', 'uvicorn', 'ai_service.main:app', '--host', '127.0.0.1', '--port', '8001'],
            ['-m', 'ai_service.worker'],
        ]:
            log = (ROOT / "artifacts" / ("demo-" + str(len(children)) + ".log")).open("w",encoding="utf-8")
            children.append(subprocess.Popen([sys.executable, *command],stdout=log,stderr=subprocess.STDOUT))
        print('录制环境：http://127.0.0.1:8000；数据库：' + str(target), flush=True)
        while all(p.poll() is None for p in children):
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for p in children:
            if p.poll() is None:
                p.terminate()
        for p in children:
            p.wait(timeout=15)


if __name__ == '__main__':
    main()
