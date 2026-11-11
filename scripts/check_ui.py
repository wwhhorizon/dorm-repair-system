"""安装 npm install --prefix artifacts/ui-tools axe-core 后执行。"""
import os,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.dev import load_env
from playwright.sync_api import sync_playwright

def main():
    load_env();reports={};path=Path('artifacts/ui-tools/node_modules/axe-core/axe.min.js')
    if not path.exists():raise SystemExit('Run: npm install --prefix artifacts/ui-tools axe-core')
    check="""async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}});return r.violations.map(x=>({id:x.id,impact:x.impact,nodes:x.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}))}"""
    with sync_playwright() as p:
        b=p.chromium.launch();ctx=b.new_context(viewport={'width':1440,'height':1000},bypass_csp=True);page=ctx.new_page()
        def audit(name):
            page.add_script_tag(path=str(path));reports[name]=page.evaluate(check)
        page.goto('http://127.0.0.1:8000');audit('login')
        page.screenshot(path='artifacts/login-desktop.png',full_page=True)
        page.locator('[name=username]').fill(os.getenv('DEMO_ADMIN','admin'));page.locator('[name=password]').fill(os.environ['DEMO_PASSWORD']);page.locator('#auth-submit').click();page.locator('.metrics').wait_for();audit('dashboard')
        page.screenshot(path='artifacts/dashboard-desktop.png',full_page=True)
        page.locator('#nav [data-page=tickets]').click();page.locator('table').wait_for();audit('tickets')
        page.locator('[data-ticket]').first.click();page.locator('#detail').wait_for();audit('detail')
        page.locator('#close-detail').click();page.locator('#nav [data-page=dashboard]').click();page.locator('.metrics').wait_for()
        page.set_viewport_size({'width':390,'height':844});audit('mobile-dashboard');page.screenshot(path='artifacts/dashboard-mobile.png',full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
        b.close()
    Path('artifacts/accessibility.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(reports,ensure_ascii=False),flush=True)
    assert not any(reports.values()),'Accessibility violations need repair'

if __name__=='__main__':main()
