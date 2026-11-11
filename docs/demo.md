# 中文解说演示

成片：`deliverables/宿修-中文解说演示.mp4`，1600 × 900，中文配音与字幕。

## 内容

从空工单环境开始，实际录制十五章：登录与学生工作台、提交报修、分类建议、管理员派单、维修接单、提交结果、学生返修、复查完工、验收评价、继续报修、筛选统计、导出日志、账号管理、手机端。

演示包含三张工单：一张漏水报修走完维修及返修流程，另两张分别为照明与门锁问题。所有工单、事件、分类结果、评价和统计通过运行中的服务产生。录制环境与日常数据库分开。

## 复现

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-video.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe scripts/demo_session.py
# 第二个终端：正式录制
.\.venv\Scripts\python.exe scripts/record_demo.py
```

`demo_session.py` 每次新建独立数据库，初始化学生、管理员和维修值班账号。登录凭据从本地 `.env` 读取。

`record_demo.py --dry-run` 快速检查所有操作；正式录制前重新启动一个空环境。`--voices` 可先生成解说；`--assemble` 可使用已录制素材重新导出。

## 制作

浏览器操作由 Playwright 驱动，每章单独录制。解说使用微软中文合成语音，逐句时间信息用于字幕。根据实际音频时长安排镜头和操作停顿，字幕单独放在画面底部。FFmpeg 输出 H.264 视频及 AAC 音频，文件可以直接用浏览器和播放器打开。

剪辑素材保存在 `deliverables/demo-source/`，按编号排列：原始录屏、配音、字幕和 MANIFEST.json。完整解说词位于 `scripts/demo_story.py`。视频无背景音乐。

## 成片章节

- 00:00 宿修 · 高新校区
- 00:25 学生工作台
- 00:51 提交第一张报修
- 01:17 工单与分类建议
- 01:46 管理员安排维修
- 02:12 维修人员接单
- 02:37 提交维修结果
- 03:05 学生申请返修
- 03:33 返修后再次完工
- 03:59 验收并评价
- 04:28 继续提交不同故障
- 04:55 筛选与统计
- 05:23 导出与处理记录
- 05:51 账号与宿舍维护
- 06:17 手机端与流程回顾
