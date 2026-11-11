# 指导书要求对照与验收矩阵

根据自选的宿舍报修场景，对指导书的业务功能与工程要求作如下对应。

| 原要求 | 本项目落实方式 | 实现 / 验证 |
|---|---|---|
| 学生注册、登录、改密 | 同功能；维修及管理员注册需邀请码 | main.py auth路由；权限测试 |
| 学生发送emoji、查看个人历史 | 提交报修、查看个人工单和处理历史 | 创建/列表/详情接口；端到端演示 |
| 教师查看所授课堂数据 | 维修人员仅查看分配给自己的任务及统计 | scoped_tickets；横向权限测试 |
| 管理员查看用户和记录 | 用户管理、全量工单、审核日志 | 管理端页面及admin接口 |
| 安排特定时间用户列表 | 按工单安排维修人员与未来预约时间，支持重派 | assign动作；过去时间拒绝测试 |
| 实时看板与多维统计 | WebSocket、楼栋/类别/日期筛选、状态/趋势/评价图表 | dashboard、statistics |
| CSV导出及公式注入防护 | 权限校验、BOM CSV、危险起始字符转义 | export、safe_cell测试 |
| 客户端可用浏览器 | 学生及维修浏览器界面，手机适配 | static；浏览器与移动尺寸验证 |
| 修改版MVC | 前端Model/View/Controller，后端分层 | design.md及对应模块 |
| REST/JSON与关系数据库 | FastAPI，MySQL部署；SQLite仅本地便捷模式 | OpenAPI、MySQL SQL、Compose CI |
| User/Course/ClassSession/ScheduleUser/EmojiRecord | User/Building/Room/Ticket预约字段/Event/Prediction | ER图与数据库脚本 |
| 密码哈希、后端RBAC | bcrypt与数据库会话，数据范围过滤 | password与越权测试 |
| 独立Python AI推理 | TF-IDF＋逻辑回归，独立分类API和worker | ai_service/ |
| 视频采样/人脸检测/情绪分类 | 经选题替换为周期领取工单/文本特征提取/故障分类 | 工单文本分类流程及对应接口 |
| 至少5类、分数过滤、AI来源与时间 | 五类故障、阈值、工单ID、模型版本、AI时间记录 | Prediction；AI接口测试 |
| 采样频率及阈值配置 | AI_POLL_SECONDS、AI_CONFIDENCE_THRESHOLD | worker与后端配置 |
| 独立服务令牌 | X-Service-Token；普通会话不能代替 | service_auth；独立认证测试 |
| 不保留原始人脸图像/视频 | AI只处理描述；没有摄像头采集；业务附件单独授权管理 | 上传路径、AI pending响应 |
| 断线重试及错误日志 | 指数退避，日志仅故障类型与工单ID | worker.py；故障注入测试 |
| 单元/接口/端到端/安全/可用性测试 | pytest、在线smoke、Playwright流程及移动布局 | tests/与scripts/，testing.md |
| Git分支管理 | feature分支开发，main集成 | 仓库分支及提交记录 |
| Docker Compose与CI（选做） | MySQL/后端/AI/worker四服务与GitHub Actions | compose.yaml、ci.yml |
| 需求、设计、ER、接口、部署、手册 | 独立Markdown文档及OpenAPI/SQL | docs/、database/ |
| 测试报告与用例 | 测试用例、自动执行结果、浏览器证据 | testing.md、验证产物 |
| 5～8分钟演示 | 实际浏览器操作录屏及可复现脚本 | demo.md与deliverables/ |
| 实验报告及AI局限分析 | 报告包含需求、设计、实现、测试及AI分类结果分析 | PDF与LaTeX源码独立提交 |
| 团队分工及贡献度 | 报告封面列出小组成员 | 实验报告封面 |
| 签到、现场演示、答辩 | 课程现场安排 | 现场展示系统及回答问题 |

消息队列及MCP属于原指导书选做项，本版使用REST，不纳入必做验收。
