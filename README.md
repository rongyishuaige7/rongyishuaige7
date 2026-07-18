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
  <source media="(prefers-color-scheme: dark)" srcset="./assets/yipan-flow-dark.svg?v=8">
  <source media="(prefers-color-scheme: light)" srcset="./assets/yipan-flow-light.svg?v=8">
  <img src="./assets/yipan-flow-light.svg?v=8" width="100%" alt="Yi盘工作方式：盘内资料和任务进入 Yi盘工作台，需要智能处理时按需调用云端模型，产出和任务记录留在盘内，经记录或沉淀后成为下一次继续工作的基础，数据随盘走。">
</picture>

<br>

**Yi盘是一套装在 U 盘里的随身 AI 工作台。** 长期资料、任务记录和主要产出保存在盘内；需要智能处理时，主要调用云端模型。

| 项目 | 当前事实 |
|:--|:--|
| 当前状态 | 受控内测，正在完成上市前验证 |
| 平台验证 | Linux 测试最完整；Windows 和 macOS 继续真机测试 |
| 公开范围 | 产品事实、已知限制和开发复盘公开；核心实现、客户配置与制盘工具不公开 |

> 结构示意，不是产品截图。最后核对：**2026-07-15**。

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

> **公开证据核对：2026-07-15。** Problem Solution Recorder 的固定验证运行成功；DevFlow 只检查 Web 单元测试与前端构建。

<details>
<summary><b><code>// MORE EXPERIMENTS</code></b> 硬件与桌面实验</summary>
<br>

完整硬件项目、真实构建证据与真机验证边界统一收录在 [Hardware Lab](https://github.com/rongyishuaige7/hardware-lab)。

最新收录：[基于STM32F103和OV7670的智能门口提醒系统](https://github.com/rongyishuaige7/stm32f103-ov7670-smart-door-reminder-system)。

- **构建证据：** 公开范围扫描（含 fail-closed 敏感文件回归测试）、源码/协议契约、Host 内存串口单元测试与 STM32 PlatformIO 隔离构建已由 [固定 exact-HEAD Actions 构建证据](https://github.com/rongyishuaige7/stm32f103-ov7670-smart-door-reminder-system/actions/runs/29636386247) 验证；CI 不上传构建产物。
- **真机与素材：** 当前 STM32、OV7670、PIR、USB-TTL、SYN6288 与串口端到端链路尚未按当前公开提交重新真机复测；实物照片、视频、原理图、PCB、EDA、Gerber 与制造文件未提供。CI 和构建不代表烧录、采图、触发、播报、图像质量或电气安全。
- **公开默认与边界：** 公开 Host 只在内存中校验固定 `80 × 60` RGB565 串口帧，并回传固定通用 GBK 提示；不含真人图像、人脸样本、身份模板、身份识别、图像落盘或网络服务。XOR 只用于误码检测，不提供认证、加密、可靠送达或安全保证；固件仍会初始化 GPIO/UART/MCO，满足触发与接线条件时可能产生采集、串口与语音 I/O。
- **不适用：** 门禁、门锁、安防、身份认证、人员追踪、可靠提醒、公共场所监控、无人值守或生产系统。

### [ESP32 RPS Game](https://github.com/rongyishuaige7/ESP32_RPS_Game)

基于 ESP32-S3 的视觉猜拳硬件实验，包含摄像头识别、OLED、音频与 RGB 反馈。

`C++` `PlatformIO` `ESP32-S3` `OV3660` | [固件构建与 Artifact 上传通过](https://github.com/rongyishuaige7/ESP32_RPS_Game/actions/runs/29339478819) | MIT

### [Multimodal Smart Pot](https://github.com/rongyishuaige7/esp32-s3-multimodal-smart-pot)

独立完成的 ESP32-S3 + FreeRTOS 软硬件原型，包含环境感知、双泵灌溉、本地彩屏、局域网控制、语音和手势交互；公开固件、EDA/制造文件与历史实物照片。

`C++` `PlatformIO` `FreeRTOS` `EasyEDA` | [固件 CI 通过](https://github.com/rongyishuaige7/esp32-s3-multimodal-smart-pot/actions/runs/29518255431) | 历史真机照片，当前硬件未复测 | MIT

### [Desktop Pet](https://github.com/rongyishuaige7/pet-desktop-tauri)

使用 Tauri、React、Rust 与 GTK 构建的 Linux 原生透明桌面宠物原型。

`Tauri` `React` `Rust` `GTK` | [Web 单元测试与前端构建通过](https://github.com/rongyishuaige7/pet-desktop-tauri/actions/runs/29339475309) | Linux prototype | MIT

> **实验验证范围：2026-07-18。** Desktop Pet 只检查 Web 单元测试与前端构建；ESP32 RPS Game 与智能花盆的 CI 只检查固件能否按固定配置编译；智能农业环境监测系统的 CI 还检查公开范围、源码契约、.NET 8 构建与 ESP32-S3 三种隔离构建，且不上传构建产物；智能门口提醒系统的 CI 检查 fail-closed 公开范围扫描、协议单元测试与 STM32 隔离构建，且不上传构建产物。智能花盆照片与房卡系统界面截图属于历史演示证据，不等同于当前公开提交的真机复测。STM32、LoRa、树莓派 RFID、交通信号、健康科普语音终端、触摸手势控制、多传感器手环、Arduino 多传感器教学原型、智能农业环境监测系统与智能门口提醒系统等完整项目与边界见 Hardware Lab。若项目上传 Actions Artifact，其保留期会过期；部分项目不上传构建产物，以项目条目为准。

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
</div>
