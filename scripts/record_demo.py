"""实际浏览器录制 + 中文配音 + 字幕，输出可直接播放的 MP4。

pip install -r requirements-video.txt
python scripts/demo_session.py    # 单独启动空的录制环境
python scripts/record_demo.py --dry-run
python scripts/record_demo.py     # 正式录制前重新启动空环境
"""
import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.dev import load_env
from scripts.demo_story import SCENES

WORK = ROOT / 'artifacts' / 'demo-v2'
EXPORT = ROOT / 'deliverables' / 'demo-source'
BASE = 'http://127.0.0.1:8000'


def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def duration(path):
    r = subprocess.run([ffmpeg(), '-i', str(path)], capture_output=True, text=True, encoding='utf-8', errors='replace')
    m = re.search(r'Duration: (\d+):(\d+):(\d+\.\d+)', r.stderr)
    if not m:
        raise RuntimeError('Cannot probe ' + str(path))
    h, m, s = map(float, m.groups())
    return h * 3600 + m * 60 + s


async def narrate():
    import edge_tts
    semaphore = asyncio.Semaphore(3)

    async def one(i, text):
        path = WORK / f'{i:02}-voice.mp3'
        boundary = WORK / f'{i:02}-words.json'
        if path.exists() and boundary.exists():
            return
        async with semaphore:
            for attempt in range(3):
                chunks = []
                try:
                    voice = edge_tts.Communicate(text, 'zh-CN-XiaoxiaoNeural', rate='-3%', boundary='SentenceBoundary')
                    with path.open('wb') as f:
                        async for chunk in voice.stream():
                            if chunk['type'] == 'audio':
                                f.write(chunk['data'])
                            elif chunk['type'] == 'SentenceBoundary':
                                chunks.append({k: chunk[k] for k in ['offset', 'duration', 'text']})
                    boundary.write_text(json.dumps(chunks, ensure_ascii=False), encoding='utf-8')
                    print('VOICE', i, round(duration(path), 2), flush=True)
                    return
                except Exception:
                    if attempt == 2:
                        raise
                    await asyncio.sleep(2)

    await asyncio.gather(*(one(i, text) for i, (_, text) in enumerate(SCENES, 1)))


def capture(dry=False):
    from playwright.sync_api import sync_playwright, expect
    errors = []
    manifest = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        contexts = {}
        for role, username in [('student', '袁谦朗'), ('admin', '宿管值班'), ('repair', '维修值班'), ('guest', '')]:
            kwargs = dict(viewport={'width': 1600, 'height': 810}, locale='zh-CN', timezone_id='Asia/Shanghai', device_scale_factor=1)
            if not dry:
                kwargs.update(record_video_dir=str(WORK / 'raw'), record_video_size={'width': 1600, 'height': 810})
            ctx = browser.new_context(**kwargs)
            if username:
                r = ctx.request.post(BASE + '/api/auth/login', headers={'X-Requested-With': 'RepairApp'}, data={'username': username, 'password': os.environ['DEMO_PASSWORD']})
                assert r.status == 200, r.text()
            contexts[role] = ctx
        # Cursor layer records actual mouse movement; it never replaces page content.
        pointer = """document.addEventListener('DOMContentLoaded',()=>{const c=document.createElement('div');c.style.cssText='position:fixed;width:16px;height:16px;border:2px solid #2455c7;border-radius:50%;background:#ffffff88;pointer-events:none;z-index:2147483647;left:-30px;top:-30px;transform:translate(-50%,-50%)';document.body.append(c);document.addEventListener('mousemove',e=>{c.style.left=e.clientX+'px';c.style.top=e.clientY+'px'});document.addEventListener('mousedown',()=>{c.animate([{boxShadow:'0 0 0 0 #2455c777'},{boxShadow:'0 0 0 18px #2455c700'}],{duration:450})})})"""
        for ctx in contexts.values():
            ctx.add_init_script(pointer)
        ticket = None

        def click(page, selector):
            target = page.locator(selector).first
            target.scroll_into_view_if_needed()
            box = target.bounding_box()
            if box:
                page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2, steps=12)
            page.wait_for_timeout(250 if not dry else 30)
            target.click()
            page.wait_for_timeout(450 if not dry else 80)

        def fill(page, selector, value):
            field = page.locator(selector)
            field.scroll_into_view_if_needed()
            if not dry and field.evaluate("e=>e.tagName==='TEXTAREA'||['comment','note'].includes(e.name)"):
                field.fill(''); field.press_sequentially(value,delay=35)
            else:
                field.fill(value)
            page.wait_for_timeout(400 if not dry else 30)

        def open_ticket(page):
            click(page, f'[data-ticket="{ticket}"]')
            expect(page.locator('#detail')).to_be_visible()

        def make_ticket(page, description, category, building=0, room=0, submit_at=None):
            click(page, '#nav [data-page=new]')
            page.locator('#building-select').select_option(index=building + 1)
            page.locator('#room-select').select_option(index=room + 1)
            page.locator('#ticket-form [name=category]').select_option(category)
            fill(page, '#ticket-form textarea', description)
            if not dry:
                page.wait_for_timeout(1800)
            if submit_at is not None: cue(submit_at)
            click(page, '#ticket-form button.primary')
            expect(page.locator('#detail')).to_be_visible()
            return int(page.locator('.detail-summary .eyebrow').inner_text().split('#')[1])

        roles = ['guest', 'student', 'student', 'student', 'admin', 'repair', 'repair', 'student', 'repair', 'student', 'student', 'admin', 'admin', 'admin', 'student']
        for number, ((title, narration), role) in enumerate(zip(SCENES, roles), 1):
            print('SCENE', number, title, flush=True)
            page = contexts[role].new_page()
            page.on('pageerror', lambda err: errors.append(str(err)))
            started = time.monotonic()
            def cue(seconds):
                if not dry: page.wait_for_timeout(max(0,(seconds-(time.monotonic()-started))*1000))
            route = '#tickets' if number in [4, 7, 8, 9, 10] else ''
            page.goto(BASE + '/' + route)
            expect(page.locator('#auth' if role == 'guest' else '#shell')).to_be_visible()
            if role != 'guest':
                page.locator('.metrics, .table-panel').first.wait_for()
            page.wait_for_timeout(400 if not dry else 40)
            if number == 2:
                expect(page.locator('.metrics article').first).to_contain_text('0')
                page.screenshot(path=str(WORK / 'empty-dashboard.png'))
            elif number == 3:
                ticket = make_ticket(page, '洗手池下方接头持续滴水，柜底已经积水，今晚可以上门检查。', 'other', room=3, submit_at=19)
            elif number == 4:
                open_ticket(page)
                for _ in range(30):
                    d = page.request.get(BASE + f'/api/tickets/{ticket}').json()
                    if d.get('prediction'):
                        break
                    page.wait_for_timeout(500)
                assert d.get('prediction'), 'AI prediction not returned'
                click(page, '#close-detail'); open_ticket(page)
                click(page, '.prediction-meta summary')
                page.screenshot(path=str(WORK / 'classification.png'))
            elif number == 5:
                cue(3); open_ticket(page)
                cue(7)
                page.locator('#classify-form select').select_option('water')
                click(page, '#classify-form button')
                expect(page.locator('.timeline')).to_contain_text('分类确认')
                page.locator('#assign-form [name=assignee_id]').select_option(label='维修值班')
                # A future booking is a scenario input, never a backdated event.
                fill(page, '#assign-form [name=scheduled_at]', (datetime.now()+timedelta(minutes=30)).strftime('%Y-%m-%dT%H:%M'))
                fill(page, '#assign-form [name=note]', '检查下水接头及密封圈，到达前联系同学。')
                if not dry: page.wait_for_timeout(2000)
                cue(20)
                click(page, '#assign-form button.primary')
                expect(page.locator('#detail .badge')).to_have_text('已派单')
            elif number == 6:
                open_ticket(page)
                cue(11)
                click(page, '#action-form button[value=start]')
                expect(page.locator('#detail .badge')).to_have_text('处理中')
                fill(page, '#action-form textarea', '正在检查下水接头，已暂时关闭进水。')
                click(page, '#action-form button[value=comment]')
            elif number == 7:
                open_ticket(page)
                fill(page, '#action-form textarea', '更换接头密封圈并紧固接口，通水检查未见滴漏。')
                cue(13)
                click(page, '#action-form button[value=finish]')
                expect(page.locator('#detail .badge')).to_have_text('待验收')
                page.locator('.timeline').scroll_into_view_if_needed()
            elif number == 8:
                open_ticket(page)
                fill(page, '#action-form textarea', '放水后接口处仍有少量渗水，请复查排水接头。')
                if not dry: page.wait_for_timeout(1800)
                cue(16)
                click(page, '#action-form button[value=reject]')
                expect(page.locator('#detail .badge')).to_have_text('处理中')
            elif number == 9:
                open_ticket(page)
                fill(page, '#action-form textarea', '重新调整排水接头并更换垫片，持续放水检查正常。')
                cue(13)
                click(page, '#action-form button[value=finish]')
                expect(page.locator('#detail .badge')).to_have_text('待验收')
                page.locator('.timeline').scroll_into_view_if_needed()
            elif number == 10:
                open_ticket(page)
                cue(5)
                click(page, '#action-form button[value=accept]')
                expect(page.locator('#detail .badge')).to_have_text('已完成')
                cue(10)
                fill(page, '#evaluation-form [name=comment]', '复查后不再漏水，处理过程有反馈。')
                click(page, '#evaluation-form button')
                expect(page.locator('#detail-content')).to_contain_text('服务评价：5 星')
                page.locator('.timeline').scroll_into_view_if_needed()
                page.screenshot(path=str(WORK / 'completed-ticket.png'))
            elif number == 11:
                make_ticket(page, '书桌上方照明灯开启后持续闪烁，影响晚间使用，请检查灯具。', 'electric', room=4)
                click(page, '#close-detail')
                make_ticket(page, '阳台门锁扣无法扣紧，推拉时会松开，请检查门锁。', 'door', room=2)
                click(page, '#close-detail')
                click(page, '#nav [data-page=dashboard]')
                expect(page.locator('.metrics article').first).to_contain_text('3')
            elif number == 12:
                expect(page.locator('.metrics article').first).to_contain_text('3')
                page.screenshot(path=str(WORK / 'dashboard.png'), full_page=True)
                if not dry: page.wait_for_timeout(3000)
                page.locator('.chart-grid').scroll_into_view_if_needed()
                if not dry: page.wait_for_timeout(2500)
                cue(13)
                click(page, '#nav [data-page=tickets]')
                cue(18)
                page.locator('#filters [name=category]').select_option('electric')
                click(page, '#filters button.ghost')
                expect(page.locator('tbody tr')).to_have_count(1)
                page.screenshot(path=str(WORK / 'filtered-tickets.png'))
                if not dry: page.wait_for_timeout(2000)
                click(page, '[data-action=reset]')
            elif number == 13:
                click(page, '#nav [data-page=tickets]')
                with page.expect_download() as dl:
                    click(page, '[data-action=export]')
                dl.value.save_as(str(WORK / 'repair-tickets.csv'))
                click(page, '#nav [data-page=audit]')
                expect(page.locator('#content')).to_contain_text('导出工单')
                page.screenshot(path=str(WORK / 'audit.png'), full_page=True)
                if not dry:
                    page.wait_for_timeout(4000); page.mouse.wheel(0, 350)
            elif number == 14:
                click(page, '#nav [data-page=users]')
                expect(page.locator('#location-form')).to_be_visible()
                if not dry: page.wait_for_timeout(6000)
                cue(17)
                click(page, '#nav [data-page=settings]')
            elif number == 15:
                page.set_viewport_size({'width': 390, 'height': 810})
                expect(page.locator('.metrics')).to_be_visible()
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                page.screenshot(path=str(WORK / 'mobile.png'), full_page=True)
                if not dry:
                    page.wait_for_timeout(5000);page.mouse.wheel(0, 450);page.wait_for_timeout(4000)
                    page.mouse.wheel(0, -450);page.wait_for_timeout(3000)
                # Center the true mobile viewport on the video canvas at edit time.
            if not dry:
                desired = max(20, duration(WORK / f'{number:02}-voice.mp3') + 2)
                elapsed = time.monotonic() - started
                page.wait_for_timeout(max(1000, (desired - elapsed) * 1000))
            video = page.video
            page.close()
            clip = WORK / f'{number:02}-screen.webm'
            if video:
                video.save_as(str(clip))
                manifest.append(dict(number=number, title=title, narration=narration, source='real-browser', clip=clip.name, duration=duration(clip)))
        # Verify the end state through the actual server, independent of screenshots.
        data = contexts['admin'].request.get(BASE + '/api/tickets').json()
        assert data['total'] == 3, data
        assert sum(t['status'] == 'completed' for t in data['items']) == 1
        stats = contexts['admin'].request.get(BASE + '/api/statistics').json()
        assert (stats['total'], stats['completed'], stats['open']) == (3, 1, 2), stats
        result = dict(passed=not errors, page_errors=errors, ticket_id=ticket, statistics=stats, scenes=manifest)
        (WORK / ('dry-run.json' if dry else 'manifest.json')).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        assert not errors, errors
        for ctx in contexts.values(): ctx.close()
        browser.close()
        return manifest


def stamp(seconds):
    h = int(seconds // 3600); m = int(seconds // 60 % 60); s = seconds % 60
    return f'{h}:{m:02}:{s:05.2f}'


def assemble(manifest, reuse=False):
    import shutil
    EXPORT.mkdir(parents=True, exist_ok=True)
    ass = ['[Script Info]', 'ScriptType: v4.00+', 'PlayResX: 1600', 'PlayResY: 900', '[V4+ Styles]',
        'Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding',
        'Style: Caption,Microsoft YaHei,23,&H00FFFFFF,&H00FFFFFF,&H0016344B,&H0016344B,0,0,0,0,100,100,0,0,1,0,0,5,20,20,0,1',
        'Style: Chapter,Microsoft YaHei,16,&H00D4E2EE,&H00D4E2EE,&H0016344B,&H0016344B,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1',
        '[Events]', 'Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text']
    offset = 0
    srt = []
    for item in manifest:
        i = item['number']; length = item['duration']
        boundaries = json.loads((WORK / f'{i:02}-words.json').read_text(encoding='utf-8'))
        ass.append(f'Dialogue: 0,{stamp(offset)},{stamp(offset+length)},Chapter,,0,0,0,,{{\\pos(30,839)}}{item["title"]}')
        for boundary in boundaries:
            text = boundary['text']; count=max(1,(len(text)+37)//38); size=(len(text)+count-1)//count; pieces=[text[j:j+size] for j in range(0,len(text),size)]
            begin = offset + .7 + boundary['offset'] / 1e7
            span = boundary['duration'] / 1e7
            for j, piece in enumerate(pieces):
                a = begin + span*j/len(pieces); b = min(offset+length, begin+span*(j+1)/len(pieces))
                if b <= a: continue
                ass.append(f'Dialogue: 1,{stamp(a)},{stamp(b)},Caption,,0,0,0,,{{\\pos(940,854)}}{piece}')
                srt.append((a,b,piece))
        # Real mobile capture is 390px wide inside a 1600px recording. Center it.
        vf = 'crop=390:810:0:0,pad=1600:900:605:0:color=0x16344b' if i == 15 else 'pad=1600:900:0:0:color=0x16344b'
        out = WORK / f'{i:02}-chapter.mp4'
        cmd = [ffmpeg(), '-y', '-i', str(WORK/item['clip']), '-i', str(WORK/f'{i:02}-voice.mp3'), '-vf', vf,
            '-af', 'adelay=700|700,apad,loudnorm=I=-16:TP=-1.5:LRA=9', '-t', str(length), '-r', '30', '-c:v', 'libx264', '-preset', 'fast', '-crf', '20', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-ar', '48000', '-b:a', '160k', '-movflags', '+faststart', str(out)]
        if not reuse or not out.exists():
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=(WORK/f'{i:02}-encode.log').open('w'))
        shutil.copy2(WORK/item['clip'], EXPORT/f'{i:02}-screen.webm')
        shutil.copy2(WORK/f'{i:02}-voice.mp3', EXPORT/f'{i:02}-voice.mp3')
        offset += length
        print('ENCODED',i,round(length,2),flush=True)
    (WORK/'captions.ass').write_text('\n'.join(ass),encoding='utf-8-sig')
    (WORK/'concat.txt').write_text('\n'.join(f"file '{i:02}-chapter.mp4'" for i in range(1,len(manifest)+1)),encoding='utf-8')
    target = ROOT/'deliverables'/'宿修-中文解说演示.mp4'
    subprocess.run([ffmpeg(),'-y','-f','concat','-safe','0','-i','concat.txt','-vf','ass=captions.ass','-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-ar','48000','-b:a','128k','-movflags','+faststart',str(target)],cwd=WORK,check=True,stdout=subprocess.DEVNULL,stderr=(WORK/'final-encode.log').open('w'))
    def srt_time(value):
        milliseconds = round(value*1000)
        h, milliseconds = divmod(milliseconds,3600000)
        m, milliseconds = divmod(milliseconds,60000)
        sec, ms = divmod(milliseconds,1000)
        return f"{h:02}:{m:02}:{sec:02},{ms:03}"
    (EXPORT/'captions.srt').write_text("\n\n".join(f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{text}" for i,(a,b,text) in enumerate(srt,1))+"\n",encoding='utf-8-sig')
    (EXPORT/'MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    shutil.copy2(WORK/'captions.ass',EXPORT/'captions.ass')
    (EXPORT/'README.md').write_text('素材按编号排序。screen.webm 是实际网页录屏，voice.mp3 是对应中文合成解说。MANIFEST.json 记录分镜、解说和实际时长。字幕在 captions.ass；无背景音乐。\n',encoding='utf-8')
    assert 300 <= duration(target) <= 480
    print('FINAL',target,'SECONDS',round(duration(target),2),flush=True)


def main():
    os.chdir(ROOT); load_env(); WORK.mkdir(parents=True,exist_ok=True)
    parser=argparse.ArgumentParser();parser.add_argument('--dry-run',action='store_true');parser.add_argument('--assemble',action='store_true');parser.add_argument('--voices',action='store_true');args=parser.parse_args()
    if args.voices:
        asyncio.run(narrate()); return
    if args.assemble:
        assemble(json.loads((WORK/'manifest.json').read_text(encoding='utf-8'))['scenes'],reuse=True); return
    if not args.dry_run: asyncio.run(narrate())
    manifest=capture(args.dry_run)
    if not args.dry_run: assemble(manifest)


if __name__=='__main__':main()
