<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/hero-dark.svg?v=6">
  <source media="(prefers-color-scheme: light)" srcset="./assets/hero-light.svg?v=6">
  <img src="./assets/hero-light.svg?v=6" width="100%" alt="Rongyi，Yi盘创始人。让 AI 上下文随身移动。">
</picture>

<div align="center">
  <a href="https://github.com/rongyishuaige7/yipan-showcase"><img src="./assets/badge-yipan.svg?v=2" height="36" alt="了解 Yi盘"></a>
  &nbsp;&nbsp;
  <a href="https://rongyishuaige7.github.io/#log"><img src="./assets/badge-build-log.svg?v=1" height="36" alt="查看开发记录"></a>
</div>

我是 **Rongyi**，一名独立开发者，目前在杭州开发 **Yi盘**，也持续发布本地优先的桌面工具和有趣的硬件项目。

---

## `// YI盘 PRODUCT`

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
  <a href="https://github.com/rongyishuaige7/yipan-showcase/blob/main/docs/%E4%BA%A7%E5%93%81%E4%BA%8B%E5%AE%9E%E4%B8%8E%E9%99%90%E5%88%B6.md"><img src="./assets/badge-product-facts.svg?v=1" height="36" alt="查看 Yi盘产品事实与限制"></a>
  &nbsp;&nbsp;
  <a href="https://github.com/rongyishuaige7/yipan-showcase/issues"><img src="./assets/badge-feedback.svg?v=2" height="36" alt="提交 Yi盘反馈"></a>
</div>

---

## `// OPEN BUILDS`

### [Problem Solution Recorder](https://github.com/rongyishuaige7/problem-solution-recorder-oss)

`RECORD` 把排障过程保存成可检索的 Markdown，同时生成人读索引和 AI 索引。

`Agent Skill` `Markdown` `Shell` | [v0.2.0 正式发布](https://github.com/rongyishuaige7/problem-solution-recorder-oss/releases/tag/v0.2.0) | [Skill 验证通过](https://github.com/rongyishuaige7/problem-solution-recorder-oss/actions/runs/29339468636) | MIT

### [DevFlow Recorder](https://github.com/rongyishuaige7/devflow-recorder)

`OBSERVE` 在 GNOME Wayland 上记录窗口焦点变化，形成保存在本机的工作时间线。

`Rust` `Tauri` `React` `SQLite` | [Web 单元测试与前端构建通过](https://github.com/rongyishuaige7/devflow-recorder/actions/runs/29339471902) | GNOME Wayland MVP | MIT

> **公开证据：** Problem Solution Recorder 的固定验证运行成功；DevFlow 只检查 Web 单元测试与前端构建。

<details>
<summary><b><code>// MORE EXPERIMENTS</code></b> 硬件与桌面实验</summary>
<br>

完整的 24 个硬件项目、真实构建证据、素材证据与真机验证边界统一收录在 [Hardware Lab](https://github.com/rongyishuaige7/hardware-lab)。索引已更新至 2026-07-19；本轮素材发布没有进行真机复测。

最新收录：[基于树莓派的居家环境与活动状态监测教学原型](https://github.com/rongyishuaige7/raspberry-pi-home-environment-activity-monitoring-demo)。

- **构建证据：** Python 编译、11 项后端与源码合同、Android Gradle test task（当前 `NO-SOURCE`）、lint、debug assembly、敏感信息扫描与精确公开清单已由 [固定 exact-HEAD Actions 构建证据](https://github.com/rongyishuaige7/raspberry-pi-home-environment-activity-monitoring-demo/actions/runs/29652508046) 验证；CI 不上传构建产物。
- **真机与素材：** 当前树莓派、传感器、显示屏、继电器、蜂鸣器、摄像头、MySQL 部署、网络链路和 Android 尚未按当前公开提交重新真机复测；本批公开了一张已脱敏的 2026-03-17 历史实物照片，四张旧界面截图未上传，演示视频、原理图、PCB、EDA、Gerber 与制造文件未提供。历史照片、CI、模拟器和构建不代表当前提交的实体读数、输出动作、设备在线、通知送达、稳定性或电气安全。
- **公开默认与边界：** `ENABLE_PHYSICAL_OUTPUTS=false`、`ENABLE_CAMERA=false`，继电器、蜂鸣器和摄像头默认关闭。MQ-7 数字 GPIO 只表示未标定教学阈值事件，MPU6050 阈值不能可靠判断人员跌倒，可选图片路径不是身份认证；HTTP/Socket.IO 共享 Token 只适合隔离实验网络。
- **不适用：** 医疗或养老看护、CO/燃气报警、跌倒或生命安全判断、身份认证、消费产品、无人值守控制或生产系统。

### [ESP32 RPS Game](https://github.com/rongyishuaige7/ESP32_RPS_Game)

基于 ESP32-S3 的视觉猜拳硬件实验，包含摄像头识别、OLED、音频与 RGB 反馈。

`C++` `PlatformIO` `ESP32-S3` `OV3660` | [固件构建与 Artifact 上传通过](https://github.com/rongyishuaige7/ESP32_RPS_Game/actions/runs/29654421275) | 历史原理图，当前硬件未复测 | MIT

### [Multimodal Smart Pot](https://github.com/rongyishuaige7/esp32-s3-multimodal-smart-pot)

独立完成的 ESP32-S3 + FreeRTOS 软硬件原型，包含环境感知、双泵灌溉、本地彩屏、局域网控制、语音和手势交互；公开固件、EDA/制造文件与历史实物照片。

`C++` `PlatformIO` `FreeRTOS` `EasyEDA` | [固件 CI 通过](https://github.com/rongyishuaige7/esp32-s3-multimodal-smart-pot/actions/runs/29518255431) | 历史真机照片，当前硬件未复测 | MIT

### [Desktop Pet](https://github.com/rongyishuaige7/pet-desktop-tauri)

使用 Tauri、React、Rust 与 GTK 构建的 Linux 原生透明桌面宠物原型。

`Tauri` `React` `Rust` `GTK` | [Web 单元测试与前端构建通过](https://github.com/rongyishuaige7/pet-desktop-tauri/actions/runs/29339475309) | Linux prototype | MIT

> **实验验证范围：** Desktop Pet 只检查 Web 单元测试与前端构建；ESP32 RPS Game 与智能花盆的 CI 只检查固件能否按固定配置编译；居家环境与活动状态监测教学原型的 CI 检查 Python 编译、11 项后端与源码合同、Android Gradle test task（当前 `NO-SOURCE`）、lint、debug assembly、敏感信息与精确公开清单，且不上传构建产物；掌机界面教学原型的 CI 检查公开范围、仓库结构、7 项源码契约、ESP32 默认与背光 opt-in 编译，且不上传构建产物；衣柜环境监测与自动通风控制系统的 CI 检查公开范围、仓库结构、15 项源码契约、STM32 安全默认与风扇精确 opt-in 隔离构建，且不上传构建产物；智能农业环境监测系统的 CI 还检查公开范围、源码契约、.NET 8 构建与 ESP32-S3 三种隔离构建，且不上传构建产物；智能门口提醒系统的 CI 检查 fail-closed 公开范围扫描、协议单元测试与 STM32 隔离构建，且不上传构建产物。Hardware Lab 已同步本批 20 个仓库的 exact-HEAD Actions 与已脱敏历史照片、截图和 EDA/制造衍生材料；这些历史素材不等同于当前公开提交的真机复测，本轮没有进行真机复测。若项目上传 Actions Artifact，其保留期会过期；部分项目不上传构建产物，以 24 项 Hardware Lab 索引条目为准。

</details>

<details>
<summary><b><code>// ENGLISH OVERVIEW</code></b></summary>
<br>

I am **Rongyi**, founder of **Yi盘**, a portable AI workspace designed to run from a USB drive. Long-term files, task records, and primary outputs stay on the drive, while intelligent processing mainly uses cloud models. Yi盘 is currently in controlled testing, with Linux coverage furthest along and Windows and macOS validation continuing on real machines. Public repositories document verified product facts, known limitations, and selected open-source tools.

</details>

---

<div align="center">
  <strong>Rongyi / Yi盘 / Hangzhou</strong>
  <br><br>
  <a href="https://github.com/rongyishuaige7?tab=repositories"><strong>全部仓库</strong></a>
  &nbsp;&nbsp;|&nbsp;&nbsp;
  <a href="https://github.com/rongyishuaige7/hardware-lab"><strong>Hardware Lab</strong></a>
  &nbsp;&nbsp;|&nbsp;&nbsp;
  <a href="https://github.com/rongyishuaige7/yipan-showcase/issues"><strong>提交 Yi盘反馈</strong></a>
  &nbsp;&nbsp;|&nbsp;&nbsp;
  <a href="mailto:2830305965@qq.com"><strong>2830305965@qq.com</strong></a>
</div>
