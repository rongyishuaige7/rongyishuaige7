#!/usr/bin/env python3
"""Render profile SVGs and the marked native npm snapshot in README.md.

Dark/light pairs share geometry; width/reduced-motion sources use adaptive
SVGs so GitHub's manual theme rewrite cannot erase their media guards.
The hero embeds real WebP media because GitHub's SVG CSP blocks external images.
README asset links carry ?v=<content hash> so GitHub never serves a stale image;
DSH hashes leave out the daily npm figures, so the bot only touches the snapshot.
Run this script after editing templates or npm data; CI checks generated output.
"""

import base64
import hashlib
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
# Public projects per controller platform, most first; README.md lists the same counts.
HARDWARE_PLATFORMS = (("ESP32", 15), ("STM32", 3), ("树莓派", 3), ("Arduino", 1))
assert sum(count for _, count in HARDWARE_PLATFORMS) == HARDWARE_PROTOTYPES

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
        "ink": "#f3f6fa",
        "muted": "#9da6b4",
        "faint": "#737e8e",
        "carry": "#ff6b4a",
        "carry_2": "#ff9a3d",
        "carry_text": "#ff6b4a",
        "see": "#6ea8ff",
        "see_2": "#63ccf8",
        "see_text": "#6ea8ff",
        "touch": "#46d89c",
        "touch_2": "#b6ec6a",
        "touch_text": "#46d89c",
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
        "ink": "#18202a",
        "muted": "#5f6876",
        "faint": "#646d7b",
        "carry": "#e45738",
        "carry_2": "#f08a2c",
        "carry_text": "#c8452a",
        "see": "#3d7be0",
        "see_2": "#1e93cc",
        "see_text": "#2559c4",
        "touch": "#1aa572",
        "touch_2": "#7cc23a",
        "touch_text": "#0b7d50",
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
        "flow_tag": "#b4520e",
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
# The narrow hero reuses this style: the same classes play the same one-shot story.
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
      40%, 62% { transform: translateY(-23px); }
      100% { transform: translateY(0); }
    }
    @keyframes deck-1 {
      0% { transform: rotate(8deg) translate(52px, -6px); }
      80% { transform: rotate(-0.8deg) translate(-2px, 0.5px); }
      100% { transform: rotate(0deg) translate(0px, 0px); }
    }
    @keyframes deck-2 {
      0% { transform: rotate(-7deg) translate(-52px, -4px); }
      80% { transform: rotate(0.8deg) translate(2px, 0.5px); }
      100% { transform: rotate(0deg) translate(0px, 0px); }
    }
    @keyframes deck-3 {
      0% { transform: rotate(1deg) translate(0px, 5px); }
      80% { transform: rotate(-0.3deg) translate(0px, -1px); }
      100% { transform: rotate(0deg) translate(0px, 0px); }
    }
  </style>"""

# Pieces shared by the desktop and narrow heroes. Both captures need 23px of hidden
# height below their clip for the pan; layouts place them with their own clip rects.
HERO_GRADIENTS = """    <linearGradient id="surface" x1="0" y1="0" x2="1" y2="1">
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
    <clipPath id="faceClip"><path d="M150 244H234A13 13 0 0 1 247 257V313A13 13 0 0 1 234 326H150Z"/></clipPath>
    <clipPath id="photoClip"><rect x="-64" y="-48" width="128" height="96" rx="8"/></clipPath>
    <filter id="photoShadow" x="-40%" y="-40%" width="180%" height="200%">
      <feDropShadow dx="0" dy="10" stdDeviation="9" flood-color="#000000" flood-opacity="${shadow_opacity}"/>
    </filter>
"""

# The drive is drawn at its desktop size; the narrow hero scales the same group.
DRIVE_BODY = """      <rect x="111" y="244" width="52" height="82" rx="11" fill="${drive_port}" stroke="${carry_2}" stroke-opacity="0.38"/>
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
"""

# Each deck photo is drawn centred on its own origin, and the deck around the origin of its
# group. The outer group holds the final fanned pose; the animated inner group starts with the
# inverse rotation and offset, so all three begin stacked at the deck centre and settle into
# the pose. Left to right the photos follow the TOUCH featured builds: pot, traffic, voice.
PHOTO_DECK = """        <g transform="translate(-52 6) rotate(-8)">
          <g class="deck-1">
            <g filter="url(#photoShadow)"><g clip-path="url(#photoClip)"><image x="-64" y="-48" width="128" height="96" preserveAspectRatio="xMidYMid slice" href="${photo_pot}"/></g></g>
            <rect x="-63.5" y="-47.5" width="127" height="95" rx="7.5" fill="none" stroke="${touch}" stroke-opacity="0.38"/>
          </g>
        </g>
        <g transform="translate(52 4) rotate(7)">
          <g class="deck-2">
            <g filter="url(#photoShadow)"><g clip-path="url(#photoClip)"><image x="-64" y="-48" width="128" height="96" preserveAspectRatio="xMidYMid slice" href="${photo_voice}"/></g></g>
            <rect x="-63.5" y="-47.5" width="127" height="95" rx="7.5" fill="none" stroke="${touch}" stroke-opacity="0.38"/>
          </g>
        </g>
        <g transform="translate(0 -5) rotate(-1)">
          <g class="deck-3">
            <g filter="url(#photoShadow)"><g clip-path="url(#photoClip)"><image x="-64" y="-48" width="128" height="96" preserveAspectRatio="xMidYMid slice" href="${photo_traffic}"/></g></g>
            <rect x="-63.5" y="-47.5" width="127" height="95" rx="7.5" fill="none" stroke="${touch}" stroke-opacity="0.38"/>
          </g>
        </g>
"""

HERO_DESC = (
    "${theme_desc}品牌横幅，三张项目入口卡。Yi盘：U 盘里的 AI 工作台，受控内测，资料与产出留在盘内，云端模型按需调用，配 U 盘功能示意。"
    "DSH Usage：会话、Token 与模型费用，配用量趋势页的运行截图，夹具数据。"
    "Hardware Lab：${prototypes} 个硬件原型，配三张历史原型照片：多模态智能花盆、车流自适应交通信号、健康科普语音终端。"
)

# Desktop: Yi盘 leads with the widest card (400) and carries its status and two facts;
# DSH Usage and Hardware Lab share 328 each. Every label is at least 17 units.
HERO = Template("""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="420" viewBox="0 0 1200 420" role="img" aria-labelledby="title desc">
  <title id="title">Rongyi，独立开发者 · Yi盘创始人</title>
  <desc id="desc">""" + HERO_DESC + """</desc>
  <defs>
""" + HERO_GRADIENTS + """    <mask id="gridMask" maskUnits="userSpaceOnUse" x="16" y="16" width="1168" height="388">
      <rect x="16" y="16" width="1168" height="388" fill="url(#gridFade)"/>
    </mask>
    <clipPath id="panelClip"><rect x="16" y="16" width="1168" height="388" rx="16"/></clipPath>
    <clipPath id="shotClip"><rect x="494" y="210" width="284" height="132" rx="8"/></clipPath>
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
    <text x="64" y="18" fill="${ink}" font-size="18" font-weight="700" letter-spacing="3">RONGYI</text>
    <text x="64" y="42" fill="${muted}" font-size="17" letter-spacing="1.2">INDIE DEVELOPER · FOUNDER OF YI盘</text>
  </g>

  <g id="entry-carry" class="entry-carry">
    <rect x="48" y="114" width="400" height="274" rx="14" fill="${card}" stroke="${carry}" stroke-opacity="0.32"/>
    <rect x="48" y="114" width="400" height="274" rx="14" fill="url(#tintCarry)"/>
    <text x="72" y="162" fill="${carry_text}" font-size="30" font-weight="800" letter-spacing="-0.6">Yi盘</text>
    <text x="72" y="192" fill="${soft}" font-size="18">U 盘里的 AI 工作台</text>
    <g id="carry-status">
      <rect x="316.5" y="136.5" width="107" height="31" rx="15.5" fill="${tag_fill}" stroke="${carry}" stroke-opacity="0.45"/>
      <circle cx="334" cy="152" r="4" fill="${carry}"/>
      <text x="346" y="158" fill="${carry_text}" font-size="17">受控内测</text>
    </g>
    <g id="drive" transform="translate(-39 0)">
      <ellipse cx="208" cy="342" rx="108" ry="10" fill="url(#driveShadow)"/>
""" + DRIVE_BODY + """    </g>
    <g id="carry-facts">
      <circle cx="236" cy="266" r="4" fill="${carry}"/>
      <text x="250" y="272" fill="${soft}" font-size="17">资料与产出留在盘内</text>
      <circle cx="236" cy="304" r="3.5" fill="none" stroke="${muted}" stroke-width="1.5"/>
      <text x="250" y="310" fill="${muted}" font-size="17">云端模型按需调用</text>
    </g>
    <text x="72" y="370" fill="${muted}" font-size="17">功能示意</text>
  </g>

  <g id="entry-see" class="entry-see">
    <rect x="472" y="114" width="328" height="274" rx="14" fill="${card}" stroke="${see}" stroke-opacity="0.32"/>
    <rect x="472" y="114" width="328" height="274" rx="14" fill="url(#tintSee)"/>
    <text x="496" y="162" fill="${see_text}" font-size="30" font-weight="800" letter-spacing="-0.6">DSH Usage</text>
    <text x="496" y="192" fill="${soft}" font-size="18">会话、Token 与模型费用</text>
    <g id="dsh-shot">
      <rect x="494" y="210" width="284" height="132" rx="8" fill="${shot_bg}"/>
      <g clip-path="url(#shotClip)">
        <image class="shot-pan dsh-capture" x="494" y="210" width="284" height="155.3" preserveAspectRatio="xMidYMin slice" href="${dsh_trends}"/>
      </g>
      <rect x="494.5" y="210.5" width="283" height="131" rx="7.5" fill="none" stroke="${see}" stroke-opacity="0.3"/>
    </g>
    <text x="496" y="370" fill="${muted}" font-size="17">运行截图 · 夹具数据</text>
  </g>

  <g id="entry-touch" class="entry-touch">
    <rect x="824" y="114" width="328" height="274" rx="14" fill="${card}" stroke="${touch}" stroke-opacity="0.32"/>
    <rect x="824" y="114" width="328" height="274" rx="14" fill="url(#tintTouch)"/>
    <text x="848" y="162" fill="${touch_text}" font-size="30" font-weight="800" letter-spacing="-0.6">Hardware Lab</text>
    <text x="848" y="192" fill="${soft}" font-size="18">${prototypes} 个硬件原型</text>
    <g id="photo-deck" transform="translate(988 268)">
""" + PHOTO_DECK + """    </g>
    <text x="848" y="370" fill="${muted}" font-size="17">历史原型照片</text>
  </g>
</svg>
""")

# Narrow screens get the same three entries as stacked rows at 360 units wide, so text
# keeps its 17-unit floor at phone width instead of shrinking with the 1200-wide banner.
HERO_NARROW = Template("""<svg xmlns="http://www.w3.org/2000/svg" width="360" height="500" viewBox="0 0 360 500" role="img" aria-labelledby="title desc">
  <title id="title">Rongyi，独立开发者 · Yi盘创始人</title>
  <desc id="desc">""" + HERO_DESC + """</desc>
  <defs>
""" + HERO_GRADIENTS + """    <mask id="gridMask" maskUnits="userSpaceOnUse" x="10" y="10" width="340" height="480">
      <rect x="10" y="10" width="340" height="480" fill="url(#gridFade)"/>
    </mask>
    <clipPath id="panelClip"><rect x="10" y="10" width="340" height="480" rx="14"/></clipPath>
    <clipPath id="shotClip"><rect x="248" y="266" width="74" height="57" rx="6"/></clipPath>
  </defs>
${style}

  <rect x="0.5" y="0.5" width="359" height="499" rx="18" fill="${shell}" stroke="${shell_stroke}"/>
  <rect x="10" y="10" width="340" height="480" rx="14" fill="url(#surface)" stroke="${panel_stroke}"/>
  <g clip-path="url(#panelClip)">
    <rect x="10" y="10" width="340" height="480" fill="url(#grid)" mask="url(#gridMask)"/>
  </g>
  <rect x="10.5" y="10.5" width="339" height="479" rx="13.5" fill="none" stroke="url(#edge)" opacity="0.8"/>

  <g transform="translate(24 26)">
    <rect width="44" height="44" rx="11" fill="${card}" stroke="${carry}" stroke-width="2"/>
    <text x="22" y="30" fill="${carry_text}" font-size="23" font-weight="800" text-anchor="middle">R</text>
    <text x="58" y="18" fill="${ink}" font-size="18" font-weight="700" letter-spacing="2.4">RONGYI</text>
    <text x="58" y="40" fill="${muted}" font-size="17" letter-spacing="1">INDIE DEVELOPER</text>
    <text x="58" y="62" fill="${muted}" font-size="17" letter-spacing="1">FOUNDER OF YI盘</text>
  </g>

  <g id="entry-carry" class="entry-carry">
    <rect x="24" y="112" width="312" height="112" rx="12" fill="${card}" stroke="${carry}" stroke-opacity="0.32"/>
    <rect x="24" y="112" width="312" height="112" rx="12" fill="url(#tintCarry)"/>
    <text x="40" y="150" fill="${carry_text}" font-size="26" font-weight="800" letter-spacing="-0.4">Yi盘</text>
    <text x="40" y="176" fill="${soft}" font-size="17">U 盘里的 AI 工作台</text>
    <g id="carry-status">
      <circle cx="45" cy="198" r="4" fill="${carry}"/>
      <text x="56" y="204" fill="${carry_text}" font-size="17">受控内测</text>
    </g>
    <g id="drive" transform="translate(167.4 -16.1) scale(0.618)">
""" + DRIVE_BODY + """    </g>
    <text x="278" y="210" fill="${muted}" font-size="17" text-anchor="middle">功能示意</text>
  </g>

  <g id="entry-see" class="entry-see">
    <rect x="24" y="238" width="312" height="112" rx="12" fill="${card}" stroke="${see}" stroke-opacity="0.32"/>
    <rect x="24" y="238" width="312" height="112" rx="12" fill="url(#tintSee)"/>
    <text x="40" y="276" fill="${see_text}" font-size="26" font-weight="800" letter-spacing="-0.4">DSH Usage</text>
    <text x="40" y="302" fill="${soft}" font-size="17">会话、Token 与模型费用</text>
    <text x="40" y="330" fill="${muted}" font-size="17">运行截图 · 夹具数据</text>
    <g id="dsh-shot">
      <rect x="248" y="266" width="74" height="57" rx="6" fill="${shot_bg}"/>
      <g clip-path="url(#shotClip)">
        <image class="shot-pan dsh-capture" x="248" y="266" width="147" height="80.4" preserveAspectRatio="xMinYMin slice" href="${dsh_trends}"/>
      </g>
      <rect x="248.5" y="266.5" width="73" height="56" rx="5.5" fill="none" stroke="${see}" stroke-opacity="0.3"/>
    </g>
  </g>

  <g id="entry-touch" class="entry-touch">
    <rect x="24" y="364" width="312" height="112" rx="12" fill="${card}" stroke="${touch}" stroke-opacity="0.32"/>
    <rect x="24" y="364" width="312" height="112" rx="12" fill="url(#tintTouch)"/>
    <text x="40" y="402" fill="${touch_text}" font-size="26" font-weight="800" letter-spacing="-0.4">Hardware Lab</text>
    <text x="40" y="428" fill="${soft}" font-size="17">${prototypes} 个硬件原型</text>
    <text x="40" y="456" fill="${muted}" font-size="17">历史原型照片</text>
    <g id="photo-deck" transform="translate(278 420) scale(0.42)">
""" + PHOTO_DECK + """    </g>
  </g>
</svg>
""")

# The Hardware Lab card follows the DSH card's anatomy: name, descriptor, headline, tags and
# the index button on the left; the platform breakdown on the right. It is one series, so
# plain horizontal bars sorted by count, values at the tips in text colors and no legend;
# README.md states the same numbers as text. The bars grow once in order and the values
# fade in after them, all within two seconds; base styles are the final frame, so reduced
# motion shows the finished chart.
HARDWARE_STYLE = """  <style>
    text { font-family: Arial, "PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif; }
    .bar { transform-box: fill-box; transform-origin: 0 50%; }
    @media (prefers-reduced-motion: no-preference) {
      .bar-1 { animation: bar-grow 0.9s cubic-bezier(0.16, 1, 0.3, 1) 0.2s both; }
      .bar-2 { animation: bar-grow 0.9s cubic-bezier(0.16, 1, 0.3, 1) 0.32s both; }
      .bar-3 { animation: bar-grow 0.9s cubic-bezier(0.16, 1, 0.3, 1) 0.44s both; }
      .bar-4 { animation: bar-grow 0.9s cubic-bezier(0.16, 1, 0.3, 1) 0.56s both; }
      .value { animation: value-in 0.4s ease-out 1.2s both; }
    }
    @keyframes bar-grow {
      from { transform: scaleX(0); }
      to { transform: none; }
    }
    @keyframes value-in {
      from { opacity: 0; }
      to { opacity: 1; }
    }
  </style>"""


def platform_bars(x0: int, tops: tuple[int, ...], thickness: int, unit: int, label_x: int, font_size: int) -> str:
    """One row per platform: label, bar with a 4px rounded data end, value at the tip.

    Bars use the deeper lane green so they keep 3:1 against the light card wash."""
    rows = []
    for index, ((name, count), top) in enumerate(zip(HARDWARE_PLATFORMS, tops), start=1):
        end = x0 + count * unit
        baseline = round(top + thickness / 2 + font_size * 0.35)
        bottom = top + thickness
        rows.append(
            f'    <g id="platform-{index}">\n'
            f'      <text x="{label_x}" y="{baseline}" fill="${{soft}}" font-size="{font_size}" text-anchor="end">{name}</text>\n'
            f'      <path class="bar bar-{index}" d="M{x0} {top}H{end - 4}A4 4 0 0 1 {end} {top + 4}V{bottom - 4}A4 4 0 0 1 {end - 4} {bottom}H{x0}Z" fill="${{touch_text}}"/>\n'
            f'      <text class="value" x="{end + 10}" y="{baseline}" fill="${{ink}}" font-size="{font_size}" font-weight="700">{count}</text>\n'
            f'    </g>'
        )
    return "\n".join(rows)


HARDWARE_DESC = (
    "公开硬件项目统一收录在 Hardware Lab 索引，每个附项目介绍、构建证据与使用限制。"
    "条形图按主控平台统计公开项目数："
    + "、".join(f"{name} {count} 个" for name, count in HARDWARE_PLATFORMS)
    + "。"
)

HARDWARE = Template("""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="300" viewBox="0 0 1200 300" role="img" aria-labelledby="title desc">
  <title id="title">Hardware Lab：${prototypes} 个公开硬件项目</title>
  <desc id="desc">${theme_desc}Hardware Lab 项目卡。${prototypes} 个""" + HARDWARE_DESC + """</desc>
  <defs>
    <linearGradient id="cardWash" x1="0" y1="0" x2="1" y2="1"><stop stop-color="${touch}" stop-opacity="0.12"/><stop offset="1" stop-color="${touch}" stop-opacity="0.02"/></linearGradient>
  </defs>
${style}
  <rect x="0.5" y="0.5" width="1199" height="299" rx="18" fill="${page_bg}"/>
  <rect x="0.5" y="0.5" width="1199" height="299" rx="18" fill="url(#cardWash)" stroke="${touch}" stroke-opacity="0.26"/>
  <g id="card-copy">
    <text x="48" y="72" fill="${ink}" font-size="37" font-weight="700">Hardware Lab</text>
    <text x="48" y="107" fill="${touch_text}" font-size="18">硬件原型索引</text>
    <text id="hardware-count" x="48" y="157" fill="${ink}" font-size="23">${prototypes} 个公开硬件项目</text>
  </g>
  <g id="card-tags"><text x="48" y="191" fill="${soft}" font-size="18">项目介绍 · 构建证据 · 使用限制</text></g>
  <path d="M397 48V252" fill="none" stroke="${fig_stroke}"/>
  <g id="card-cta">
    <text x="48" y="257" fill="${touch_text}" font-size="19" font-weight="600">查看项目索引</text>
    <path d="M175 257L188 244M178 244H188V254" fill="none" stroke="${touch_text}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  </g>
  <g id="platform-chart">
    <text x="443" y="75" fill="${ink}" font-size="24" font-weight="600">按主控平台</text>
    <text x="1148" y="75" fill="${muted}" font-size="17" text-anchor="end">公开项目数</text>
    <path d="M560.5 100V258" fill="none" stroke="${fig_stroke}"/>
""" + platform_bars(560, (108, 148, 188, 228), 22, 34, 544, 18) + """
  </g>
</svg>
""")

HARDWARE_MOBILE = Template("""<svg xmlns="http://www.w3.org/2000/svg" width="360" height="362" viewBox="0 0 360 362" role="img" aria-labelledby="title desc">
  <title id="title">Hardware Lab：${prototypes} 个公开硬件项目</title>
  <desc id="desc">${prototypes} 个""" + HARDWARE_DESC + """</desc>
${style}
  <rect x="0.5" y="0.5" width="359" height="361" rx="18" fill="${page_bg}" stroke="${touch}" stroke-opacity="0.35"/>
  <g id="card-copy">
    <text x="24" y="45" fill="${ink}" font-size="27" font-weight="700">Hardware Lab</text>
    <text id="hardware-count" x="24" y="77" fill="${soft}" font-size="18">${prototypes} 个公开硬件项目</text>
  </g>
  <g id="card-tags"><text x="24" y="108" fill="${muted}" font-size="17">项目介绍 · 构建证据 · 使用限制</text></g>
  <g id="platform-chart">
    <text x="24" y="146" fill="${muted}" font-size="17">按主控平台 · 公开项目数</text>
    <path d="M104.5 156V290" fill="none" stroke="${fig_stroke}"/>
""" + platform_bars(104, (162, 196, 230, 264), 20, 12, 92, 17) + """
  </g>
  <path d="M24 306.5H336" stroke="${fig_stroke}"/>
  <g id="card-cta">
    <text x="24" y="339" fill="${touch_text}" font-size="18" font-weight="600">查看项目索引</text>
    <path d="M144 339L156 327M147 327H156V336" fill="none" stroke="${touch_text}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  </g>
</svg>
""")


# The Yi盘 card follows the homepage featured card and the DSH card's anatomy: title,
# descriptor, summary, tags, the repo button and status on the left, the structure diagram
# inset on the right. In the diagram the three nodes sit inside a dashed "U 盘内" boundary
# and the cloud model stays outside it. Each 8s pass lights the steps in causal order:
# context, retrieve, workspace, request, cloud, result, workspace, generate, output, then a
# packet runs the record rail back to the context. The status dot breathes and the button
# shines once per pass. After three passes every animation stops on the base frame, the
# complete diagram, so the card does not keep moving beside the text; reduced motion shows
# that frame from the start.
FLOW_STYLE = """  <style>
    text { font-family: Arial, "PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif; }
    .lit, .packet, .pulse-ring { opacity: 0; }
    .pulse-ring { transform-box: fill-box; transform-origin: center; }
    @media (prefers-reduced-motion: no-preference) {
      .lit-context { animation: lit-context 8s ease-in-out 3; }
      .packet-retrieve { animation: packet-retrieve 8s linear 3; }
      .lit-workspace-in { animation: lit-workspace-in 8s ease-in-out 3; }
      .packet-request { animation: packet-request 8s linear 3; }
      .lit-cloud { animation: lit-cloud 8s ease-in-out 3; }
      .packet-result { animation: packet-result 8s linear 3; }
      .lit-workspace-back { animation: lit-workspace-back 8s ease-in-out 3; }
      .packet-generate { animation: packet-generate 8s linear 3; }
      .lit-output { animation: lit-output 8s ease-in-out 3; }
      .lit-rail { animation: lit-rail 8s ease-in-out 3; }
      .packet-rail { animation: packet-rail 8s linear 3; }
      .status-pulse { animation: status-pulse 8s ease-out 3; }
      .cta-shine { animation: cta-shine 8s ease-in-out 3; }
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
      77% { transform: translateY(-17px); }
      79% { transform: translateY(-78px); }
      81% { transform: translateY(-156px); }
      83% { opacity: 1; transform: translateY(-196px); }
      84%, 100% { opacity: 0; transform: translateY(-196px); }
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

# A node's highlight: a soft outer ring and a tinted fill over the node's own box.
def flow_lit(cls: str, x: float, y: float, width: float, height: float, radius: float, color: str, **extra: str) -> str:
    attrs = "".join(f' {key.replace("_", "-")}="{value}"' for key, value in extra.items())
    return (
        f'<g class="lit {cls}">'
        f'<rect x="{x - 3.5:g}" y="{y - 3.5:g}" width="{width + 7:g}" height="{height + 7:g}" rx="{radius + 3.5:g}" fill="none" stroke="{color}" stroke-opacity="0.18" stroke-width="4"/>'
        f'<rect x="{x:g}" y="{y:g}" width="{width:g}" height="{height:g}" rx="{radius:g}" fill="{color}" fill-opacity="0.07" stroke="{color}" stroke-width="1.5"{attrs}/>'
        "</g>"
    )


FLOW_DESC = (
    "Yi盘：U 盘里的 AI 工作台。资料、任务记录和产出保存在盘内，智能处理主要调用云端模型；状态受控内测。"
    "结构示意，非产品截图：虚线框表示 U 盘内，盘内资料与任务（Inbox 确认后写入长期知识）经检索供 Yi盘工作台使用，受管 Agent 处理当前任务；"
    "生成的产出与任务记录留在盘内，随盘带走，并经记录与沉淀回到盘内资料。框外是云端模型：工作台按需请求，模型按需推理后返回结果。"
)

FLOW = Template("""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="488" viewBox="0 0 1200 488" role="img" aria-labelledby="title desc">
  <title id="title">Yi盘：U 盘里的 AI 工作台</title>
  <desc id="desc">${theme_desc}Yi盘项目卡，标签 U 盘存储、云端模型，"查看公开仓库"按钮。""" + FLOW_DESC + """</desc>
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
    <clipPath id="figClip"><rect x="449" y="49" width="702" height="391" rx="13.5"/></clipPath>
    <filter id="ctaGlow" x="-30%" y="-40%" width="160%" height="230%">
      <feDropShadow dx="0" dy="12" stdDeviation="14" flood-color="${carry}" flood-opacity="0.18"/>
    </filter>
    <clipPath id="ctaClip"><rect x="48" y="290" width="200" height="58" rx="14"/></clipPath>
  </defs>
${style}

  <rect x="0.5" y="0.5" width="1199" height="487" rx="18" fill="${page_bg}"/>
  <rect x="0.5" y="0.5" width="1199" height="487" rx="18" fill="url(#cardWash)"/>
  <rect x="0.5" y="0.5" width="1199" height="487" rx="18" fill="url(#cardGlow)"/>
  <rect x="0.5" y="0.5" width="1199" height="487" rx="18" fill="none" stroke="${carry}" stroke-opacity="0.26"/>

  <g id="card-copy">
    <text x="48" y="72" fill="${ink}" font-size="37" font-weight="700">Yi盘</text>
    <text x="48" y="107" fill="${carry_text}" font-size="18">U 盘里的 AI 工作台</text>
    <text x="48" y="160" fill="${soft}" font-size="23">资料、任务记录和产出保存在盘内，</text>
    <text x="48" y="195" fill="${soft}" font-size="23">智能处理主要调用云端模型。</text>
  </g>
  <g id="card-tags" text-anchor="middle">
    <rect x="48.5" y="222.5" width="99" height="33" rx="8.5" fill="${tag_fill}" stroke="${tag_stroke}"/>
    <text x="98" y="245" fill="${muted}" font-size="17">U 盘存储</text>
    <rect x="157.5" y="222.5" width="99" height="33" rx="8.5" fill="${tag_fill}" stroke="${tag_stroke}"/>
    <text x="207" y="245" fill="${muted}" font-size="17">云端模型</text>
  </g>
  <g id="card-cta">
    <rect x="48" y="290" width="200" height="58" rx="14" fill="url(#ctaFill)" filter="url(#ctaGlow)"/>
    <g clip-path="url(#ctaClip)">
      <path class="cta-shine" d="M0 290H40L20 348H-20Z" fill="url(#ctaShine)"/>
    </g>
    <text x="72" y="325" fill="${cta_ink}" font-size="19" font-weight="700">查看公开仓库</text>
    <path d="M207 326L220 313M210 313H220V323" fill="none" stroke="${cta_ink}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  </g>
  <g id="card-status">
    <circle cx="274" cy="319" r="8" fill="${carry}" opacity="0.18"/>
    <circle class="pulse-ring status-pulse" cx="274" cy="319" r="4" fill="${carry}"/>
    <circle cx="274" cy="319" r="4" fill="${carry}"/>
    <text x="289" y="325" fill="${muted}" font-size="17">受控内测</text>
  </g>

  <g id="flow-figure">
    <rect x="448.5" y="48.5" width="703" height="392" rx="14" fill="${fig_bg}" stroke="${fig_stroke}"/>
    <g clip-path="url(#figClip)">
      <rect x="449" y="49" width="702" height="391" fill="url(#figGrid)"/>
    </g>

    <g id="cloud-branch">
      <g id="link-request">
        <path d="M895 247.5H997" stroke="${link_line}"/>
        <path d="M996 243V252L1003 247.5Z" fill="${link_head}"/>
        <text x="959" y="236" fill="${faint}" font-size="17" text-anchor="middle">按需请求</text>
        <g class="packet packet-request">
          <rect x="898" y="246" width="16" height="3" rx="1.5" fill="url(#trailRight)"/>
          <circle cx="914" cy="247.5" r="7" fill="${link_dot}" opacity="0.2"/>
          <circle cx="914" cy="247.5" r="3.5" fill="${link_dot}"/>
        </g>
      </g>
      <g id="link-result">
        <path d="M902 271.5H1004" stroke="${link_line}"/>
        <path d="M902 267V276L895 271.5Z" fill="${link_head}"/>
        <text x="959" y="295" fill="${faint}" font-size="17" text-anchor="middle">返回结果</text>
        <g class="packet packet-result">
          <rect x="986" y="270" width="16" height="3" rx="1.5" fill="url(#trailLeft)"/>
          <circle cx="986" cy="271.5" r="7" fill="${link_dot}" opacity="0.2"/>
          <circle cx="986" cy="271.5" r="3.5" fill="${link_dot}"/>
        </g>
      </g>
      <g id="flow-cloud">
        <rect x="1004.5" y="212.5" width="128" height="94" rx="12.5" fill="${card}" stroke="${cloud_stroke}" stroke-dasharray="6 5"/>
        """ + flow_lit("lit-cloud", 1004.5, 212.5, 128, 94, 12.5, "${cloud_lit}", stroke_dasharray="6 5") + """
        <text x="1068.5" y="255" fill="${ink}" font-size="22" font-weight="700" text-anchor="middle">云端模型</text>
        <text x="1068.5" y="283" fill="${muted}" font-size="17" text-anchor="middle">按需推理</text>
      </g>
    </g>

    <g id="drive">
      <rect id="drive-boundary" x="468.5" y="98.5" width="446" height="322" rx="14" fill="${carry}" fill-opacity="${drive_fill}" stroke="${carry}" stroke-opacity="0.45" stroke-dasharray="6 5"/>
      <text x="910" y="86" fill="${flow_tag}" font-size="17" text-anchor="end">U 盘内</text>

      <g id="continuity-rail">
        <path d="M524 369.5H496A8 8 0 0 1 488 361.5V157.5A8 8 0 0 1 496 149.5H517" fill="none" stroke="${carry}" stroke-opacity="0.4"/>
        <path d="M517 145V154L524 149.5Z" fill="${carry}" fill-opacity="0.65"/>
        <text fill="${faint}" font-size="17" text-anchor="middle"><tspan x="505" y="225.5">记</tspan><tspan x="505" y="245.5">录</tspan><tspan x="505" y="265.5">·</tspan><tspan x="505" y="285.5">沉</tspan><tspan x="505" y="305.5">淀</tspan></text>
        <g class="lit lit-rail">
          <path d="M524 369.5H496A8 8 0 0 1 488 361.5V157.5A8 8 0 0 1 496 149.5H517" fill="none" stroke="${carry_2}" stroke-width="1.5"/>
          <path d="M517 145V154L524 149.5Z" fill="${carry_2}"/>
        </g>
        <g class="packet packet-rail">
          <rect x="486.5" y="354" width="3" height="16" rx="1.5" fill="url(#trailUp)"/>
          <circle cx="488" cy="354" r="7" fill="${carry_2}" opacity="0.22"/>
          <circle cx="488" cy="354" r="3.5" fill="${carry_2}"/>
        </g>
      </g>

      <g id="step-retrieve">
        <path d="M564 188V217" stroke="${carry}" stroke-opacity="0.45"/>
        <path d="M559 216H569L564 223Z" fill="${carry}" fill-opacity="0.7"/>
        <text x="582" y="210" fill="${faint}" font-size="17">检索 / 继续</text>
        <g class="packet packet-retrieve">
          <rect x="562.5" y="172" width="3" height="16" rx="1.5" fill="url(#trailDown)"/>
          <circle cx="564" cy="188" r="7" fill="${carry_2}" opacity="0.22"/>
          <circle cx="564" cy="188" r="3.5" fill="${carry_2}"/>
        </g>
      </g>
      <g id="step-generate">
        <path d="M564 298V327" stroke="${carry}" stroke-opacity="0.45"/>
        <path d="M559 326H569L564 333Z" fill="${carry}" fill-opacity="0.7"/>
        <text x="582" y="320" fill="${faint}" font-size="17">生成 / 记录</text>
        <g class="packet packet-generate">
          <rect x="562.5" y="282" width="3" height="16" rx="1.5" fill="url(#trailDown)"/>
          <circle cx="564" cy="298" r="7" fill="${carry_2}" opacity="0.22"/>
          <circle cx="564" cy="298" r="3.5" fill="${carry_2}"/>
        </g>
      </g>

      <g id="flow-context">
        <rect x="524.5" y="114.5" width="370" height="70" rx="10.5" fill="${card}" stroke="${carry}" stroke-opacity="0.3"/>
        """ + flow_lit("lit-context", 524.5, 114.5, 370, 70, 10.5, "${carry}") + """
        <text x="544" y="143" fill="${ink}" font-size="22" font-weight="700">盘内资料与任务</text>
        <text x="544" y="170" fill="${muted}" font-size="17">Inbox 确认后写入长期知识</text>
      </g>
      <g id="flow-workspace">
        <rect x="524.5" y="224.5" width="370" height="70" rx="10.5" fill="${card}" stroke="${carry}" stroke-opacity="0.3"/>
        """ + flow_lit("lit-workspace-in", 524.5, 224.5, 370, 70, 10.5, "${carry}") + """
        """ + flow_lit("lit-workspace-back", 524.5, 224.5, 370, 70, 10.5, "${carry}") + """
        <text x="544" y="253" fill="${ink}" font-size="22" font-weight="700">Yi盘工作台</text>
        <text x="544" y="280" fill="${muted}" font-size="17">受管 Agent 处理当前任务</text>
      </g>
      <g id="flow-output">
        <rect x="524.5" y="334.5" width="370" height="70" rx="10.5" fill="${card}" stroke="${carry}" stroke-opacity="0.3"/>
        """ + flow_lit("lit-output", 524.5, 334.5, 370, 70, 10.5, "${carry}") + """
        <text x="544" y="363" fill="${ink}" font-size="22" font-weight="700">产出与任务记录</text>
        <text x="544" y="390" fill="${muted}" font-size="17">留在盘内，随盘带走</text>
      </g>
    </g>
  </g>
</svg>
""")

# Narrow screens get the same card stacked at 360 units: the summary, then the diagram with
# node titles only (the README table and alt text carry the details), then status and link.
# It lights the nodes in the same order on the same 8s pass, without packets.
FLOW_MOBILE = Template("""<svg xmlns="http://www.w3.org/2000/svg" width="360" height="460" viewBox="0 0 360 460" role="img" aria-labelledby="title desc">
  <title id="title">Yi盘：U 盘里的 AI 工作台</title>
  <desc id="desc">""" + FLOW_DESC + """</desc>
${style}
  <rect x="0.5" y="0.5" width="359" height="459" rx="18" fill="${page_bg}" stroke="${carry}" stroke-opacity="0.35"/>
  <g id="card-copy">
    <text x="24" y="45" fill="${ink}" font-size="27" font-weight="700">Yi盘</text>
    <text x="24" y="77" fill="${carry_text}" font-size="18">U 盘里的 AI 工作台</text>
    <text x="24" y="110" fill="${soft}" font-size="17">资料、任务记录和产出保存在盘内，</text>
    <text x="24" y="134" fill="${soft}" font-size="17">智能处理主要调用云端模型。</text>
  </g>

  <g id="flow-figure">
    <g id="cloud-branch">
      <path d="M229 283.5H255M236 295.5H262" stroke="${link_line}"/>
      <path d="M255 279.5V287.5L262 283.5ZM236 291.5V299.5L229 295.5Z" fill="${link_head}"/>
      <g id="flow-cloud">
        <rect x="262.5" y="254.5" width="73" height="70" rx="10" fill="${card}" stroke="${cloud_stroke}" stroke-dasharray="6 5"/>
        """ + flow_lit("lit-cloud", 262.5, 254.5, 73, 70, 10, "${cloud_lit}", stroke_dasharray="6 5") + """
        <text x="299" y="285" fill="${ink}" font-size="18" font-weight="700" text-anchor="middle">云端</text>
        <text x="299" y="307" fill="${ink}" font-size="18" font-weight="700" text-anchor="middle">模型</text>
      </g>
    </g>
    <g id="drive">
      <rect id="drive-boundary" x="24.5" y="186.5" width="216" height="206" rx="12" fill="${carry}" fill-opacity="${drive_fill}" stroke="${carry}" stroke-opacity="0.45" stroke-dasharray="6 5"/>
      <text x="236" y="174" fill="${flow_tag}" font-size="17" text-anchor="end">U 盘内</text>
      <g id="continuity-rail">
        <path d="M52 357.5H44A6 6 0 0 1 38 351.5V227.5A6 6 0 0 1 44 221.5H46" fill="none" stroke="${carry}" stroke-opacity="0.4"/>
        <path d="M46 217.5V225.5L52 221.5Z" fill="${carry}" fill-opacity="0.65"/>
        <g class="lit lit-rail">
          <path d="M52 357.5H44A6 6 0 0 1 38 351.5V227.5A6 6 0 0 1 44 221.5H46" fill="none" stroke="${carry_2}" stroke-width="1.5"/>
          <path d="M46 217.5V225.5L52 221.5Z" fill="${carry_2}"/>
        </g>
      </g>
      <path d="M140 248V258M140 316V326" stroke="${carry}" stroke-opacity="0.45"/>
      <path d="M135 258H145L140 265ZM135 326H145L140 333Z" fill="${carry}" fill-opacity="0.7"/>
      <g id="flow-context">
        <rect x="52.5" y="198.5" width="176" height="46" rx="9" fill="${card}" stroke="${carry}" stroke-opacity="0.3"/>
        """ + flow_lit("lit-context", 52.5, 198.5, 176, 46, 9, "${carry}") + """
        <text x="66" y="228" fill="${ink}" font-size="18" font-weight="700">盘内资料与任务</text>
      </g>
      <g id="flow-workspace">
        <rect x="52.5" y="266.5" width="176" height="46" rx="9" fill="${card}" stroke="${carry}" stroke-opacity="0.3"/>
        """ + flow_lit("lit-workspace-in", 52.5, 266.5, 176, 46, 9, "${carry}") + """
        """ + flow_lit("lit-workspace-back", 52.5, 266.5, 176, 46, 9, "${carry}") + """
        <text x="66" y="296" fill="${ink}" font-size="18" font-weight="700">Yi盘工作台</text>
      </g>
      <g id="flow-output">
        <rect x="52.5" y="334.5" width="176" height="46" rx="9" fill="${card}" stroke="${carry}" stroke-opacity="0.3"/>
        """ + flow_lit("lit-output", 52.5, 334.5, 176, 46, 9, "${carry}") + """
        <text x="66" y="364" fill="${ink}" font-size="18" font-weight="700">产出与任务记录</text>
      </g>
    </g>
  </g>

  <path d="M24 406.5H336" stroke="${fig_stroke}"/>
  <g id="card-status">
    <circle class="pulse-ring status-pulse" cx="30" cy="431" r="4" fill="${carry}"/>
    <circle cx="30" cy="431" r="4" fill="${carry}"/>
    <text x="42" y="437" fill="${muted}" font-size="17">受控内测</text>
  </g>
  <g id="card-cta">
    <text x="312" y="437" fill="${carry_text}" font-size="18" font-weight="700" text-anchor="end">查看公开仓库</text>
    <path d="M318 438L330 426M321 426H330V435" fill="none" stroke="${carry_text}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  </g>
</svg>
""")


# DSH's functional illustration tells its causal story (sessions, packets, projects, usage
# bars, timeline lanes, scan) in three 8s passes. Each pass opens by dimming the complete
# illustration, builds it back stage by stage and ends complete, so passes join seamlessly
# and the card stops on the complete illustration (its base frame). The -0.4s delay starts
# the first pass already dimmed. npm metrics and product facts stay visible throughout;
# transient packets and the scanner are hidden in the base frame and both static variants.
DSH_STYLE = """  <style>
    text { font-family: Arial, "PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif; }
    .mono { font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace; }
    .record, .usage-bars, .time-lane, .cta-arrow { transform-box: fill-box; }
    .usage-bars { transform-origin: center bottom; }
    .time-lane { transform-origin: left center; }
    .packet, .timeline-scan { opacity: 0; }
    @media (prefers-reduced-motion: no-preference) {
      .record-a { animation: record-a 8s ease-in-out -0.4s 3; }
      .record-b { animation: record-b 8s ease-in-out -0.4s 3; }
      .record-c { animation: record-c 8s ease-in-out -0.4s 3; }
      .packet-a { animation: packet-a 8s linear -0.4s 3; }
      .packet-b { animation: packet-b 8s linear -0.4s 3; }
      .packet-c { animation: packet-c 8s linear -0.4s 3; }
      .project-a { animation: project-a 8s ease-in-out -0.4s 3; }
      .project-b { animation: project-b 8s ease-in-out -0.4s 3; }
      .project-c { animation: project-c 8s ease-in-out -0.4s 3; }
      .usage-a { animation: usage-a 8s cubic-bezier(0.2, 0.7, 0.2, 1) -0.4s 3; }
      .usage-b { animation: usage-b 8s cubic-bezier(0.2, 0.7, 0.2, 1) -0.4s 3; }
      .usage-c { animation: usage-c 8s cubic-bezier(0.2, 0.7, 0.2, 1) -0.4s 3; }
      .lane-a { animation: lane-a 8s cubic-bezier(0.2, 0.7, 0.2, 1) -0.4s 3; }
      .lane-b { animation: lane-b 8s cubic-bezier(0.2, 0.7, 0.2, 1) -0.4s 3; }
      .lane-c { animation: lane-c 8s cubic-bezier(0.2, 0.7, 0.2, 1) -0.4s 3; }
      .timeline-scan { animation: timeline-scan 8s ease-in-out -0.4s 3; }
      .cta-arrow { animation: cta-nudge 8s ease-out -0.4s 3; }
    }
    @keyframes record-a {
      0% { opacity: 1; transform: translateY(0); }
      5%, 8% { opacity: 0.35; transform: translateY(8px); }
      12%, 100% { opacity: 1; transform: translateY(0); }
    }
    @keyframes record-b {
      0% { opacity: 1; transform: translateY(0); }
      5%, 10% { opacity: 0.35; transform: translateY(8px); }
      14%, 100% { opacity: 1; transform: translateY(0); }
    }
    @keyframes record-c {
      0% { opacity: 1; transform: translateY(0); }
      5%, 12% { opacity: 0.35; transform: translateY(8px); }
      16%, 100% { opacity: 1; transform: translateY(0); }
    }
    @keyframes packet-a {
      0%, 22% { opacity: 0; transform: translateX(0); }
      23% { opacity: 1; transform: translateX(0); }
      26% { transform: translateX(12px); }
      31% { transform: translateX(55px); }
      35% { opacity: 1; transform: translateX(85px); }
      36%, 100% { opacity: 0; transform: translateX(var(--packet-distance, 98px)); }
    }
    @keyframes packet-b {
      0%, 25% { opacity: 0; transform: translateX(0); }
      26% { opacity: 1; transform: translateX(0); }
      29% { transform: translateX(12px); }
      34% { transform: translateX(55px); }
      38% { opacity: 1; transform: translateX(85px); }
      39%, 100% { opacity: 0; transform: translateX(var(--packet-distance, 98px)); }
    }
    @keyframes packet-c {
      0%, 28% { opacity: 0; transform: translateX(0); }
      29% { opacity: 1; transform: translateX(0); }
      32% { transform: translateX(12px); }
      37% { transform: translateX(55px); }
      41% { opacity: 1; transform: translateX(85px); }
      42%, 100% { opacity: 0; transform: translateX(var(--packet-distance, 98px)); }
    }
    @keyframes project-a {
      0% { opacity: 1; }
      5%, 34% { opacity: 0.4; }
      36% { opacity: 1; }
      39% { opacity: 0.75; }
      42%, 100% { opacity: 1; }
    }
    @keyframes project-b {
      0% { opacity: 1; }
      5%, 37% { opacity: 0.4; }
      39% { opacity: 1; }
      42% { opacity: 0.75; }
      45%, 100% { opacity: 1; }
    }
    @keyframes project-c {
      0% { opacity: 1; }
      5%, 40% { opacity: 0.4; }
      42% { opacity: 1; }
      45% { opacity: 0.75; }
      48%, 100% { opacity: 1; }
    }
    @keyframes usage-a {
      0% { opacity: 1; transform: none; }
      5%, 46% { opacity: 0.35; transform: scaleY(0.15); }
      52% { opacity: 1; transform: scaleY(1.08); }
      56% { transform: scaleY(0.97); }
      59%, 100% { opacity: 1; transform: none; }
    }
    @keyframes usage-b {
      0% { opacity: 1; transform: none; }
      5%, 49% { opacity: 0.35; transform: scaleY(0.15); }
      55% { opacity: 1; transform: scaleY(1.08); }
      59% { transform: scaleY(0.97); }
      62%, 100% { opacity: 1; transform: none; }
    }
    @keyframes usage-c {
      0% { opacity: 1; transform: none; }
      5%, 52% { opacity: 0.35; transform: scaleY(0.15); }
      58% { opacity: 1; transform: scaleY(1.08); }
      62% { transform: scaleY(0.97); }
      65%, 100% { opacity: 1; transform: none; }
    }
    @keyframes lane-a {
      0% { opacity: 1; transform: none; }
      5%, 56% { opacity: 0.35; transform: scaleX(0.1); }
      62% { opacity: 1; transform: scaleX(1.04); }
      66% { transform: scaleX(0.99); }
      69%, 100% { opacity: 1; transform: none; }
    }
    @keyframes lane-b {
      0% { opacity: 1; transform: none; }
      5%, 59% { opacity: 0.35; transform: scaleX(0.1); }
      65% { opacity: 1; transform: scaleX(1.04); }
      69% { transform: scaleX(0.99); }
      72%, 100% { opacity: 1; transform: none; }
    }
    @keyframes lane-c {
      0% { opacity: 1; transform: none; }
      5%, 62% { opacity: 0.35; transform: scaleX(0.1); }
      68% { opacity: 1; transform: scaleX(1.04); }
      72% { transform: scaleX(0.99); }
      75%, 100% { opacity: 1; transform: none; }
    }
    @keyframes timeline-scan {
      0%, 72% { opacity: 0; transform: translateX(0); }
      74% { opacity: 0.95; transform: translateX(0); }
      90% { opacity: 0.95; transform: translateX(290px); }
      92%, 100% { opacity: 0; transform: translateX(290px); }
    }
    @keyframes cta-nudge {
      0%, 92% { transform: translateX(0); }
      95% { transform: translateX(6px); }
      98% { transform: translateX(1px); }
      100% { transform: translateX(0); }
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
    <path class="cta-arrow" d="M137 377L150 364M140 364H150V374" fill="none" stroke="${see_text}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  </g>
  <g id="card-status"><text x="350" y="377" fill="${muted}" font-size="17" text-anchor="end">npm · MIT</text></g>
  <g id="dsh-panel">
    <text x="443" y="75" fill="${ink}" font-size="24" font-weight="600">会话 → 项目 → 时间线</text>
    <text id="flow-caption" x="1148" y="75" fill="${muted}" font-size="17" text-anchor="end">功能示意</text>
    <text id="session-source" x="443" y="128" fill="${muted}" font-size="17">会话记录</text>
    <text id="project-grouping" x="645" y="128" fill="${muted}" font-size="17">按项目归集</text>
    <g id="card-views">
      <g id="view-2"><text x="815" y="128" fill="${muted}" font-size="17">开发时间线</text></g>
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


# Link badges share one anatomy: an uppercase label, a rule, then the action. Primary badges
# are solid Yi盘 orange in both themes; secondary badges are outlined and follow the page
# theme through their own color-scheme query, so they are not dark blocks on a light page.
BADGE_FONT = 'Arial, "PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif'
BADGES = {
    "badge-studio": ("STUDIO", "访问主页", "访问主页", "前往 Rongyi Studio 个人主页。", True),
    "badge-build-log": ("BUILD", "开发记录", "查看开发记录", "前往 Rongyi 的公开开发记录。", False),
    "badge-product-facts": ("FACTS", "产品事实与限制", "Yi盘产品事实与限制", "查看 Yi盘已确认的产品事实、限制和验证范围。", False),
    "badge-feedback": ("FEEDBACK", "提交反馈", "提交 Yi盘反馈", "前往 Yi盘公开反馈页面。", True),
}
# Arial Bold advance widths (units per 1000) of the label letters; labels are 10px with 1px tracking.
LABEL_ADVANCE = {"A": 722, "B": 722, "C": 722, "D": 722, "E": 667, "F": 611, "I": 278, "K": 722, "L": 611, "O": 778, "S": 667, "T": 611, "U": 722}


def badge(label: str, action: str, title: str, desc: str, primary: bool) -> str:
    label_end = 14 + sum(LABEL_ADVANCE[letter] for letter in label) / 100 + len(label)
    rule = round(label_end + 12)
    action_x = rule + 14
    width = action_x + 14 * len(action) + 16
    head = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="36" viewBox="0 0 {width} 36" role="img" aria-labelledby="title desc">\n'
        f'  <title id="title">{title}</title>\n'
        f'  <desc id="desc">{desc}</desc>\n'
        f'  <style>\n'
        f'    text {{ font-family: {BADGE_FONT}; font-weight: 700; }}\n'
    )
    if primary:
        return head + (
            f'  </style>\n'
            f'  <rect x="0.75" y="0.75" width="{width - 1.5:g}" height="34.5" rx="7.5" fill="#c44227" stroke="#ff8a70" stroke-width="1.5"/>\n'
            f'  <rect x="2" y="2" width="{width - 4}" height="32" rx="6.5" fill="none" stroke="#ffffff" stroke-opacity="0.14"/>\n'
            f'  <text class="label" x="14" y="22" fill="#ffffff" font-size="10" letter-spacing="1">{label}</text>\n'
            f'  <path d="M{rule} 8V28" stroke="#ffffff" stroke-opacity="0.42"/>\n'
            f'  <text class="action" x="{action_x}" y="23" fill="#ffffff" font-size="14">{action}</text>\n'
            f'</svg>\n'
        )
    return head + (
        f'    .surface {{ fill: #ffffff; }}\n'
        f'    .label {{ fill: #c8452a; }}\n'
        f'    .action {{ fill: #18202a; }}\n'
        f'    @media (prefers-color-scheme: dark) {{\n'
        f'      .surface {{ fill: #202631; }}\n'
        f'      .label {{ fill: #ff8a70; }}\n'
        f'      .action {{ fill: #f4f6f8; }}\n'
        f'    }}\n'
        f'  </style>\n'
        f'  <rect class="surface" x="0.5" y="0.5" width="{width - 1}" height="35" rx="8" fill="#ffffff" stroke="#e45738"/>\n'
        f'  <text class="label" x="14" y="22" fill="#c8452a" font-size="10" letter-spacing="1">{label}</text>\n'
        f'  <path d="M{rule} 8V28" stroke="#e45738" stroke-opacity="0.55"/>\n'
        f'  <text class="action" x="{action_x}" y="23" fill="#18202a" font-size="14">{action}</text>\n'
        f'</svg>\n'
    )


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
        "photo_pot": media_uri("esp32-s3-multimodal-smart-pot.webp"),
        "photo_traffic": media_uri("adaptive-traffic-signal-system.webp"),
        "photo_voice": media_uri("esp32-s3-health-voice-terminal.webp"),
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


def both_captures(svg: str) -> str:
    """Adaptive heroes carry both real DSH captures; CSS shows the one matching the theme."""
    image = re.search(r'<image class="shot-pan dsh-capture"[^>]+/>', svg).group(0)
    light_image = image.replace('dsh-capture"', 'dsh-capture theme-light"')
    dark_image = image.replace('dsh-capture"', 'dsh-capture theme-dark"').replace(
        media_uri('dsh-trends-light.webp'), media_uri('dsh-trends-dark.webp'))
    return svg.replace(image, light_image + "\n        " + dark_image)


# Placeholder npm figures for version hashes: the daily refresh changes the numbers
# inside the DSH SVGs, but not their ?v= in README, so the bot stays inside its markers.
NPM_PLACEHOLDER = {"npm_downloads": "0", "npm_latest": "0.0.0", "npm_versions": "0", "npm_as_of": "0000-00-00"}
VERSIONED_ASSET = re.compile(r"(\./assets/([\w.-]+))\?v=[0-9A-Za-z]+")


def stamp_versions(readme: str, hash_sources: dict[Path, str]) -> str:
    """Point every README asset link at ?v=<first 8 hex of its content hash>."""
    def version(match: re.Match) -> str:
        path = ASSETS / match.group(2)
        if path in hash_sources:
            content = hash_sources[path].encode("utf-8")
        elif path.exists():
            content = path.read_bytes()
        else:
            raise SystemExit(f"README references a missing asset: {path}")
        return f"{match.group(1)}?v={hashlib.sha256(content).hexdigest()[:8]}"
    return VERSIONED_ASSET.sub(version, readme)


def main() -> int:
    check = "--check" in sys.argv[1:]
    outputs = {
        "hero": (HERO, HERO_STYLE, hero_media),
        "yipan-flow": (FLOW, FLOW_STYLE, lambda theme: {}),
        "dsh-card": (DSH, DSH_STYLE, npm_figures),
        "hardware-card": (HARDWARE, HARDWARE_STYLE, lambda theme: {}),
    }
    rendered: dict[Path, str] = {}
    hash_sources: dict[Path, str] = {}
    for stem, (template, style, extra) in outputs.items():
        npm = stem == "dsh-card"
        for theme, palette in PALETTES.items():
            path = ASSETS / f"{stem}-{theme}.svg"
            rendered[path] = render(template, style, palette, extra(theme))
            if npm:
                hash_sources[path] = render(template, style, palette, NPM_PLACEHOLDER)
        path = ASSETS / f"{stem}-still.svg"
        rendered[path] = render_adaptive(template, style, extra('light'))
        if npm:
            hash_sources[path] = render_adaptive(template, style, NPM_PLACEHOLDER)
    hero_path = ASSETS / "hero-still.svg"
    rendered[hero_path] = both_captures(rendered[hero_path])
    # Narrow screens: one adaptive file with motion and one still file per card.
    narrow = {
        "hero": (HERO_NARROW, HERO_STYLE, hero_media('light'), both_captures),
        "yipan-flow": (FLOW_MOBILE, FLOW_STYLE, {}, lambda svg: svg),
        "hardware-card": (HARDWARE_MOBILE, HARDWARE_STYLE, {}, lambda svg: svg),
    }
    for stem, (template, style, extra, finish) in narrow.items():
        for suffix, motion in (("mobile", True), ("mobile-still", False)):
            rendered[ASSETS / f"{stem}-{suffix}.svg"] = finish(render_adaptive(template, style, extra, motion=motion))
    for name, motion in (("dsh-card-mobile.svg", True), ("dsh-card-mobile-still.svg", False)):
        rendered[ASSETS / name] = render_adaptive(DSH_MOBILE, DSH_STYLE, npm_figures('light'), motion=motion)
        hash_sources[ASSETS / name] = render_adaptive(DSH_MOBILE, DSH_STYLE, NPM_PLACEHOLDER, motion=motion)
    for stem, spec in BADGES.items():
        rendered[ASSETS / f"{stem}.svg"] = badge(*spec)
    readme = Path('README.md')
    stamped = stamp_versions(readme.read_text(encoding='utf-8'), {**rendered, **hash_sources})
    rendered[readme] = replace_snapshot(stamped, json.loads(NPM_STATS.read_text()))
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
            "Generated SVG assets, asset versions or npm text are out of date; run python3 scripts/render-svg.py:\n- " + "\n- ".join(stale),
            file=sys.stderr,
        )
        return 1
    if check:
        print("Generated SVG assets, README asset versions and npm text match scripts/render-svg.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
