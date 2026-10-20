<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/hero-dark.svg?v=8">
  <source media="(prefers-color-scheme: light)" srcset="./assets/hero-light.svg?v=8">
  <img src="./assets/hero-light.svg?v=8" width="100%" alt="Rongyi，独立开发者，Yi盘创始人。随身的上下文，看得见的 Agent，摸得着的硬件。">
</picture>

<div align="center">
  <a href="https://rongyishuaige7.github.io/"><img src="./assets/badge-studio.svg?v=1" height="36" alt="访问 Rongyi Studio 主页"></a>
  &nbsp;&nbsp;
  <a href="https://rongyishuaige7.github.io/#log"><img src="./assets/badge-build-log.svg?v=1" height="36" alt="查看开发记录"></a>
</div>

我是 **Rongyi**，一个人做产品的独立开发者。主线是 **Yi盘**：装在 U 盘里的随身 AI 工作台；同时做让 Agent 工作看得见的工具，以及 ESP32、STM32 与树莓派上的硬件原型。

---

## `// 01 CARRY` 随身 · 上下文，跟着人走。

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/yipan-flow-dark.svg?v=9">
  <source media="(prefers-color-scheme: light)" srcset="./assets/yipan-flow-light.svg?v=9">
  <img src="./assets/yipan-flow-light.svg?v=9" width="100%" alt="Yi盘工作方式：盘内资料和任务进入 Yi盘工作台，需要智能处理时按需调用云端模型，产出和任务记录留在盘内，经记录或沉淀后成为下一次继续工作的基础，数据随盘走。">
</picture>

> 结构示意，非产品截图。

**Yi盘是一套装在 U 盘里的随身 AI 工作台。** 长期资料、任务记录和主要产出保存在盘内；需要智能处理时，主要调用云端模型。

| 项目 | 当前事实 |
|:--|:--|
| 当前状态 | 受控内测，正在完成上市前验证 |
| 平台验证 | Linux 测试最完整；Windows 和 macOS 继续真机测试 |
| 公开范围 | 产品事实、已知限制和开发复盘公开；核心实现、客户配置与制盘工具不公开 |

<div align="center">
  <a href="https://github.com/rongyishuaige7/yipan-showcase"><img src="./assets/badge-yipan.svg?v=2" height="36" alt="了解 Yi盘"></a>
  &nbsp;&nbsp;
  <a href="https://github.com/rongyishuaige7/yipan-showcase/blob/main/docs/%E4%BA%A7%E5%93%81%E4%BA%8B%E5%AE%9E%E4%B8%8E%E9%99%90%E5%88%B6.md"><img src="./assets/badge-product-facts.svg?v=1" height="36" alt="查看 Yi盘产品事实与限制"></a>
  &nbsp;&nbsp;
  <a href="https://github.com/rongyishuaige7/yipan-showcase/issues"><img src="./assets/badge-feedback.svg?v=2" height="36" alt="提交 Yi盘反馈"></a>
</div>

---

## `// 02 SEE` 可见 · 看得见，才管得住。

Agent 用了多少、花了多少、为什么这样写，都应该能查。下面是我给自己做、也公开发布的工具。

### [DSH Usage](https://github.com/rongyishuaige7/dsh-stats)

`USAGE` DeepSeek Harness 插件：按项目整理 DSH 会话，Token、开发时长、模型费用和账户余额一屏看清。无法确认价格时明确标记，不硬猜；密钥只在本机使用。

`TypeScript` `DSH Plugin` `Local-first` | 以 `@rongyi7/dsh-stats` 发布在 npm | MIT

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/dsh-timeline-dark.png?v=1">
  <source media="(prefers-color-scheme: light)" srcset="./assets/dsh-timeline-light.png?v=1">
  <img src="./assets/dsh-timeline-light.png?v=1" width="100%" alt="DSH Usage 开发时间线界面：每半小时的 Token 柱与按项目排列的会话泳道">
</picture>

> 真实运行界面，夹具数据，项目名为占位；图中为 Token 模式。切换到费用时按公开 API 计价规则推算，最终以 Provider 账单为准。

### Agent 工作流

- **[dsh-spec](https://github.com/rongyishuaige7/dsh-spec)** `SPEC` 规格驱动开发的 DSH 插件，含写规格、实现、验收三个技能：先写需求、设计和任务，再按规格实现与验收。`DSH Plugin` `npm` | MIT
- **[Tech Mentor](https://github.com/rongyishuaige7/tech-mentor)** `MENTOR` 把 AI 写好的代码讲透：架构意图、流转图、源码解剖和暗坑考查四阶带读。`Agent Skill` `Shell` | MIT
- **[Problem Solution Recorder](https://github.com/rongyishuaige7/problem-solution-recorder-oss)** `RECORD` 把排障过程保存成可检索的 Markdown，同时生成人读索引和 AI 索引。`Agent Skill` `Markdown` | [v0.2.0 正式发布](https://github.com/rongyishuaige7/problem-solution-recorder-oss/releases/tag/v0.2.0) | [Skill 验证通过](https://github.com/rongyishuaige7/problem-solution-recorder-oss/actions/runs/29339468636) | MIT
- **[宁缺](https://github.com/rongyishuaige7/ningque)** `AI-LED` 一份持续发布品味裁决的独立审美公报。产品由 Codex 独立构思、设计与开发；我负责审查、授权和发布渠道。`Codex` `GitHub Pages`

### 桌面工具

- **[DevFlow Recorder](https://github.com/rongyishuaige7/devflow-recorder)** `OBSERVE` 在 GNOME Wayland 上记录窗口焦点变化，形成保存在本机的工作时间线。`Rust` `Tauri` `SQLite` | [Web 单元测试与前端构建通过](https://github.com/rongyishuaige7/devflow-recorder/actions/runs/29339471902) | MIT
- **[Memory Monitor](https://github.com/rongyishuaige7/memory-monitor)** `PSI` GNOME Shell 扩展：状态栏颜色跟随 PSI 卡顿时间而不是占用率，机器真的变慢时才提醒，并列出 Swap 大户。`GNOME Shell` `JavaScript` | [语法检查、gjs 测试与扩展打包通过](https://github.com/rongyishuaige7/memory-monitor/actions/runs/30213179885) | MIT
- **[Desktop Pet](https://github.com/rongyishuaige7/pet-desktop-tauri)** `PLAY` Linux 桌面宠物原型：React 负责设置界面，Rust + GTK 负责透明置顶窗口。`Tauri` `Rust` `GTK` | [Web 单元测试与前端构建通过](https://github.com/rongyishuaige7/pet-desktop-tauri/actions/runs/29339475309) | MIT

> **公开证据：** Problem Solution Recorder 的固定验证运行成功；DevFlow 只检查 Web 单元测试与前端构建。

<div align="center">
  <a href="https://github.com/rongyishuaige7/dsh-stats"><img src="./assets/badge-dsh.svg?v=1" height="36" alt="查看 DSH Usage"></a>
</div>

---

## `// 03 TOUCH` 可触 · 把代码烧进板子里。

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/hardware-strip-dark.svg?v=1">
  <source media="(prefers-color-scheme: light)" srcset="./assets/hardware-strip-light.svg?v=1">
  <img src="./assets/hardware-strip-light.svg?v=1" width="100%" alt="Hardware Lab 电路走线示意：传感器信号汇入中间芯片，再依次点亮右侧 LED。">
</picture>

完整的 **22 个公开硬件项目**统一收录在 [Hardware Lab](https://github.com/rongyishuaige7/hardware-lab)：ESP32 15 个、STM32 3 个、树莓派 3 个、Arduino 1 个，每个都附项目介绍、构建证据、公开资料与实际使用注意事项。索引更新至 2026-10-20，[索引与公开证据校验通过](https://github.com/rongyishuaige7/hardware-lab/actions/runs/39375071963)。

### [ESP32 RPS Game](https://github.com/rongyishuaige7/ESP32_RPS_Game)

基于 ESP32-S3 的视觉猜拳硬件实验，包含摄像头识别、OLED、音频与 RGB 反馈。

`C++` `PlatformIO` `ESP32-S3` `OV3660` | [固件构建与 Artifact 上传通过](https://github.com/rongyishuaige7/ESP32_RPS_Game/actions/runs/29669939600) | 历史原理图资料 | MIT

### [Multimodal Smart Pot](https://github.com/rongyishuaige7/esp32-s3-multimodal-smart-pot)

独立完成的 ESP32-S3 + FreeRTOS 软硬件原型，包含环境感知、双泵灌溉、本地彩屏、局域网控制、语音和手势交互；公开固件、EDA/制造文件与项目实物照片。

`C++` `PlatformIO` `FreeRTOS` `EasyEDA` | [固件 CI 通过](https://github.com/rongyishuaige7/esp32-s3-multimodal-smart-pot/actions/runs/29669976115) | 项目照片与 EDA 资料 | MIT

<details>
<summary><b><code>// LATEST BUILD</code></b> 最新收录的硬件项目</summary>
<br>

最新收录：[基于树莓派的居家环境与活动状态监测教学原型](https://github.com/rongyishuaige7/raspberry-pi-home-environment-activity-monitoring-demo)。

- **构建证据：** Python 编译、11 项后端与源码合同、Android Gradle test task（当前 `NO-SOURCE`）、lint、debug assembly、敏感信息扫描与精确公开清单已由 [固定 Actions 构建证据](https://github.com/rongyishuaige7/raspberry-pi-home-environment-activity-monitoring-demo/actions/runs/29670051197) 验证；CI 不上传构建产物。
- **项目资料：** 公开一张已脱敏的 2026-03-17 项目照片；四张旧界面截图未上传，未公开 APK、演示视频或 EDA/制造文件。
- **实际使用限制：** `ENABLE_PHYSICAL_OUTPUTS=false`、`ENABLE_CAMERA=false`，继电器、蜂鸣器和摄像头默认关闭。MQ-7 数字 GPIO 只表示未标定教学阈值事件，MPU6050 阈值不能可靠判断人员跌倒，可选图片路径不是身份认证；HTTP/Socket.IO 共享 Token 只适合隔离实验网络。
- **不适用：** 医疗或养老看护、CO/燃气报警、跌倒或生命安全判断、身份认证、消费产品、无人值守控制或生产系统。

</details>

> **构建说明：** 各项目的 GitHub Actions 负责固定配置下的构建与仓库检查；对应的精确构建链接、公开资料和使用限制以 [Hardware Lab](https://github.com/rongyishuaige7/hardware-lab) 为准。部分项目上传的 Actions Artifact 按平台保留期自动过期。

<div align="center">
  <a href="https://github.com/rongyishuaige7/hardware-lab"><img src="./assets/badge-hardware.svg?v=1" height="36" alt="查看 Hardware Lab 硬件项目索引"></a>
</div>

---

<details>
<summary><b><code>// ENGLISH OVERVIEW</code></b></summary>
<br>

I am **Rongyi**, an independent developer and the founder of **Yi盘**. My work runs in three lanes. **Carry:** Yi盘 is a portable AI workspace designed to run from a USB drive; long-term files, task records, and primary outputs stay on the drive, while intelligent processing mainly uses cloud models. It is in controlled testing, with Linux coverage furthest along and Windows and macOS validation continuing on real machines. **See:** tools that make agent work visible, such as DSH Usage for per-project token, time, and cost tracking. **Touch:** 22 public hardware prototypes on ESP32, STM32, Raspberry Pi, and Arduino, indexed in Hardware Lab. Public repositories document verified facts, known limitations, and build evidence.

</details>

---

<div align="center">
  <strong>Rongyi Studio · 随身 / 可见 / 可触</strong>
  <br><br>
  <a href="https://rongyishuaige7.github.io/"><strong>个人主页</strong></a>
  &nbsp;&nbsp;|&nbsp;&nbsp;
  <a href="https://github.com/rongyishuaige7?tab=repositories"><strong>全部仓库</strong></a>
  &nbsp;&nbsp;|&nbsp;&nbsp;
  <a href="https://github.com/rongyishuaige7/hardware-lab"><strong>Hardware Lab</strong></a>
  &nbsp;&nbsp;|&nbsp;&nbsp;
  <a href="https://github.com/rongyishuaige7/yipan-showcase/issues"><strong>提交 Yi盘反馈</strong></a>
</div>
