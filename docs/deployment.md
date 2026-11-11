# 部署说明

## 本地运行

使用Python 3.12，执行README的安装和`python scripts/dev.py --seed`。默认主服务127.0.0.1:8000、AI服务127.0.0.1:8001、worker独立进程。浏览器访问主服务。首次启动生成随机服务令牌、邀请码和演示密码，均存本地`.env`且被Git忽略。已有环境变量优先于`.env`。

`.env`不应从未知来源复制。`scripts/dev.py`是本地启动器，默认只绑定回环地址；正式部署按下节使用容器或自行配置进程管理。

## MySQL容器部署

安装Docker Engine及Compose插件，复制`.env.example`为`.env`并替换全部CHANGE_ME。数据库密码采用字母数字的随机字符串，避免连接URL中的保留字符。演示密码需含字母数字且不少于10位。

```sh
docker compose config
docker compose up -d --build --wait
docker compose exec backend python -m app.seed
```

主界面为localhost:8000，MySQL、AI和worker不公开端口。演示初始化为显式命令，不在每次容器启动时自动创建默认账号。移除演示账号或改密后再用于实际场景。

验收：将`.env`的DEMO_PASSWORD设为本地环境变量后运行`python scripts/live_smoke.py`。该脚本会创建一张真实测试工单并完成全流程，适合专用验收数据库。GitHub Actions自动使用全新MySQL服务运行此步骤，失败时保留容器日志。

## 配置

| 配置 | 作用 |
|---|---|
| DATABASE_URL | 正式mysql+pymysql连接；本地默认sqlite:///data/repair.db |
| AI_SERVICE_TOKEN | 主后端、AI API和worker一致的独立随机令牌 |
| ADMIN_INVITE_CODE | 管理员注册邀请码 |
| TECHNICIAN_INVITE_CODE | 维修人员注册邀请码 |
| DEMO_PASSWORD | 仅新建演示账号使用 |
| AI_CONFIDENCE_THRESHOLD | 后端入库阈值，默认0.35 |
| AI_POLL_SECONDS | worker轮询周期，默认5秒，最小1秒 |
| BACKEND_URL / AI_URL | worker调用地址 |
| COOKIE_SECURE | HTTPS上线时设1，本地HTTP为0 |

## HTTPS与反向代理

实际域名部署在Nginx或等效网关终止TLS；证书由部署者为自己的域名配置。将HTTPS请求转发到backend:8000，保留Host，设置X-Forwarded-Proto，并为`/ws/dashboard`启用Upgrade及Connection头。只有受信任网关可以设置转发头；uvicorn的forwarded-allow-ips应限定为网关地址。设置COOKIE_SECURE=1。前端与API保持同源，避免关闭Origin校验。

本仓库没有实际域名及证书，也不声称已经公网HTTPS上线。课程本机演示无需注册域名。

## 数据与备份

SQLite位于data/repair.db，附件在data/uploads；复制数据库备份时先停止写服务，连同附件一起备份。MySQL使用命名卷mysql_data，附件使用uploads卷。可在db容器运行`mysqldump --single-transaction`，由管理员从安全配置读取凭据；备份必须限制访问。

更新前备份，再执行`docker compose up -d --build`。当前为初版schema，create_all只负责建表，不会自动迁移已有表；结构变更需要显式迁移脚本，禁止假设重启即可升级。回滚代码前核对数据库兼容性。`docker compose down`保留数据；`down -v`会删除卷，仅用于可丢弃的验收环境。

## 故障排查

- 401：登录过期、账号停用、改密后会话被吊销，或AI令牌不一致。
- 403：角色不符、邀请码不符、来源或写请求校验头不符。
- 409：工单被其他操作更新，重新打开详情获取新版本。
- AI无结果：检查AI/worker健康、令牌和阈值，查看worker日志；仍可人工派单。
- 无房间：先执行演示初始化或管理员新增楼栋与房间。
- Cookie在HTTP不发送：本地将COOKIE_SECURE设0。

## 环境验证边界

本地Windows没有Docker命令，SQLite和浏览器通过本机执行验证；MySQL容器由仓库CI验收，其实际运行结果以GitHub Actions为准。最终测试记录应注明CI结果，不能用“配置存在”替代“容器已运行”。
