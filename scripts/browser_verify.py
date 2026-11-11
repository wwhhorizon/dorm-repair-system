"""浏览器全流程验收；解说录制使用 scripts/record_demo.py。"""
import os,sys,json,time
from pathlib import Path
from datetime import datetime,timedelta
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.dev import load_env
from playwright.sync_api import sync_playwright,expect

def main():
    load_env();Path('artifacts').mkdir(exist_ok=True);Path('deliverables').mkdir(exist_ok=True)
    started=time.monotonic();errors=[];stages=[]
    with sync_playwright() as p:
        browser=p.chromium.launch()
        kwargs=dict(viewport={'width':1440,'height':1000})
        ctx=browser.new_context(**kwargs);page=ctx.new_page()
        page.on('pageerror',lambda error:errors.append(str(error)))
        def stage(text):
            stages.append(text);print(text,flush=True)
        def login(name):
            page.request.post('http://127.0.0.1:8000/api/auth/logout',headers={'X-Requested-With':'RepairApp'})
            page.goto('http://127.0.0.1:8000')
            expect(page.locator('#auth')).to_be_visible()
            page.locator('[name=username]').fill(name)
            page.locator('[name=password]').fill(os.environ['DEMO_PASSWORD'])
            page.locator('#auth-submit').click();expect(page.locator('#shell')).to_be_visible(timeout=20000)
        page.goto('http://127.0.0.1:8000')
        stage('01 / 宿修：学生报修、管理员派单、维修人员处理，学生验收。三种角色协作。')
        login(os.getenv('DEMO_STUDENT','student'));stage('02 / 学生工作台：查看自己的报修数量、处理进度和历史记录。')
        page.locator('#nav [data-page=new]').click()
        page.locator('#building-select').select_option(index=1)
        page.locator('#room-select').select_option(index=1)
        page.locator('#ticket-form [name=category]').select_option('other')
        description='洗手池水龙头一直漏水，地面有积水，请安排维修。'
        page.locator('#ticket-form [name=description]').fill(description)
        stage('03 / 提交问题：选择宿舍位置，填写故障现象；系统稍后给出分类建议。')
        page.locator('#ticket-form button.primary').click()
        expect(page.locator('#detail')).to_be_visible(timeout=20000)
        expect(page.locator('#detail .badge')).to_have_text('待受理')
        ticket_id=int(page.locator('.detail-summary .eyebrow').inner_text().split('#')[1])
        stage('04 / 工单已创建。每次状态变化都保留操作者、时间和处理说明。')
        page.locator('#close-detail').click();login(os.getenv('DEMO_ADMIN','admin'))
        page.locator('#nav [data-page=tickets]').click()
        page.locator(f'[data-ticket="{ticket_id}"]').click()
        # 等待独立worker真正入库，而不是在页面伪造预测。
        for _ in range(30):
            d=page.request.get(f'http://127.0.0.1:8000/api/tickets/{ticket_id}').json()
            if d.get('prediction'):break
            page.wait_for_timeout(1000)
        assert d.get('prediction'),'AI worker did not ingest a prediction'
        page.locator('#close-detail').click();page.locator(f'[data-ticket="{ticket_id}"]').click()
        stage('05 / 本地AI分类：独立服务处理故障文字，显示建议类别与模型分数，管理员负责确认。')
        page.locator('#classify-form select').select_option('water');page.locator('#classify-form button').click()
        expect(page.locator('.timeline')).to_contain_text('分类确认')
        page.locator('#assign-form [name=assignee_id]').select_option(label=os.getenv('DEMO_REPAIR','repair'))
        page.locator('#assign-form [name=scheduled_at]').fill((datetime.now()+timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'))
        page.locator('#assign-form [name=note]').fill('已确认水路故障，请检查接头密封。')
        stage('06 / 管理员确认类别、安排维修人员和预约时间。派单通过后端权限和版本校验。')
        page.locator('#assign-form button.primary').click();expect(page.locator('#detail .badge')).to_have_text('已派单')
        page.locator('#close-detail').click();login(os.getenv('DEMO_REPAIR','repair'));page.locator('#nav [data-page=tickets]').click();page.locator(f'[data-ticket="{ticket_id}"]').click()
        stage('07 / 维修人员只能看到分配给自己的工单，核对位置、描述和预约时间后开始维修。')
        page.locator('#action-form button[value=start]').click();expect(page.locator('#detail .badge')).to_have_text('处理中')
        page.locator('#action-form textarea').fill('更换水龙头密封圈并紧固接口，通水测试正常。')
        page.locator('#action-form button[value=finish]').click();expect(page.locator('#detail .badge')).to_have_text('待验收')
        stage('08 / 维修提交完工说明，工单进入待验收。学生可以确认，也可以填写原因申请返修。')
        page.locator('#close-detail').click();login(os.getenv('DEMO_STUDENT','student'));page.locator('#nav [data-page=tickets]').click();page.locator(f'[data-ticket="{ticket_id}"]').click()
        page.locator('#action-form button[value=accept]').click();expect(page.locator('#detail .badge')).to_have_text('已完成')
        page.locator('#evaluation-form [name=comment]').fill('维修及时，漏水问题已解决。');page.locator('#evaluation-form button').click()
        expect(page.locator('#detail-content')).to_contain_text('服务评价：5 星')
        stage('09 / 学生完成验收并评价。处理历史完整保留，结束工单不再允许任意修改。')
        page.locator('#close-detail').click();login(os.getenv('DEMO_STUDENT2','student2'))
        unauthorized=page.request.get(f'http://127.0.0.1:8000/api/tickets/{ticket_id}')
        assert unauthorized.status==404
        stage('10 / 数据隔离验证：另一名学生访问刚才的工单，后端返回404；各人只能查看自己的数据。')
        login(os.getenv('DEMO_ADMIN','admin'));expect(page.locator('.metrics')).to_be_visible()
        page.screenshot(path='artifacts/dashboard-desktop.png',full_page=True)
        stage('11 / 实时统计：总量、待解决、类别分布、趋势、完工时长和评分。可以组合筛选楼栋与日期。')
        page.locator('#nav [data-page=tickets]').click()
        with page.expect_download() as dl:page.locator('[data-action=export]').click()
        path=dl.value.path();assert path and Path(path).stat().st_size>0
        page.locator('#nav [data-page=users]').click();expect(page.locator('#location-form')).to_be_visible()
        stage('12 / 管理员可以导出CSV，维护账号和宿舍位置。导出操作和权限变更均保留审计记录。')
        page.locator('#nav [data-page=audit]').click();expect(page.locator('#content')).to_contain_text('导出工单')
        page.screenshot(path='artifacts/audit-desktop.png',full_page=True)
        stage('13 / 审计与交付：浏览器界面、本地AI、权限控制、测试和部署资料共同构成完整项目。')
        page.set_viewport_size({'width':390,'height':844});page.locator('#nav [data-page=dashboard]').click()
        expect(page.locator('.metrics')).to_be_visible();page.screenshot(path='artifacts/dashboard-mobile.png',full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth+1'),'mobile horizontal overflow'
        ctx.close()
        browser.close()
    result={'passed':not errors,'stages':stages,'page_errors':errors,'ticket_id':ticket_id,'seconds':round(time.monotonic()-started,1),'video':None}
    Path('artifacts/browser-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    assert not errors,errors
    print(json.dumps(result,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
