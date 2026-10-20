#!/usr/bin/env python3
"""Render the generated profile SVG pairs from one template per asset.

hero-*.svg and hardware-strip-*.svg are generated: edit this file, then run
`python3 scripts/render-svg.py`. CI runs `--check` so committed files cannot
drift from the templates. Dark and light variants share geometry and motion
CSS; only the palette tokens below differ.
"""

from pathlib import Path
from string import Template
import sys

ASSETS = Path("assets")
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
        "card_stroke": "#2a3341",
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
        "wash": "0.18",
        "board": "#0a1714",
        "led_off": "#183a2e",
        "led_on": "#b6ec6a",
        "pulse": "#b6ec6a",
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
        "card_stroke": "#d5dbe4",
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
        "wash": "0.1",
        "board": "#f1faf5",
        "led_off": "#cfe9dc",
        "led_on": "#1aa572",
        "pulse": "#1aa572",
    },
}

# Motion CSS is palette-free so both themes share it byte for byte. Every
# animation sits inside the no-preference guard; reduced motion shows a still frame.
HERO_STYLE = """  <style>
    text { font-family: Arial, "PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif; }
    .mono { font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace; }
    .route { stroke-dasharray: 4 7; stroke-linecap: round; }
    .orbit { stroke-dasharray: 2 6; }
    .underline, .core-pulse { transform-box: fill-box; }
    .underline { transform-origin: 0 50%; }
    .core-pulse { transform-origin: 50% 50%; }
    .orbit-a, .orbit-b, .orbit-c { transform-box: view-box; transform-origin: 853px 180px; }
    .packet, .activity, .lit, .core-pulse { opacity: 0; }
    @media (prefers-reduced-motion: no-preference) {
      .underline { animation: underline 0.9s cubic-bezier(0.2, 0.7, 0.2, 1) both; }
      .orbit-a { animation: spin 14s linear infinite; }
      .orbit-b { animation: spin 20s linear infinite reverse; }
      .orbit-c { animation: spin 26s linear infinite; }
      .core-pulse { animation: core-pulse 7.2s ease-out infinite; }
      .packet-see { animation: packet-see 7.2s cubic-bezier(0.4, 0, 0.2, 1) infinite; }
      .activity-see { animation: activity-see 7.2s ease-in-out infinite; }
      .packet-touch { animation: packet-touch 7.2s cubic-bezier(0.4, 0, 0.2, 1) infinite; }
      .pulse-a { animation: pulse-a 7.2s linear infinite; }
      .pulse-b { animation: pulse-b 7.2s linear infinite; }
      .pulse-c { animation: pulse-c 7.2s linear infinite; }
      .lit-a { animation: lit-a 7.2s ease-in-out infinite; }
      .lit-b { animation: lit-b 7.2s ease-in-out infinite; }
      .lit-c { animation: lit-c 7.2s ease-in-out infinite; }
    }
    @keyframes underline {
      from { transform: scaleX(0); }
      to { transform: scaleX(1); }
    }
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
    @keyframes core-pulse {
      0%, 1% { transform: scale(1); opacity: 0; }
      2% { transform: scale(1); opacity: 0.85; }
      12%, 100% { transform: scale(1.7); opacity: 0; }
    }
    @keyframes packet-see {
      0%, 12% { transform: translateX(0); opacity: 0; }
      13% { transform: translateX(0); opacity: 1; }
      26% { transform: translateX(-49px); opacity: 1; }
      27%, 100% { transform: translateX(-49px); opacity: 0; }
    }
    @keyframes activity-see {
      0%, 27% { opacity: 0; }
      29%, 37% { opacity: 1; }
      41%, 100% { opacity: 0; }
    }
    @keyframes packet-touch {
      0%, 41% { transform: translateX(0); opacity: 0; }
      42% { transform: translateX(0); opacity: 1; }
      55% { transform: translateX(49px); opacity: 1; }
      56%, 100% { transform: translateX(49px); opacity: 0; }
    }
    @keyframes pulse-a {
      0%, 56% { transform: translate(0, 0); opacity: 0; }
      57% { transform: translate(0, 0); opacity: 1; }
      61.5% { transform: translate(24px, 0); }
      65.5% { transform: translate(38px, -14px); }
      71% { transform: translate(71px, -14px); opacity: 1; }
      72%, 100% { transform: translate(71px, -14px); opacity: 0; }
    }
    @keyframes pulse-b {
      0%, 58% { transform: translateX(0); opacity: 0; }
      59% { transform: translateX(0); opacity: 1; }
      73% { transform: translateX(71px); opacity: 1; }
      74%, 100% { transform: translateX(71px); opacity: 0; }
    }
    @keyframes pulse-c {
      0%, 60% { transform: translate(0, 0); opacity: 0; }
      61% { transform: translate(0, 0); opacity: 1; }
      65.5% { transform: translate(24px, 0); }
      69.5% { transform: translate(38px, 14px); }
      75% { transform: translate(71px, 14px); opacity: 1; }
      76%, 100% { transform: translate(71px, 14px); opacity: 0; }
    }
    @keyframes lit-a {
      0%, 71% { opacity: 0; }
      73%, 84% { opacity: 1; }
      90%, 100% { opacity: 0; }
    }
    @keyframes lit-b {
      0%, 73% { opacity: 0; }
      75%, 86% { opacity: 1; }
      92%, 100% { opacity: 0; }
    }
    @keyframes lit-c {
      0%, 75% { opacity: 0; }
      77%, 88% { opacity: 1; }
      94%, 100% { opacity: 0; }
    }
  </style>"""

HERO = Template("""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="360" viewBox="0 0 1200 360" role="img" aria-labelledby="title desc">
  <title id="title">Rongyi，独立开发者 · Yi盘创始人</title>
  <desc id="desc">${theme_desc}品牌横幅。左侧是三行主张：随身的上下文，看得见的 Agent，摸得着的硬件。右侧是三条线的工作室结构示意：Yi盘居中，左边列出三个公开 Agent 工具（DSH Usage、dsh-spec、DevFlow），右边是硬件原型电路板，信号从中心依次流向两侧。结构示意，非产品截图。</desc>
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
    <radialGradient id="washCarry">
      <stop stop-color="${carry}" stop-opacity="${wash}"/>
      <stop offset="1" stop-color="${carry}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="washSee">
      <stop stop-color="${see}" stop-opacity="${wash}"/>
      <stop offset="1" stop-color="${see}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="washTouch">
      <stop stop-color="${touch}" stop-opacity="${wash}"/>
      <stop offset="1" stop-color="${touch}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="coreFill">
      <stop stop-color="${carry}" stop-opacity="0.3"/>
      <stop offset="1" stop-color="${carry}" stop-opacity="0.05"/>
    </radialGradient>
    <radialGradient id="ledGlow">
      <stop stop-color="${led_on}" stop-opacity="0.55"/>
      <stop offset="1" stop-color="${led_on}" stop-opacity="0"/>
    </radialGradient>
    <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
      <path d="M40 0H0V40" fill="none" stroke="${grid_line}" stroke-width="0.6" opacity="${grid_opacity}"/>
      <circle r="1" fill="${carry}" opacity="0.15"/>
    </pattern>
    <mask id="gridMask" maskUnits="userSpaceOnUse" x="16" y="16" width="1168" height="328">
      <rect x="16" y="16" width="1168" height="328" fill="url(#gridFade)"/>
    </mask>
    <marker id="arrowSee" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
      <path d="M0 0 8 4 0 8Z" fill="${see}"/>
    </marker>
    <marker id="arrowTouch" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
      <path d="M0 0 8 4 0 8Z" fill="${touch}"/>
    </marker>
    <clipPath id="panelClip">
      <rect x="16" y="16" width="1168" height="328" rx="16"/>
    </clipPath>
  </defs>
${style}

  <rect x="0.5" y="0.5" width="1199" height="359" rx="20" fill="${shell}" stroke="${shell_stroke}"/>
  <rect x="16" y="16" width="1168" height="328" rx="16" fill="url(#surface)" stroke="${panel_stroke}"/>
  <g clip-path="url(#panelClip)">
    <rect x="16" y="16" width="1168" height="328" fill="url(#grid)" mask="url(#gridMask)"/>
    <circle cx="674" cy="196" r="170" fill="url(#washSee)"/>
    <circle cx="853" cy="180" r="210" fill="url(#washCarry)"/>
    <circle cx="1032" cy="196" r="170" fill="url(#washTouch)"/>
  </g>
  <rect x="16.5" y="16.5" width="1167" height="327" rx="15.5" fill="none" stroke="url(#edge)" opacity="0.8"/>

  <g transform="translate(54 42)">
    <rect width="46" height="46" rx="12" fill="${card}" stroke="${carry}" stroke-width="2"/>
    <text x="23" y="31" fill="${carry_text}" font-size="24" font-weight="800" text-anchor="middle">R</text>
    <text x="64" y="18" fill="${ink}" font-size="16" font-weight="700" letter-spacing="3">RONGYI</text>
    <text x="64" y="40" fill="${muted}" font-size="13" letter-spacing="1.4">INDIE DEVELOPER · FOUNDER OF YI盘</text>
  </g>

  <g font-size="46" font-weight="800" letter-spacing="-1.2">
    <text x="54" y="162" fill="${ink}"><tspan fill="${carry_text}">随身</tspan>的上下文，</text>
    <text x="54" y="220" fill="${ink}"><tspan fill="${see_text}">看得见</tspan>的 Agent，</text>
    <text x="54" y="278" fill="${ink}"><tspan fill="${touch_text}">摸得着</tspan>的硬件。</text>
  </g>
  <rect class="underline" x="55" y="172" width="88" height="4" rx="2" fill="${carry}" style="animation-delay: 0.3s"/>
  <rect class="underline" x="55" y="230" width="134" height="4" rx="2" fill="${see}" style="animation-delay: 0.55s"/>
  <rect class="underline" x="55" y="288" width="134" height="4" rx="2" fill="${touch}" style="animation-delay: 0.8s"/>

  <g id="studio-map">
    <rect id="map-frame" x="560" y="40" width="586" height="280" rx="14" fill="${card}" fill-opacity="0.72" stroke="${card_stroke}"/>
    <text x="578" y="62" class="mono" fill="${faint}" font-size="11" letter-spacing="1.2">RONGYI STUDIO / 三条线示意</text>
    <text x="1128" y="62" fill="${faint}" font-size="11" text-anchor="end">结构示意 · 非产品截图</text>
    <path d="M560 74H1146" stroke="${card_stroke}"/>

    <g id="zone-see">
      <rect x="578" y="90" width="196" height="212" rx="12" fill="${zone_fill}" stroke="${see}" stroke-opacity="0.45"/>
      <text x="594" y="114" fill="${ink}" font-size="14" font-weight="700">AGENT 工具</text>
      <text x="758" y="114" fill="${see_text}" font-size="12" text-anchor="end">可见</text>
      <text x="594" y="138" class="mono" fill="${faint}" font-size="10" letter-spacing="1">PUBLIC REPOS</text>
      <g fill="${card}" stroke="${card_stroke}">
        <rect x="588" y="150" width="176" height="42" rx="8"/>
        <rect x="588" y="198" width="176" height="42" rx="8"/>
        <rect x="588" y="246" width="176" height="42" rx="8"/>
      </g>
      <rect class="activity activity-see" x="588" y="150" width="176" height="42" rx="8" fill="${see}" fill-opacity="0.12" stroke="${see}" stroke-width="1.5"/>
      <g fill="${see}">
        <circle cx="601" cy="163" r="3.5"/>
        <circle cx="601" cy="211" r="3.5"/>
        <circle cx="601" cy="259" r="3.5"/>
      </g>
      <g font-size="13" font-weight="700" fill="${ink}">
        <text x="612" y="167">DSH Usage</text>
        <text x="612" y="215">dsh-spec</text>
        <text x="612" y="263">DevFlow</text>
      </g>
      <g font-size="11" fill="${muted}">
        <text x="612" y="183">Token · 时长 · 费用</text>
        <text x="612" y="231">规格 · 实现 · 验收</text>
        <text x="612" y="279">窗口焦点 · 本地时间线</text>
      </g>
      <g class="mono" font-size="9" letter-spacing="0.8" fill="${see_text}" text-anchor="end">
        <text x="754" y="167">USAGE</text>
        <text x="754" y="215">SPEC</text>
        <text x="754" y="263">OBSERVE</text>
      </g>
    </g>

    <g id="zone-carry">
      <g class="orbit-a">
        <circle class="orbit" cx="853" cy="180" r="42" fill="none" stroke="${carry}" stroke-opacity="0.45"/>
        <circle cx="823.3" cy="150.3" r="3" fill="${carry_2}"/>
      </g>
      <g class="orbit-b">
        <circle class="orbit" cx="853" cy="180" r="52" fill="none" stroke="${see}" stroke-opacity="0.32"/>
        <circle cx="898" cy="206" r="2.6" fill="${see}"/>
      </g>
      <g class="orbit-c">
        <circle class="orbit" cx="853" cy="180" r="62" fill="none" stroke="${touch}" stroke-opacity="0.28"/>
        <circle cx="884" cy="126.3" r="2.6" fill="${touch}"/>
      </g>
      <path class="route" d="M821 180H780" fill="none" stroke="${see}" stroke-width="1.6" marker-end="url(#arrowSee)"/>
      <path class="route" d="M885 180H926" fill="none" stroke="${touch}" stroke-width="1.6" marker-end="url(#arrowTouch)"/>
      <circle class="core-pulse" cx="853" cy="180" r="32" fill="none" stroke="${carry}" stroke-width="2"/>
      <circle cx="853" cy="180" r="32" fill="url(#coreFill)" stroke="${carry}" stroke-width="1.5"/>
      <text class="core-name" x="853" y="187" fill="${ink}" font-size="20" font-weight="800" text-anchor="middle">YI<tspan fill="${carry_text}">盘</tspan></text>
      <text x="853" y="262" fill="${carry_text}" font-size="13" font-weight="700" text-anchor="middle">随身</text>
      <text class="mono core-label" x="853" y="280" fill="${faint}" font-size="10" letter-spacing="1" text-anchor="middle">PORTABLE CONTEXT</text>
    </g>

    <g id="zone-touch">
      <rect x="932" y="90" width="196" height="212" rx="12" fill="${zone_fill}" stroke="${touch}" stroke-opacity="0.45"/>
      <text x="948" y="114" fill="${ink}" font-size="14" font-weight="700">硬件原型</text>
      <text x="1112" y="114" fill="${touch_text}" font-size="12" text-anchor="end">可触</text>
      <rect x="948" y="128" width="164" height="96" rx="8" fill="${board}" stroke="${touch}" stroke-opacity="0.5"/>
      <path d="M968 152V146M976 152V146M984 152V146M992 152V146M968 200V206M976 200V206M984 200V206M992 200V206" stroke="${touch}" stroke-opacity="0.55" stroke-width="1.5"/>
      <rect x="960" y="152" width="40" height="48" rx="4" fill="${zone_fill}" stroke="${touch}" stroke-opacity="0.7"/>
      <text x="980" y="180" class="mono" fill="${touch_text}" font-size="9" text-anchor="middle">MCU</text>
      <g fill="none" stroke="${touch}" stroke-opacity="0.45" stroke-width="1.5">
        <path d="M1000 162H1024L1038 148H1071"/>
        <path d="M1000 176H1071"/>
        <path d="M1000 190H1024L1038 204H1071"/>
      </g>
      <circle cx="1024" cy="162" r="2.2" fill="${touch}"/>
      <circle cx="1024" cy="190" r="2.2" fill="${touch}"/>
      <g fill="${led_off}" stroke="${touch}" stroke-opacity="0.5">
        <circle cx="1080" cy="148" r="5"/>
        <circle cx="1080" cy="176" r="5"/>
        <circle cx="1080" cy="204" r="5"/>
      </g>
      <g class="lit lit-a"><circle cx="1080" cy="148" r="13" fill="url(#ledGlow)"/><circle cx="1080" cy="148" r="5" fill="${led_on}"/></g>
      <g class="lit lit-b"><circle cx="1080" cy="176" r="13" fill="url(#ledGlow)"/><circle cx="1080" cy="176" r="5" fill="${led_on}"/></g>
      <g class="lit lit-c"><circle cx="1080" cy="204" r="13" fill="url(#ledGlow)"/><circle cx="1080" cy="204" r="5" fill="${led_on}"/></g>
      <g fill="${pulse}">
        <circle class="packet pulse-a" cx="1000" cy="162" r="2.6"/>
        <circle class="packet pulse-b" cx="1000" cy="176" r="2.6"/>
        <circle class="packet pulse-c" cx="1000" cy="190" r="2.6"/>
      </g>
      <g class="mono" font-size="10" fill="none" stroke="${touch}" stroke-opacity="0.45">
        <rect x="948" y="238" width="50" height="18" rx="9"/>
        <rect x="1004" y="238" width="50" height="18" rx="9"/>
        <rect x="1060" y="238" width="40" height="18" rx="9"/>
      </g>
      <g class="mono" font-size="10" fill="${touch_text}" text-anchor="middle">
        <text x="973" y="251">ESP32</text>
        <text x="1029" y="251">STM32</text>
        <text x="1080" y="251">RPi</text>
      </g>
      <text x="948" y="284" class="mono" fill="${faint}" font-size="10" letter-spacing="1">SENSOR → MCU → LED</text>
    </g>

    <g fill="${packet_fill}" stroke-width="2">
      <circle class="packet packet-see" cx="825" cy="180" r="4" stroke="${see}"/>
      <circle class="packet packet-touch" cx="881" cy="180" r="4" stroke="${touch}"/>
    </g>
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


def render(template: Template, style: str, palette: dict[str, str], extra: dict[str, str] | None = None) -> str:
    tokens = dict(palette)
    tokens.update(style=style, prototypes=str(HARDWARE_PROTOTYPES))
    tokens.update(extra or {})
    return template.substitute(tokens)


def main() -> int:
    check = "--check" in sys.argv[1:]
    outputs = {
        "hero": (HERO, HERO_STYLE, lambda: {}),
        "hardware-strip": (STRIP, STRIP_STYLE, lambda: {}),
    }
    stale: list[str] = []
    for stem, (template, style, extra) in outputs.items():
        for theme, palette in PALETTES.items():
            path = ASSETS / f"{stem}-{theme}.svg"
            svg = render(template, style, palette, extra())
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
