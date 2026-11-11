import { state, roles, api, send, query, utcDate } from "./model.js";
import * as view from "./view.js";
const $ = (s) => document.querySelector(s);
let socket, toastTimer;
let requestVersion = 0;
function toast(message, error = false) {
  $("#toast").textContent = message;
  $("#toast").className = error ? "show error" : "show";
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => ($("#toast").className = ""), 5000);
}
async function session() {
  try {
    state.user = await api("/users/me");
    await enter();
  } catch {
    $("#auth").hidden = false;
    $("#shell").hidden = true;
  }
}
async function enter() {
  state.locations = await api("/locations");
  if (state.user.role === "admin") state.users = await api("/admin/users");
  $("#auth").hidden = true;
  $("#shell").hidden = false;
  $("#identity").textContent =
    state.user.username + " · " + roles[state.user.role];
  $("#role-caption").textContent = roles[state.user.role] + "工作台";
  const links = {
    dashboard: "总览",
    tickets: state.user.role === "technician" ? "维修任务" : "报修工单",
    ...(state.user.role === "student" ? { new: "提交报修" } : {}),
    ...(state.user.role === "admin"
      ? { users: "用户与宿舍", audit: "操作日志" }
      : {}),
    settings: "账号设置",
  };
  if (!links[state.page]) state.page = "dashboard";
  $("#nav").innerHTML = Object.entries(links)
    .map(
      ([k, v]) =>
        `<a href="#${k}" data-page="${k}">${view.icon(k)}<span>${v}</span></a>`,
    )
    .join("");
  $("#today").textContent = new Intl.DateTimeFormat("zh-CN", {
    month: "long",
    day: "numeric",
    weekday: "long",
  }).format(new Date());
  connect();
  await render();
}
function connect() {
  socket?.close();
  socket = new WebSocket(
    `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/dashboard`,
  );
  socket.onmessage = async (e) => {
    const d = JSON.parse(e.data);
    $("#live-status").textContent = `实时连接 · ${d.total} 张工单`;
    if (state.page === "dashboard") {
      try {
        const s = await api(
          "/statistics?" +
            query(
              Object.fromEntries(
                Object.entries(state.filters).filter(([k]) => k !== "status"),
              ),
            ),
        );
        if (state.page !== "dashboard") return;
        const container = document.createElement("div");
        container.innerHTML = view.dashboard(s);
        for (const selector of [".metrics", ".chart-grid"]) {
          const target = $("#content " + selector);
          if (target) target.replaceWith(container.querySelector(selector));
        }
      } catch {}
    }
  };
  socket.onclose = () =>
    ($("#live-status").textContent = "实时连接断开 · 自动重连中");
  socket.onerror = () => ($("#live-status").textContent = "实时连接暂不可用");
}
setInterval(() => {
  if (
    state.user &&
    !$("#shell").hidden &&
    socket?.readyState === WebSocket.CLOSED
  )
    connect();
}, 10000);
async function render() {
  const version = ++requestVersion;
  const page = state.page;
  const titles = {
    dashboard: "服务总览",
    tickets: state.user.role === "technician" ? "我的维修任务" : "报修工单",
    new: "提交报修",
    users: "用户与宿舍",
    settings: "账号设置",
    audit: "操作日志",
  };
  $("#page-title").textContent = titles[page];
  document.querySelectorAll("#nav [data-page]").forEach((b) => {
    b.classList.toggle("active", b.dataset.page === page);
    if (b.dataset.page === page) b.setAttribute("aria-current", "page");
    else b.removeAttribute("aria-current");
  });
  let html = "";
  try {
    if (page === "dashboard")
      html = view.dashboard(
        await api(
          "/statistics?" +
            query(
              Object.fromEntries(
                Object.entries(state.filters).filter(([k]) => k !== "status"),
              ),
            ),
        ),
      );
    if (page === "tickets")
      html = view.tickets(
        await api("/tickets?" + query() + "&page=" + state.listPage),
      );
    if (page === "new") html = view.newTicket();
    if (page === "users") {
      state.users = await api("/admin/users");
      state.locations = await api("/locations");
      html = view.users(state.users);
    }
    if (page === "settings") html = view.settings();
    if (page === "audit") {
      const logs = await api("/admin/audit");
      html =
        '<section class="panel"><h2>最近100条操作</h2><ol class="timeline">' +
        logs
          .map(
            (e) =>
              `<li><span>${view.date(e.created_at)} · ${view.esc(e.actor || "系统服务")}</span><p>${view.esc(e.action)} ${view.esc(e.detail)}</p></li>`,
          )
          .join("") +
        "</ol></section>";
    }
    if (version === requestVersion) $("#content").innerHTML = html;
  } catch (e) {
    toast(e.message, true);
  }
}
async function openTicket(id) {
  state.detail = await api("/tickets/" + id);
  $("#detail-content").innerHTML = view.detail(state.detail);
  if (!$("#detail").open) $("#detail").showModal();
}
async function refreshDetail() {
  await openTicket(state.detail.id);
  await render();
}
async function busy(form, fn) {
  const buttons = [...form.querySelectorAll("button")];
  form.querySelector(".form-error")?.remove();
  form.setAttribute("aria-busy", "true");
  buttons.forEach((b) => (b.disabled = true));
  try {
    await fn();
    form.dataset.dirty = "";
  } catch (e) {
    const error = document.createElement("p");
    error.className = "form-error error";
    error.setAttribute("role", "alert");
    error.tabIndex = -1;
    error.textContent = e.message;
    form.append(error);
    error.focus();
    toast(e.message, true);
  } finally {
    form.removeAttribute("aria-busy");
    buttons.forEach((b) => (b.disabled = false));
  }
}
$("#auth-toggle").onclick = () => {
  state.register = !state.register;
  $("#register-fields").hidden = !state.register;
  $("#auth-title").textContent = state.register
    ? "创建你的账号"
    : "登录你的账号";
  $("#auth-submit").textContent = state.register ? "注册并登录" : "登录";
  $("#auth-toggle").textContent = state.register
    ? "已有账号？登录"
    : "还没有账号？注册";
  $("#auth-error").textContent = "";
};
$("#auth-form").onsubmit = (e) => {
  e.preventDefault();
  busy(e.target, async () => {
    const d = Object.fromEntries(new FormData(e.target));
    try {
      if (state.register) await send("/auth/register", d);
      const result = await send("/auth/login", {
        username: d.username,
        password: d.password,
      });
      state.user = result.user;
      e.target.reset();
      state.page = "dashboard";
      await enter();
    } catch (err) {
      $("#auth-error").textContent = err.message;
    }
  });
};
$("#logout").onclick = async () => {
  try {
    await send("/auth/logout", {});
    socket?.close();
    location.reload();
  } catch (e) {
    toast(e.message, true);
  }
};
$("#close-detail").onclick = () => $("#detail").close();
document.addEventListener("change", (e) => {
  if (e.target.id === "building-select") {
    const b = state.locations.find((b) => b.id === +e.target.value);
    $("#room-select").innerHTML =
      '<option value="">请选择房间</option>' +
      view.options(
        Object.fromEntries((b?.rooms || []).map((r) => [r.id, r.name])),
      );
  }
});
document.addEventListener("click", async (e) => {
  const b = e.target.closest("button, a[data-page]");
  if (!b) return;
  if (b.tagName === "A" && (e.ctrlKey || e.metaKey || e.shiftKey)) return;
  try {
    if (b.dataset.page) {
      e.preventDefault();
      if (
        document.querySelector("#content form[data-dirty=true]") &&
        !confirm("还有未保存的内容，确定离开当前页面吗？")
      )
        return;
      state.page = b.dataset.page;
      state.listPage = 1;
      syncURL();
      await render();
    }
    if (b.dataset.ticket) await openTicket(b.dataset.ticket);
    if (b.dataset.user) {
      if (
        b.dataset.active === "0" &&
        !confirm("停用后，该账号将无法继续访问。确认停用吗？")
      )
        return;
      await send(
        "/admin/users/" + b.dataset.user,
        { active: b.dataset.active === "1" },
        "PUT",
      );
      await render();
    }
    if (b.dataset.action === "reset") {
      state.filters = {};
      state.listPage = 1;
      syncURL();
      await render();
    }
    if (b.dataset.action === "previous") {
      state.listPage--;
      syncURL();
      await render();
    }
    if (b.dataset.action === "next") {
      state.listPage++;
      syncURL();
      await render();
    }
    if (b.dataset.action === "export") {
      const res = await fetch("/api/admin/export?" + query(), {
        credentials: "same-origin",
      });
      if (!res.ok) throw new Error("导出失败");
      const url = URL.createObjectURL(await res.blob());
      const a = document.createElement("a");
      a.href = url;
      a.download = "宿舍报修.csv";
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    }
  } catch (err) {
    toast(err.message, true);
  }
});
document.addEventListener("submit", (e) => {
  const form = e.target;
  if (form.id === "auth-form") return;
  e.preventDefault();
  const d = Object.fromEntries(new FormData(form));
  const submitAction = e.submitter?.value;
  if (
    submitAction === "cancel" &&
    !confirm("确认取消这张尚未派单的报修工单吗？")
  )
    return;
  busy(form, async () => {
    if (form.id === "filters") {
      state.filters = {
        ...d,
        start: utcDate(d.start),
        end: utcDate(d.end, true),
      };
      state.listPage = 1;
      syncURL();
      await render();
    }
    if (form.id === "ticket-form") {
      if (d.image?.size > 5 * 1024 * 1024) throw new Error("图片最大5MB");
      const t = await send("/tickets", {
        room_id: +d.room_id,
        description: d.description,
        category: d.category,
      });
      if (d.image?.size) {
        const fd = new FormData();
        fd.append("file", d.image);
        try {
          await api(`/tickets/${t.id}/attachments`, {
            method: "POST",
            body: fd,
          });
        } catch (err) {
          toast("工单已创建，图片上传失败：" + err.message, true);
        }
      }
      state.page = "tickets";
      await render();
      await openTicket(t.id);
    }
    if (form.id === "action-form") {
      await send(`/tickets/${state.detail.id}/actions`, {
        action: submitAction,
        version: state.detail.version,
        note: d.note,
      });
      await refreshDetail();
    }
    if (form.id === "assign-form") {
      await send(`/tickets/${state.detail.id}/actions`, {
        action: "assign",
        version: state.detail.version,
        assignee_id: +d.assignee_id,
        scheduled_at: new Date(d.scheduled_at).toISOString(),
        note: d.note,
      });
      await refreshDetail();
    }
    if (form.id === "classify-form") {
      await send(`/tickets/${state.detail.id}/actions`, {
        action: "classify",
        version: state.detail.version,
        category: d.category,
      });
      await refreshDetail();
    }
    if (form.id === "attachment-form") {
      const fd = new FormData();
      fd.append("file", d.image);
      await api(`/tickets/${state.detail.id}/attachments`, {
        method: "POST",
        body: fd,
      });
      await refreshDetail();
    }
    if (form.id === "evaluation-form") {
      await send(`/tickets/${state.detail.id}/evaluation`, {
        score: +d.score,
        comment: d.comment,
      });
      await refreshDetail();
    }
    if (form.id === "location-form") {
      await send("/admin/locations", {
        name: d.name,
        building_id: d.building_id ? +d.building_id : null,
      });
      await render();
    }
    if (form.id === "password-form") {
      await send("/auth/password", d, "PUT");
      socket?.close();
      location.reload();
    }
  });
});
function syncURL() {
  const params = new URLSearchParams(query());
  params.set("page", state.listPage);
  history.pushState(
    {},
    "",
    location.pathname + "?" + params + "#" + state.page,
  );
}
function readURL() {
  state.page = location.hash.slice(1) || "dashboard";
  const p = new URLSearchParams(location.search);
  state.filters = Object.fromEntries(
    ["building", "category", "status", "start", "end"]
      .filter((k) => p.get(k))
      .map((k) => [k, p.get(k)]),
  );
  state.listPage = Math.max(1, Number(p.get("page")) || 1);
}
window.addEventListener("popstate", () => {
  readURL();
  if (state.user) render();
});
document.addEventListener("input", (e) => {
  const form = e.target.closest("form");
  if (
    form &&
    ["ticket-form", "password-form", "action-form", "assign-form"].includes(
      form.id,
    )
  )
    form.dataset.dirty = "true";
});
window.addEventListener("beforeunload", (e) => {
  if (document.querySelector("form[data-dirty=true]")) {
    e.preventDefault();
    e.returnValue = "";
  }
});
for (const element of document.querySelectorAll(
  "[name=username],[name=email],[name=invite_code]",
))
  element.spellcheck = false;
readURL();
session();
