# 界面设计与修缮说明

## 设计目标

宿舍服务台面向学生、维修人员和管理人员，优先展示下一步操作、问题位置、处理状态和责任人。界面采用冷白底与深蓝导航，蓝色标识主要操作，绿/黄等状态色辅助识别，文字标签始终保留，避免只靠颜色表达状态。

## 视觉规范

| Token | 值与用途 |
|---|---|
| ink | #18344c，正文重点、深蓝服务导航 |
| action | #285de5，主要操作与选中强调 |
| canvas | #f5f7fa，页面背景 |
| surface | #ffffff，表格、表单和统计内容 |
| success | #3e8b76，完成比例与实时连接 |
| attention | #ba7c2e，待办提示 |

正文优先使用本地微软雅黑UI、微软雅黑或苹方，不依赖外部字体CDN；数字使用Bahnschrift并开启等宽数字。移动端改为顶部横向导航，指标区两列排列，图表单列显示，表格在局部容器横向滚动。

登录页使用中国科大高新校区建筑夜景，总览使用高新校区建筑及水面倒影。照片来自中国科大招生网，已优化为本地WebP，来源见image-credits.md，界面保留署名链接。图表使用真实统计值，环形图同时提供完成率文字和可访问名称。

## 应用的两个技能

- [Anthropic frontend-design](https://github.com/anthropics/skills/tree/main/skills/frontend-design)：确定主题、字体、颜色和内容层级，先设计后检查浏览器截图。
- [Vercel web-design-guidelines](https://github.com/vercel-labs/agent-skills/tree/main/skills/web-design-guidelines)：检查语义、焦点、表单、响应式、动画偏好和状态表达。

技能安装到个人Codex技能目录，源码仓库不复制其内容或许可证。新页面基于实际宿舍报修业务设计。

## 修缮内容

- 重做登录页、服务总览、侧栏、图标、数据区、工单列表、表单与详情。
- 导航使用链接并标明aria-current，支持键盘、跳到主要内容和URL状态。
- 保留表单label、密码自动填充、错误文本和aria-live提示；提交中禁用按钮并显示忙状态。
- 图片提供固定尺寸、alt和懒加载；装饰图标对读屏隐藏。
- 对未保存内容离开页面进行提醒；取消报修和停用账号要求确认。
- 使用focus-visible，遵循prefers-reduced-motion；详情滚动不传递至背景。
- 桌面1440px与手机390px通过真实浏览器流程及截图检查。
