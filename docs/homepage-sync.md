# 个人主页 README 与主页同步（2026-10-20）

主页（`rongyishuaige7.github.io`）已完成配色统一、真实画面和动效调整。个人主页 README 仍保留上一版的旧紫色、浅色 DSH 截图和没有来源的示例数据，硬件区也没有实物照片。本轮让两边的事实、配色和素材口径一致。

## 范围

- 去掉示例数据：删除 DSH 信号卡；首图工具区改为真实公开工具名，不再显示会话列表和 Token 柱。
- 配色与截图：SEE 线辅助色按主页改为 `#63ccf8`（浅色主题另取对比度足够的蓝）；DSH 截图换成 dsh-stats 夹具的 Token 模式时间线，深色和浅色主题各一张。
- 硬件照片：精选与主页一致（智能花盆、交通信号、健康科普语音终端），使用各仓库公开的历史原型照片并标注日期。
- 文案：去掉与首图、标题重复的句子和链接，工具描述与主页事实对齐。
- 定时检查：每周运行一次内容、链接和固定证据校验。

## 非目标

不改三条线结构、主色、品牌徽章样式、Yi盘流程图和 Hardware Lab 计数；不增加依赖；不修改其他仓库。置顶仓库和仓库简介只能在 GitHub 网页修改，不在本轮范围内。

## 实现与约束

- `hero-*.svg`、`hardware-strip-*.svg` 只改 `scripts/render-svg.py` 后重新生成，CI 用 `--check` 防止漂移。
- 位图放在 `assets/`，不带 EXIF/文本元数据并限制体积；`validate-profile.py` 同步维护素材清单、必需仓库和必须出现的事实文本。
- 改动的 SVG 提升 `?v=` 版本号，避免 GitHub 图片缓存继续显示旧图。
- 新增的固定 Actions 证据链接必须在 `validate-evidence-links.py` 中声明工作流和触发事件，并对应各仓库默认分支 HEAD。

## 风险

- 照片条在浅色和深色主题下的边缘观感不同：使用带透明圆角的 WebP，不铺底色。
- 截图体积超过现有 150KB 上限：先缩放和无抖动量化；仍不够时再调整上限并说明理由。
- 定时链接检查可能因外部站点短暂失败而变红：失败时先重跑确认，不放宽检查。

## 验证

每次提交前运行 `render-svg.py --check`、`validate-svg.py`、`validate-motion.py`、`validate-profile.py`、`validate-evidence-links.py` 与 markdownlint，并在浏览器中查看深色和浅色主题下的 SVG 与截图。推送后检查 Actions，并在线查看个人主页的桌面和手机布局。

## 分阶段交付

1. 去掉示例数据。
2. 配色与双主题截图。
3. 精选硬件照片。
4. 文案精简。
5. 每周定时检查。
6. 验收记录。

## 验收记录（2026-10-20）

| 阶段 | 提交 | Actions 运行 |
| --- | --- | --- |
| 方案 | `b02a20b` | 39425214315 成功 |
| 1 去掉示例数据 | `0c92618` | 39425901410 成功 |
| 2 配色与双主题截图 | `09f0d6e` | 39426686121 成功 |
| 3 精选硬件照片 | `795e8c2` | 39427683884 成功 |
| 4 文案精简 | `b42038d` | 39429715514 成功 |
| 5 每周定时检查 | `e6c278b` | 39429932600 成功（内容与 Secret scan 两个作业都运行） |

本地检查：每次提交前 `render-svg.py --check`、`validate-svg.py`、`validate-motion.py`、`validate-profile.py` 通过；`validate-evidence-links.py` 核对 9 条固定证据链接；markdownlint 检查 README 和 `docs/` 共 0 个问题。

素材：

- `dsh-timeline-dark.png` 1600×723，72,476 字节；`dsh-timeline-light.png` 62,245 字节。两张都是 256 色无抖动量化，没有元数据块。
- `hardware-featured.webp` 1600×390，109,986 字节，块为 VP8X/ALPH/VP8，不含 EXIF/XMP。
- `hero-*.svg` 约 15.4KB。浏览器截图覆盖深浅两种主题、减少动效和正常动效：工具高亮落在 DSH Usage 行，文字没有重叠。

线上（Playwright Chromium，深色/浅色 × 1280/390 宽）：

- README 的 11 张图片全部加载，0 张失败。
- 首图、Yi盘流程图、DSH 截图、硬件条四组 `<picture>` 都按主题切换。
- 照片条的透明圆角在两种底色上都没有色块。
- README 高度：第 3 阶段后为 3472/4047px，第 4 阶段后为 3357/3892px。

偏差：

- 首图副标题与 README 第一句重复，第 4 阶段删去，标语下移 14px 居中；"一个人做产品的独立开发者"仍保留在 README 开头。
- Tech Mentor 保留仓库原有的四个阶段名称，只调整语序。
- 石头剪刀布原型移出精选，仍可从 Hardware Lab 进入。
- 截图靠量化满足 150KB 上限，未放宽；照片条单独设 160KB 上限。
- 每周运行跳过 Secret scan：历史只会在推送时变化，推送时仍会扫描。

未验证：

- Safari、Firefox 和 GitHub 手机 App 中的显示。
- 定时任务已注册为 active，但还没有触发过；按 cron 预计第一次在 2026-10-26 02:17 UTC 左右运行。
- 仓库连续 60 天没有活动时，GitHub 会自动停用定时工作流，需要在 Actions 页面重新启用。

需要在 GitHub 网页手动处理：把 dsh-stats 加入置顶仓库；把 yipan-showcase 仓库简介中的破折号改为逗号或句号。
