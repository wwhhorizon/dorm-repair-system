import { categories, states, roles, state } from "./model.js";
export const esc = (x) =>
  String(x ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
export const date = (x) =>
  x
    ? new Date(x.endsWith("Z") ? x : x + "Z").toLocaleString("zh-CN", {
        hour12: false,
      })
    : "—";
export const options = (obj, selected = "") =>
  Object.entries(obj)
    .map(
      ([k, v]) =>
        `<option value="${esc(k)}" ${String(k) === String(selected) ? "selected" : ""}>${esc(v)}</option>`,
    )
    .join("");
export const badge = (status) =>
  `<span class="badge ${esc(status)}">${states[status] || esc(status)}</span>`;
const dateInput = (value) =>
  value
    ? new Intl.DateTimeFormat("en-CA", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
      }).format(new Date(value))
    : "";
export function filters(includeStatus = false) {
  return `<form id="filters" class="filters"><label>楼栋<select name="building"><option value="">全部楼栋</option>${options(Object.fromEntries(state.locations.map((b) => [b.id, b.name])), state.filters.building)}</select></label><label>类别<select name="category"><option value="">全部类别</option>${options(categories, state.filters.category)}</select></label>${includeStatus ? `<label>状态<select name="status"><option value="">全部状态</option>${options(states, state.filters.status)}</select></label>` : ""}<label>开始日期<input type="date" name="start" value="${esc(dateInput(state.filters.start))}"></label><label>结束日期<input type="date" name="end" value="${esc(dateInput(state.filters.end))}"></label><button class="ghost">筛选</button><button type="button" data-action="reset" class="text">重置</button></form>`;
}
export function bars(values, labels) {
  const max = Math.max(1, ...Object.values(values));
  return Object.entries(labels)
    .map(
      ([key, label]) =>
        `<div class="bar-row"><span>${esc(label)}</span><div class="bar-track"><div class="bar-fill" style="width:${((values[key] || 0) / max) * 100}%"></div></div><strong>${values[key] || 0}</strong></div>`,
    )
    .join("");
}
export function icon(name) {
  const paths = {
    dashboard: "M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z",
    tickets: "M7 3h10l4 4v14H3V3h4 M7 9h10 M7 13h10 M7 17h6",
    new: "M12 5v14 M5 12h14",
    users:
      "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2 M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8 M22 21v-2a4 4 0 0 0-3-3.87 M16 3.13a4 4 0 0 1 0 7.75",
    settings: "M4 7h16 M4 17h16 M8 4v6 M16 14v6",
    audit: "M6 3h12v18H6z M9 8h6 M9 12h6 M9 16h4",
    clock: "M12 8v4l3 2 M22 12a10 10 0 1 0-20 0 10 10 0 0 0 20 0",
    check: "M5 12l4 4L19 6",
    arrow: "M5 12h14 M13 6l6 6-6 6",
  };
  return `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${(
    paths[name] || paths.tickets
  )
    .split(" M")
    .map((d, i) => `<path d="${i ? "M" : ""}${d}"/>`)
    .join("")}</svg>`;
}
export function dashboard(s, records = []) {
  const role = state.user.role;
  const wanted =
    role === "admin"
      ? ["pending"]
      : role === "technician"
        ? ["assigned", "working"]
        : ["review", "pending", "assigned", "working"];
  const work = records
    .filter((t) => wanted.includes(t.status))
    .sort((a, b) => wanted.indexOf(a.status) - wanted.indexOf(b.status));
  const heading =
    role === "admin"
      ? "待受理报修"
      : role === "technician"
        ? "待处理任务"
        : "我的报修";
  const visible = (
    role === "student"
      ? [...work, ...records.filter((t) => !wanted.includes(t.status))]
      : work
  ).slice(0, 5);
  const empty = role === "student" ? "还没有报修记录" : "当前没有待处理工单";
  const action = role === "student" ? "提交报修" : "查看全部工单";
  const metrics = [
    ["报修总数", s.total, "tickets"],
    ["待处理", s.open, "clock"],
    ["已完成", s.completed, "check"],
    [
      "平均处理时间",
      s.average_hours === null
        ? "—"
        : s.average_hours < 1
          ? s.average_hours < 1 / 60
            ? "不足 1"
            : Math.round(s.average_hours * 60)
          : s.average_hours,
      "clock",
    ],
  ];
  return `<section class="campus-strip"><div><h2>${role === "student" ? "宿舍报修" : role === "technician" ? "维修工作台" : "报修管理"}</h2><p>中科大高新校区</p></div><button class="primary" data-page="${role === "student" ? "new" : "tickets"}">${action}${icon("arrow")}</button><img src="/static/images/ustc-gaoxin-campus.webp" alt="高新校区建筑与水面" width="1920" height="1402"><a class="photo-credit" href="https://zsb.ustc.edu.cn/2024/0326/c35540a633997/page.htm" target="_blank" rel="noopener noreferrer">校园影像</a></section>
  ${filters()}<div class="metrics">${metrics.map(([label, value, ic], i) => `<article><span class="metric-icon ${i === 1 ? "amber" : i === 2 ? "mint" : ""}">${icon(ic)}</span><div><p>${label}</p><strong>${value}${i === 3 && s.average_hours !== null ? `<em>${s.average_hours < 1 ? "分钟" : "小时"}</em>` : ""}</strong></div></article>`).join("")}</div>
  <section class="panel work-queue"><div class="panel-heading"><h2>${heading}</h2><button class="text" data-page="tickets">全部工单 ${icon("arrow")}</button></div>${visible.length ? visible.map((t) => `<button class="queue-row" data-ticket="${t.id}"><span class="queue-number">#${t.id}</span><span class="queue-description"><strong>${esc(t.description)}</strong><small>${esc(t.building)} · ${esc(t.room)}${t.scheduled_at ? " · 预约 " + date(t.scheduled_at) : ""}</small></span>${badge(t.status)}<span class="queue-arrow">${icon("arrow")}</span></button>`).join("") : `<div class="empty"><span class="empty-icon">${icon("tickets")}</span><h3>${empty}</h3><p>${role === "student" ? "设施出现故障时，在这里提交并跟进维修。" : "新的报修和待办会显示在这里。"}</p>${role === "student" ? '<button class="primary" data-page="new">提交报修</button>' : ""}</div>`}</section>
  <div class="chart-grid" ${s.total ? "" : "hidden"}><section class="panel category-panel"><div class="panel-heading"><h2>故障分类</h2><span class="subtle-tag">${s.total} 张</span></div>${s.total ? bars(s.categories, categories) : '<p class="chart-empty">暂无分类记录</p>'}</section><section class="panel progress-panel"><div class="panel-heading"><h2>工单状态</h2><span class="subtle-tag">${s.average_rating === null ? "暂无评价" : "服务评分 " + s.average_rating + " / 5"}</span></div>${s.total ? bars(s.states, states) : '<p class="chart-empty">暂无处理记录</p>'}</section><section class="panel trend-panel"><div class="panel-heading"><h2>报修趋势</h2></div>${Object.keys(s.days).length ? bars(s.days, Object.fromEntries(Object.keys(s.days).map((d) => [d, d.slice(5)]))) : '<p class="chart-empty">提交报修后显示每日数量</p>'}</section><section class="panel rating-panel"><div class="panel-heading"><h2>维修评价</h2></div>${Object.keys(s.ratings).length ? bars(s.ratings, { 5: "5 星", 4: "4 星", 3: "3 星", 2: "2 星", 1: "1 星" }) : '<p class="chart-empty">验收完成后可以评价维修服务</p>'}</section></div>`;
}
export function tickets(data) {
  return `<div class="section-head"><p class="muted">${data.total} 张工单 · 第 ${state.listPage} 页</p>${state.user.role === "admin" ? '<button data-action="export" class="ghost">导出工单</button>' : ""}${state.user.role === "student" ? '<button data-page="new" class="primary">＋ 提交报修</button>' : ""}</div>${filters(true)}<section class="panel table-panel"><table><thead><tr><th>工单 / 问题</th><th>位置</th><th>分类</th><th>状态</th><th>维修人员</th><th>提交时间</th><th></th></tr></thead><tbody>${data.items.map((t) => `<tr><td><strong>#${t.id}</strong> ${esc(t.description.slice(0, 42))}</td><td>${esc(t.building)} · ${esc(t.room)}</td><td>${categories[t.category]}</td><td>${badge(t.status)}</td><td>${esc(t.assignee || "待分配")}</td><td>${date(t.created_at)}</td><td><button class="text" data-ticket="${t.id}">查看详情</button></td></tr>`).join("") || '<tr><td colspan="7" class="empty">没有符合条件的工单</td></tr>'}</tbody></table></section><div class="pagination"><button class="ghost" data-action="previous" ${state.listPage === 1 ? "disabled" : ""}>上一页</button><button class="ghost" data-action="next" ${state.listPage * 30 >= data.total ? "disabled" : ""}>下一页</button></div>`;
}
export function newTicket() {
  return `<form id="ticket-form" class="panel editor"><h2>哪里需要维修？</h2><p class="muted">请描述故障现象。详细的信息可以帮助维修人员提前准备。</p><div class="two-cols"><label>宿舍楼<select name="building" id="building-select" required><option value="">请选择楼栋</option>${options(Object.fromEntries(state.locations.map((b) => [b.id, b.name])))}</select></label><label>房间<select name="room_id" id="room-select" required><option value="">请先选择楼栋</option></select></label></div><label>问题类别<select name="category">${options(categories, "other")}</select></label><label>问题描述<textarea name="description" minlength="5" maxlength="2000" required rows="6" placeholder="例如：洗手池下方水管持续漏水，地面有积水。"></textarea></label><label>现场照片（选填）<input type="file" name="image" accept="image/png,image/jpeg,image/webp"><small>支持 JPG、PNG、WebP，最大 5 MB</small></label><button class="primary">提交报修</button></form>`;
}
export function eventNote(e) {
  let note = e.note || "";
  if (e.action === "classify")
    for (const [key, label] of Object.entries(categories))
      note = note.replaceAll(key, label);
  if (e.action === "assign")
    note = note.replace(
      /时间 (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})/,
      (_, value) => "预约 " + date(value.replace(" ", "T")),
    );
  return esc(note);
}
export function detail(t) {
  const actions = {
    create: "提交报修",
    assign: "安排维修",
    start: "开始维修",
    finish: "维修完成",
    accept: "验收通过",
    reject: "申请返修",
    cancel: "取消报修",
    classify: "确认分类",
    comment: "补充说明",
  };
  let controls = "";
  const role = state.user.role;
  if (role === "student" && t.status === "pending")
    controls +=
      '<button name="action" value="cancel" class="danger">取消报修</button>';
  if (role === "technician" && t.status === "assigned")
    controls +=
      '<button name="action" value="start" class="primary">开始维修</button>';
  if (role === "technician" && t.status === "working")
    controls +=
      '<button name="action" value="finish" class="primary">提交完工</button>';
  if (role === "student" && t.status === "review")
    controls +=
      '<button name="action" value="accept" class="primary">确认验收</button><button name="action" value="reject" class="ghost">申请返修</button>';
  const open = !["completed", "cancelled"].includes(t.status);
  return `<div class="detail-summary"><span class="eyebrow">工单 #${t.id}</span>${badge(t.status)}<h2>${esc(t.description)}</h2><p class="muted">${esc(t.building)} · ${esc(t.room)}　${categories[t.category]}</p></div><div class="two-cols meta"><p>报修人 <strong>${esc(t.student)}</strong></p><p>维修人员 <strong>${esc(t.assignee || "待分配")}</strong></p><p>提交时间 <strong>${date(t.created_at)}</strong></p><p>预约维修 <strong>${date(t.scheduled_at)}</strong></p></div><div class="hint">${t.prediction ? `建议分类 <strong>${categories[t.prediction.category]}</strong><details class="prediction-meta"><summary>查看分类详情</summary><small>匹配分数 ${(t.prediction.confidence * 100).toFixed(1)}% · ${esc(t.prediction.model_version)}</small></details>` : "正在识别故障类别…"}</div><div class="attachments">${t.attachments.map((a) => `<a href="${a.url}" target="_blank"><img width="110" height="90" loading="lazy" src="${a.url}" alt="${a.purpose === "repair" ? "维修结果" : "报修现场"}照片"></a>`).join("")}</div>${open ? '<form id="attachment-form"><label>补充图片<input type="file" name="image" accept="image/png,image/jpeg,image/webp" required></label><button class="ghost">上传图片</button></form>' : ""}${role === "admin" && open ? `<form id="classify-form" class="inline-form"><label>确认故障类别<select name="category">${options(categories, t.category)}</select></label><button class="ghost">保存分类</button></form>` : ""}${role === "admin" && ["pending", "assigned", "working"].includes(t.status) ? `<form id="assign-form" class="subform"><h3>${t.assignee ? "重新派单" : "安排维修"}</h3><div class="two-cols"><label>维修人员<select name="assignee_id" required><option value="">请选择</option>${options(Object.fromEntries(state.users.filter((u) => u.role === "technician" && u.active).map((u) => [u.id, u.username])), t.assignee_id)}</select></label><label>预约时间<input type="datetime-local" name="scheduled_at" required></label></div><label>派单说明${t.assignee ? "（必填）" : ""}<input name="note" ${t.assignee ? "required" : ""} maxlength="2000"></label><button class="primary">确认派单</button></form>` : ""}${open ? `<form id="action-form" class="subform"><label>处理说明<textarea name="note" rows="3" maxlength="2000" placeholder="填写处理结果或需要补充的情况"></textarea></label><div class="button-row">${controls}<button name="action" value="comment" class="ghost">补充说明</button></div></form>` : ""}${role === "student" && t.status === "completed" && !t.evaluation ? '<form id="evaluation-form" class="subform"><h3>这次维修怎么样？</h3><label>评分<select name="score"><option value="5">5 星 · 很满意</option><option value="4">4 星 · 满意</option><option value="3">3 星 · 一般</option><option value="2">2 星 · 不满意</option><option value="1">1 星 · 很不满意</option></select></label><label>评价<input name="comment" maxlength="1000"></label><button class="primary">提交评价</button></form>' : ""}${t.evaluation ? `<p class="hint">服务评价：${t.evaluation.score} 星 · ${esc(t.evaluation.comment)}</p>` : ""}<h3>处理记录</h3><ol class="timeline">${t.events.map((e) => `<li><span>${date(e.created_at)} · ${esc(e.actor)}</span><p><strong>${actions[e.action] || esc(e.action)}</strong>${e.note ? `<br>${eventNote(e)}` : ""}</p><small>${states[e.from_state]} → ${states[e.to_state]}</small></li>`).join("")}</ol>`;
}
export function users(data) {
  return `<section class="panel"><h2>账号管理</h2><p class="muted">管理账号状态与访问身份。</p><div class="table-panel"><table><thead><tr><th>用户名</th><th>角色</th><th>邮箱</th><th>状态</th><th>操作</th></tr></thead><tbody>${data.map((u) => `<tr><td>${esc(u.username)}</td><td>${roles[u.role]}</td><td>${esc(u.email || "—")}</td><td>${u.active ? "启用" : "停用"}</td><td>${u.role !== "admin" ? `<button class="text" data-user="${u.id}" data-active="${u.active ? "0" : "1"}">${u.active ? "停用" : "启用"}</button>` : "—"}</td></tr>`).join("")}</tbody></table></div></section><section class="panel"><h2>宿舍位置</h2><p>${state.locations.map((b) => `${esc(b.name)}：${b.rooms.map((r) => esc(r.name)).join("、")}`).join("<br>") || "请先添加楼栋和房间"}</p><form id="location-form" class="inline-form"><label>位置类型<select name="building_id"><option value="">新建楼栋</option>${options(Object.fromEntries(state.locations.map((b) => [b.id, "添加房间至 " + b.name])))}</select></label><label>名称<input name="name" required maxlength="30"></label><button class="ghost">添加</button></form></section>`;
}
export function settings() {
  return `<form id="password-form" class="panel editor"><h2>修改密码</h2><p class="muted">保存后请使用新密码重新登录。</p><label>原密码<input type="password" name="old_password" required autocomplete="current-password"></label><label>新密码<input type="password" name="new_password" required minlength="10" maxlength="64" autocomplete="new-password"><small>至少10位，同时包含字母和数字</small></label><button class="primary">保存新密码</button></form>`;
}
