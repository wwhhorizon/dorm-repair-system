# REST API契约

在线文档：`http://127.0.0.1:8000/docs`；机器可读版本：`docs/openapi.json`。发布接口契约版本1.0.0。修改字段、权限及行为时，同步更新OpenAPI、测试和本文件；不兼容变更升级主版本。

认证使用8小时有效的数据库随机会话。登录返回access_token，并设置repair_session Cookie。浏览器使用Cookie；自动化客户端可使用`Authorization: Bearer <token>`。数据库只存令牌摘要。退出与改密可吊销会话。权限不能只依赖前端菜单。

所有`/api/`写请求要求`X-Requested-With: RepairApp`。存在Origin时必须同源。AI接口另外要求`X-Service-Token`，用户令牌不能替代。不会在接口说明提供实际部署密钥。

| 方法 | 地址 | 权限和作用 |
|---|---|---|
| POST | /api/auth/register | 公开；非学生需对应角色邀请码 |
| POST | /api/auth/login | 用户名密码；返回用户、会话令牌 |
| POST | /api/auth/logout | 当前用户；吊销当前会话 |
| PUT | /api/auth/password | 当前用户；原密码、新密码；吊销全部会话 |
| GET | /api/users/me | 当前用户公开字段 |
| GET | /api/admin/users | 管理员；查看用户 |
| PUT | /api/admin/users/{id} | 管理员；启用/停用非管理员 |
| GET | /api/locations | 已登录；楼栋与房间 |
| POST | /api/admin/locations | 管理员；新增楼栋或指定楼栋的房间 |
| GET | /api/tickets | 按角色范围；支持status/category/building/start/end/page/page_size |
| POST | /api/tickets | 学生；room_id、description、category |
| GET | /api/tickets/{id} | 按角色范围；事件、图片、评价和预测 |
| POST | /api/tickets/{id}/actions | 按角色与状态；必须携带当前version |
| POST | /api/tickets/{id}/attachments | 按角色范围；multipart字段file |
| GET | /api/attachments/{id} | 按所属工单范围；返回重编码后的JPEG |
| POST | /api/tickets/{id}/evaluation | 本人已完成工单；score/comment |
| GET | /api/statistics | 按角色范围；楼栋/类别/日期组合筛选 |
| GET | /api/admin/export | 管理员；与列表相同筛选；UTF-8 BOM CSV |
| GET | /api/admin/audit | 管理员；最近100条审计 |
| GET | /api/ai/pending | AI独立服务令牌；最多100条未预测活跃工单 |
| POST | /api/ai/results | AI独立服务令牌；验证分数/时间/类型并去重 |
| WS | /ws/dashboard | 同源会话；每3秒发送当前账号可见汇总 |
| GET | /health | 健康检查，包含数据库连通性 |

派单请求示例：

```json
{"action":"assign","version":1,"assignee_id":4,"scheduled_at":"2026-12-01T02:00:00Z","note":"请检查水管接头"}
```

动作枚举：cancel、assign、start、finish、accept、reject、comment、classify。非法角色/状态组合409，资源不可见404，越权管理接口403。

预测请求示例（时间应为当前UTC时间）：

```json
{"ticket_id":1,"category":"water","confidence":0.83,"model_version":"char-tfidf-logreg-v1","timestamp":"2026-11-11T02:00:00Z"}
```

预测时间与服务端不能相差超过5分钟；重复工单返回已有预测且duplicate=true；低于配置阈值时返回accepted=false，不入库。模型分数不代表真实正确概率。

所有错误统一返回`{"code":"HTTP_409","message":"工单已更新，请刷新后重试"}`或`VALIDATION_ERROR`。成功响应按资源结构返回，创建资源201，其余200。400用于原密码错误，401未认证，403权限/来源拒绝，404不可见资源，409冲突，413附件过大，422参数不合法，429登录限速。

起止时间建议ISO8601 UTC；页面按本地日期转换。类别枚举water/electric/door/furniture/other。状态枚举pending/assigned/working/review/completed/cancelled。
