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
import math
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
        "led_red": "#ff6369",
        "led_amber": "#ffc53d",
        "led_green": "#46d89c",
        "led_red_off": "#3a1a1d",
        "led_amber_off": "#3a2f14",
        "led_green_off": "#183a2e",
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
        # The card CTA follows the primary badge: white ink on Yi盘 orange. Both
        # gradient ends keep at least 4.5:1 against white (5.63:1 and 4.55:1).
        "cta_ink": "#ffffff",
        "cta_from": "#b93c22",
        "cta_to": "#cf482b",
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
        "faint": "#646d7b",
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
        "led_red": "#e5484d",
        "led_amber": "#f0a020",
        "led_green": "#1aa572",
        "led_red_off": "#f9dede",
        "led_amber_off": "#fcefd0",
        "led_green_off": "#cfe9dc",
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
        # Same white-on-orange CTA in both themes, matching the primary badges.
        "cta_ink": "#ffffff",
        "cta_from": "#b93c22",
        "cta_to": "#cf482b",
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
    .lane-dot-carry, .lane-dot-see, .lane-dot-touch { opacity: 0.32; }
    .lane-ring-carry, .lane-ring-see, .lane-ring-touch { opacity: 0; transform-box: fill-box; transform-origin: center; }
    @media (prefers-reduced-motion: no-preference) {
      .entry-carry { animation: entry-in 0.6s cubic-bezier(0.16, 1, 0.3, 1) 0.1s both; }
      .entry-see { animation: entry-in 0.6s cubic-bezier(0.16, 1, 0.3, 1) 0.25s both; }
      .entry-touch { animation: entry-in 0.6s cubic-bezier(0.16, 1, 0.3, 1) 0.4s both; }
      .drive-shine { animation: drive-shine 0.85s cubic-bezier(0.25, 1, 0.5, 1) 0.9s both; }
      .shot-pan { animation: shot-pan 2.8s cubic-bezier(0.4, 0, 0.2, 1) 1.2s both; }
      .deck-1 { animation: deck-1 0.75s cubic-bezier(0.16, 1, 0.3, 1) 1.6s both; }
      .deck-2 { animation: deck-2 0.75s cubic-bezier(0.16, 1, 0.3, 1) 1.75s both; }
      .deck-3 { animation: deck-3 0.75s cubic-bezier(0.16, 1, 0.3, 1) 1.9s both; }
      .lane-dot-carry { animation: lane-dot 6s ease-in-out 4.2s 3; }
      .lane-ring-carry { animation: lane-ring 6s ease-out 4.2s 3; }
      .lane-dot-see { animation: lane-dot 6s ease-in-out 6.2s 3; }
      .lane-ring-see { animation: lane-ring 6s ease-out 6.2s 3; }
      .lane-dot-touch { animation: lane-dot 6s ease-in-out 8.2s 3; }
      .lane-ring-touch { animation: lane-ring 6s ease-out 8.2s 3; }
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
    @keyframes lane-dot {
      0%, 18% { opacity: 0.32; }
      22%, 30% { opacity: 1; }
      38%, 100% { opacity: 0.32; }
    }
    @keyframes lane-ring {
      0%, 18% { opacity: 0; transform: none; }
      22% { opacity: 0.55; transform: none; }
      34%, 100% { opacity: 0; transform: scale(2); }
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
    <circle id="lane-dot-carry" class="lane-dot-carry" cx="58" cy="152" r="4.5" fill="${carry}"/>
    <circle class="lane-ring-carry" cx="58" cy="152" r="4.5" fill="none" stroke="${carry}" stroke-width="1.5"/>
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
    <circle id="lane-dot-see" class="lane-dot-see" cx="482" cy="152" r="4.5" fill="${see}"/>
    <circle class="lane-ring-see" cx="482" cy="152" r="4.5" fill="none" stroke="${see}" stroke-width="1.5"/>
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
    <circle id="lane-dot-touch" class="lane-dot-touch" cx="834" cy="152" r="4.5" fill="${touch}"/>
    <circle class="lane-ring-touch" cx="834" cy="152" r="4.5" fill="none" stroke="${touch}" stroke-width="1.5"/>
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
    <circle id="lane-dot-carry" class="lane-dot-carry" cx="30" cy="140" r="3.5" fill="${carry}"/>
    <circle class="lane-ring-carry" cx="30" cy="140" r="3.5" fill="none" stroke="${carry}" stroke-width="1.5"/>
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
    <circle id="lane-dot-see" class="lane-dot-see" cx="30" cy="266" r="3.5" fill="${see}"/>
    <circle class="lane-ring-see" cx="30" cy="266" r="3.5" fill="none" stroke="${see}" stroke-width="1.5"/>
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
    <circle id="lane-dot-touch" class="lane-dot-touch" cx="30" cy="392" r="3.5" fill="${touch}"/>
    <circle class="lane-ring-touch" cx="30" cy="392" r="3.5" fill="none" stroke="${touch}" stroke-width="1.5"/>
    <text x="40" y="402" fill="${touch_text}" font-size="26" font-weight="800" letter-spacing="-0.4">Hardware Lab</text>
    <text x="40" y="428" fill="${soft}" font-size="17">${prototypes} 个硬件原型</text>
    <text x="40" y="456" fill="${muted}" font-size="17">历史原型照片</text>
    <g id="photo-deck" transform="translate(278 420) scale(0.42)">
""" + PHOTO_DECK + """    </g>
  </g>
</svg>
""")

# The Hardware Lab strip is a small circuit board: each sensor pad ripples as its signal leaves,
# the signals run along the traces with a glowing tail into the HW LAB chip, the chip lights and
# a wave runs across its pins, then the signal runs out and three LEDs light in turn. The pin-1
# dot ticks once a second between passes. It loops every 6s like the original strip; reduced
# motion shows the still board. Labels are at least 17 units so they stay readable when GitHub
# scales the image down.
STRIP_STYLE_BASE = """  <style>
    text { font-family: Arial, "PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif; }
    .mono { font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace; }
    .signal, .chip-on, .led-on, .comet, .pin-hi, .pad-ring, .bloom { opacity: 0; }
    .pad-ring, .bloom { transform-box: fill-box; transform-origin: center; }
    @media (prefers-reduced-motion: no-preference) {
      .pad-a { animation: pad-a 6s ease-out infinite; }
      .pad-b { animation: pad-b 6s ease-out infinite; }
      .pad-c { animation: pad-c 6s ease-out infinite; }
      .sig-in-a { animation: sig-in-a 6s linear infinite; }
      .sig-in-b { animation: sig-in-b 6s linear infinite; }
      .sig-in-c { animation: sig-in-c 6s linear infinite; }
      .comet-in-a { animation: comet-in-a 6s linear infinite; }
      .comet-in-b { animation: comet-in-b 6s linear infinite; }
      .comet-in-c { animation: comet-in-c 6s linear infinite; }
      .chip-on { animation: chip-on 6s ease-in-out infinite; }
      .pin-hi { animation: pin-wave 6s ease-out infinite; }
      .pin-1 { animation-delay: 0.08s; }
      .pin-2 { animation-delay: 0.16s; }
      .pin-3 { animation-delay: 0.24s; }
      .pin-4 { animation-delay: 0.32s; }
      .pin-5 { animation-delay: 0.4s; }
      .pin-6 { animation-delay: 0.48s; }
      .sig-out-a { animation: sig-out-a 6s linear infinite; }
      .sig-out-b { animation: sig-out-b 6s linear infinite; }
      .sig-out-c { animation: sig-out-c 6s linear infinite; }
      .comet-out-a { animation: comet-out-a 6s linear infinite; }
      .comet-out-b { animation: comet-out-b 6s linear infinite; }
      .comet-out-c { animation: comet-out-c 6s linear infinite; }
      .led-a { animation: led-a 6s ease-in-out infinite; }
      .led-b { animation: led-b 6s ease-in-out infinite; }
      .led-c { animation: led-c 6s ease-in-out infinite; }
      .bloom-a { animation: bloom-a 6s ease-out infinite; }
      .bloom-b { animation: bloom-b 6s ease-out infinite; }
      .bloom-c { animation: bloom-c 6s ease-out infinite; }
      .heartbeat { animation: heartbeat 6s ease-out infinite; }
    }
    @keyframes pad-a {
      0%, 0.5% { opacity: 0; transform: none; }
      1% { opacity: 0.75; transform: none; }
      6.5%, 100% { opacity: 0; transform: scale(2.4); }
    }
    @keyframes pad-b {
      0%, 2.5% { opacity: 0; transform: none; }
      3% { opacity: 0.75; transform: none; }
      8.5%, 100% { opacity: 0; transform: scale(2.4); }
    }
    @keyframes pad-c {
      0%, 4.5% { opacity: 0; transform: none; }
      5% { opacity: 0.75; transform: none; }
      10.5%, 100% { opacity: 0; transform: scale(2.4); }
    }
    @keyframes pin-wave {
      0%, 35% { opacity: 0; }
      36.5% { opacity: 1; }
      40%, 100% { opacity: 0; }
    }
    @keyframes heartbeat {
      0%, 16.67%, 33.33%, 50%, 66.67%, 83.33%, 100% { opacity: 1; }
      5%, 16.6%, 21.67%, 33.26%, 38.33%, 49.93%, 55%, 66.6%, 71.67%, 83.26%, 88.33%, 99.93% { opacity: 0.25; }
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
    @keyframes bloom-a {
      0%, 73.5% { opacity: 0; transform: none; }
      74% { opacity: 0.8; transform: none; }
      83%, 100% { opacity: 0; transform: scale(2.8); }
    }
    @keyframes bloom-b {
      0%, 75.5% { opacity: 0; transform: none; }
      76% { opacity: 0.8; transform: none; }
      85%, 100% { opacity: 0; transform: scale(2.8); }
    }
    @keyframes bloom-c {
      0%, 77.5% { opacity: 0; transform: none; }
      78% { opacity: 0.8; transform: none; }
      87%, 100% { opacity: 0; transform: scale(2.8); }
    }
  </style>"""

STRIP = Template("""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="170" viewBox="0 0 1200 170" role="img" aria-labelledby="title desc">
  <title id="title">Hardware Lab 电路走线示意</title>
  <desc id="desc">${theme_desc}电路板横条。左侧三路传感器信号沿走线汇入中间标注 HW LAB 与 ${prototypes} PROTOTYPES 的芯片，芯片亮起后信号继续流向右侧红、黄、绿三颗 LED，LED 依次点亮。结构示意，非实物照片。</desc>
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
    <radialGradient id="ledGlow-a">
      <stop stop-color="${led_red}" stop-opacity="0.6"/>
      <stop offset="1" stop-color="${led_red}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="ledGlow-b">
      <stop stop-color="${led_amber}" stop-opacity="0.6"/>
      <stop offset="1" stop-color="${led_amber}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="ledGlow-c">
      <stop stop-color="${led_green}" stop-opacity="0.6"/>
      <stop offset="1" stop-color="${led_green}" stop-opacity="0"/>
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

  <text x="40" y="48" class="mono" fill="${touch_text}" font-size="17" letter-spacing="1.6">HARDWARE LAB / SENSOR TO OUTPUT</text>
  <text x="1160" y="48" class="mono" fill="${muted}" font-size="17" letter-spacing="1" text-anchor="end">ESP32 · STM32 · RPi · ARDUINO</text>

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
  <g id="trace-comets" fill="none" stroke="${pulse}" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="44 2000">
    <path class="comet comet-in-a" d="M60 82H280L298 100H520" stroke-width="8" stroke-opacity="0.2"/><path class="comet comet-in-a" d="M60 82H280L298 100H520" stroke-width="3"/>
    <path class="comet comet-in-b" d="M60 108H520" stroke-width="8" stroke-opacity="0.2"/><path class="comet comet-in-b" d="M60 108H520" stroke-width="3"/>
    <path class="comet comet-in-c" d="M60 134H280L298 116H520" stroke-width="8" stroke-opacity="0.2"/><path class="comet comet-in-c" d="M60 134H280L298 116H520" stroke-width="3"/>
    <path class="comet comet-out-a" d="M680 100H902L920 82H1130" stroke-width="8" stroke-opacity="0.2"/><path class="comet comet-out-a" d="M680 100H902L920 82H1130" stroke-width="3"/>
    <path class="comet comet-out-b" d="M680 108H1130" stroke-width="8" stroke-opacity="0.2"/><path class="comet comet-out-b" d="M680 108H1130" stroke-width="3"/>
    <path class="comet comet-out-c" d="M680 116H902L920 134H1130" stroke-width="8" stroke-opacity="0.2"/><path class="comet comet-out-c" d="M680 116H902L920 134H1130" stroke-width="3"/>
  </g>
  <g fill="${zone_fill}" stroke="${touch}" stroke-width="2">
    <circle cx="54" cy="82" r="6"/>
    <circle cx="54" cy="108" r="6"/>
    <circle cx="54" cy="134" r="6"/>
  </g>
  <g id="pad-ripples" fill="none" stroke="${touch}" stroke-width="1.5">
    <circle class="pad-ring pad-a" cx="54" cy="82" r="6"/>
    <circle class="pad-ring pad-b" cx="54" cy="108" r="6"/>
    <circle class="pad-ring pad-c" cx="54" cy="134" r="6"/>
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
    <circle class="heartbeat" cx="531" cy="83" r="2.6" fill="${touch_text}"/>
    <rect class="chip-on" x="513" y="65" width="174" height="86" rx="11" fill="none" stroke="${touch}" stroke-width="2"/>
    <text x="600" y="104" fill="${ink}" font-size="20" font-weight="800" letter-spacing="1" text-anchor="middle">HW LAB</text>
    <text class="mono" x="600" y="131" fill="${touch_text}" font-size="17" letter-spacing="0.5" text-anchor="middle">${prototypes} PROTOTYPES</text>
  </g>
  <g id="chip-bus" stroke="${pulse}" stroke-width="2.5" stroke-linecap="round">
    <path class="pin-hi pin-0" d="M540 72V63M540 144V153"/>
    <path class="pin-hi pin-1" d="M560 72V63M560 144V153"/>
    <path class="pin-hi pin-2" d="M580 72V63M580 144V153"/>
    <path class="pin-hi pin-3" d="M600 72V63M600 144V153"/>
    <path class="pin-hi pin-4" d="M620 72V63M620 144V153"/>
    <path class="pin-hi pin-5" d="M640 72V63M640 144V153"/>
    <path class="pin-hi pin-6" d="M660 72V63M660 144V153"/>
  </g>

  <circle cx="1138" cy="82" r="6" fill="${led_red_off}" stroke="${led_red}" stroke-opacity="0.55"/>
  <g class="led-on led-a"><circle cx="1138" cy="82" r="17" fill="url(#ledGlow-a)"/><circle cx="1138" cy="82" r="6" fill="${led_red}"/></g>
  <circle class="bloom bloom-a" cx="1138" cy="82" r="6" fill="none" stroke="${led_red}" stroke-width="1.5"/>
  <circle cx="1138" cy="108" r="6" fill="${led_amber_off}" stroke="${led_amber}" stroke-opacity="0.55"/>
  <g class="led-on led-b"><circle cx="1138" cy="108" r="17" fill="url(#ledGlow-b)"/><circle cx="1138" cy="108" r="6" fill="${led_amber}"/></g>
  <circle class="bloom bloom-b" cx="1138" cy="108" r="6" fill="none" stroke="${led_amber}" stroke-width="1.5"/>
  <circle cx="1138" cy="134" r="6" fill="${led_green_off}" stroke="${led_green}" stroke-opacity="0.55"/>
  <g class="led-on led-c"><circle cx="1138" cy="134" r="17" fill="url(#ledGlow-c)"/><circle cx="1138" cy="134" r="6" fill="${led_green}"/></g>
  <circle class="bloom bloom-c" cx="1138" cy="134" r="6" fill="none" stroke="${led_green}" stroke-width="1.5"/>

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


def signal_keyframes(name: str, points: tuple[tuple[int, int], ...], start: int, end: int) -> str:
    """A signal that fades in at start%, follows the trace at constant speed and fades out after end%."""
    lengths = [((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5 for (x0, y0), (x1, y1) in zip(points, points[1:])]
    total = sum(lengths)

    def shift(point: tuple[int, int]) -> str:
        return f"translate({point[0] - points[0][0]}px, {point[1] - points[0][1]}px)"

    rows = [
        f"      0%, {start - 1}% {{ transform: translate(0, 0); opacity: 0; }}",
        f"      {start}% {{ transform: translate(0, 0); opacity: 1; }}",
    ]
    travelled = 0.0
    for point, length in zip(points[1:-1], lengths):
        travelled += length
        rows.append(f"      {start + (end - start) * travelled / total:.1f}% {{ transform: {shift(point)}; }}")
    rows.append(f"      {end}% {{ transform: {shift(points[-1])}; opacity: 1; }}")
    rows.append(f"      {end + 1}%, 100% {{ transform: {shift(points[-1])}; opacity: 0; }}")
    return f"    @keyframes {name} {{\n" + "\n".join(rows) + "\n    }"


# Tail length in viewBox units: the desktop traces are ~460 long, the narrow ones ~70.
COMET_TAIL = 44
COMET_TAIL_NARROW = 22
SIGNAL_KEYFRAMES = re.compile(r"    @keyframes sig-(in|out)-([abc]) \{\n(.*?)\n    \}", re.DOTALL)
SIGNAL_ROW = re.compile(r"(?P<points>[\d.%, ]+?)\s*\{\s*transform:\s*translateX?\((?P<shift>[^)]*)\);(?:\s*opacity:\s*(?P<opacity>[\d.]+);)?\s*\}")


def number(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def comet_keyframes(style: str, tail: int = COMET_TAIL) -> str:
    """Tail keyframes read from each signal's own keyframes, so the glow stays under the dot.

    The trace is dashed into one tail-long dash; its offset follows the distance the
    signal has travelled, then the tail drains into the end pad at the same speed and fades.
    """
    blocks = []
    for match in SIGNAL_KEYFRAMES.finditer(style):
        stops = []
        for row in SIGNAL_ROW.finditer(match.group(3)):
            shift = [float(value) for value in re.findall(r"-?[\d.]+", row.group("shift"))] + [0.0]
            opacity = row.group("opacity")
            for point in re.findall(r"[\d.]+(?=%)", row.group("points")):
                stops.append((float(point), shift[0], shift[1], None if opacity is None else float(opacity)))
        stops.sort()
        start = next(point for point, _, _, opacity in stops if opacity == 1)
        end = max(point for point, _, _, opacity in stops if opacity == 1)
        hidden = max(point for point, _, _, _ in stops if point < start)
        rows = [f"      0%, {number(hidden)}% {{ opacity: 0; stroke-dashoffset: {tail}px; }}"]
        travelled, previous = 0.0, None
        for point, x, y, _ in stops:
            if not start <= point <= end:
                continue
            if previous is not None:
                travelled += ((x - previous[0]) ** 2 + (y - previous[1]) ** 2) ** 0.5
            previous = (x, y)
            rows.append(f"      {number(point)}% {{ opacity: 1; stroke-dashoffset: {number(tail - travelled)}px; }}")
        drained = end + (end - start) * tail / travelled
        rows.append(f"      {number(drained)}%, 100% {{ opacity: 0; stroke-dashoffset: {number(-travelled)}px; }}")
        name = f"comet-{match.group(1)}-{match.group(2)}"
        blocks.append(f"    @keyframes {name} {{\n" + "\n".join(rows) + "\n    }")
    if len(blocks) != 6:
        raise ValueError("expected six strip signals")
    return style.replace("  </style>", "\n".join(blocks) + "\n  </style>", 1)


STRIP_STYLE = comet_keyframes(STRIP_STYLE_BASE)


# The narrow strip keeps the same board, chip, LEDs and 6s story on shorter traces. Its signals
# keep the desktop timing windows, so only their paths are regenerated.
STRIP_MOBILE_SIGNALS = {
    "sig-in-a": (((36, 124), (52, 124), (70, 142), (100, 142)), 2, 30),
    "sig-in-b": (((36, 150), (100, 150)), 4, 32),
    "sig-in-c": (((36, 176), (52, 176), (70, 158), (100, 158)), 6, 34),
    "sig-out-a": (((260, 142), (272, 142), (290, 124), (324, 124)), 46, 72),
    "sig-out-b": (((260, 150), (324, 150)), 48, 74),
    "sig-out-c": (((260, 158), (272, 158), (290, 176), (324, 176)), 50, 76),
}


def narrow_strip_style() -> str:
    style = STRIP_STYLE_BASE
    for name, (points, start, end) in STRIP_MOBILE_SIGNALS.items():
        keyframes = signal_keyframes(name, points, start, end)
        style, count = re.subn(rf"    @keyframes {name} \{{\n.*?\n    \}}", lambda _: keyframes, style, count=1, flags=re.DOTALL)
        if count != 1:
            raise ValueError(f"missing keyframes {name}")
    return comet_keyframes(style, COMET_TAIL_NARROW)


STRIP_MOBILE = Template("""<svg xmlns="http://www.w3.org/2000/svg" width="360" height="222" viewBox="0 0 360 222" role="img" aria-labelledby="title desc">
  <title id="title">Hardware Lab 电路走线示意</title>
  <desc id="desc">电路板示意。左侧三路传感器信号沿走线汇入中间标注 HW LAB 与 ${prototypes} PROTOTYPES 的芯片，芯片亮起后信号继续流向右侧红、黄、绿三颗 LED，LED 依次点亮。结构示意，非实物照片。</desc>
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
    <radialGradient id="ledGlow-a">
      <stop stop-color="${led_red}" stop-opacity="0.6"/>
      <stop offset="1" stop-color="${led_red}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="ledGlow-b">
      <stop stop-color="${led_amber}" stop-opacity="0.6"/>
      <stop offset="1" stop-color="${led_amber}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="ledGlow-c">
      <stop stop-color="${led_green}" stop-opacity="0.6"/>
      <stop offset="1" stop-color="${led_green}" stop-opacity="0"/>
    </radialGradient>
    <pattern id="dots" width="20" height="20" patternUnits="userSpaceOnUse">
      <circle cx="10" cy="10" r="0.9" fill="${touch}" opacity="0.18"/>
    </pattern>
    <clipPath id="panelClip">
      <rect x="10" y="10" width="340" height="202" rx="14"/>
    </clipPath>
  </defs>
${style}

  <rect x="0.5" y="0.5" width="359" height="221" rx="18" fill="${shell}" stroke="${shell_stroke}"/>
  <rect x="10" y="10" width="340" height="202" rx="14" fill="url(#surface)" stroke="${panel_stroke}"/>
  <g clip-path="url(#panelClip)">
    <rect x="10" y="10" width="340" height="202" fill="url(#dots)"/>
  </g>
  <rect x="10.5" y="10.5" width="339" height="201" rx="13.5" fill="none" stroke="url(#edge)" opacity="0.8"/>

  <text x="28" y="46" class="mono" fill="${touch_text}" font-size="17" letter-spacing="1.6">HARDWARE LAB</text>
  <text x="28" y="74" fill="${muted}" font-size="17">ESP32 · STM32 · RPi · ARDUINO</text>

  <g id="traces-in" fill="none" stroke="${touch}" stroke-opacity="0.5" stroke-width="2" stroke-linejoin="round">
    <path d="M36 124H52L70 142H100"/>
    <path d="M36 150H100"/>
    <path d="M36 176H52L70 158H100"/>
  </g>
  <g id="traces-out" fill="none" stroke="${touch}" stroke-opacity="0.5" stroke-width="2" stroke-linejoin="round">
    <path d="M260 142H272L290 124H324"/>
    <path d="M260 150H324"/>
    <path d="M260 158H272L290 176H324"/>
  </g>
  <g id="trace-comets" fill="none" stroke="${pulse}" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="22 2000">
    <path class="comet comet-in-a" d="M36 124H52L70 142H100" stroke-width="8" stroke-opacity="0.2"/><path class="comet comet-in-a" d="M36 124H52L70 142H100" stroke-width="3"/>
    <path class="comet comet-in-b" d="M36 150H100" stroke-width="8" stroke-opacity="0.2"/><path class="comet comet-in-b" d="M36 150H100" stroke-width="3"/>
    <path class="comet comet-in-c" d="M36 176H52L70 158H100" stroke-width="8" stroke-opacity="0.2"/><path class="comet comet-in-c" d="M36 176H52L70 158H100" stroke-width="3"/>
    <path class="comet comet-out-a" d="M260 142H272L290 124H324" stroke-width="8" stroke-opacity="0.2"/><path class="comet comet-out-a" d="M260 142H272L290 124H324" stroke-width="3"/>
    <path class="comet comet-out-b" d="M260 150H324" stroke-width="8" stroke-opacity="0.2"/><path class="comet comet-out-b" d="M260 150H324" stroke-width="3"/>
    <path class="comet comet-out-c" d="M260 158H272L290 176H324" stroke-width="8" stroke-opacity="0.2"/><path class="comet comet-out-c" d="M260 158H272L290 176H324" stroke-width="3"/>
  </g>
  <g fill="${zone_fill}" stroke="${touch}" stroke-width="2">
    <circle cx="30" cy="124" r="6"/>
    <circle cx="30" cy="150" r="6"/>
    <circle cx="30" cy="176" r="6"/>
  </g>
  <g id="pad-ripples" fill="none" stroke="${touch}" stroke-width="1.5">
    <circle class="pad-ring pad-a" cx="30" cy="124" r="6"/>
    <circle class="pad-ring pad-b" cx="30" cy="150" r="6"/>
    <circle class="pad-ring pad-c" cx="30" cy="176" r="6"/>
  </g>
  <g fill="${touch}">
    <circle cx="52" cy="124" r="3.5"/>
    <circle cx="52" cy="176" r="3.5"/>
    <circle cx="290" cy="124" r="3.5"/>
    <circle cx="290" cy="176" r="3.5"/>
  </g>

  <g id="strip-chip">
    <path d="M120 114V107M140 114V107M160 114V107M180 114V107M200 114V107M220 114V107M240 114V107M120 186V193M140 186V193M160 186V193M180 186V193M200 186V193M220 186V193M240 186V193" stroke="${touch}" stroke-opacity="0.6" stroke-width="2"/>
    <rect x="100" y="114" width="160" height="72" rx="6" fill="${board}" stroke="${touch}" stroke-width="1.5"/>
    <circle class="heartbeat" cx="111" cy="125" r="2.6" fill="${touch_text}"/>
    <rect class="chip-on" x="93" y="107" width="174" height="86" rx="11" fill="none" stroke="${touch}" stroke-width="2"/>
    <text x="180" y="146" fill="${ink}" font-size="20" font-weight="800" letter-spacing="1" text-anchor="middle">HW LAB</text>
    <text class="mono" x="180" y="173" fill="${touch_text}" font-size="17" letter-spacing="0.5" text-anchor="middle">${prototypes} PROTOTYPES</text>
  </g>
  <g id="chip-bus" stroke="${pulse}" stroke-width="2.5" stroke-linecap="round">
    <path class="pin-hi pin-0" d="M120 114V106M120 186V194"/>
    <path class="pin-hi pin-1" d="M140 114V106M140 186V194"/>
    <path class="pin-hi pin-2" d="M160 114V106M160 186V194"/>
    <path class="pin-hi pin-3" d="M180 114V106M180 186V194"/>
    <path class="pin-hi pin-4" d="M200 114V106M200 186V194"/>
    <path class="pin-hi pin-5" d="M220 114V106M220 186V194"/>
    <path class="pin-hi pin-6" d="M240 114V106M240 186V194"/>
  </g>

  <circle cx="330" cy="124" r="6" fill="${led_red_off}" stroke="${led_red}" stroke-opacity="0.55"/>
  <g class="led-on led-a"><circle cx="330" cy="124" r="14" fill="url(#ledGlow-a)"/><circle cx="330" cy="124" r="6" fill="${led_red}"/></g>
  <circle class="bloom bloom-a" cx="330" cy="124" r="6" fill="none" stroke="${led_red}" stroke-width="1.5"/>
  <circle cx="330" cy="150" r="6" fill="${led_amber_off}" stroke="${led_amber}" stroke-opacity="0.55"/>
  <g class="led-on led-b"><circle cx="330" cy="150" r="14" fill="url(#ledGlow-b)"/><circle cx="330" cy="150" r="6" fill="${led_amber}"/></g>
  <circle class="bloom bloom-b" cx="330" cy="150" r="6" fill="none" stroke="${led_amber}" stroke-width="1.5"/>
  <circle cx="330" cy="176" r="6" fill="${led_green_off}" stroke="${led_green}" stroke-opacity="0.55"/>
  <g class="led-on led-c"><circle cx="330" cy="176" r="14" fill="url(#ledGlow-c)"/><circle cx="330" cy="176" r="6" fill="${led_green}"/></g>
  <circle class="bloom bloom-c" cx="330" cy="176" r="6" fill="none" stroke="${led_green}" stroke-width="1.5"/>

  <g fill="${packet_fill}" stroke="${pulse}" stroke-width="2">
    <circle class="signal sig-in-a" cx="36" cy="124" r="3.5"/>
    <circle class="signal sig-in-b" cx="36" cy="150" r="3.5"/>
    <circle class="signal sig-in-c" cx="36" cy="176" r="3.5"/>
    <circle class="signal sig-out-a" cx="260" cy="142" r="3.5"/>
    <circle class="signal sig-out-b" cx="260" cy="150" r="3.5"/>
    <circle class="signal sig-out-c" cx="260" cy="158" r="3.5"/>
  </g>
</svg>
""")


# The Yi盘 card follows the homepage featured card and the DSH card's anatomy: title,
# descriptor, summary, tags, the repo button and status on the left, the structure diagram
# inset on the right. In the diagram the three nodes sit inside a dashed "U 盘内" boundary
# and the cloud model stays outside it. Each 8s pass lights the steps in causal order:
# context, retrieve, workspace, request, cloud, result, workspace, generate, output, then a
# packet runs the record rail back to the context. The drive's activity LED flickers while
# data moves on the drive (retrieve, generate, rail), three dots think inside the lit cloud,
# and each pass lands one sheet on the output's record stack with a "+1", so the stack grows
# to three over the card's three passes. The status dot breathes; the button shines, a ring
# leaves it and its arrow nudges once per pass. After three passes every animation stops on
# the base frame, the complete diagram with all three sheets, so the card does not keep
# moving beside the text; reduced motion shows that frame from the start.
FLOW_STYLE_BASE = """  <style>
    text { font-family: Arial, "PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif; }
    .lit, .packet, .pulse-ring, .io-on, .think, .plus-one, .cta-ring { opacity: 0; }
    .pulse-ring, .think, .cta-ring { transform-box: fill-box; transform-origin: center; }
    @media (prefers-reduced-motion: no-preference) {
      .lit-context { animation: lit-context 8s ease-in-out 3; }
      .packet-retrieve { animation: packet-retrieve 8s linear 3; }
      .io-read { animation: io-read 8s linear 3; }
      .lit-workspace-in { animation: lit-workspace-in 8s ease-in-out 3; }
      .packet-request { animation: packet-request 8s linear 3; }
      .lit-cloud { animation: lit-cloud 8s ease-in-out 3; }
      .think-a { animation: think-a 8s ease-in-out 3; }
      .think-b { animation: think-b 8s ease-in-out 3; }
      .think-c { animation: think-c 8s ease-in-out 3; }
      .packet-result { animation: packet-result 8s linear 3; }
      .lit-workspace-back { animation: lit-workspace-back 8s ease-in-out 3; }
      .packet-generate { animation: packet-generate 8s linear 3; }
      .io-write { animation: io-write 8s linear 3; }
      .lit-output { animation: lit-output 8s ease-in-out 3; }
      .plus-one { animation: plus-one 8s ease-out 3; }
      .sheet-1 { animation: sheet-1 24s cubic-bezier(0.2, 0.7, 0.2, 1) 1; }
      .sheet-2 { animation: sheet-2 24s cubic-bezier(0.2, 0.7, 0.2, 1) 1; }
      .sheet-3 { animation: sheet-3 24s cubic-bezier(0.2, 0.7, 0.2, 1) 1; }
      .lit-rail { animation: lit-rail 8s ease-in-out 3; }
      .packet-rail { animation: packet-rail 8s linear 3; }
      .io-sync { animation: io-sync 8s linear 3; }
      .status-pulse { animation: status-pulse 8s ease-out 3; }
      .cta-shine { animation: cta-shine 8s ease-in-out 3; }
      .cta-ring { animation: cta-ring 8s ease-out 3; }
      .cta-arrow { animation: cta-arrow 8s ease-out 3; }
      .march { animation: march 1.6s linear 15; }
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
    @keyframes think-a {
      0%, 33% { opacity: 0; transform: none; }
      34% { opacity: 1; transform: translateY(-3px); }
      35.6% { opacity: 0.35; transform: none; }
      37.2% { opacity: 1; transform: translateY(-3px); }
      38.8% { opacity: 0.35; transform: none; }
      40.6%, 100% { opacity: 0; transform: none; }
    }
    @keyframes think-b {
      0%, 33.7% { opacity: 0; transform: none; }
      34.7% { opacity: 1; transform: translateY(-3px); }
      36.3% { opacity: 0.35; transform: none; }
      37.9% { opacity: 1; transform: translateY(-3px); }
      39.5% { opacity: 0.35; transform: none; }
      41.3%, 100% { opacity: 0; transform: none; }
    }
    @keyframes think-c {
      0%, 34.4% { opacity: 0; transform: none; }
      35.4% { opacity: 1; transform: translateY(-3px); }
      37% { opacity: 0.35; transform: none; }
      38.6% { opacity: 1; transform: translateY(-3px); }
      40.2% { opacity: 0.35; transform: none; }
      42%, 100% { opacity: 0; transform: none; }
    }
    @keyframes plus-one {
      0%, 65.5% { opacity: 0; transform: translateY(6px); }
      67% { opacity: 1; transform: none; }
      71% { opacity: 1; transform: translateY(-5px); }
      74%, 100% { opacity: 0; transform: translateY(-10px); }
    }
    @keyframes sheet-1 {
      0%, 21.4% { opacity: 0; transform: translateY(-16px); }
      22.9% { opacity: 1; transform: translateY(1.5px); }
      23.8%, 100% { opacity: 1; transform: none; }
    }
    @keyframes sheet-2 {
      0%, 54.73% { opacity: 0; transform: translateY(-16px); }
      56.23% { opacity: 1; transform: translateY(1.5px); }
      57.13%, 100% { opacity: 1; transform: none; }
    }
    @keyframes sheet-3 {
      0%, 88.07% { opacity: 0; transform: translateY(-16px); }
      89.57% { opacity: 1; transform: translateY(1.5px); }
      90.47%, 100% { opacity: 1; transform: none; }
    }
    @keyframes cta-ring {
      0%, 87% { opacity: 0; transform: none; }
      88% { opacity: 0.6; transform: none; }
      96%, 100% { opacity: 0; transform: scale(1.06, 1.22); }
    }
    @keyframes cta-arrow {
      0%, 95.5% { transform: none; }
      97.5% { transform: translate(3px, -3px); }
      99.2%, 100% { transform: none; }
    }
    @keyframes march {
      0% { stroke-dashoffset: 0; }
      100% { stroke-dashoffset: -11px; }
    }
  </style>"""


# The activity LED flickers through each disk access: bright and dim in 1.1/0.9% steps.
def io_keyframes(access: str, start: int, end: int) -> str:
    rows = [f"      0%, {number(start - 0.6)}% {{ opacity: 0; }}"]
    tenth, lit = start * 10, True
    while tenth <= end * 10:
        rows.append(f"      {number(tenth / 10)}% {{ opacity: {1 if lit else 0.22}; }}")
        tenth += 11 if lit else 9
        lit = not lit
    rows.append(f"      {number(end + 1)}%, 100% {{ opacity: 0; }}")
    return f"    @keyframes io-{access} {{\n" + "\n".join(rows) + "\n    }\n"


# Reads while the retrieve packet moves, writes while the output is generated, syncs with the rail.
IO_ACCESSES = {"read": (9, 17), "write": (57, 65), "sync": (75, 83)}


def io_led(cx: float, cy: float, radius: float, glow: float) -> str:
    """The drive's activity LED: an unlit housing and one flicker layer per disk access."""
    layers = "".join(
        f'<g class="io-on io-{access}"><circle cx="{cx:g}" cy="{cy:g}" r="{glow:g}" fill="${{carry_2}}" opacity="0.25"/>'
        f'<circle cx="{cx:g}" cy="{cy:g}" r="{radius:g}" fill="${{carry_2}}"/></g>'
        for access in IO_ACCESSES
    )
    return f'<g id="drive-io"><circle cx="{cx:g}" cy="{cy:g}" r="{radius:g}" fill="${{tag_stroke}}"/>{layers}</g>'


def record_stack(x: float, ys: tuple[float, ...], width: float, height: float, radius: float) -> str:
    """Output records: sheet n lands during pass n, from the bottom of the stack up."""
    return '<g id="record-stack">' + "".join(
        f'<rect class="sheet sheet-{n}" x="{x:g}" y="{y:g}" width="{width:g}" height="{height:g}" rx="{radius:g}" '
        'fill="${carry}" fill-opacity="0.16" stroke="${carry}" stroke-opacity="0.65"/>'
        for n, y in enumerate(ys, start=1)
    ) + "</g>"


def think_dots(xs: tuple[float, ...], cy: float, radius: float) -> str:
    return '<g fill="${cloud_lit}">' + "".join(
        f'<circle class="think think-{letter}" cx="{x:g}" cy="{cy:g}" r="{radius:g}"/>' for letter, x in zip("abc", xs)
    ) + "</g>"


FLOW_STYLE = FLOW_STYLE_BASE.replace(
    "  </style>", "".join(io_keyframes(access, *span) for access, span in IO_ACCESSES.items()) + "  </style>", 1
)

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
      <stop stop-color="${cta_from}"/>
      <stop offset="1" stop-color="${cta_to}"/>
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
    <rect class="cta-ring" x="48" y="290" width="200" height="58" rx="14" fill="none" stroke="${carry}" stroke-width="2"/>
    <text x="72" y="325" fill="${cta_ink}" font-size="19" font-weight="700">查看公开仓库</text>
    <path class="cta-arrow" d="M207 326L220 313M210 313H220V323" fill="none" stroke="${cta_ink}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
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
        """ + think_dots((1055.5, 1068.5, 1081.5), 229, 3.5) + """
        <text x="1068.5" y="255" fill="${ink}" font-size="22" font-weight="700" text-anchor="middle">云端模型</text>
        <text x="1068.5" y="283" fill="${muted}" font-size="17" text-anchor="middle">按需推理</text>
      </g>
    </g>

    <g id="drive">
      <rect id="drive-boundary" class="march" x="468.5" y="98.5" width="446" height="322" rx="14" fill="${carry}" fill-opacity="${drive_fill}" stroke="${carry}" stroke-opacity="0.45" stroke-dasharray="6 5"/>
      <text x="910" y="86" fill="${flow_tag}" font-size="17" text-anchor="end">U 盘内</text>
      """ + io_led(845, 80, 4.5, 10) + """

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
        """ + record_stack(830, (384, 372, 360), 46, 10, 2.5) + """
        <text class="plus-one" x="818" y="377" fill="${carry_text}" font-size="17" font-weight="700" text-anchor="end">+1</text>
      </g>
    </g>
  </g>
</svg>
""")

# Narrow screens get the same card stacked at 360 units: the summary, then the diagram with
# node titles only (the README table and alt text carry the details), then status and link.
# It lights the nodes in the same order on the same 8s pass, without packets and the "+1";
# the activity LED, thinking dots, record stack and link arrow keep the desktop timing.
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
        """ + think_dots((290, 299, 308), 265, 2.5) + """
        <text x="299" y="288" fill="${ink}" font-size="18" font-weight="700" text-anchor="middle">云端</text>
        <text x="299" y="310" fill="${ink}" font-size="18" font-weight="700" text-anchor="middle">模型</text>
      </g>
    </g>
    <g id="drive">
      <rect id="drive-boundary" class="march" x="24.5" y="186.5" width="216" height="206" rx="12" fill="${carry}" fill-opacity="${drive_fill}" stroke="${carry}" stroke-opacity="0.45" stroke-dasharray="6 5"/>
      <text x="236" y="174" fill="${flow_tag}" font-size="17" text-anchor="end">U 盘内</text>
      """ + io_led(172, 168, 4, 9) + """
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
        """ + record_stack(201, (364, 356, 348), 20, 6, 1.5) + """
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
    <path class="cta-arrow" d="M318 438L330 426M321 426H330V435" fill="none" stroke="${carry_text}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  </g>
</svg>
""")


# DSH's functional illustration tells its causal story (sessions, packets, projects, usage
# bars, timeline lanes, scan) in three 8s passes. Each pass opens by dimming the complete
# illustration, builds it back stage by stage and ends complete, so passes join seamlessly
# and the card stops on the complete illustration (its base frame). The -0.4s delay starts
# the first pass already dimmed. As the scan crosses the timeline it lights each usage bar
# and lane it passes; then the 30-day downloads figure rolls one full turn per digit and
# lands on the real value, and the link draws its underline and nudges its arrow. Product
# facts stay visible throughout; transient packets, highlights and the scanner are hidden
# in the base frame and both static variants.
DSH_STYLE_BASE = """  <style>
    text { font-family: Arial, "PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif; }
    .mono { font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace; }
    .record, .usage-bars, .time-lane, .cta-arrow, .cta-underline { transform-box: fill-box; }
    .usage-bars { transform-origin: center bottom; }
    .time-lane, .cta-underline { transform-origin: left center; }
    .packet, .timeline-scan, .scan-mark { opacity: 0; }
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
      .cta-underline { animation: cta-underline 8s cubic-bezier(0.2, 0.7, 0.2, 1) -0.4s 3; }
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
    @keyframes cta-underline {
      0% { transform: none; }
      4%, 90.5% { transform: scaleX(0); }
      96%, 100% { transform: none; }
    }
  </style>"""

# Timeline geometry. Usage bars are (x, top, height), 12 wide on the 224 baseline; lanes
# are (x, y, width), 8 tall. The scan line starts at x 835 and travels 290 units from 74%
# to 90% of the pass with ease-in-out, as in timeline-scan above.
DSH_BARS = {
    "a": ((837, 208, 16), (861, 194, 30), (885, 202, 22), (909, 184, 40)),
    "b": ((933, 196, 28), (957, 177, 47), (981, 191, 33), (1005, 171, 53)),
    "c": ((1029, 182, 42), (1053, 201, 23), (1077, 188, 36), (1101, 207, 17)),
}
DSH_LANES = {
    "a": ((837, 247, 86), (960, 247, 130)),
    "b": ((870, 272, 141), (1030, 272, 64)),
    "c": ((837, 297, 55), (934, 297, 110), (1070, 297, 52)),
}
SCAN_X, SCAN_TRAVEL, SCAN_START, SCAN_END = 835, 290, 74, 90


def scan_reaches(x: float) -> float:
    """Percent of the pass at which the ease-in-out scan line crosses x."""
    progress = min(max((x - SCAN_X) / SCAN_TRAVEL, 0), 1)

    def bezier(t: float, first: float, second: float) -> float:
        return 3 * (1 - t) ** 2 * t * first + 3 * (1 - t) * t ** 2 * second + t ** 3

    low, high = 0.0, 1.0
    for _ in range(50):
        middle = (low + high) / 2
        low, high = (middle, high) if bezier(middle, 0, 1) < progress else (low, middle)
    return SCAN_START + (SCAN_END - SCAN_START) * bezier(low, 0.42, 0.58)


def dsh_bars() -> str:
    return "".join(
        f'<g class="usage-bars usage-{group}">'
        + "".join(f'<rect x="{x}" y="{y}" width="12" height="{height}" rx="3"/>' for x, y, height in bars)
        + "</g>"
        for group, bars in DSH_BARS.items()
    )


def dsh_lanes() -> str:
    return "".join(
        f'<g class="time-lane lane-{group}">'
        + "".join(f'<rect x="{x}" y="{y}" width="{width}" height="8" rx="4"/>' for x, y, width in lanes)
        + "</g>"
        for group, lanes in DSH_LANES.items()
    )


def scan_marks() -> tuple[str, str, str]:
    """Highlights the scan lights as it crosses each bar's center and each lane's span."""
    rules, frames, marks = [], [], []
    bars = [bar for group in DSH_BARS.values() for bar in group]
    lanes = [lane for group in DSH_LANES.values() for lane in group]
    for index, (x, y, height) in enumerate(bars):
        name, at = f"mark-bar-{index}", scan_reaches(x + 6)
        rules.append(f"      .{name} {{ animation: {name} 8s ease-out -0.4s 3; }}")
        frames.append(
            f"    @keyframes {name} {{\n      0%, {number(at - 0.4)}% {{ opacity: 0; }}\n"
            f"      {number(at + 0.3)}% {{ opacity: 1; }}\n      {number(at + 4)}%, 100% {{ opacity: 0; }}\n    }}\n"
        )
        marks.append(f'<rect class="scan-mark {name}" x="{x - 1}" y="{y - 1}" width="14" height="{height + 2}" rx="3.5"/>')
    for index, (x, y, width) in enumerate(lanes):
        name, start = f"mark-lane-{index}", scan_reaches(x)
        end = max(scan_reaches(x + width), start + 0.6)
        rules.append(f"      .{name} {{ animation: {name} 8s ease-out -0.4s 3; }}")
        frames.append(
            f"    @keyframes {name} {{\n      0%, {number(start - 0.3)}% {{ opacity: 0; }}\n"
            f"      {number(start + 0.3)}% {{ opacity: 0.9; }}\n      {number(end)}% {{ opacity: 0.9; }}\n"
            f"      {number(end + 3.5)}%, 100% {{ opacity: 0; }}\n    }}\n"
        )
        marks.append(f'<rect class="scan-mark {name}" x="{x}" y="{y - 1}" width="{width}" height="10" rx="5"/>')
    return "\n".join(rules), "".join(frames), "".join(marks)


# The downloads odometer: one column per digit, numbered from the ones place so the CSS
# does not depend on the figure. Each column stacks its digit and the next ten (one full
# turn that ends on the same digit), rolls up one turn after the scan, then snaps back to
# the identical first row. The ones digit lands last.
ODOMETER_COLUMNS = 6
ODOMETER_ROW = 40


def odometer_style() -> tuple[str, str]:
    rules, frames = [], []
    for place in range(ODOMETER_COLUMNS):
        start = 90.2 + (ODOMETER_COLUMNS - 1 - place) * 0.6
        rules.append(f"      .odo-{place} {{ animation: odo-{place} 8s linear -0.4s 3; }}")
        frames.append(
            f"    @keyframes odo-{place} {{\n"
            f"      0%, {number(start)}% {{ transform: none; animation-timing-function: cubic-bezier(0.35, 0, 0.15, 1); }}\n"
            f"      {number(start + 6)}% {{ transform: translateY({-10 * ODOMETER_ROW}px); animation-timing-function: steps(1, end); }}\n"
            f"      {number(start + 6.1)}%, 100% {{ transform: none; }}\n    }}\n"
        )
    return "\n".join(rules), "".join(frames)


def odometer(value: str, x: float, y: float, size: int) -> str:
    """Monospace columns for a figure such as 1,031; separators stay still."""
    digits = sum(char.isdigit() for char in value)
    if digits > ODOMETER_COLUMNS:
        raise SystemExit(f"downloads figure {value} needs more than {ODOMETER_COLUMNS} odometer columns")
    font = f'font-size="{size}" font-weight="600"'
    columns, place = [], digits
    for index, char in enumerate(value):
        left = number(x + index * size * 0.6)
        if not char.isdigit():
            columns.append(f'<text class="mono" x="{left}" y="{y:g}" {font}>{escape(char)}</text>')
            continue
        place -= 1
        rows = "".join(f'<tspan x="{left}" y="{y + row * ODOMETER_ROW:g}">{(int(char) + row) % 10}</tspan>' for row in range(11))
        columns.append(f'<text class="mono odo odo-{place}" {font}>{rows}</text>')
    return "".join(columns)


SCAN_RULES, SCAN_FRAMES, SCAN_MARKS = scan_marks()
ODOMETER_RULES, ODOMETER_FRAMES = odometer_style()
DSH_STYLE = DSH_STYLE_BASE.replace(
    "      .cta-underline {", SCAN_RULES + "\n" + ODOMETER_RULES + "\n      .cta-underline {", 1
).replace("  </style>", SCAN_FRAMES + ODOMETER_FRAMES + "  </style>", 1)

DSH = Template("""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="420" viewBox="0 0 1200 420" role="img" aria-labelledby="title desc">
  <title id="title">DSH Usage：按项目统计会话用量</title>
  <desc id="desc">${theme_desc}DSH Usage 项目卡。DeepSeek Harness 用量插件，按项目统计 Token、开发时长和预估费用，另含账户余额查询。右侧为功能示意，非产品截图：会话记录按项目归集，形成用量柱和开发时间线；图形不代表真实用量。项目总览可导出 CSV/JSON，用量趋势可选近 7 / 30 / 90 天。npm 近 30 天下载 ${npm_downloads} 次，最新版本 ${npm_latest}，已发布 ${npm_versions} 个版本，下载统计截至 ${npm_as_of}。包名 @rongyi7/dsh-stats，MIT 许可。</desc>
  <defs>
    <linearGradient id="cardWash" x1="0" y1="0" x2="1" y2="1"><stop stop-color="${see}" stop-opacity="0.12"/><stop offset="1" stop-color="${see}" stop-opacity="0.02"/></linearGradient>
    <linearGradient id="laneFill"><stop stop-color="${see}"/><stop offset="1" stop-color="${see_2}"/></linearGradient>
    <clipPath id="odoClip"><rect x="44" y="264" width="170" height="38"/></clipPath>
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
    <g id="npm-downloads" clip-path="url(#odoClip)" fill="${ink}">${npm_odometer}</g>
    <text id="npm-latest" x="218" y="293" fill="${ink}" font-size="32" font-weight="600" class="mono">${npm_latest}</text>
  </g>
  <text id="npm-as-of" x="48" y="324" fill="${muted}" font-size="17">统计截至 ${npm_as_of}</text>
  <g id="card-cta">
    <text x="48" y="377" fill="${see_text}" font-size="19" font-weight="600">查看仓库</text>
    <rect class="cta-underline" x="48" y="384" width="76" height="2" rx="1" fill="${see_text}"/>
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
        <g fill="${see}">""" + dsh_bars() + """</g>
        <g fill="url(#laneFill)">""" + dsh_lanes() + """</g>
        <g id="scan-marks" fill="${see_2}">""" + SCAN_MARKS + """</g>
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
  <defs><clipPath id="odoClip"><rect x="20" y="294" width="178" height="36"/></clipPath></defs>
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
    <g id="npm-downloads" clip-path="url(#odoClip)" fill="${ink}">${npm_odometer_narrow}</g>
    <text id="npm-latest" x="202" y="322" fill="${ink}" font-size="30" font-weight="600" class="mono">${npm_latest}</text>
  </g>
  <text id="npm-as-of" x="24" y="355" fill="${muted}" font-size="17">统计截至 ${npm_as_of}</text>
</svg>
""")


# The terminal signature sits above the footer. It types ./ship --carry --see --touch,
# prints the three lane states, then holds a blinking prompt before the next pass.
# Desktop keeps the command on one line; the narrow version wraps it onto two lines and
# stacks the three states so 17-unit text stays readable at 360 wide.
TERMINAL_STYLE = """  <style>
    text { font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace; font-size: 20px; }
    .panel { fill: ${tab_bg}; stroke: ${tag_stroke}; }
    .ink { fill: ${ink}; } .muted { fill: ${muted}; }
    .carry { fill: ${carry_text}; } .see { fill: ${see_text}; } .touch { fill: ${touch_text}; }
    .cover { fill: ${tab_bg}; transform-box: fill-box; transform-origin: right center; transform: scaleX(0); }
    @media (prefers-reduced-motion: no-preference) {
      .cover { animation: cover 12s linear infinite; }
      .out { animation: out 12s linear infinite; }
      .cur-line { animation: cur-line 12s linear infinite; }
      .cur-type { animation: cur-type 12s linear infinite; }
      .blink { animation: blink 1.1s steps(1, end) infinite; }
    }
    @keyframes cover {
      0%, 5% { transform: none; animation-timing-function: steps(28, end); }
      30% { transform: scaleX(0); }
      90% { transform: scaleX(0); animation-timing-function: steps(28, end); }
      95%, 100% { transform: none; }
    }
    @keyframes out {
      0%, 32% { opacity: 0; }
      33%, 89% { opacity: 1; }
      90%, 100% { opacity: 0; }
    }
    @keyframes cur-line {
      0% { transform: translateY(-72px); animation-timing-function: steps(1, end); }
      35% { transform: none; animation-timing-function: steps(1, end); }
      90%, 100% { transform: translateY(-72px); }
    }
    @keyframes cur-type {
      0%, 5% { transform: none; animation-timing-function: steps(28, end); }
      30% { transform: translateX(336px); animation-timing-function: steps(1, end); }
      35% { transform: none; animation-timing-function: steps(1, end); }
      90% { transform: translateX(336px); animation-timing-function: steps(28, end); }
      95%, 100% { transform: none; }
    }
    @keyframes blink {
      0% { opacity: 1; }
      50% { opacity: 0; }
      100% { opacity: 1; }
    }
  </style>"""

TERMINAL = Template("""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="168" viewBox="0 0 1200 168" role="img" aria-labelledby="title desc">
  <title id="title">rongyi@studio 终端签名</title>
  <desc id="desc">终端签名：输入 ./ship --carry --see --touch，输出 Yi盘受控内测、DSH Usage npm 插件、Hardware Lab ${prototypes} 个原型，随后重新输入。</desc>
${style}
  <rect class="panel" x="0.5" y="0.5" width="1199" height="167" rx="16"/>
  <text x="40" y="54"><tspan class="carry">rongyi</tspan><tspan class="muted">@</tspan><tspan class="see">studio</tspan><tspan class="muted"> ~ %</tspan></text>
  <text class="ink" x="256" y="54">./ship --carry --see --touch</text>
  <rect class="cover" x="254" y="32" width="344" height="30"/>
  <g class="out">
    <text x="40" y="90"><tspan class="carry">● carry</tspan><tspan class="muted">  受控内测   </tspan><tspan class="see">● see</tspan><tspan class="muted">  npm 插件   </tspan><tspan class="touch">● touch</tspan><tspan class="muted">  ${prototypes} 个原型</tspan></text>
    <text x="40" y="126"><tspan class="carry">rongyi</tspan><tspan class="muted">@</tspan><tspan class="see">studio</tspan><tspan class="muted"> ~ %</tspan></text>
  </g>
  <g class="cur-line"><g class="cur-type"><rect class="ink blink" x="256" y="108" width="11" height="23" opacity="0.85"/></g></g>
</svg>
""")

TERMINAL_MOBILE_STYLE = """  <style>
    text { font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace; font-size: 17px; }
    .panel { fill: ${tab_bg}; stroke: ${tag_stroke}; }
    .ink { fill: ${ink}; } .muted { fill: ${muted}; }
    .carry { fill: ${carry_text}; } .see { fill: ${see_text}; } .touch { fill: ${touch_text}; }
    .cover-1, .cover-2 { fill: ${tab_bg}; transform-box: fill-box; transform-origin: right center; transform: scaleX(0); }
    .out, .cursor { opacity: 1; }
    @media (prefers-reduced-motion: no-preference) {
      .cover-1 { animation: cover-1 12s linear infinite; }
      .cover-2 { animation: cover-2 12s linear infinite; }
      .out { animation: out 12s linear infinite; }
      .cursor { animation: cursor 12s linear infinite; }
      .blink { animation: blink 1.1s steps(1, end) infinite; }
    }
    @keyframes cover-1 {
      0%, 5% { transform: none; animation-timing-function: steps(14, end); }
      18% { transform: scaleX(0); }
      90% { transform: scaleX(0); animation-timing-function: steps(14, end); }
      95%, 100% { transform: none; }
    }
    @keyframes cover-2 {
      0%, 18% { transform: none; animation-timing-function: steps(15, end); }
      30% { transform: scaleX(0); }
      90% { transform: scaleX(0); animation-timing-function: steps(15, end); }
      95%, 100% { transform: none; }
    }
    @keyframes out {
      0%, 32% { opacity: 0; }
      33%, 89% { opacity: 1; }
      90%, 100% { opacity: 0; }
    }
    @keyframes cursor {
      0%, 34% { opacity: 0; }
      35%, 89% { opacity: 1; }
      90%, 100% { opacity: 0; }
    }
    @keyframes blink {
      0% { opacity: 1; }
      50% { opacity: 0; }
      100% { opacity: 1; }
    }
  </style>"""

TERMINAL_MOBILE = Template("""<svg xmlns="http://www.w3.org/2000/svg" width="360" height="218" viewBox="0 0 360 218" role="img" aria-labelledby="title desc">
  <title id="title">rongyi@studio 终端签名</title>
  <desc id="desc">终端签名：输入 ./ship --carry --see --touch，输出 Yi盘受控内测、DSH Usage npm 插件、Hardware Lab ${prototypes} 个原型，随后重新输入。</desc>
${style}
  <rect class="panel" x="0.5" y="0.5" width="359" height="217" rx="16"/>
  <text x="18" y="38"><tspan class="carry">rongyi</tspan><tspan class="muted">@</tspan><tspan class="see">studio</tspan><tspan class="muted"> ~ %</tspan></text>
  <text class="ink" x="18" y="64">./ship --carry</text>
  <text class="ink" x="36" y="90">--see --touch</text>
  <rect class="cover-1" x="16" y="44" width="153" height="26"/>
  <rect class="cover-2" x="34" y="70" width="143" height="26"/>
  <g class="out">
    <text x="18" y="122"><tspan class="carry">● carry</tspan><tspan class="muted">  受控内测</tspan></text>
    <text x="18" y="148"><tspan class="see">● see</tspan><tspan class="muted">  npm 插件</tspan></text>
    <text x="18" y="174"><tspan class="touch">● touch</tspan><tspan class="muted">  ${prototypes} 个原型</tspan></text>
    <text x="18" y="204"><tspan class="carry">rongyi</tspan><tspan class="muted">@</tspan><tspan class="see">studio</tspan><tspan class="muted"> ~ %</tspan></text>
  </g>
  <g class="cursor"><rect class="ink blink" x="202" y="186" width="9" height="20" opacity="0.85"/></g>
</svg>
""")


# Link badges share one anatomy: an uppercase label, a rule, then the action. Primary badges
# are solid Yi盘 orange in both themes; secondary badges are outlined in their lane color and
# follow the page theme through their own color-scheme query, so they are not dark blocks on
# a light page.
BADGE_FONT = 'Arial, "PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif'
BADGES = {
    "badge-studio": ("STUDIO", "访问主页", "访问主页", "前往 Rongyi Studio 个人主页。", "primary"),
    "badge-build-log": ("BUILD", "开发记录", "查看开发记录", "前往 Rongyi 的公开开发记录。", "carry"),
    "badge-product-facts": ("FACTS", "产品事实与限制", "Yi盘产品事实与限制", "查看 Yi盘已确认的产品事实、限制和验证范围。", "carry"),
    "badge-feedback": ("FEEDBACK", "提交反馈", "提交 Yi盘反馈", "前往 Yi盘公开反馈页面。", "primary"),
    "badge-hardware": ("TOUCH", "Hardware Lab", "查看 Hardware Lab", "前往 Hardware Lab 公开硬件项目索引。", "touch"),
}
# Badge motion follows each badge's lane. Primary buttons shine and nudge an arrow like the
# Yi盘 button (8s x 3, staggered by their delays); BUILD blinks a terminal cursor; FACTS sends
# a Yi盘 packet along its bottom edge (8s x 3); TOUCH carries an LED that lights briefly every
# 6s. Base styles are the resting frame: shine off-badge, arrow in place, packet hidden,
# cursor shown, LED unlit; reduced motion keeps that frame.
BADGE_MOTION = {
    "badge-studio": ("shine", 1.2),
    "badge-build-log": ("cursor", 0),
    "badge-product-facts": ("packet", 0.8),
    "badge-feedback": ("shine", 0.6),
    "badge-hardware": ("led", 0),
}
# Outlined badge colors per lane: (border, light label, dark label).
BADGE_ACCENTS = {"carry": ("#e45738", "#c8452a", "#ff8a70"), "touch": ("#2fa877", "#0b7d50", "#6fe0ae")}
# Arial Bold advance widths (units per 1000) for the Latin letters in badges; CJK glyphs are one em.
ARIAL_BOLD = {
    "A": 722, "B": 722, "C": 722, "D": 722, "E": 667, "F": 611, "H": 722, "I": 278, "K": 722, "L": 611, "O": 778,
    "S": 667, "T": 611, "U": 722, "a": 556, "b": 611, "d": 611, "e": 556, "r": 389, "w": 778, " ": 278,
}
MOTION_GUARD = "@media (prefers-reduced-motion: no-preference)"


def text_width(text: str, size: float, tracking: float = 0) -> float:
    return sum(ARIAL_BOLD[char] * size / 1000 if char in ARIAL_BOLD else size for char in text) + tracking * len(text)


def badge_motion(kind: str, delay: float, width: int, rule: int, style: str) -> dict[str, str]:
    """Defs, resting CSS, guarded animation rules, keyframes and markup for one badge's motion."""
    if kind == "shine":
        return {
            "defs": (
                f'<clipPath id="clip"><rect x="0.75" y="0.75" width="{width - 1.5:g}" height="34.5" rx="7.5"/></clipPath>'
                '<linearGradient id="sheen" x1="0" x2="1"><stop stop-color="#ffffff" stop-opacity="0"/>'
                '<stop offset="0.5" stop-color="#ffffff" stop-opacity="0.42"/><stop offset="1" stop-color="#ffffff" stop-opacity="0"/></linearGradient>'
            ),
            "rest": "    .shine { transform: translateX(-60px); }\n",
            "rules": f"      .shine {{ animation: shine 8s ease-in-out {delay:g}s 3; }}\n      .arrow {{ animation: arrow-nudge 8s ease-out {delay:g}s 3; }}\n",
            "frames": (
                f"    @keyframes shine {{\n      0% {{ transform: translateX(-60px); }}\n      11%, 100% {{ transform: translateX({width + 60}px); }}\n    }}\n"
                "    @keyframes arrow-nudge {\n      0%, 10% { transform: none; }\n      13% { transform: translate(2px, -2px); }\n      16%, 100% { transform: none; }\n    }\n"
            ),
            "under": '  <g clip-path="url(#clip)"><path class="shine" d="M18 0H46L30 36H2Z" fill="url(#sheen)"/></g>\n',
            "over": f'  <path class="arrow" d="M{width - 25} 23L{width - 17} 15M{width - 23} 15H{width - 17}V21" fill="none" stroke="#ffffff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>\n',
        }
    border, light_label, dark_label = BADGE_ACCENTS[style]
    if kind == "cursor":
        return {
            "rules": "      .cursor { animation: cursor 1.1s steps(1, end) infinite; }\n",
            "frames": "    @keyframes cursor {\n      0% { opacity: 1; }\n      50% { opacity: 0; }\n      100% { opacity: 1; }\n    }\n",
            "over": f'  <rect class="label cursor" x="{rule - 10}" y="13" width="5" height="10" fill="{light_label}"/>\n',
        }
    if kind == "packet":
        return {
            "defs": f'<linearGradient id="trail" x1="0" x2="1"><stop stop-color="{border}" stop-opacity="0"/><stop offset="1" stop-color="{border}" stop-opacity="0.7"/></linearGradient>',
            "rest": "    .packet { opacity: 0; }\n    .packet-dot { fill: " + border + "; }\n",
            "dark": f"      .packet-dot {{ fill: {dark_label}; }}\n",
            "rules": f"      .packet {{ animation: packet 8s cubic-bezier(0.45, 0, 0.25, 1) {delay:g}s 3; }}\n",
            "frames": (
                "    @keyframes packet {\n      0% { opacity: 0; transform: none; }\n      1.5% { opacity: 1; transform: none; }\n"
                f"      13% {{ opacity: 1; transform: translateX({width - 30}px); }}\n"
                f"      15%, 100% {{ opacity: 0; transform: translateX({width - 30}px); }}\n    }}\n"
            ),
            "over": (
                '  <g class="packet"><rect x="3" y="33.2" width="14" height="1.6" rx="0.8" fill="url(#trail)"/>'
                f'<circle class="packet-dot" cx="17" cy="34" r="1.8" fill="{border}"/></g>\n'
            ),
        }
    light, dark = PALETTES["light"], PALETTES["dark"]
    return {
        "rest": (
            f"    .led-ring {{ fill: {light['led_off']}; stroke: {border}; }}\n"
            f"    .led-core {{ fill: {light['touch']}; }}\n    .led-lit {{ opacity: 0; }}\n"
        ),
        "dark": f"      .led-ring {{ fill: {dark['led_off']}; stroke: {dark_label}; }}\n      .led-core {{ fill: {dark['touch']}; }}\n",
        "rules": "      .led-lit { animation: badge-led 6s ease-in-out infinite; }\n",
        "frames": "    @keyframes badge-led {\n      0%, 72% { opacity: 0; }\n      74%, 82% { opacity: 1; }\n      88% { opacity: 0.4; }\n      94%, 100% { opacity: 0; }\n    }\n",
        "under": (
            f'  <circle class="led-ring" cx="14" cy="18" r="3.4" fill="{light["led_off"]}" stroke="{border}" stroke-opacity="0.6"/>\n'
            f'  <g class="led-lit"><circle class="led-core" cx="14" cy="18" r="7" fill="{light["touch"]}" opacity="0.28"/>'
            f'<circle class="led-core" cx="14" cy="18" r="3.4" fill="{light["touch"]}"/></g>\n'
        ),
    }


def badge(label: str, action: str, title: str, desc: str, style: str, kind: str, delay: float) -> str:
    label_x = 24 if kind == "led" else 14
    rule = round(label_x + text_width(label, 10, 1) + 12)
    action_x = rule + 14
    width = round(action_x + text_width(action, 14) + 16) + (14 if kind == "shine" else 0)
    motion = badge_motion(kind, delay, width, rule, style)
    defs = f'  <defs>{motion["defs"]}</defs>\n' if "defs" in motion else ""
    guarded = f'    {MOTION_GUARD} {{\n{motion["rules"]}    }}\n{motion["frames"]}'
    head = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="36" viewBox="0 0 {width} 36" role="img" aria-labelledby="title desc">\n'
        f'  <title id="title">{title}</title>\n'
        f'  <desc id="desc">{desc}</desc>\n'
        f'{defs}'
        f'  <style>\n'
        f'    text {{ font-family: {BADGE_FONT}; font-weight: 700; }}\n'
        f'{motion.get("rest", "")}'
    )
    if style == "primary":
        return head + (
            f'{guarded}'
            f'  </style>\n'
            f'  <rect x="0.75" y="0.75" width="{width - 1.5:g}" height="34.5" rx="7.5" fill="#c44227" stroke="#ff8a70" stroke-width="1.5"/>\n'
            f'  <rect x="2" y="2" width="{width - 4}" height="32" rx="6.5" fill="none" stroke="#ffffff" stroke-opacity="0.14"/>\n'
            f'{motion.get("under", "")}'
            f'  <text class="label" x="{label_x}" y="22" fill="#ffffff" font-size="10" letter-spacing="1">{label}</text>\n'
            f'  <path d="M{rule} 8V28" stroke="#ffffff" stroke-opacity="0.42"/>\n'
            f'  <text class="action" x="{action_x}" y="23" fill="#ffffff" font-size="14">{action}</text>\n'
            f'{motion.get("over", "")}'
            f'</svg>\n'
        )
    border, light_label, dark_label = BADGE_ACCENTS[style]
    return head + (
        f'    .surface {{ fill: #ffffff; }}\n'
        f'    .label {{ fill: {light_label}; }}\n'
        f'    .action {{ fill: #18202a; }}\n'
        f'    @media (prefers-color-scheme: dark) {{\n'
        f'      .surface {{ fill: #202631; }}\n'
        f'      .label {{ fill: {dark_label}; }}\n'
        f'      .action {{ fill: #f4f6f8; }}\n'
        f'{motion.get("dark", "")}'
        f'    }}\n'
        f'{guarded}'
        f'  </style>\n'
        f'  <rect class="surface" x="0.5" y="0.5" width="{width - 1}" height="35" rx="8" fill="#ffffff" stroke="{border}"/>\n'
        f'{motion.get("under", "")}'
        f'  <text class="label" x="{label_x}" y="22" fill="{light_label}" font-size="10" letter-spacing="1">{label}</text>\n'
        f'  <path d="M{rule} 8V28" stroke="{border}" stroke-opacity="0.55"/>\n'
        f'  <text class="action" x="{action_x}" y="23" fill="#18202a" font-size="14">{action}</text>\n'
        f'{motion.get("over", "")}'
        f'</svg>\n'
    )


# Lane dividers replace the Markdown rules before CARRY, SEE and TOUCH: a trace in the lane's
# color that jogs down once (at 30/50/70% of the width, so the three read as one signal
# stepping across the page). Every 6s a head with a dashed tail runs it in 1.3s and lights the
# end node, then the line rests. They follow the page theme through their own color-scheme
# query; reduced motion shows the resting trace.
DIVIDER_JOGS = {"carry": 0.30, "see": 0.50, "touch": 0.70}
DIVIDER_GEOMETRY = {
    # width, height, start x, end x, upper y, lower y, half jog, ring r, head r, glow r, line, trail, tail
    "wide": (1200, 36, 24, 1172, 12, 24, 8, 5, 3.5, 11, 2, 3, 90),
    "narrow": (360, 28, 16, 338, 9, 19, 7, 3.5, 2.8, 8, 1.5, 2.5, 44),
}
DIVIDER_RUN = (8, 30)


def divider(lane: str, size: str) -> str:
    width, height, x0, x1, y1, y2, half, ring, head, glow, line, trail, tail = DIVIDER_GEOMETRY[size]
    jog = round(width * DIVIDER_JOGS[lane])
    first, diagonal, last = jog - half - x0, math.hypot(2 * half, y2 - y1), x1 - jog - half
    length = first + diagonal + last
    start, end = DIVIDER_RUN
    corner_a = start + (end - start) * first / length
    corner_b = start + (end - start) * (first + diagonal) / length
    path = f"M{x0} {y1}H{jog - half}L{jog + half} {y2}H{x1}"
    light, dark = PALETTES["light"][lane], PALETTES["dark"][lane]
    name = {"carry": "CARRY", "see": "SEE", "touch": "TOUCH"}[lane]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
  <title id="title">{name} 泳道分隔</title>
  <desc id="desc">装饰分隔线：一条 {name} 泳道颜色的走线，信号每 6 秒沿它跑一遍。</desc>
  <style>
    :root {{ --lane: {light}; }}
    @media (prefers-color-scheme: dark) {{ :root {{ --lane: {dark}; }} }}
    .line {{ stroke: var(--lane); }}
    .dot {{ fill: var(--lane); }}
    .head, .trail, .node {{ opacity: 0; }}
    {MOTION_GUARD} {{
      .head {{ animation: head 6s linear infinite; }}
      .trail {{ animation: trail 6s linear infinite; }}
      .node {{ animation: node 6s ease-out infinite; }}
    }}
    @keyframes head {{
      0%, {number(start - 0.5)}% {{ opacity: 0; transform: none; }}
      {start}% {{ opacity: 1; transform: none; }}
      {number(corner_a)}% {{ transform: translate({first}px, 0); }}
      {number(corner_b)}% {{ transform: translate({first + 2 * half}px, {y2 - y1}px); }}
      {end}% {{ opacity: 1; transform: translate({x1 - x0}px, {y2 - y1}px); }}
      {number(end + 1.5)}%, 100% {{ opacity: 0; transform: translate({x1 - x0}px, {y2 - y1}px); }}
    }}
    @keyframes trail {{
      0%, {number(start - 0.5)}% {{ opacity: 0; stroke-dashoffset: {tail}px; }}
      {start}% {{ opacity: 1; stroke-dashoffset: {tail}px; }}
      {end}% {{ opacity: 1; stroke-dashoffset: {number(tail - length)}px; }}
      {end + 3}%, 100% {{ opacity: 0; stroke-dashoffset: {number(tail - length)}px; }}
    }}
    @keyframes node {{
      0%, {number(end - 0.5)}% {{ opacity: 0; }}
      {end + 1}% {{ opacity: 1; }}
      {end + 14}%, 100% {{ opacity: 0; }}
    }}
  </style>
  <path class="line" d="{path}" fill="none" stroke="{light}" stroke-opacity="0.32" stroke-width="{line}" stroke-linejoin="round"/>
  <circle class="line" cx="{x0 - ring - 1}" cy="{y1}" r="{ring}" fill="none" stroke="{light}" stroke-width="{line}" stroke-opacity="0.55"/>
  <circle class="dot" cx="{jog - half}" cy="{y1}" r="{ring / 2:g}" fill="{light}" opacity="0.6"/>
  <circle class="dot" cx="{jog + half}" cy="{y2}" r="{ring / 2:g}" fill="{light}" opacity="0.6"/>
  <circle class="dot" cx="{x1 + ring + 1}" cy="{y2}" r="{ring}" fill="{light}" opacity="0.4"/>
  <g class="node"><circle class="dot" cx="{x1 + ring + 1}" cy="{y2}" r="{glow}" fill="{light}" opacity="0.18"/><circle class="dot" cx="{x1 + ring + 1}" cy="{y2}" r="{ring}" fill="{light}"/></g>
  <path class="line trail" d="{path}" fill="none" stroke="{light}" stroke-width="{trail}" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="{tail} 3000"/>
  <circle class="dot head" cx="{x0}" cy="{y1}" r="{head}" fill="{light}"/>
</svg>
"""


def media_uri(name: str) -> str:
    data = base64.b64encode((MEDIA / name).read_bytes()).decode("ascii")
    return f"data:image/webp;base64,{data}"


def npm_tokens(downloads: str, latest: str, versions: str, as_of: str) -> dict[str, str]:
    return {
        "npm_downloads": downloads,
        "npm_latest": latest,
        "npm_versions": versions,
        "npm_as_of": as_of,
        "npm_odometer": odometer(downloads, 48, 293, 32),
        "npm_odometer_narrow": odometer(downloads, 24, 322, 30),
    }


def npm_figures(theme: str) -> dict[str, str]:
    """The DSH card's npm metrics, formatted like the homepage (validate-svg.py re-checks them)."""
    stats = json.loads(NPM_STATS.read_text(encoding="utf-8"))
    return npm_tokens(
        f"{int(stats['downloads_last_month']):,}",
        escape(str(stats["latest"])),
        f"{int(stats['version_count']):,}",
        escape(str(stats["downloads_end"])),
    )


def hero_media(theme: str) -> dict[str, str]:
    return {
        "dsh_trends": media_uri(f"dsh-trends-{theme}.webp"),
        "photo_pot": media_uri("esp32-s3-multimodal-smart-pot.webp"),
        "photo_traffic": media_uri("adaptive-traffic-signal-system.webp"),
        "photo_voice": media_uri("esp32-s3-health-voice-terminal.webp"),
    }


def render(template: Template, style: str, palette: dict[str, str], extra: dict[str, str] | None = None) -> str:
    tokens = dict(palette)
    tokens.update(prototypes=str(HARDWARE_PROTOTYPES))
    tokens.update(extra or {})
    # Styles may carry palette tokens themselves (the terminal does); resolve them before
    # the outer template substitutes the whole style block.
    tokens["style"] = Template(style).substitute(tokens)
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
NPM_PLACEHOLDER = npm_tokens("0", "0.0.0", "0", "0000-00-00")
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
        "hardware-strip": (STRIP, STRIP_STYLE, lambda theme: {}),
        "terminal": (TERMINAL, TERMINAL_STYLE, lambda theme: {}),
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
        "hardware-strip": (STRIP_MOBILE, narrow_strip_style(), {}, lambda svg: svg),
        "terminal": (TERMINAL_MOBILE, TERMINAL_MOBILE_STYLE, {}, lambda svg: svg),
    }
    for stem, (template, style, extra, finish) in narrow.items():
        for suffix, motion in (("mobile", True), ("mobile-still", False)):
            rendered[ASSETS / f"{stem}-{suffix}.svg"] = finish(render_adaptive(template, style, extra, motion=motion))
    for name, motion in (("dsh-card-mobile.svg", True), ("dsh-card-mobile-still.svg", False)):
        rendered[ASSETS / name] = render_adaptive(DSH_MOBILE, DSH_STYLE, npm_figures('light'), motion=motion)
        hash_sources[ASSETS / name] = render_adaptive(DSH_MOBILE, DSH_STYLE, NPM_PLACEHOLDER, motion=motion)
    for stem, spec in BADGES.items():
        rendered[ASSETS / f"{stem}.svg"] = badge(*spec, *BADGE_MOTION[stem])
    for lane in DIVIDER_JOGS:
        rendered[ASSETS / f"divider-{lane}.svg"] = divider(lane, "wide")
        rendered[ASSETS / f"divider-{lane}-mobile.svg"] = divider(lane, "narrow")
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
