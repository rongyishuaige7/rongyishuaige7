#!/usr/bin/env python3
"""Render the generated profile SVG pairs from one template per asset.

hero-*.svg, yipan-flow-*.svg and hardware-strip-*.svg are generated: edit this file, then run
`python3 scripts/render-svg.py`. CI runs `--check` so committed files cannot
drift from the templates. Dark and light variants share geometry and motion
CSS; only the palette tokens below differ. The hero embeds the WebP files in
media/hero/ as data URIs (GitHub serves README SVGs with default-src 'none',
so external images would not load); the dark and light DSH captures are the
only per-theme media.
"""

import base64
from pathlib import Path
from string import Template
import sys

ASSETS = Path("assets")
MEDIA = Path("media/hero")
# Must match the "**N 个公开硬件项目**" fact in README.md (validate-profile.py checks it).
HARDWARE_PROTOTYPES = 22

# Lane colors follow the homepage: carry #ff6b4a/#ff9a3d, see #6ea8ff/#63ccf8,
# touch #46d89c/#b6ec6a. Each lane's second color is lighter and leans toward
# yellow-green. Light text tokens are darkened for contrast on white; the light
# see_2 keeps at least 3:1 against white like the other graphic tokens.
PALETTES = {
    "dark": {
        "theme_desc": "深色",
        "shell": "#080c13",
        "shell_stroke": "#303846",
        "panel_stroke": "#414b5b",
        "surface_a": "#111722",
        "surface_b": "#0b1018",
        "surface_c": "#121117",
        "grid_line": "#526171",
        "grid_opacity": "0.5",
        "card": "#101722",
        "zone_fill": "#0c121b",
        "ink": "#f3f6fa",
        "muted": "#9da6b4",
        "faint": "#737e8e",
        "packet_fill": "#fff7f2",
        "carry": "#ff6b4a",
        "carry_2": "#ff9a3d",
        "carry_text": "#ff6b4a",
        "see": "#6ea8ff",
        "see_2": "#63ccf8",
        "see_text": "#6ea8ff",
        "touch": "#46d89c",
        "touch_2": "#b6ec6a",
        "touch_text": "#46d89c",
        "board": "#0a1714",
        "led_off": "#183a2e",
        "led_on": "#b6ec6a",
        "pulse": "#b6ec6a",
        "soft": "#c3cad4",
        "tint": "0.12",
        "drive_port": "#161a21",
        "drive_face_a": "#20252d",
        "drive_face_b": "#0d1117",
        "drive_slot": "#232934",
        "drive_slot_stroke": "#4e5663",
        "drive_ink": "#f3f6fa",
        "shine": "#ffffff",
        "shine_opacity": "0.16",
        "shadow_opacity": "0.45",
        "shot_bg": "#161a21",
        "flow_grid_opacity": "0.35",
        "drive_fill": "0.03",
        "flow_tag": "#ff9a3d",
        "link_line": "#45494f",
        "link_head": "#85878b",
        "link_dot": "#e8edf3",
        "cloud_stroke": "#5a5f66",
        "cloud_lit": "#c7ced8",
    },
    "light": {
        "theme_desc": "浅色",
        "shell": "#edf0f4",
        "shell_stroke": "#cbd2dc",
        "panel_stroke": "#cbd2dc",
        "surface_a": "#ffffff",
        "surface_b": "#f7f8fa",
        "surface_c": "#f6f7fb",
        "grid_line": "#8795a3",
        "grid_opacity": "0.42",
        "card": "#ffffff",
        "zone_fill": "#f8fafc",
        "ink": "#18202a",
        "muted": "#5f6876",
        "faint": "#6c7583",
        "packet_fill": "#ffffff",
        "carry": "#e45738",
        "carry_2": "#f08a2c",
        "carry_text": "#c8452a",
        "see": "#3d7be0",
        "see_2": "#1e93cc",
        "see_text": "#2559c4",
        "touch": "#1aa572",
        "touch_2": "#7cc23a",
        "touch_text": "#0b7d50",
        "board": "#f1faf5",
        "led_off": "#cfe9dc",
        "led_on": "#1aa572",
        "pulse": "#1aa572",
        "soft": "#3a4350",
        "tint": "0.08",
        "drive_port": "#eef1f5",
        "drive_face_a": "#ffffff",
        "drive_face_b": "#eef1f6",
        "drive_slot": "#dde3ea",
        "drive_slot_stroke": "#b9c2cd",
        "drive_ink": "#18202a",
        "shine": "#f08a2c",
        "shine_opacity": "0.2",
        "shadow_opacity": "0.16",
        "shot_bg": "#f3f5f8",
        "flow_grid_opacity": "0.3",
        "drive_fill": "0.03",
        "flow_tag": "#c25a12",
        "link_line": "#b9c1cc",
        "link_head": "#7d8794",
        "link_dot": "#4c5562",
        "cloud_stroke": "#9aa3ae",
        "cloud_lit": "#4c5562",
    },
}

# Motion CSS is palette-free so both themes share it byte for byte. Every
# animation sits inside the no-preference guard; reduced motion shows a still frame.

# The hero plays one entrance pass like the homepage entry cards, then holds the final frame:
# cards rise in order, the drive face shines once, the DSH capture pans down and back, and the
# photo deck fans out. Base styles are the final frame, so reduced motion shows it directly.
HERO_STYLE = """  <style>
    text { font-family: Arial, "PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif; }
    .entry-carry, .entry-see, .entry-touch, .drive-shine, .shot-pan, .deck-1, .deck-2, .deck-3 { transform-box: view-box; transform-origin: 0 0; }
    @media (prefers-reduced-motion: no-preference) {
      .entry-carry { animation: entry-in 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) 0.1s both; }
      .entry-see { animation: entry-in 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) 0.25s both; }
      .entry-touch { animation: entry-in 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) 0.4s both; }
      .drive-shine { animation: drive-shine 0.9s cubic-bezier(0.4, 0, 0.2, 1) 0.9s both; }
      .shot-pan { animation: shot-pan 2.8s cubic-bezier(0.4, 0, 0.2, 1) 1.2s both; }
      .deck-1 { animation: deck-1 0.8s cubic-bezier(0.2, 0.8, 0.2, 1) 1.6s both; }
      .deck-2 { animation: deck-2 0.8s cubic-bezier(0.2, 0.8, 0.2, 1) 1.6s both; }
      .deck-3 { animation: deck-3 0.8s cubic-bezier(0.2, 0.8, 0.2, 1) 1.6s both; }
    }
    @keyframes entry-in {
      from { transform: translateY(14px); opacity: 0; }
      to { transform: translateY(0); opacity: 1; }
    }
    @keyframes drive-shine {
      from { transform: translateX(0); }
      to { transform: translateX(172px); }
    }
    @keyframes shot-pan {
      0% { transform: translateY(0); }
      40%, 62% { transform: translateY(-72.5px); }
      100% { transform: translateY(0); }
    }
    @keyframes deck-1 {
      from { transform: rotate(8deg) translate(48px, -6px); }
      to { transform: rotate(0deg) translate(0px, 0px); }
    }
    @keyframes deck-2 {
      from { transform: rotate(-7deg) translate(-48px, -4px); }
      to { transform: rotate(0deg) translate(0px, 0px); }
    }
    @keyframes deck-3 {
      from { transform: rotate(1deg) translate(0px, 5px); }
      to { transform: rotate(0deg) translate(0px, 0px); }
    }
  </style>"""

# Each deck photo is drawn centred on its own origin. The outer group holds the final fanned pose;
# the animated inner group starts with the inverse rotation and offset, so all three begin stacked
# at the deck centre (996, 266) and settle into the pose.
HERO = Template("""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="420" viewBox="0 0 1200 420" role="img" aria-labelledby="title desc">
  <title id="title">Rongyi，独立开发者 · Yi盘创始人</title>
  <desc id="desc">${theme_desc}品牌横幅，三张项目入口卡。Yi盘：U 盘里的 AI 工作台，受控内测，配 U 盘功能示意。DSH Usage：会话、Token 与模型费用，配用量趋势页的运行截图，夹具数据。Hardware Lab：${prototypes} 个硬件原型，配三张历史原型照片：天气时钟、车流自适应交通信号、多传感器手环。</desc>
  <defs>
    <linearGradient id="surface" x1="0" y1="0" x2="1" y2="1">
      <stop stop-color="${surface_a}"/>
      <stop offset="0.6" stop-color="${surface_b}"/>
      <stop offset="1" stop-color="${surface_c}"/>
    </linearGradient>
    <linearGradient id="edge" x1="0" y1="0" x2="1" y2="0">
      <stop stop-color="${carry}" stop-opacity="0.7"/>
      <stop offset="0.3" stop-color="${carry}" stop-opacity="0"/>
      <stop offset="0.72" stop-color="${touch}" stop-opacity="0"/>
      <stop offset="1" stop-color="${touch}" stop-opacity="0.5"/>
    </linearGradient>
    <linearGradient id="gridFade" x1="0" y1="0" x2="1" y2="0">
      <stop stop-color="#ffffff" stop-opacity="0.22"/>
      <stop offset="0.5" stop-color="#ffffff" stop-opacity="0.48"/>
      <stop offset="1" stop-color="#ffffff" stop-opacity="0.78"/>
    </linearGradient>
    <radialGradient id="tintCarry" cx="0.5" cy="1" r="0.75">
      <stop stop-color="${carry}" stop-opacity="${tint}"/>
      <stop offset="1" stop-color="${carry}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="tintSee" cx="0.5" cy="1" r="0.75">
      <stop stop-color="${see}" stop-opacity="${tint}"/>
      <stop offset="1" stop-color="${see}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="tintTouch" cx="0.5" cy="1" r="0.75">
      <stop stop-color="${touch}" stop-opacity="${tint}"/>
      <stop offset="1" stop-color="${touch}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="driveFace" x1="0" y1="0" x2="1" y2="1">
      <stop stop-color="${drive_face_a}"/>
      <stop offset="1" stop-color="${drive_face_b}"/>
    </linearGradient>
    <linearGradient id="shineBand" x1="0" y1="0" x2="1" y2="0">
      <stop stop-color="${shine}" stop-opacity="0"/>
      <stop offset="0.5" stop-color="${shine}" stop-opacity="${shine_opacity}"/>
      <stop offset="1" stop-color="${shine}" stop-opacity="0"/>
    </linearGradient>
    <radialGradient id="driveShadow">
      <stop stop-color="#000000" stop-opacity="${shadow_opacity}"/>
      <stop offset="1" stop-color="#000000" stop-opacity="0"/>
    </radialGradient>
    <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
      <path d="M40 0H0V40" fill="none" stroke="${grid_line}" stroke-width="0.6" opacity="${grid_opacity}"/>
    </pattern>
    <mask id="gridMask" maskUnits="userSpaceOnUse" x="16" y="16" width="1168" height="388">
      <rect x="16" y="16" width="1168" height="388" fill="url(#gridFade)"/>
    </mask>
    <clipPath id="panelClip"><rect x="16" y="16" width="1168" height="388" rx="16"/></clipPath>
    <clipPath id="faceClip"><path d="M150 244H234A13 13 0 0 1 247 257V313A13 13 0 0 1 234 326H150Z"/></clipPath>
    <clipPath id="shotClip"><rect x="414" y="196" width="396" height="144" rx="8"/></clipPath>
    <clipPath id="photoClip"><rect x="-58" y="-43.5" width="116" height="87" rx="8"/></clipPath>
    <filter id="photoShadow" x="-40%" y="-40%" width="180%" height="200%">
      <feDropShadow dx="0" dy="10" stdDeviation="9" flood-color="#000000" flood-opacity="${shadow_opacity}"/>
    </filter>
  </defs>
${style}

  <rect x="0.5" y="0.5" width="1199" height="419" rx="20" fill="${shell}" stroke="${shell_stroke}"/>
  <rect x="16" y="16" width="1168" height="388" rx="16" fill="url(#surface)" stroke="${panel_stroke}"/>
  <g clip-path="url(#panelClip)">
    <rect x="16" y="16" width="1168" height="388" fill="url(#grid)" mask="url(#gridMask)"/>
  </g>
  <rect x="16.5" y="16.5" width="1167" height="387" rx="15.5" fill="none" stroke="url(#edge)" opacity="0.8"/>

  <g transform="translate(48 40)">
    <rect width="46" height="46" rx="12" fill="${card}" stroke="${carry}" stroke-width="2"/>
    <text x="23" y="31" fill="${carry_text}" font-size="24" font-weight="800" text-anchor="middle">R</text>
    <text x="64" y="18" fill="${ink}" font-size="16" font-weight="700" letter-spacing="3">RONGYI</text>
    <text x="64" y="40" fill="${muted}" font-size="13" letter-spacing="1.4">INDIE DEVELOPER · FOUNDER OF YI盘</text>
  </g>

  <g id="entry-carry" class="entry-carry">
    <rect x="48" y="114" width="320" height="274" rx="14" fill="${card}" stroke="${carry}" stroke-opacity="0.32"/>
    <rect x="48" y="114" width="320" height="274" rx="14" fill="url(#tintCarry)"/>
    <text x="72" y="162" fill="${carry_text}" font-size="28" font-weight="800" letter-spacing="-0.6">Yi盘</text>
    <text x="72" y="188" fill="${soft}" font-size="14">U 盘里的 AI 工作台</text>
    <text x="72" y="208" fill="${muted}" font-size="12">受控内测</text>
    <g id="drive">
      <ellipse cx="208" cy="342" rx="108" ry="10" fill="url(#driveShadow)"/>
      <rect x="111" y="244" width="52" height="82" rx="11" fill="${drive_port}" stroke="${carry_2}" stroke-opacity="0.38"/>
      <rect x="150" y="244" width="13" height="82" fill="${drive_port}"/>
      <g fill="${drive_slot}" stroke="${drive_slot_stroke}">
        <rect x="126" y="262" width="6" height="46"/>
        <rect x="135" y="262" width="6" height="46"/>
        <rect x="144" y="262" width="6" height="46"/>
      </g>
      <path d="M150 244H234A13 13 0 0 1 247 257V313A13 13 0 0 1 234 326H150Z" fill="url(#driveFace)" stroke="${carry_2}" stroke-opacity="0.42"/>
      <text x="172" y="294" fill="${drive_ink}" font-size="26" font-weight="800">YI<tspan fill="${carry_text}">盘</tspan></text>
      <g fill="${carry_2}">
        <rect x="174" y="308" width="18" height="3" opacity="0.25"/>
        <rect x="196" y="308" width="18" height="3" opacity="0.55"/>
        <rect x="218" y="308" width="18" height="3"/>
      </g>
      <g clip-path="url(#faceClip)">
        <path class="drive-shine" d="M110 244H150L120 326H80Z" fill="url(#shineBand)"/>
      </g>
    </g>
    <text x="72" y="370" fill="${muted}" font-size="13">功能示意</text>
  </g>

  <g id="entry-see" class="entry-see">
    <rect x="392" y="114" width="440" height="274" rx="14" fill="${card}" stroke="${see}" stroke-opacity="0.32"/>
    <rect x="392" y="114" width="440" height="274" rx="14" fill="url(#tintSee)"/>
    <text x="416" y="162" fill="${see_text}" font-size="28" font-weight="800" letter-spacing="-0.6">DSH Usage</text>
    <text x="416" y="188" fill="${soft}" font-size="14">会话、Token 与模型费用</text>
    <g id="dsh-shot">
      <rect x="414" y="196" width="396" height="144" rx="8" fill="${shot_bg}"/>
      <g clip-path="url(#shotClip)">
        <image class="shot-pan" x="414" y="196" width="396" height="216.5" preserveAspectRatio="xMidYMin slice" href="${dsh_trends}"/>
      </g>
      <rect x="414.5" y="196.5" width="395" height="143" rx="7.5" fill="none" stroke="${see}" stroke-opacity="0.3"/>
    </g>
    <text x="416" y="370" fill="${muted}" font-size="13">运行截图 · 夹具数据</text>
  </g>

  <g id="entry-touch" class="entry-touch">
    <rect x="856" y="114" width="280" height="274" rx="14" fill="${card}" stroke="${touch}" stroke-opacity="0.32"/>
    <rect x="856" y="114" width="280" height="274" rx="14" fill="url(#tintTouch)"/>
    <text x="880" y="162" fill="${touch_text}" font-size="28" font-weight="800" letter-spacing="-0.6">Hardware Lab</text>
    <text x="880" y="188" fill="${soft}" font-size="14">${prototypes} 个硬件原型</text>
    <g id="photo-deck">
      <g transform="translate(948 272) rotate(-8)">
        <g class="deck-1">
          <g filter="url(#photoShadow)"><g clip-path="url(#photoClip)"><image x="-58" y="-43.5" width="116" height="87" preserveAspectRatio="xMidYMid slice" href="${photo_weather}"/></g></g>
          <rect x="-57.5" y="-43" width="115" height="86" rx="7.5" fill="none" stroke="${touch}" stroke-opacity="0.38"/>
        </g>
      </g>
      <g transform="translate(1044 270) rotate(7)">
        <g class="deck-2">
          <g filter="url(#photoShadow)"><g clip-path="url(#photoClip)"><image x="-58" y="-43.5" width="116" height="87" preserveAspectRatio="xMidYMid slice" href="${photo_traffic}"/></g></g>
          <rect x="-57.5" y="-43" width="115" height="86" rx="7.5" fill="none" stroke="${touch}" stroke-opacity="0.38"/>
        </g>
      </g>
      <g transform="translate(996 261) rotate(-1)">
        <g class="deck-3">
          <g filter="url(#photoShadow)"><g clip-path="url(#photoClip)"><image x="-58" y="-43.5" width="116" height="87" preserveAspectRatio="xMidYMid slice" href="${photo_band}"/></g></g>
          <rect x="-57.5" y="-43" width="115" height="86" rx="7.5" fill="none" stroke="${touch}" stroke-opacity="0.38"/>
        </g>
      </g>
    </g>
    <text x="880" y="370" fill="${muted}" font-size="13">历史原型照片</text>
  </g>
</svg>
""")

STRIP_STYLE = """  <style>
    text { font-family: Arial, "PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif; }
    .mono { font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace; }
    .signal, .chip-on, .led-on { opacity: 0; }
    @media (prefers-reduced-motion: no-preference) {
      .sig-in-a { animation: sig-in-a 6s linear infinite; }
      .sig-in-b { animation: sig-in-b 6s linear infinite; }
      .sig-in-c { animation: sig-in-c 6s linear infinite; }
      .chip-on { animation: chip-on 6s ease-in-out infinite; }
      .sig-out-a { animation: sig-out-a 6s linear infinite; }
      .sig-out-b { animation: sig-out-b 6s linear infinite; }
      .sig-out-c { animation: sig-out-c 6s linear infinite; }
      .led-a { animation: led-a 6s ease-in-out infinite; }
      .led-b { animation: led-b 6s ease-in-out infinite; }
      .led-c { animation: led-c 6s ease-in-out infinite; }
    }
    @keyframes sig-in-a {
      0%, 1% { transform: translate(0, 0); opacity: 0; }
      2% { transform: translate(0, 0); opacity: 1; }
      15% { transform: translate(220px, 0); }
      16.5% { transform: translate(238px, 18px); }
      30% { transform: translate(460px, 18px); opacity: 1; }
      31%, 100% { transform: translate(460px, 18px); opacity: 0; }
    }
    @keyframes sig-in-b {
      0%, 3% { transform: translateX(0); opacity: 0; }
      4% { transform: translateX(0); opacity: 1; }
      32% { transform: translateX(460px); opacity: 1; }
      33%, 100% { transform: translateX(460px); opacity: 0; }
    }
    @keyframes sig-in-c {
      0%, 5% { transform: translate(0, 0); opacity: 0; }
      6% { transform: translate(0, 0); opacity: 1; }
      19% { transform: translate(220px, 0); }
      20.5% { transform: translate(238px, -18px); }
      34% { transform: translate(460px, -18px); opacity: 1; }
      35%, 100% { transform: translate(460px, -18px); opacity: 0; }
    }
    @keyframes chip-on {
      0%, 34% { opacity: 0; }
      36%, 46% { opacity: 1; }
      50%, 100% { opacity: 0; }
    }
    @keyframes sig-out-a {
      0%, 45% { transform: translate(0, 0); opacity: 0; }
      46% { transform: translate(0, 0); opacity: 1; }
      58.5% { transform: translate(222px, 0); }
      60% { transform: translate(240px, -18px); }
      72% { transform: translate(450px, -18px); opacity: 1; }
      73%, 100% { transform: translate(450px, -18px); opacity: 0; }
    }
    @keyframes sig-out-b {
      0%, 47% { transform: translateX(0); opacity: 0; }
      48% { transform: translateX(0); opacity: 1; }
      74% { transform: translateX(450px); opacity: 1; }
      75%, 100% { transform: translateX(450px); opacity: 0; }
    }
    @keyframes sig-out-c {
      0%, 49% { transform: translate(0, 0); opacity: 0; }
      50% { transform: translate(0, 0); opacity: 1; }
      62.5% { transform: translate(222px, 0); }
      64% { transform: translate(240px, 18px); }
      76% { transform: translate(450px, 18px); opacity: 1; }
      77%, 100% { transform: translate(450px, 18px); opacity: 0; }
    }
    @keyframes led-a {
      0%, 72% { opacity: 0; }
      74%, 86% { opacity: 1; }
      92%, 100% { opacity: 0; }
    }
    @keyframes led-b {
      0%, 74% { opacity: 0; }
      76%, 88% { opacity: 1; }
      94%, 100% { opacity: 0; }
    }
    @keyframes led-c {
      0%, 76% { opacity: 0; }
      78%, 90% { opacity: 1; }
      96%, 100% { opacity: 0; }
    }
  </style>"""

STRIP = Template("""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="170" viewBox="0 0 1200 170" role="img" aria-labelledby="title desc">
  <title id="title">Hardware Lab 电路走线示意</title>
  <desc id="desc">${theme_desc}电路板横条。左侧三路传感器信号沿走线汇入中间标注 HW LAB 与 ${prototypes} PROTOTYPES 的芯片，芯片亮起后信号继续流向右侧三颗 LED，LED 依次点亮。结构示意，非实物照片。</desc>
  <defs>
    <linearGradient id="surface" x1="0" y1="0" x2="1" y2="1">
      <stop stop-color="${surface_a}"/>
      <stop offset="1" stop-color="${surface_b}"/>
    </linearGradient>
    <linearGradient id="edge" x1="0" y1="0" x2="1" y2="0">
      <stop stop-color="${touch}" stop-opacity="0.6"/>
      <stop offset="0.35" stop-color="${touch}" stop-opacity="0"/>
      <stop offset="0.7" stop-color="${touch_2}" stop-opacity="0"/>
      <stop offset="1" stop-color="${touch_2}" stop-opacity="0.45"/>
    </linearGradient>
    <radialGradient id="ledGlow">
      <stop stop-color="${led_on}" stop-opacity="0.55"/>
      <stop offset="1" stop-color="${led_on}" stop-opacity="0"/>
    </radialGradient>
    <pattern id="dots" width="20" height="20" patternUnits="userSpaceOnUse">
      <circle cx="10" cy="10" r="0.9" fill="${touch}" opacity="0.18"/>
    </pattern>
    <clipPath id="panelClip">
      <rect x="16" y="16" width="1168" height="138" rx="14"/>
    </clipPath>
  </defs>
${style}

  <rect x="0.5" y="0.5" width="1199" height="169" rx="20" fill="${shell}" stroke="${shell_stroke}"/>
  <rect x="16" y="16" width="1168" height="138" rx="14" fill="url(#surface)" stroke="${panel_stroke}"/>
  <g clip-path="url(#panelClip)">
    <rect x="16" y="16" width="1168" height="138" fill="url(#dots)"/>
  </g>
  <rect x="16.5" y="16.5" width="1167" height="137" rx="13.5" fill="none" stroke="url(#edge)" opacity="0.8"/>

  <text x="40" y="46" class="mono" fill="${touch_text}" font-size="14" letter-spacing="1.6">HARDWARE LAB / SENSOR TO OUTPUT</text>
  <text x="1160" y="46" class="mono" fill="${faint}" font-size="13" letter-spacing="1" text-anchor="end">ESP32 · STM32 · RPi · ARDUINO</text>

  <g id="traces-in" fill="none" stroke="${touch}" stroke-opacity="0.5" stroke-width="2" stroke-linejoin="round">
    <path d="M60 82H280L298 100H520"/>
    <path d="M60 108H520"/>
    <path d="M60 134H280L298 116H520"/>
  </g>
  <g id="traces-out" fill="none" stroke="${touch}" stroke-opacity="0.5" stroke-width="2" stroke-linejoin="round">
    <path d="M680 100H902L920 82H1130"/>
    <path d="M680 108H1130"/>
    <path d="M680 116H902L920 134H1130"/>
  </g>
  <g fill="${zone_fill}" stroke="${touch}" stroke-width="2">
    <circle cx="54" cy="82" r="6"/>
    <circle cx="54" cy="108" r="6"/>
    <circle cx="54" cy="134" r="6"/>
  </g>
  <g fill="${touch}">
    <circle cx="280" cy="82" r="3.5"/>
    <circle cx="280" cy="134" r="3.5"/>
    <circle cx="920" cy="82" r="3.5"/>
    <circle cx="920" cy="134" r="3.5"/>
  </g>
  <g fill="${board}" stroke="${touch}" stroke-opacity="0.6">
    <rect x="170" y="100" width="40" height="16" rx="2"/>
    <rect x="990" y="100" width="40" height="16" rx="2"/>
  </g>

  <g id="strip-chip">
    <path d="M540 72V64M560 72V64M580 72V64M600 72V64M620 72V64M640 72V64M660 72V64M540 144V152M560 144V152M580 144V152M600 144V152M620 144V152M640 144V152M660 144V152" stroke="${touch}" stroke-opacity="0.6" stroke-width="2"/>
    <rect x="520" y="72" width="160" height="72" rx="6" fill="${board}" stroke="${touch}" stroke-width="1.5"/>
    <rect class="chip-on" x="513" y="65" width="174" height="86" rx="11" fill="none" stroke="${touch}" stroke-width="2"/>
    <text x="600" y="104" fill="${ink}" font-size="16" font-weight="800" letter-spacing="1" text-anchor="middle">HW LAB</text>
    <text class="mono" x="600" y="126" fill="${touch_text}" font-size="12" letter-spacing="1" text-anchor="middle">${prototypes} PROTOTYPES</text>
  </g>

  <g fill="${led_off}" stroke="${touch}" stroke-opacity="0.5">
    <circle cx="1138" cy="82" r="6"/>
    <circle cx="1138" cy="108" r="6"/>
    <circle cx="1138" cy="134" r="6"/>
  </g>
  <g class="led-on led-a"><circle cx="1138" cy="82" r="16" fill="url(#ledGlow)"/><circle cx="1138" cy="82" r="6" fill="${led_on}"/></g>
  <g class="led-on led-b"><circle cx="1138" cy="108" r="16" fill="url(#ledGlow)"/><circle cx="1138" cy="108" r="6" fill="${led_on}"/></g>
  <g class="led-on led-c"><circle cx="1138" cy="134" r="16" fill="url(#ledGlow)"/><circle cx="1138" cy="134" r="6" fill="${led_on}"/></g>

  <g fill="${packet_fill}" stroke="${pulse}" stroke-width="2">
    <circle class="signal sig-in-a" cx="60" cy="82" r="3.5"/>
    <circle class="signal sig-in-b" cx="60" cy="108" r="3.5"/>
    <circle class="signal sig-in-c" cx="60" cy="134" r="3.5"/>
    <circle class="signal sig-out-a" cx="680" cy="100" r="3.5"/>
    <circle class="signal sig-out-b" cx="680" cy="108" r="3.5"/>
    <circle class="signal sig-out-c" cx="680" cy="116" r="3.5"/>
  </g>
</svg>
""")


# The Yi盘 diagram follows the homepage: the three nodes sit inside a dashed "U 盘内"
# boundary and the cloud model stays outside it. One 8s loop lights each step in causal
# order: context, retrieve, workspace, request, cloud, result, workspace, generate,
# output, then the record rail back to the context. Reduced motion shows the still diagram.
FLOW_STYLE = """  <style>
    text { font-family: Arial, "PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif; }
    .lit, .packet { opacity: 0; }
    @media (prefers-reduced-motion: no-preference) {
      .lit-context { animation: lit-context 8s ease-in-out infinite; }
      .packet-retrieve { animation: packet-retrieve 8s linear infinite; }
      .lit-workspace-in { animation: lit-workspace-in 8s ease-in-out infinite; }
      .packet-request { animation: packet-request 8s linear infinite; }
      .lit-cloud { animation: lit-cloud 8s ease-in-out infinite; }
      .packet-result { animation: packet-result 8s linear infinite; }
      .lit-workspace-back { animation: lit-workspace-back 8s ease-in-out infinite; }
      .packet-generate { animation: packet-generate 8s linear infinite; }
      .lit-output { animation: lit-output 8s ease-in-out infinite; }
      .lit-rail { animation: lit-rail 8s ease-in-out infinite; }
    }
    @keyframes lit-context {
      0% { opacity: 0; }
      2%, 7% { opacity: 1; }
      9%, 100% { opacity: 0; }
    }
    @keyframes packet-retrieve {
      0%, 8% { opacity: 0; transform: translateY(0); }
      9% { opacity: 1; transform: translateY(0); }
      17% { opacity: 1; transform: translateY(38px); }
      18%, 100% { opacity: 0; transform: translateY(38px); }
    }
    @keyframes lit-workspace-in {
      0%, 16% { opacity: 0; }
      18%, 23% { opacity: 1; }
      25%, 100% { opacity: 0; }
    }
    @keyframes packet-request {
      0%, 24% { opacity: 0; transform: translateX(0); }
      25% { opacity: 1; transform: translateX(0); }
      33% { opacity: 1; transform: translateX(86px); }
      34%, 100% { opacity: 0; transform: translateX(86px); }
    }
    @keyframes lit-cloud {
      0%, 32% { opacity: 0; }
      34%, 39% { opacity: 1; }
      41%, 100% { opacity: 0; }
    }
    @keyframes packet-result {
      0%, 40% { opacity: 0; transform: translateX(0); }
      41% { opacity: 1; transform: translateX(0); }
      49% { opacity: 1; transform: translateX(-86px); }
      50%, 100% { opacity: 0; transform: translateX(-86px); }
    }
    @keyframes lit-workspace-back {
      0%, 48% { opacity: 0; }
      50%, 55% { opacity: 1; }
      57%, 100% { opacity: 0; }
    }
    @keyframes packet-generate {
      0%, 56% { opacity: 0; transform: translateY(0); }
      57% { opacity: 1; transform: translateY(0); }
      65% { opacity: 1; transform: translateY(38px); }
      66%, 100% { opacity: 0; transform: translateY(38px); }
    }
    @keyframes lit-output {
      0%, 64% { opacity: 0; }
      66%, 71% { opacity: 1; }
      73%, 100% { opacity: 0; }
    }
    @keyframes lit-rail {
      0%, 72% { opacity: 0; }
      74%, 83% { opacity: 1; }
      85%, 100% { opacity: 0; }
    }
  </style>"""

FLOW = Template("""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="492" viewBox="0 0 1200 492" role="img" aria-labelledby="title desc">
  <title id="title">Yi盘结构示意</title>
  <desc id="desc">${theme_desc}结构示意，非产品截图。虚线框表示 U 盘内：盘内资料与任务（Inbox 确认后写入长期知识）经检索供 Yi盘工作台使用，受管 Agent 处理当前任务；生成的产出与任务记录留在盘内，随盘带走，并经记录与沉淀回到盘内资料，供下一次继续。框外是云端模型：工作台按需请求，模型按需推理后返回结果。</desc>
  <defs>
    <linearGradient id="surface" x1="0" y1="0" x2="1" y2="1">
      <stop stop-color="${surface_a}"/>
      <stop offset="1" stop-color="${surface_b}"/>
    </linearGradient>
    <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
      <path d="M40 0H0V40" fill="none" stroke="${grid_line}" stroke-width="0.6" opacity="${flow_grid_opacity}"/>
    </pattern>
    <clipPath id="panelClip"><rect x="1" y="1" width="1198" height="490" rx="18"/></clipPath>
  </defs>
${style}

  <rect x="0.5" y="0.5" width="1199" height="491" rx="18" fill="url(#surface)" stroke="${shell_stroke}"/>
  <g clip-path="url(#panelClip)">
    <rect x="1" y="1" width="1198" height="490" fill="url(#grid)"/>
  </g>

  <g transform="translate(0 -28)">
  <g id="drive">
    <rect id="drive-boundary" x="180.5" y="84.5" width="599" height="407" rx="18" fill="${carry}" fill-opacity="${drive_fill}" stroke="${carry}" stroke-opacity="0.45" stroke-dasharray="6 5"/>
    <text x="776" y="72" fill="${flow_tag}" font-size="15" text-anchor="end">U 盘内</text>

    <g id="continuity-rail">
      <path d="M232 428H212A8 8 0 0 1 204 420V156A8 8 0 0 1 212 148H225" fill="none" stroke="${carry}" stroke-opacity="0.4"/>
      <path d="M225 143.5V152.5L232 148Z" fill="${carry}" fill-opacity="0.65"/>
      <text fill="${faint}" font-size="13" text-anchor="middle"><tspan x="218" y="253">记</tspan><tspan x="218" y="273">录</tspan><tspan x="218" y="293">·</tspan><tspan x="218" y="313">沉</tspan><tspan x="218" y="333">淀</tspan></text>
      <g class="lit lit-rail">
        <path d="M232 428H212A8 8 0 0 1 204 420V156A8 8 0 0 1 212 148H225" fill="none" stroke="${carry_2}" stroke-width="1.5"/>
        <path d="M225 143.5V152.5L232 148Z" fill="${carry_2}"/>
      </g>
    </g>

    <g id="flow-context">
      <rect x="232.5" y="106.5" width="519" height="83" rx="11.5" fill="${card}" stroke="${carry}" stroke-opacity="0.32"/>
      <g class="lit lit-context">
        <rect x="229" y="103" width="526" height="90" rx="15" fill="none" stroke="${carry}" stroke-opacity="0.18" stroke-width="4"/>
        <rect x="232.5" y="106.5" width="519" height="83" rx="11.5" fill="none" stroke="${carry}" stroke-width="1.5"/>
      </g>
      <text x="256" y="142" fill="${ink}" font-size="21" font-weight="700">盘内资料与任务</text>
      <text x="256" y="168" fill="${muted}" font-size="15">Inbox 确认后写入长期知识</text>
    </g>

    <g id="step-retrieve">
      <path d="M272 194V237" stroke="${carry}" stroke-opacity="0.45"/>
      <path d="M267 236H277L272 243Z" fill="${carry}" fill-opacity="0.7"/>
      <text x="292" y="223" fill="${faint}" font-size="14">检索 / 继续</text>
      <g class="packet packet-retrieve" fill="${carry_2}">
        <circle cx="272" cy="196" r="9" opacity="0.22"/>
        <circle cx="272" cy="196" r="4.5"/>
      </g>
    </g>

    <g id="flow-workspace">
      <rect x="232.5" y="246.5" width="519" height="83" rx="11.5" fill="${card}" stroke="${carry}" stroke-opacity="0.32"/>
      <g class="lit lit-workspace-in">
        <rect x="229" y="243" width="526" height="90" rx="15" fill="none" stroke="${carry}" stroke-opacity="0.18" stroke-width="4"/>
        <rect x="232.5" y="246.5" width="519" height="83" rx="11.5" fill="none" stroke="${carry}" stroke-width="1.5"/>
      </g>
      <g class="lit lit-workspace-back">
        <rect x="229" y="243" width="526" height="90" rx="15" fill="none" stroke="${carry}" stroke-opacity="0.18" stroke-width="4"/>
        <rect x="232.5" y="246.5" width="519" height="83" rx="11.5" fill="none" stroke="${carry}" stroke-width="1.5"/>
      </g>
      <text x="256" y="282" fill="${ink}" font-size="21" font-weight="700">Yi盘工作台</text>
      <text x="256" y="308" fill="${muted}" font-size="15">受管 Agent 处理当前任务</text>
    </g>

    <g id="step-generate">
      <path d="M272 334V377" stroke="${carry}" stroke-opacity="0.45"/>
      <path d="M267 376H277L272 383Z" fill="${carry}" fill-opacity="0.7"/>
      <text x="292" y="363" fill="${faint}" font-size="14">生成 / 记录</text>
      <g class="packet packet-generate" fill="${carry_2}">
        <circle cx="272" cy="336" r="9" opacity="0.22"/>
        <circle cx="272" cy="336" r="4.5"/>
      </g>
    </g>

    <g id="flow-output">
      <rect x="232.5" y="386.5" width="519" height="83" rx="11.5" fill="${card}" stroke="${carry}" stroke-opacity="0.32"/>
      <g class="lit lit-output">
        <rect x="229" y="383" width="526" height="90" rx="15" fill="none" stroke="${carry}" stroke-opacity="0.18" stroke-width="4"/>
        <rect x="232.5" y="386.5" width="519" height="83" rx="11.5" fill="none" stroke="${carry}" stroke-width="1.5"/>
      </g>
      <text x="256" y="422" fill="${ink}" font-size="21" font-weight="700">产出与任务记录</text>
      <text x="256" y="448" fill="${muted}" font-size="15">留在盘内，随盘带走</text>
    </g>
  </g>

  <g id="cloud-branch">
    <g id="link-request">
      <path d="M752 276H849" stroke="${link_line}"/>
      <path d="M848 271.5V280.5L855 276Z" fill="${link_head}"/>
      <text x="804" y="263" fill="${faint}" font-size="14" text-anchor="middle">按需请求</text>
      <g class="packet packet-request" fill="${link_dot}">
        <circle cx="758" cy="276" r="8" opacity="0.2"/>
        <circle cx="758" cy="276" r="4"/>
      </g>
    </g>
    <g id="link-result">
      <path d="M759 300H856" stroke="${link_line}"/>
      <path d="M760 295.5V304.5L753 300Z" fill="${link_head}"/>
      <text x="804" y="324" fill="${faint}" font-size="14" text-anchor="middle">返回结果</text>
      <g class="packet packet-result" fill="${link_dot}">
        <circle cx="850" cy="300" r="8" opacity="0.2"/>
        <circle cx="850" cy="300" r="4"/>
      </g>
    </g>
    <g id="flow-cloud">
      <rect x="856.5" y="242.5" width="167" height="91" rx="13.5" fill="${card}" stroke="${cloud_stroke}" stroke-dasharray="6 5"/>
      <g class="lit lit-cloud">
        <rect x="853" y="239" width="174" height="98" rx="17" fill="none" stroke="${cloud_lit}" stroke-opacity="0.18" stroke-width="4"/>
        <rect x="856.5" y="242.5" width="167" height="91" rx="13.5" fill="none" stroke="${cloud_lit}" stroke-width="1.5" stroke-dasharray="6 5"/>
      </g>
      <text x="940" y="282" fill="${ink}" font-size="20" font-weight="700" text-anchor="middle">云端模型</text>
      <text x="940" y="308" fill="${muted}" font-size="14" text-anchor="middle">按需推理</text>
    </g>
  </g>
  </g>
</svg>
""")


def media_uri(name: str) -> str:
    data = base64.b64encode((MEDIA / name).read_bytes()).decode("ascii")
    return f"data:image/webp;base64,{data}"


def hero_media(theme: str) -> dict[str, str]:
    return {
        "dsh_trends": media_uri(f"dsh-trends-{theme}.webp"),
        "photo_weather": media_uri("esp32-weather-clock.webp"),
        "photo_traffic": media_uri("adaptive-traffic-signal-system.webp"),
        "photo_band": media_uri("esp32-c3-smart-band.webp"),
    }


def render(template: Template, style: str, palette: dict[str, str], extra: dict[str, str] | None = None) -> str:
    tokens = dict(palette)
    tokens.update(style=style, prototypes=str(HARDWARE_PROTOTYPES))
    tokens.update(extra or {})
    return template.substitute(tokens)


def main() -> int:
    check = "--check" in sys.argv[1:]
    outputs = {
        "hero": (HERO, HERO_STYLE, hero_media),
        "yipan-flow": (FLOW, FLOW_STYLE, lambda theme: {}),
        "hardware-strip": (STRIP, STRIP_STYLE, lambda theme: {}),
    }
    stale: list[str] = []
    for stem, (template, style, extra) in outputs.items():
        for theme, palette in PALETTES.items():
            path = ASSETS / f"{stem}-{theme}.svg"
            svg = render(template, style, palette, extra(theme))
            if check:
                if not path.exists() or path.read_text(encoding="utf-8") != svg:
                    stale.append(str(path))
            else:
                path.write_text(svg, encoding="utf-8")
                print(f"wrote {path}")
    if stale:
        print(
            "Generated SVG assets are out of date; run python3 scripts/render-svg.py:\n- " + "\n- ".join(stale),
            file=sys.stderr,
        )
        return 1
    if check:
        print("Generated SVG assets match scripts/render-svg.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
