# Rongyi

<div align="center">
  <a href="https://rongyishuaige7.github.io/">
    <img src="./assets/founder-lab.svg" width="100%" alt="Rongyi — Make AI context move with you" />
  </a>
</div>

<div align="center">
  <a href="https://rongyishuaige7.github.io/"><strong>个人主页</strong></a>
  &nbsp;·&nbsp;
  <a href="https://github.com/rongyishuaige7/yipan-showcase"><strong>Yi盘</strong></a>
</div>

我是 **Rongyi**，在杭州做 **Yi盘**——一套装在 U 盘里的随身 AI 工作台。除了 Yi盘，我也在做桌面工具和硬件项目。

## 正在做：Yi盘

<a href="https://github.com/rongyishuaige7/yipan-showcase">
  <img src="./assets/yipan-feature.svg" width="100%" alt="Yi盘 — Portable AI Agent Workspace 抽象能力图" />
</a>

Yi盘把长期资料、任务记录和主要产出保存在盘内；需要智能处理时主要调用云端模型。

- **当前状态** · 受控内测，正在完成上市前验证
- **测试进度** · Linux 测试最完整；Windows 和 macOS 仍在真机测试
- **公开仓库** · [`yipan-showcase`](https://github.com/rongyishuaige7/yipan-showcase) 记录已确认的功能、已知限制和开发进度；核心实现、客户配置和制盘工具不公开

> 上图是功能示意，不是产品截图。信息更新于 **2026-07-15**；详细状态见 [`Yi盘产品事实与限制`](https://github.com/rongyishuaige7/yipan-showcase/blob/main/docs/%E4%BA%A7%E5%93%81%E4%BA%8B%E5%AE%9E%E4%B8%8E%E9%99%90%E5%88%B6.md)。

## 其他开源项目

### [Problem Solution Recorder](https://github.com/rongyishuaige7/problem-solution-recorder-oss)

把排障过程保存成可检索的 Markdown：记录症状、命令、原因和修复方法，同时生成人读索引和 AI 索引。

`Agent Skill` `Markdown` `Shell` · **[v0.2.0 正式发布](https://github.com/rongyishuaige7/problem-solution-recorder-oss/releases/tag/v0.2.0)** · **[Skill 验证通过](https://github.com/rongyishuaige7/problem-solution-recorder-oss/actions/runs/29339468636)** · MIT

### [DevFlow Recorder](https://github.com/rongyishuaige7/devflow-recorder)

在 Linux/Wayland 上记录窗口焦点变化，并整理成便于回看的工作时间线；数据保存在本机。

`Rust` `Tauri` `React` `SQLite` · **[Web 单元测试与前端构建通过](https://github.com/rongyishuaige7/devflow-recorder/actions/runs/29339471902)** · GNOME Wayland MVP · MIT

### [ESP32 RPS Game](https://github.com/rongyishuaige7/ESP32_RPS_Game)

基于 ESP32-S3 的视觉猜拳游戏：摄像头启发式识别、OLED、音频、RGB 反馈与可选 MJPEG 推流。

`C++` `PlatformIO` `ESP32-S3` `OV3660` · **[固件构建与 Artifact 上传通过](https://github.com/rongyishuaige7/ESP32_RPS_Game/actions/runs/29339478819)** · MIT

### [Desktop Pet](https://github.com/rongyishuaige7/pet-desktop-tauri)

一个 Linux 桌面宠物原型。React 负责设置界面，Rust + GTK 负责透明置顶窗口和本地动画。

`Tauri` `React` `Rust` `GTK` · **[Web 单元测试与前端构建通过](https://github.com/rongyishuaige7/pet-desktop-tauri/actions/runs/29339475309)** · Linux prototype · MIT

> **CI 范围 · 2026-07-15**：DevFlow 和 Desktop Pet 只检查 Web 测试与前端构建；ESP32 只检查固件能否按固定配置编译。Actions 中的固件会过期。

更多开发记录见 [个人主页](https://rongyishuaige7.github.io/#log)。

---

<div align="center">
  <strong>Rongyi · Yi盘 · Hangzhou</strong>
  <br />
  <a href="https://rongyishuaige7.github.io/">个人主页</a>
  &nbsp;·&nbsp;
  <a href="https://github.com/rongyishuaige7?tab=repositories">全部仓库</a>
  &nbsp;·&nbsp;
  <a href="https://github.com/rongyishuaige7/yipan-showcase/issues">Yi盘反馈</a>
</div>
