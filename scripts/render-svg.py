#!/usr/bin/env python3
"""Render profile SVGs and the marked native npm snapshot in README.md.

Dark/light pairs share geometry; width/reduced-motion sources use adaptive
SVGs so GitHub's manual theme rewrite cannot erase their media guards.
The hero embeds real WebP media because GitHub's SVG CSP blocks external images.
Run this script after editing templates or npm data; CI checks generated output.
"""

import base64
import json
from pathlib import Path
import re
from string import Template
import sys
from xml.sax.saxutils import escape

from npm_snapshot import replace_snapshot

ASSETS = Path("assets")
MEDIA = Path("media/hero")
NPM_STATS = Path("data/npm-stats.json")
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
        "page_bg": "#0d1117",
        "wash": "0.085",
        "glow": "0.1",
        "fig_bg": "#080b10",
        "fig_stroke": "#262c35",
        "fig_grid": "#141920",
        "cta_ink": "#17100d",
        "tag_fill": "#12161d",
        "tag_stroke": "#2b3038",
        "see_wash": "0.085",
        "see_glow": "0.1",
        "see_ink": "#0b1020",
        "metric_bg": "#0a0e15",
        "tab_bg": "#0b0f16",
        "pill_fill": "#142033",
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
        "page_bg": "#ffffff",
        "wash": "0.06",
        "glow": "0.07",
        "fig_bg": "#fbfcfd",
        "fig_stroke": "#dfe3e8",
        "fig_grid": "#eef1f5",
        "cta_ink": "#17100d",
        "tag_fill": "#f7f8fa",
        "tag_stroke": "#d5dbe4",
        "see_wash": "0.06",
        "see_glow": "0.07",
        "see_ink": "#0b1020",
        "metric_bg": "#ffffff",
        "tab_bg": "#f4f6f9",
        "pill_fill": "#e8f0fd",
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
      .entry-carry { animation: entry-in 0.6s cubic-bezier(0.16, 1, 0.3, 1) 0.1s both; }
      .entry-see { animation: entry-in 0.6s cubic-bezier(0.16, 1, 0.3, 1) 0.25s both; }
      .entry-touch { animation: entry-in 0.6s cubic-bezier(0.16, 1, 0.3, 1) 0.4s both; }
      .drive-shine { animation: drive-shine 0.85s cubic-bezier(0.25, 1, 0.5, 1) 0.9s both; }
      .shot-pan { animation: shot-pan 2.8s cubic-bezier(0.4, 0, 0.2, 1) 1.2s both; }
      .deck-1 { animation: deck-1 0.75s cubic-bezier(0.16, 1, 0.3, 1) 1.6s both; }
      .deck-2 { animation: deck-2 0.75s cubic-bezier(0.16, 1, 0.3, 1) 1.75s both; }
      .deck-3 { animation: deck-3 0.75s cubic-bezier(0.16, 1, 0.3, 1) 1.9s both; }
    }
    @keyframes entry-in {
      0% { transform: translateY(14px); opacity: 0; }
      75% { transform: translateY(-1px); opacity: 1; }
      100% { transform: translateY(0); opacity: 1; }
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
      0% { transform: rotate(8deg) translate(48px, -6px); }
      80% { transform: rotate(-0.8deg) translate(-2px, 0.5px); }
      100% { transform: rotate(0deg) translate(0px, 0px); }
    }
    @keyframes deck-2 {
      0% { transform: rotate(-7deg) translate(-48px, -4px); }
      80% { transform: rotate(0.8deg) translate(2px, 0.5px); }
      100% { transform: rotate(0deg) translate(0px, 0px); }
    }
    @keyframes deck-3 {
      0% { transform: rotate(1deg) translate(0px, 5px); }
      80% { transform: rotate(-0.3deg) translate(0px, -1px); }
      100% { transform: rotate(0deg) translate(0px, 0px); }
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
      14% { transform: translate(210px, 0); }
      15% { transform: translate(220px, 0); }
      16.5% { transform: translate(238px, 18px); }
      17.5% { transform: translate(248px, 18px); }
      30% { transform: translate(460px, 18px); opacity: 1; }
      31%, 100% { transform: translate(460px, 18px); opacity: 0; }
    }
    @keyframes sig-in-b {
      0%, 3% { transform: translateX(0); opacity: 0; }
      4% { transform: translateX(0); opacity: 1; }
      10% { transform: translateX(70px); }
      18% { transform: translateX(230px); }
      26% { transform: translateX(390px); }
      32% { transform: translateX(460px); opacity: 1; }
      33%, 100% { transform: translateX(460px); opacity: 0; }
    }
    @keyframes sig-in-c {
      0%, 5% { transform: translate(0, 0); opacity: 0; }
      6% { transform: translate(0, 0); opacity: 1; }
      18% { transform: translate(210px, 0); }
      19% { transform: translate(220px, 0); }
      20.5% { transform: translate(238px, -18px); }
      21.5% { transform: translate(248px, -18px); }
      34% { transform: translate(460px, -18px); opacity: 1; }
      35%, 100% { transform: translate(460px, -18px); opacity: 0; }
    }
    @keyframes chip-on {
      0%, 34% { opacity: 0; }
      36% { opacity: 1; }
      37.5% { opacity: 0.72; }
      39%, 46% { opacity: 1; }
      50%, 100% { opacity: 0; }
    }
    @keyframes sig-out-a {
      0%, 45% { transform: translate(0, 0); opacity: 0; }
      46% { transform: translate(0, 0); opacity: 1; }
      57.5% { transform: translate(212px, 0); }
      58.5% { transform: translate(222px, 0); }
      60% { transform: translate(240px, -18px); }
      61% { transform: translate(250px, -18px); }
      72% { transform: translate(450px, -18px); opacity: 1; }
      73%, 100% { transform: translate(450px, -18px); opacity: 0; }
    }
    @keyframes sig-out-b {
      0%, 47% { transform: translateX(0); opacity: 0; }
      48% { transform: translateX(0); opacity: 1; }
      54% { transform: translateX(65px); }
      62% { transform: translateX(225px); }
      70% { transform: translateX(385px); }
      74% { transform: translateX(450px); opacity: 1; }
      75%, 100% { transform: translateX(450px); opacity: 0; }
    }
    @keyframes sig-out-c {
      0%, 49% { transform: translate(0, 0); opacity: 0; }
      50% { transform: translate(0, 0); opacity: 1; }
      61.5% { transform: translate(212px, 0); }
      62.5% { transform: translate(222px, 0); }
      64% { transform: translate(240px, 18px); }
      65% { transform: translate(250px, 18px); }
      76% { transform: translate(450px, 18px); opacity: 1; }
      77%, 100% { transform: translate(450px, 18px); opacity: 0; }
    }
    @keyframes led-a {
      0%, 72% { opacity: 0; }
      74%, 80% { opacity: 1; }
      83% { opacity: 0.72; }
      86% { opacity: 0.38; }
      89% { opacity: 0.12; }
      92%, 100% { opacity: 0; }
    }
    @keyframes led-b {
      0%, 74% { opacity: 0; }
      76%, 82% { opacity: 1; }
      85% { opacity: 0.72; }
      88% { opacity: 0.38; }
      91% { opacity: 0.12; }
      94%, 100% { opacity: 0; }
    }
    @keyframes led-c {
      0%, 76% { opacity: 0; }
      78%, 84% { opacity: 1; }
      87% { opacity: 0.72; }
      90% { opacity: 0.38; }
      93% { opacity: 0.12; }
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


# The Yi盘 card follows the homepage featured card: summary, tags, the repo button and
# status on the left, the structure diagram inset on the right. In the diagram the three
# nodes sit inside a dashed "U 盘内" boundary and the cloud model stays outside it. One 8s
# loop lights each step in causal order: context, retrieve, workspace, request, cloud,
# result, workspace, generate, output, then a packet runs the record rail back to the
# context. The status dot breathes and the button shines once per loop. Reduced motion
# shows the still card.
FLOW_STYLE = """  <style>
    text { font-family: Arial, "PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif; }
    .lit, .packet, .pulse-ring { opacity: 0; }
    .pulse-ring { transform-box: fill-box; transform-origin: center; }
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
      .packet-rail { animation: packet-rail 8s linear infinite; }
      .status-pulse { animation: status-pulse 8s ease-out infinite; }
      .cta-shine { animation: cta-shine 8s ease-in-out infinite; }
    }
    @keyframes lit-context {
      0% { opacity: 0; }
      2%, 7% { opacity: 1; }
      9%, 100% { opacity: 0; }
    }
    @keyframes packet-retrieve {
      0%, 8% { opacity: 0; transform: translateY(0); }
      9% { opacity: 1; transform: translateY(0); }
      11% { transform: translateY(3px); }
      13% { transform: translateY(12px); }
      15% { transform: translateY(24px); }
      17% { opacity: 1; transform: translateY(32px); }
      18%, 100% { opacity: 0; transform: translateY(32px); }
    }
    @keyframes lit-workspace-in {
      0%, 16% { opacity: 0; }
      18% { opacity: 1; }
      20.5% { opacity: 0.78; }
      23% { opacity: 1; }
      25%, 100% { opacity: 0; }
    }
    @keyframes packet-request {
      0%, 24% { opacity: 0; transform: translateX(0); }
      25% { opacity: 1; transform: translateX(0); }
      27% { transform: translateX(8px); }
      29% { transform: translateX(32px); }
      31% { transform: translateX(62px); }
      33% { opacity: 1; transform: translateX(76px); }
      34%, 100% { opacity: 0; transform: translateX(76px); }
    }
    @keyframes lit-cloud {
      0%, 32% { opacity: 0; }
      34% { opacity: 1; }
      36% { opacity: 0.72; }
      37.5% { opacity: 1; }
      39% { opacity: 0.88; }
      41%, 100% { opacity: 0; }
    }
    @keyframes packet-result {
      0%, 40% { opacity: 0; transform: translateX(0); }
      41% { opacity: 1; transform: translateX(0); }
      43% { transform: translateX(-8px); }
      45% { transform: translateX(-32px); }
      47% { transform: translateX(-62px); }
      49% { opacity: 1; transform: translateX(-76px); }
      50%, 100% { opacity: 0; transform: translateX(-76px); }
    }
    @keyframes lit-workspace-back {
      0%, 48% { opacity: 0; }
      50% { opacity: 1; }
      52.5% { opacity: 0.78; }
      55% { opacity: 1; }
      57%, 100% { opacity: 0; }
    }
    @keyframes packet-generate {
      0%, 56% { opacity: 0; transform: translateY(0); }
      57% { opacity: 1; transform: translateY(0); }
      59% { transform: translateY(3px); }
      61% { transform: translateY(12px); }
      63% { transform: translateY(24px); }
      65% { opacity: 1; transform: translateY(32px); }
      66%, 100% { opacity: 0; transform: translateY(32px); }
    }
    @keyframes lit-output {
      0%, 64% { opacity: 0; }
      66% { opacity: 1; }
      68.5% { opacity: 0.82; }
      71% { opacity: 1; }
      73%, 100% { opacity: 0; }
    }
    @keyframes lit-rail {
      0%, 72% { opacity: 0; }
      74% { opacity: 0.65; }
      76%, 81% { opacity: 1; }
      83% { opacity: 0.75; }
      85%, 100% { opacity: 0; }
    }
    @keyframes packet-rail {
      0%, 74% { opacity: 0; transform: translateY(0); }
      75% { opacity: 1; transform: translateY(0); }
      77% { transform: translateY(-16px); }
      79% { transform: translateY(-74px); }
      81% { transform: translateY(-148px); }
      83% { opacity: 1; transform: translateY(-186px); }
      84%, 100% { opacity: 0; transform: translateY(-186px); }
    }
    @keyframes status-pulse {
      0%, 22%, 25%, 47%, 50%, 72%, 75%, 97%, 100% { opacity: 0; transform: scale(1); }
      1%, 26%, 51%, 76% { opacity: 0.55; transform: scale(1); }
      21%, 46%, 71%, 96% { opacity: 0; transform: scale(3); }
    }
    @keyframes cta-shine {
      0%, 86% { transform: translateX(0); }
      96%, 100% { transform: translateX(300px); }
    }
  </style>"""

FLOW = Template("""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="476" viewBox="0 0 1200 476" role="img" aria-labelledby="title desc">
  <title id="title">Yi盘：U 盘里的 AI 工作台</title>
  <desc id="desc">${theme_desc}Yi盘项目卡。左栏：资料、任务记录和产出保存在盘内，智能处理主要调用云端模型；标签 U 盘存储、云端模型；"查看公开仓库"按钮；状态受控内测。右栏是结构示意，非产品截图：虚线框表示 U 盘内，盘内资料与任务（Inbox 确认后写入长期知识）经检索供 Yi盘工作台使用，受管 Agent 处理当前任务；生成的产出与任务记录留在盘内，随盘带走，并经记录与沉淀回到盘内资料。框外是云端模型：工作台按需请求，模型按需推理后返回结果。</desc>
  <defs>
    <linearGradient id="cardWash" x1="0" y1="0" x2="1" y2="0.6">
      <stop stop-color="${carry}" stop-opacity="${wash}"/>
      <stop offset="0.48" stop-color="#ffffff" stop-opacity="0.018"/>
      <stop offset="1" stop-color="${carry}" stop-opacity="0.03"/>
    </linearGradient>
    <radialGradient id="cardGlow" cx="0.16" cy="0.92" r="0.55">
      <stop stop-color="${carry}" stop-opacity="${glow}"/>
      <stop offset="1" stop-color="${carry}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="ctaFill" x1="0" y1="0" x2="1" y2="0.2">
      <stop stop-color="${carry}"/>
      <stop offset="1" stop-color="${carry_2}"/>
    </linearGradient>
    <linearGradient id="ctaShine" x1="0" y1="0" x2="1" y2="0">
      <stop stop-color="#ffffff" stop-opacity="0"/>
      <stop offset="0.5" stop-color="#ffffff" stop-opacity="0.45"/>
      <stop offset="1" stop-color="#ffffff" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="trailDown" x1="0" y1="0" x2="0" y2="1">
      <stop stop-color="${carry_2}" stop-opacity="0"/>
      <stop offset="1" stop-color="${carry_2}" stop-opacity="0.85"/>
    </linearGradient>
    <linearGradient id="trailUp" x1="0" y1="0" x2="0" y2="1">
      <stop stop-color="${carry_2}" stop-opacity="0.85"/>
      <stop offset="1" stop-color="${carry_2}" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="trailRight" x1="0" y1="0" x2="1" y2="0">
      <stop stop-color="${link_dot}" stop-opacity="0"/>
      <stop offset="1" stop-color="${link_dot}" stop-opacity="0.8"/>
    </linearGradient>
    <linearGradient id="trailLeft" x1="0" y1="0" x2="1" y2="0">
      <stop stop-color="${link_dot}" stop-opacity="0.8"/>
      <stop offset="1" stop-color="${link_dot}" stop-opacity="0"/>
    </linearGradient>
    <pattern id="figGrid" width="22" height="22" patternUnits="userSpaceOnUse">
      <path d="M22 0H0V22" fill="none" stroke="${fig_grid}"/>
    </pattern>
    <clipPath id="figClip"><rect x="489" y="49" width="662" height="378" rx="13.5"/></clipPath>
    <filter id="ctaGlow" x="-30%" y="-40%" width="160%" height="230%">
      <feDropShadow dx="0" dy="12" stdDeviation="14" flood-color="${carry}" flood-opacity="0.18"/>
    </filter>
    <clipPath id="ctaClip"><rect x="72" y="299" width="200" height="60" rx="14"/></clipPath>
  </defs>
${style}

  <rect x="0.5" y="0.5" width="1199" height="475" rx="18" fill="${page_bg}"/>
  <rect x="0.5" y="0.5" width="1199" height="475" rx="18" fill="url(#cardWash)"/>
  <rect x="0.5" y="0.5" width="1199" height="475" rx="18" fill="url(#cardGlow)"/>
  <rect x="0.5" y="0.5" width="1199" height="475" rx="18" fill="none" stroke="${carry}" stroke-opacity="0.26"/>

  <g transform="translate(0 -22)">
  <g id="card-copy">
    <text x="72" y="179" fill="${soft}" font-size="23">资料、任务记录和产出保存在盘内，</text>
    <text x="72" y="219" fill="${soft}" font-size="23">智能处理主要调用云端模型。</text>
  </g>
  <g id="card-tags" font-size="15" text-anchor="middle">
    <rect x="72.5" y="241.5" width="91" height="33" rx="8.5" fill="${tag_fill}" stroke="${tag_stroke}"/>
    <text x="118" y="263" fill="${muted}">U 盘存储</text>
    <rect x="173.5" y="241.5" width="87" height="33" rx="8.5" fill="${tag_fill}" stroke="${tag_stroke}"/>
    <text x="217" y="263" fill="${muted}">云端模型</text>
  </g>
  <g id="card-cta">
    <rect x="72" y="299" width="200" height="60" rx="14" fill="url(#ctaFill)" filter="url(#ctaGlow)"/>
    <g clip-path="url(#ctaClip)">
      <path class="cta-shine" d="M24 299H64L44 359H4Z" fill="url(#ctaShine)"/>
    </g>
    <text x="96" y="336" fill="${cta_ink}" font-size="19" font-weight="700">查看公开仓库</text>
    <path d="M231 337L244 324M234 324H244V334" fill="none" stroke="${cta_ink}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  </g>
  <g id="card-status">
    <circle cx="298" cy="329" r="8" fill="${carry}" opacity="0.18"/>
    <circle class="pulse-ring status-pulse" cx="298" cy="329" r="4" fill="${carry}"/>
    <circle cx="298" cy="329" r="4" fill="${carry}"/>
    <text x="313" y="334" fill="${muted}" font-size="15">受控内测</text>
  </g>
  </g>

  <g id="flow-figure">
    <rect x="488.5" y="48.5" width="663" height="379" rx="14" fill="${fig_bg}" stroke="${fig_stroke}"/>
    <g clip-path="url(#figClip)">
      <rect x="489" y="49" width="662" height="378" fill="url(#figGrid)"/>
    </g>

    <g id="cloud-branch">
      <g id="link-request">
        <path d="M916 240H999" stroke="${link_line}"/>
        <path d="M998 235.5V244.5L1005 240Z" fill="${link_head}"/>
        <text x="971" y="228" fill="${faint}" font-size="13" text-anchor="middle">按需请求</text>
        <g class="packet packet-request">
          <rect x="906" y="238.5" width="16" height="3" rx="1.5" fill="url(#trailRight)"/>
          <circle cx="922" cy="240" r="7" fill="${link_dot}" opacity="0.2"/>
          <circle cx="922" cy="240" r="3.5" fill="${link_dot}"/>
        </g>
      </g>
      <g id="link-result">
        <path d="M923 264H1007" stroke="${link_line}"/>
        <path d="M923 259.5V268.5L916 264Z" fill="${link_head}"/>
        <text x="971" y="285" fill="${faint}" font-size="13" text-anchor="middle">返回结果</text>
        <g class="packet packet-result">
          <rect x="1001" y="262.5" width="16" height="3" rx="1.5" fill="url(#trailLeft)"/>
          <circle cx="1001" cy="264" r="7" fill="${link_dot}" opacity="0.2"/>
          <circle cx="1001" cy="264" r="3.5" fill="${link_dot}"/>
        </g>
      </g>
      <g id="flow-cloud">
        <rect x="1007.5" y="205.5" width="123" height="93" rx="12.5" fill="${card}" stroke="${cloud_stroke}" stroke-dasharray="6 5"/>
        <g class="lit lit-cloud">
          <rect x="1004" y="202" width="130" height="100" rx="16" fill="none" stroke="${cloud_lit}" stroke-opacity="0.18" stroke-width="4"/>
          <rect x="1007.5" y="205.5" width="123" height="93" rx="12.5" fill="${cloud_lit}" fill-opacity="0.06" stroke="${cloud_lit}" stroke-width="1.5" stroke-dasharray="6 5"/>
        </g>
        <text x="1069" y="247" fill="${ink}" font-size="20" font-weight="700" text-anchor="middle">云端模型</text>
        <text x="1069" y="273" fill="${muted}" font-size="14" text-anchor="middle">按需推理</text>
      </g>
    </g>

    <g id="drive">
      <rect id="drive-boundary" x="508.5" y="94.5" width="427" height="315" rx="14" fill="${carry}" fill-opacity="${drive_fill}" stroke="${carry}" stroke-opacity="0.45" stroke-dasharray="6 5"/>
      <text x="932" y="84" fill="${flow_tag}" font-size="14" text-anchor="end">U 盘内</text>

      <g id="continuity-rail">
        <path d="M556 362H536A8 8 0 0 1 528 354V150A8 8 0 0 1 536 142H549" fill="none" stroke="${carry}" stroke-opacity="0.4"/>
        <path d="M549 137.5V146.5L556 142Z" fill="${carry}" fill-opacity="0.65"/>
        <text fill="${faint}" font-size="13" text-anchor="middle"><tspan x="542" y="221">记</tspan><tspan x="542" y="239">录</tspan><tspan x="542" y="257">·</tspan><tspan x="542" y="275">沉</tspan><tspan x="542" y="293">淀</tspan></text>
        <g class="lit lit-rail">
          <path d="M556 362H536A8 8 0 0 1 528 354V150A8 8 0 0 1 536 142H549" fill="none" stroke="${carry_2}" stroke-width="1.5"/>
          <path d="M549 137.5V146.5L556 142Z" fill="${carry_2}"/>
        </g>
        <g class="packet packet-rail">
          <rect x="526.5" y="338" width="3" height="16" rx="1.5" fill="url(#trailUp)"/>
          <circle cx="528" cy="338" r="7" fill="${carry_2}" opacity="0.22"/>
          <circle cx="528" cy="338" r="3.5" fill="${carry_2}"/>
        </g>
      </g>

      <g id="step-retrieve">
        <path d="M596 178V212" stroke="${carry}" stroke-opacity="0.45"/>
        <path d="M591 211H601L596 218Z" fill="${carry}" fill-opacity="0.7"/>
        <text x="614" y="202" fill="${faint}" font-size="13">检索 / 继续</text>
        <g class="packet packet-retrieve">
          <rect x="594.5" y="164" width="3" height="16" rx="1.5" fill="url(#trailDown)"/>
          <circle cx="596" cy="180" r="7" fill="${carry_2}" opacity="0.22"/>
          <circle cx="596" cy="180" r="3.5" fill="${carry_2}"/>
        </g>
      </g>
      <g id="step-generate">
        <path d="M596 288V322" stroke="${carry}" stroke-opacity="0.45"/>
        <path d="M591 321H601L596 328Z" fill="${carry}" fill-opacity="0.7"/>
        <text x="614" y="312" fill="${faint}" font-size="13">生成 / 记录</text>
        <g class="packet packet-generate">
          <rect x="594.5" y="274" width="3" height="16" rx="1.5" fill="url(#trailDown)"/>
          <circle cx="596" cy="290" r="7" fill="${carry_2}" opacity="0.22"/>
          <circle cx="596" cy="290" r="3.5" fill="${carry_2}"/>
        </g>
      </g>

      <g id="flow-context">
        <rect x="556.5" y="109.5" width="359" height="65" rx="10.5" fill="${card}" stroke="${carry}" stroke-opacity="0.3"/>
        <g class="lit lit-context">
          <rect x="553" y="106" width="366" height="72" rx="14" fill="none" stroke="${carry}" stroke-opacity="0.18" stroke-width="4"/>
          <rect x="556.5" y="109.5" width="359" height="65" rx="10.5" fill="${carry}" fill-opacity="0.08" stroke="${carry}" stroke-width="1.5"/>
        </g>
        <text x="576" y="137" fill="${ink}" font-size="20" font-weight="700">盘内资料与任务</text>
        <text x="576" y="161" fill="${muted}" font-size="14">Inbox 确认后写入长期知识</text>
      </g>
      <g id="flow-workspace">
        <rect x="556.5" y="219.5" width="359" height="65" rx="10.5" fill="${card}" stroke="${carry}" stroke-opacity="0.3"/>
        <g class="lit lit-workspace-in">
          <rect x="553" y="216" width="366" height="72" rx="14" fill="none" stroke="${carry}" stroke-opacity="0.18" stroke-width="4"/>
          <rect x="556.5" y="219.5" width="359" height="65" rx="10.5" fill="${carry}" fill-opacity="0.08" stroke="${carry}" stroke-width="1.5"/>
        </g>
        <g class="lit lit-workspace-back">
          <rect x="553" y="216" width="366" height="72" rx="14" fill="none" stroke="${carry}" stroke-opacity="0.18" stroke-width="4"/>
          <rect x="556.5" y="219.5" width="359" height="65" rx="10.5" fill="${carry}" fill-opacity="0.08" stroke="${carry}" stroke-width="1.5"/>
        </g>
        <text x="576" y="247" fill="${ink}" font-size="20" font-weight="700">Yi盘工作台</text>
        <text x="576" y="271" fill="${muted}" font-size="14">受管 Agent 处理当前任务</text>
      </g>
      <g id="flow-output">
        <rect x="556.5" y="329.5" width="359" height="65" rx="10.5" fill="${card}" stroke="${carry}" stroke-opacity="0.3"/>
        <g class="lit lit-output">
          <rect x="553" y="326" width="366" height="72" rx="14" fill="none" stroke="${carry}" stroke-opacity="0.18" stroke-width="4"/>
          <rect x="556.5" y="329.5" width="359" height="65" rx="10.5" fill="${carry}" fill-opacity="0.08" stroke="${carry}" stroke-width="1.5"/>
        </g>
        <text x="576" y="357" fill="${ink}" font-size="20" font-weight="700">产出与任务记录</text>
        <text x="576" y="381" fill="${muted}" font-size="14">留在盘内，随盘带走</text>
      </g>
    </g>
  </g>
</svg>
""")


# DSH's functional illustration plays once and holds its complete base frame.
# npm metrics and product facts stay visible throughout; transient packets and
# the scanner are hidden in the base frame and in both static alternatives.
# Backwards fill releases animation compositing after completion, so the final
# pixels match the static images instead of retaining scaled intermediate layers.
DSH_STYLE = """  <style>
    text { font-family: Arial, "PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif; }
    .mono { font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace; }
    .record, .usage-bars, .time-lane, .cta-arrow { transform-box: fill-box; }
    .usage-bars { transform-origin: center bottom; }
    .time-lane { transform-origin: left center; }
    .packet, .timeline-scan { opacity: 0; }
    @media (prefers-reduced-motion: no-preference) {
      .record-a { animation: record-a 8s ease-in-out infinite; }
      .record-b { animation: record-b 8s ease-in-out infinite; }
      .record-c { animation: record-c 8s ease-in-out infinite; }
      .packet-a { animation: packet-a 8s linear infinite; }
      .packet-b { animation: packet-b 8s linear infinite; }
      .packet-c { animation: packet-c 8s linear infinite; }
      .project-a { animation: project-a 8s ease-in-out infinite; }
      .project-b { animation: project-b 8s ease-in-out infinite; }
      .project-c { animation: project-c 8s ease-in-out infinite; }
      .usage-a { animation: usage-a 8s cubic-bezier(0.2, 0.7, 0.2, 1) infinite; }
      .usage-b { animation: usage-b 8s cubic-bezier(0.2, 0.7, 0.2, 1) infinite; }
      .usage-c { animation: usage-c 8s cubic-bezier(0.2, 0.7, 0.2, 1) infinite; }
      .lane-a { animation: lane-a 8s cubic-bezier(0.2, 0.7, 0.2, 1) infinite; }
      .lane-b { animation: lane-b 8s cubic-bezier(0.2, 0.7, 0.2, 1) infinite; }
      .lane-c { animation: lane-c 8s cubic-bezier(0.2, 0.7, 0.2, 1) infinite; }
      .timeline-scan { animation: timeline-scan 8s ease-in-out infinite; }
      .cta-arrow { animation: cta-nudge 8s ease-out infinite; }
    }
    @keyframes record-a {
      0%, 3% { opacity: 0.35; transform: translateY(8px); }
      7%, 88% { opacity: 1; transform: translateY(0); }
      94%, 100% { opacity: 0.35; transform: translateY(8px); }
    }
    @keyframes record-b {
      0%, 5% { opacity: 0.35; transform: translateY(8px); }
      9%, 88% { opacity: 1; transform: translateY(0); }
      94%, 100% { opacity: 0.35; transform: translateY(8px); }
    }
    @keyframes record-c {
      0%, 7% { opacity: 0.35; transform: translateY(8px); }
      11%, 88% { opacity: 1; transform: translateY(0); }
      94%, 100% { opacity: 0.35; transform: translateY(8px); }
    }
    @keyframes packet-a {
      0%, 17% { opacity: 0; transform: translateX(0); }
      18% { opacity: 1; transform: translateX(0); }
      21% { transform: translateX(12px); }
      26% { transform: translateX(55px); }
      30% { opacity: 1; transform: translateX(85px); }
      31%, 100% { opacity: 0; transform: translateX(var(--packet-distance, 98px)); }
    }
    @keyframes packet-b {
      0%, 20% { opacity: 0; transform: translateX(0); }
      21% { opacity: 1; transform: translateX(0); }
      24% { transform: translateX(12px); }
      29% { transform: translateX(55px); }
      33% { opacity: 1; transform: translateX(85px); }
      34%, 100% { opacity: 0; transform: translateX(var(--packet-distance, 98px)); }
    }
    @keyframes packet-c {
      0%, 23% { opacity: 0; transform: translateX(0); }
      24% { opacity: 1; transform: translateX(0); }
      27% { transform: translateX(12px); }
      32% { transform: translateX(55px); }
      36% { opacity: 1; transform: translateX(85px); }
      37%, 100% { opacity: 0; transform: translateX(var(--packet-distance, 98px)); }
    }
    @keyframes project-a {
      0%, 29% { opacity: 0.4; }
      31% { opacity: 1; }
      34% { opacity: 0.75; }
      37%, 88% { opacity: 1; }
      94%, 100% { opacity: 0.4; }
    }
    @keyframes project-b {
      0%, 32% { opacity: 0.4; }
      34% { opacity: 1; }
      37% { opacity: 0.75; }
      40%, 88% { opacity: 1; }
      94%, 100% { opacity: 0.4; }
    }
    @keyframes project-c {
      0%, 35% { opacity: 0.4; }
      37% { opacity: 1; }
      40% { opacity: 0.75; }
      43%, 88% { opacity: 1; }
      94%, 100% { opacity: 0.4; }
    }
    @keyframes usage-a {
      0%, 41% { opacity: 0.35; transform: scaleY(0.15); }
      47% { opacity: 1; transform: scaleY(1.08); }
      51% { transform: scaleY(0.97); }
      54%, 88% { opacity: 1; transform: none; }
      94%, 100% { opacity: 0.35; transform: scaleY(0.15); }
    }
    @keyframes usage-b {
      0%, 44% { opacity: 0.35; transform: scaleY(0.15); }
      50% { opacity: 1; transform: scaleY(1.08); }
      54% { transform: scaleY(0.97); }
      57%, 88% { opacity: 1; transform: none; }
      94%, 100% { opacity: 0.35; transform: scaleY(0.15); }
    }
    @keyframes usage-c {
      0%, 47% { opacity: 0.35; transform: scaleY(0.15); }
      53% { opacity: 1; transform: scaleY(1.08); }
      57% { transform: scaleY(0.97); }
      60%, 88% { opacity: 1; transform: none; }
      94%, 100% { opacity: 0.35; transform: scaleY(0.15); }
    }
    @keyframes lane-a {
      0%, 51% { opacity: 0.35; transform: scaleX(0.1); }
      57% { opacity: 1; transform: scaleX(1.04); }
      61% { transform: scaleX(0.99); }
      64%, 88% { opacity: 1; transform: none; }
      94%, 100% { opacity: 0.35; transform: scaleX(0.1); }
    }
    @keyframes lane-b {
      0%, 54% { opacity: 0.35; transform: scaleX(0.1); }
      60% { opacity: 1; transform: scaleX(1.04); }
      64% { transform: scaleX(0.99); }
      67%, 88% { opacity: 1; transform: none; }
      94%, 100% { opacity: 0.35; transform: scaleX(0.1); }
    }
    @keyframes lane-c {
      0%, 57% { opacity: 0.35; transform: scaleX(0.1); }
      63% { opacity: 1; transform: scaleX(1.04); }
      67% { transform: scaleX(0.99); }
      70%, 88% { opacity: 1; transform: none; }
      94%, 100% { opacity: 0.35; transform: scaleX(0.1); }
    }
    @keyframes timeline-scan {
      0%, 67% { opacity: 0; transform: translateX(0); }
      69% { opacity: 0.95; transform: translateX(0); }
      85% { opacity: 0.95; transform: translateX(290px); }
      87%, 100% { opacity: 0; transform: translateX(290px); }
    }
    @keyframes cta-nudge {
      0%, 87% { transform: translateX(0); }
      90% { transform: translateX(6px); }
      93% { transform: translateX(1px); }
      96%, 100% { transform: translateX(0); }
    }
  </style>"""

DSH = Template("""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="420" viewBox="0 0 1200 420" role="img" aria-labelledby="title desc">
  <title id="title">DSH Usage：按项目统计会话用量</title>
  <desc id="desc">${theme_desc}DSH Usage 项目卡。DeepSeek Harness 用量插件，按项目统计 Token、开发时长和预估费用，另含账户余额查询。右侧为功能示意，非产品截图：会话记录按项目归集，形成用量柱和开发时间线；图形不代表真实用量。项目总览可导出 CSV/JSON，用量趋势可选近 7 / 30 / 90 天。npm 近 30 天下载 ${npm_downloads} 次，最新版本 ${npm_latest}，已发布 ${npm_versions} 个版本，下载统计截至 ${npm_as_of}。包名 @rongyi7/dsh-stats，MIT 许可。</desc>
  <defs>
    <linearGradient id="cardWash" x1="0" y1="0" x2="1" y2="1"><stop stop-color="${see}" stop-opacity="0.12"/><stop offset="1" stop-color="${see}" stop-opacity="0.02"/></linearGradient>
    <linearGradient id="laneFill"><stop stop-color="${see}"/><stop offset="1" stop-color="${see_2}"/></linearGradient>
  </defs>
${style}
  <rect x="0.5" y="0.5" width="1199" height="419" rx="18" fill="${page_bg}"/>
  <rect x="0.5" y="0.5" width="1199" height="419" rx="18" fill="url(#cardWash)" stroke="${see}" stroke-opacity="0.26"/>
  <g id="card-copy">
    <text x="48" y="72" fill="${ink}" font-size="37" font-weight="700">DSH Usage</text>
    <text x="48" y="107" fill="${see_text}" font-size="18">DeepSeek Harness 用量插件</text>
    <text x="48" y="157" fill="${ink}" font-size="23">按项目统计会话用量</text>
  </g>
  <g id="card-tags"><text x="48" y="191" fill="${soft}" font-size="18">Token · 开发时长 · 预估费用</text></g>
  <path d="M48 222H350M397 48V372" fill="none" stroke="${fig_stroke}"/>
  <g id="card-metrics">
    <text x="48" y="253" fill="${muted}" font-size="17">近 30 天下载</text>
    <text x="218" y="253" fill="${muted}" font-size="17">npm 最新版本</text>
    <text id="npm-downloads" x="48" y="293" fill="${ink}" font-size="32" font-weight="600" class="mono">${npm_downloads}</text>
    <text id="npm-latest" x="218" y="293" fill="${ink}" font-size="32" font-weight="600" class="mono">${npm_latest}</text>
  </g>
  <text id="npm-as-of" x="48" y="324" fill="${muted}" font-size="17">统计截至 ${npm_as_of}</text>
  <g id="card-cta">
    <text x="48" y="377" fill="${see_text}" font-size="19" font-weight="600">查看仓库</text>
    <g class="cta-arrow"><text x="139" y="377" fill="${see_text}" font-size="23">↗</text></g>
  </g>
  <g id="card-status"><text x="350" y="377" fill="${muted}" font-size="17" text-anchor="end">npm · MIT</text></g>
  <g id="dsh-panel">
    <text x="443" y="75" fill="${ink}" font-size="24" font-weight="600">会话 → 项目 → 时间线</text>
    <text id="flow-caption" x="1148" y="75" fill="${muted}" font-size="17" text-anchor="end">功能示意</text>
    <text id="session-source" x="443" y="128" fill="${muted}" font-size="17">会话记录</text>
    <text id="project-grouping" x="637" y="128" fill="${muted}" font-size="17">按项目归集</text>
    <g id="card-views">
      <g id="view-2"><text x="850" y="128" fill="${muted}" font-size="17">开发时间线</text></g>
      <g id="session-records" fill="${pill_fill}" stroke="${fig_stroke}">
        <g class="record record-a"><rect x="443" y="152" width="104" height="46" rx="8"/><text x="457" y="181" fill="${soft}" stroke="none" font-size="18">会话 A</text></g>
        <g class="record record-b"><rect x="443" y="214" width="104" height="46" rx="8"/><text x="457" y="243" fill="${soft}" stroke="none" font-size="18">会话 B</text></g>
        <g class="record record-c"><rect x="443" y="276" width="104" height="46" rx="8"/><text x="457" y="305" fill="${soft}" stroke="none" font-size="18">会话 C</text></g>
      </g>
      <g id="session-links" fill="none" stroke="${link_line}"><path d="M548 175H645M548 237H645M548 299H645"/><path d="M755 175H815M755 237H815M755 299H815"/></g>
      <g id="session-packets" fill="${see_2}">
        <rect class="packet packet-a" x="552" y="172" width="12" height="6" rx="3"/>
        <rect class="packet packet-b" x="552" y="234" width="12" height="6" rx="3"/>
        <rect class="packet packet-c" x="552" y="296" width="12" height="6" rx="3"/>
      </g>
      <g id="project-groups" fill="${fig_bg}" stroke="${see}" stroke-opacity="0.6">
        <g class="project-a"><rect x="645" y="152" width="109" height="46" rx="8"/><text x="661" y="181" fill="${ink}" stroke="none" font-size="18">项目 A</text></g>
        <g class="project-b"><rect x="645" y="214" width="109" height="46" rx="8"/><text x="661" y="243" fill="${ink}" stroke="none" font-size="18">项目 B</text></g>
        <g class="project-c"><rect x="645" y="276" width="109" height="46" rx="8"/><text x="661" y="305" fill="${ink}" stroke="none" font-size="18">项目 C</text></g>
      </g>
      <g fill="${see_2}"><circle cx="798" cy="175" r="3"/><circle cx="798" cy="237" r="3"/><circle cx="798" cy="299" r="3"/></g>
      <g id="timeline-illustration">
        <rect x="815" y="151" width="333" height="173" rx="11" fill="${fig_bg}" stroke="${fig_stroke}"/>
        <path d="M854 166V308M906 166V308M958 166V308M1010 166V308M1062 166V308M1114 166V308M834 231H1129" fill="none" stroke="${fig_grid}"/>
        <g fill="${see}">
          <g class="usage-bars usage-a"><rect x="837" y="208" width="12" height="16" rx="3"/><rect x="861" y="194" width="12" height="30" rx="3"/><rect x="885" y="202" width="12" height="22" rx="3"/><rect x="909" y="184" width="12" height="40" rx="3"/></g>
          <g class="usage-bars usage-b"><rect x="933" y="196" width="12" height="28" rx="3"/><rect x="957" y="177" width="12" height="47" rx="3"/><rect x="981" y="191" width="12" height="33" rx="3"/><rect x="1005" y="171" width="12" height="53" rx="3"/></g>
          <g class="usage-bars usage-c"><rect x="1029" y="182" width="12" height="42" rx="3"/><rect x="1053" y="201" width="12" height="23" rx="3"/><rect x="1077" y="188" width="12" height="36" rx="3"/><rect x="1101" y="207" width="12" height="17" rx="3"/></g>
        </g>
        <g fill="url(#laneFill)">
          <g class="time-lane lane-a"><rect x="837" y="247" width="86" height="8" rx="4"/><rect x="960" y="247" width="130" height="8" rx="4"/></g>
          <g class="time-lane lane-b"><rect x="870" y="272" width="141" height="8" rx="4"/><rect x="1030" y="272" width="64" height="8" rx="4"/></g>
          <g class="time-lane lane-c"><rect x="837" y="297" width="55" height="8" rx="4"/><rect x="934" y="297" width="110" height="8" rx="4"/><rect x="1070" y="297" width="52" height="8" rx="4"/></g>
        </g>
        <g class="timeline-scan"><path d="M835 163V312" stroke="${see_2}" stroke-width="2"/><rect x="835" y="163" width="12" height="149" fill="${see_2}" opacity="0.08"/></g>
      </g>
      <g id="view-1"><text x="443" y="375" fill="${muted}" font-size="17">项目总览 · CSV/JSON 导出</text></g>
      <g id="view-3"><text x="710" y="375" fill="${muted}" font-size="17">用量趋势 · 近 7 / 30 / 90 天</text></g>
      <g id="view-4"><text x="1148" y="375" fill="${muted}" font-size="17" text-anchor="end">账户余额查询</text></g>
    </g>
  </g>
</svg>
""")

DSH_MOBILE = Template("""<svg xmlns="http://www.w3.org/2000/svg" width="360" height="374" viewBox="0 0 360 374" role="img" aria-labelledby="title desc">
  <title id="title">DSH Usage：按项目统计会话用量</title>
  <desc id="desc">DeepSeek Harness 用量插件，按项目统计 Token、开发时长和预估费用，另含账户余额查询。会话到项目时间线为功能示意，非产品截图，不代表真实用量。npm 近 30 天下载 ${npm_downloads} 次，最新版本 ${npm_latest}，已发布 ${npm_versions} 个版本；下载统计截至 ${npm_as_of}。</desc>
${style}
  <rect x="0.5" y="0.5" width="359" height="373" rx="18" fill="${page_bg}" stroke="${see}" stroke-opacity="0.35"/>
  <text x="24" y="45" fill="${ink}" font-size="27" font-weight="700">DSH Usage</text>
  <text x="24" y="77" fill="${soft}" font-size="18">按项目统计会话用量</text>
  <text x="24" y="108" fill="${muted}" font-size="17">Token · 时长 · 预估费用</text>
  <g id="mobile-illustration">
    <text x="24" y="145" fill="${muted}" font-size="17">会话</text>
    <text x="164" y="145" fill="${muted}" font-size="17">项目时间线</text>
    <rect x="24" y="160" width="69" height="54" rx="8" fill="${pill_fill}" stroke="${fig_stroke}"/>
    <text x="39" y="195" fill="${see_text}" font-size="24" class="mono">{ }</text>
    <path d="M93 187H164" stroke="${link_line}"/>
    <rect class="packet packet-a" x="102" y="184" width="10" height="6" rx="3" fill="${see}" style="--packet-distance: 52px"/>
    <rect x="164" y="157" width="172" height="62" rx="8" fill="${fig_bg}" stroke="${fig_stroke}"/>
    <g fill="${see}">
      <rect class="time-lane lane-a" x="177" y="169" width="104" height="6" rx="3"/>
      <rect class="time-lane lane-b" x="177" y="185" width="75" height="6" rx="3"/>
      <rect class="time-lane lane-c" x="177" y="201" width="136" height="6" rx="3"/>
    </g>
    <text id="flow-caption" x="336" y="245" fill="${muted}" font-size="17" text-anchor="end">功能示意</text>
  </g>
  <path d="M24 260H336" stroke="${fig_stroke}"/>
  <g id="card-metrics">
    <text x="24" y="286" fill="${muted}" font-size="17">近 30 天下载</text>
    <text x="202" y="286" fill="${muted}" font-size="17">最新版本</text>
    <text id="npm-downloads" x="24" y="322" fill="${ink}" font-size="30" font-weight="600" class="mono">${npm_downloads}</text>
    <text id="npm-latest" x="202" y="322" fill="${ink}" font-size="30" font-weight="600" class="mono">${npm_latest}</text>
  </g>
  <text id="npm-as-of" x="24" y="355" fill="${muted}" font-size="17">统计截至 ${npm_as_of}</text>
</svg>
""")


def media_uri(name: str) -> str:
    data = base64.b64encode((MEDIA / name).read_bytes()).decode("ascii")
    return f"data:image/webp;base64,{data}"


def npm_figures(theme: str) -> dict[str, str]:
    """The DSH card's npm metrics, formatted like the homepage (validate-svg.py re-checks them)."""
    stats = json.loads(NPM_STATS.read_text(encoding="utf-8"))
    return {
        "npm_downloads": f"{int(stats['downloads_last_month']):,}",
        "npm_latest": escape(str(stats["latest"])),
        "npm_versions": f"{int(stats['version_count']):,}",
        "npm_as_of": escape(str(stats["downloads_end"])),
    }


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


def still_style(style: str) -> str:
    """Remove whole motion blocks, including keyframes; static assets cannot animate."""
    pattern = re.compile(r"@media\s*\(prefers-reduced-motion:\s*no-preference\)\s*\{|@keyframes\s+[\w-]+\s*\{")
    while match := pattern.search(style):
        cursor, depth = match.end(), 1
        while depth and cursor < len(style):
            depth += (style[cursor] == "{") - (style[cursor] == "}")
            cursor += 1
        if depth:
            raise ValueError("unbalanced motion CSS")
        style = style[:match.start()] + style[cursor:]
    return "\n".join(line.rstrip() for line in style.splitlines())


def adaptive_style(style: str) -> str:
    # GitHub rewrites source media containing prefers-color-scheme when a user
    # chooses a theme. Width/motion sources therefore use one adaptive SVG. Its
    # color-scheme query inherits the parent image's scheme, including manual themes.
    def variables(theme: str) -> str:
        return " ".join(f"--{key}: {value};" for key, value in PALETTES[theme].items() if key != "theme_desc")
    css = (
        f"\n    :root {{ {variables('light')} }}\n"
        "    .theme-dark { display: none; }\n"
        f"    @media (prefers-color-scheme: dark) {{ :root {{ {variables('dark')} }} "
        ".theme-light { display: none; } .theme-dark { display: inline; } }\n"
    )
    return style.replace("<style>", "<style>" + css, 1)


def render_adaptive(template: Template, style: str, extra: dict[str, str], *, motion: bool = False) -> str:
    palette = {key: f"var(--{key})" for key in PALETTES['light']}
    palette['theme_desc'] = "深浅主题自适应"
    return render(template, adaptive_style(style if motion else still_style(style)), palette, extra)


def main() -> int:
    check = "--check" in sys.argv[1:]
    outputs = {
        "hero": (HERO, HERO_STYLE, hero_media),
        "yipan-flow": (FLOW, FLOW_STYLE, lambda theme: {}),
        "dsh-card": (DSH, DSH_STYLE, npm_figures),
        "hardware-strip": (STRIP, STRIP_STYLE, lambda theme: {}),
    }
    rendered: dict[Path, str] = {}
    for stem, (template, style, extra) in outputs.items():
        for theme, palette in PALETTES.items():
            path = ASSETS / f"{stem}-{theme}.svg"
            rendered[path] = render(template, style, palette, extra(theme))
        rendered[ASSETS / f"{stem}-still.svg"] = render_adaptive(template, style, extra('light'))
    # The static hero carries both real captures; CSS selects the matching one.
    hero_path = ASSETS / "hero-still.svg"
    hero = rendered[hero_path]
    image = re.search(r'<image class="shot-pan"[^>]+/>', hero).group(0)
    light_image = image.replace('class="shot-pan"', 'class="shot-pan theme-light"')
    dark_image = image.replace('class="shot-pan"', 'class="shot-pan theme-dark"').replace(
        media_uri('dsh-trends-light.webp'), media_uri('dsh-trends-dark.webp'))
    rendered[hero_path] = hero.replace(image, light_image + "\n        " + dark_image)
    rendered[ASSETS / "dsh-card-mobile.svg"] = render_adaptive(DSH_MOBILE, DSH_STYLE, npm_figures('light'), motion=True)
    rendered[ASSETS / "dsh-card-mobile-still.svg"] = render_adaptive(DSH_MOBILE, DSH_STYLE, npm_figures('light'))
    readme = Path('README.md')
    rendered[readme] = replace_snapshot(readme.read_text(encoding='utf-8'), json.loads(NPM_STATS.read_text()))
    stale: list[str] = []
    for path, content in rendered.items():
        if check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                stale.append(str(path))
        else:
            path.write_text(content, encoding="utf-8")
            print(f"wrote {path}")
    if stale:
        print(
            "Generated SVG assets or npm text are out of date; run python3 scripts/render-svg.py:\n- " + "\n- ".join(stale),
            file=sys.stderr,
        )
        return 1
    if check:
        print("Generated SVG assets and npm text match scripts/render-svg.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
