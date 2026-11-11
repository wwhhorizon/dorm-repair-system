# 宿修 · 校园宿舍报修与智能工单管理系统

软件工程实践单人项目。学生提交报修，管理员确认分类并派单，维修人员处理，学生验收与评价。独立 AI 服务提供本地故障文本分类。浏览器界面支持电脑和手机。

## 本地启动

要求 Python 3.12。PowerShell 在项目目录运行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe scripts/dev.py --seed
```

打开 <http://127.0.0.1:8000>。首次启动生成不入库的 `.env`，终端输出新建演示账号的随机密码。也可以在本地 `.env` 查看 `DEMO_PASSWORD`。账号为 `student`、`student2`、`admin`、`repair`。已有账号密码不会被初始化命令覆盖。`Ctrl+C` 关闭后端、AI API 和 worker。

本地默认 SQLite；正式部署提供 MySQL 8.4。管理员及维修人员注册需要 `.env` 内相应邀请码，学生可直接注册。

## 功能

- 身份认证、角色控制、账号停用、修改密码、登录限速、操作审计。
- 报修、现场及维修图片、历史查询、时间安排、派单和重派、状态跟踪、返修、验收、评价。
- 带版本号的乐观并发校验，过期操作返回409。
- WebSocket 实时看板，按楼栋、类别、日期筛选，多维统计及安全 CSV 导出。
- 本地五分类模型、独立服务令牌、置信度过滤、断线重试、人工确认与修正。
- 图片授权读取、实际格式检查、大小限制、重新编码去除元数据；AI 不接收图片或视频。

## 验证

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ai_service.classifier
.\.venv\Scripts\python.exe scripts/export_contract.py
```

训练数据是300条模拟描述，按故障组划分，改写不跨训练和测试集合。实际指标见 [AI评估记录](docs/ai-metrics.json)，不可当作真实校园数据的准确率。完整安装版本见 `requirements.lock`。

## 项目文档

| 文档 | 内容 |
|---|---|
| [需求规格](docs/requirements.md) | 范围、角色、用例与验收标准 |
| [指导书对照](docs/traceability.md) | 原指导书要求与报修业务的逐项对应 |
| [设计说明](docs/design.md) | 架构、MVC/MVVM、ER、状态与顺序图 |
| [接口说明](docs/api.md) | 认证方式、错误码、接口与时间约定 |
| [OpenAPI](docs/openapi.json) | 可机读接口契约，在线 `/docs` |
| [部署说明](docs/deployment.md) | 本地、MySQL Compose、备份、HTTPS |
| [用户手册](docs/user-manual.md) | 学生、管理员、维修人员操作 |
| [测试用例与记录](docs/testing.md) | 自动化、安全、UI、性能验证 |
| [个人分工及贡献说明](docs/contribution.md) | 单人职责、Git 与 AI 辅助说明 |
| [演示脚本](docs/demo.md) | 5～8分钟演示的步骤与解说 |

**实验报告按用户要求暂不编写。** 需求访谈、真实使用反馈、签到和现场答辩需要本人实际完成，项目文档不虚构这些记录。

## 项目结构

```text
app/          主后端、业务服务、数据模型、浏览器客户端
ai_service/   分类数据、模型训练、推理 API、独立入库 worker
tests/        单元与接口/集成安全测试
scripts/      本地启动、契约导出、在线验收与浏览器验证
database/     MySQL 建表脚本
docs/         需求、设计、测试与部署资料
.github/      自动测试和 MySQL Compose 验收流水线
```
