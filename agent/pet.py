"""
AnsysAgent 宠物系统 —— 彩蛋模块

三只住在终端里的仿真小精灵，陪你度过漫长的仿真时光。

宠物种类：
  - 安安（maxwell_cat）：电磁猫精灵，傲娇学霸，默认宠物
  - 氟氟（fluent_fox）：流体狐狸，元气话痨，懂 CFD
  - 马普（mapdl_dog）：结构犬，憨厚可靠，懂 MAPDL

功能：
  - 三种宠物，每种有独立 ASCII 形象库（按成长阶段 × 心情状态变化）
  - 隐藏形象「量子 Maxwell」（/bugpet）、「热力学混沌」氟氟（连续5天喂食）、「有限元之神」马普（200次仿真后摸摸）
  - 状态持久化（心情、饥饿、精力、互动次数、仿真次数、诞生日期、名字、技能）
  - 随仿真次数成长（幼崽 → 少年 → 成年 → 专家 → 传奇），每段解锁专属技能
  - 喂食、抚摸、重命名、查看状态、休息、游戏、切换宠物
  - 连续互动奖励：连续3天互动触发亲密度加成
  - 精力值系统：仿真消耗精力，精力影响成长效率
  - 每次启动有概率出来打招呼
"""

from __future__ import annotations

import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console

# ---------------------------------------------------------------------------
# 存储路径
# ---------------------------------------------------------------------------

def _pet_save_path() -> Path:
    from agent.paths import ANSYS_DATA_DIR
    return ANSYS_DATA_DIR / "pet.json"


# ---------------------------------------------------------------------------
# 宠物种类
# ---------------------------------------------------------------------------

PET_TYPES = {
    "maxwell_cat": {"name_default": "安安",  "color": "magenta",       "emoji": "🐱"},
    "fluent_fox":  {"name_default": "氟氟",  "color": "bright_blue",   "emoji": "🦊"},
    "mapdl_dog":   {"name_default": "马普",  "color": "bright_yellow", "emoji": "🐶"},
}
PET_TYPE_ALIASES = {
    "安安": "maxwell_cat", "猫": "maxwell_cat", "maxwell_cat": "maxwell_cat",
    "氟氟": "fluent_fox",  "狐": "fluent_fox",  "fluent_fox":  "fluent_fox",
    "马普": "mapdl_dog",   "狗": "mapdl_dog",   "mapdl_dog":   "mapdl_dog",
}

# ---------------------------------------------------------------------------
# 成长阶段
# ---------------------------------------------------------------------------

# (最低仿真次数, 阶段key, 阶段名, 称号_猫, 称号_狐, 称号_狗)
_STAGES = [
    (0,   "baby",   "幼崽期",   "仿真见习生",     "流体初学者",    "结构小学徒"),
    (10,  "child",  "少年期",   "麦克斯韦学徒",   "雷诺数猎手",    "应力追踪者"),
    (50,  "adult",  "成年期",   "电磁场驯服者",   "湍流驯化师",    "模态洞察者"),
    (150, "expert", "专家期",   "永磁体守护神",   "网格诗人",      "NVH 降噪师"),
    (500, "legend", "传奇期",   "PMSM 仿真宗师",  "CFD 天神",      "结构力学祖师"),
]

# 各宠物各阶段解锁技能
_SKILLS_CAT = {
    "child":  "磁场感知",
    "adult":  "涡流探测",
    "expert": "永磁守护",
    "legend": "PMSM 宗师",
}
_SKILLS_FOX = {
    "child":  "湍流直觉",
    "adult":  "雷诺数掌控",
    "expert": "网格诗人",
    "legend": "CFD 天神",
}
_SKILLS_DOG = {
    "child":  "应力嗅觉",
    "adult":  "模态洞察",
    "expert": "NVH 降噪师",
    "legend": "结构力学祖师",
}
_PET_SKILLS: dict[str, dict[str, str]] = {
    "maxwell_cat": _SKILLS_CAT,
    "fluent_fox":  _SKILLS_FOX,
    "mapdl_dog":   _SKILLS_DOG,
}

# ---------------------------------------------------------------------------
# ASCII 形象库 —— 安安（maxwell_cat）
# 按 stage_key → mood_key → 多行字符串
# mood_key: happy / normal / hungry / sad / excited
# ---------------------------------------------------------------------------

_SPRITES: dict[str, dict[str, str]] = {

    # ── 幼崽期 ──────────────────────────────────────────────────────────
    "baby": {
        "excited": r"""
   ／￣＼
  (^•ω•^)ﾉ
   ／ |
  (ﾉ__)ﾉ""",
        "happy": r"""
   ／￣＼
  ( •ω• )
   ‖ | ‖
  (_(_)_)""",
        "normal": r"""
   ／￣＼
  (・ω・ )
   ‖ | ‖
  (_(_)_)""",
        "hungry": r"""
   ／￣＼
  (；ﾟДﾟ)
   ‖ | ‖
  (_(_)_)
  ＊肚子咕咕叫""",
        "sad": r"""
   ／￣＼
  (；△；)
   ‖ | ‖
  (_(_)_)
  ＊呜……""",
    },

    # ── 少年期 ──────────────────────────────────────────────────────────
    "child": {
        "excited": r"""
    ∧＿∧
   (≧▽≦)ﾉ  ✦
   |  ⚡|
   (_＿_)""",
        "happy": r"""
    ∧＿∧
   (*•ω•*)
   |  ∥ |
   (_＿_)""",
        "normal": r"""
    ∧＿∧
   (・ω・)
   |  ∥ |
   (_＿_)""",
        "hungry": r"""
    ∧＿∧
   (>ω<；)
   |  ∥ |
   (_＿_)
  ～ 饿饿 ～""",
        "sad": r"""
    ∧＿∧
   (；△；)
   |  ∥ |
   (_＿_)
  ～ 心情低落""",
    },

    # ── 成年期 ──────────────────────────────────────────────────────────
    "adult": {
        "excited": r"""
   ╔══╗
   ║≧▽≦║  ＼(★)/
   ║ ⚡║
   ╚══╝
   /|  |\
  (_) (_)""",
        "happy": r"""
   ╔══╗
   ║^ω^║
   ║ ∥ ║
   ╚══╝
   /|  |\
  (_) (_)""",
        "normal": r"""
   ╔══╗
   ║・ω・║
   ║ ∥ ║
   ╚══╝
   /|  |\
  (_) (_)""",
        "hungry": r"""
   ╔══╗
   ║>Д<║  ← 饿！
   ║ ∥ ║
   ╚══╝
   /|  |\
  (_) (_)""",
        "sad": r"""
   ╔══╗
   ║；△；║
   ║ ∥ ║
   ╚══╝
   /|  |\
  (_) (_)""",
    },

    # ── 专家期 ──────────────────────────────────────────────────────────
    "expert": {
        "excited": r"""
   ┌─────┐
   │≧▽≦ ✦│  ⚡ MAX ⚡
   │🧲∥🧲│
   └─────┘
    /|   |\
  ∫(_) (_)∫""",
        "happy": r"""
   ┌─────┐
   │^ω^ ★│
   │🧲∥🧲│
   └─────┘
    /|   |\
  ∫(_) (_)∫""",
        "normal": r"""
   ┌─────┐
   │・ω・  │
   │🧲∥🧲│
   └─────┘
    /|   |\
  ∫(_) (_)∫""",
        "hungry": r"""
   ┌─────┐
   │>Д<；  │  ← 快饿晕了
   │🧲∥🧲│
   └─────┘
    /|   |\
  ∫(_) (_)∫""",
        "sad": r"""
   ┌─────┐
   │；△；   │
   │🧲∥🧲│
   └─────┘
    /|   |\
  ∫(_) (_)∫""",
    },

    # ── 传奇期 ──────────────────────────────────────────────────────────
    "legend": {
        "excited": r"""
  ╔══════╗
  ║ ≧▽≦ ║  ✦✦✦
  ║⚡🧲⚡║  << PMSM MASTER >>
  ║ ∫∫∫  ║
  ╚══════╝
    ║   ║
   ═╩═ ═╩═""",
        "happy": r"""
  ╔══════╗
  ║ ^ω^ ★║
  ║⚡🧲⚡║
  ║ ∫∫∫  ║
  ╚══════╝
    ║   ║
   ═╩═ ═╩═""",
        "normal": r"""
  ╔══════╗
  ║ ・ω・ ║
  ║⚡🧲⚡║
  ║ ∫∫∫  ║
  ╚══════╝
    ║   ║
   ═╩═ ═╩═""",
        "hungry": r"""
  ╔══════╗
  ║ >Д<；║  ← 传奇也要吃饭！
  ║⚡🧲⚡║
  ║ ∫∫∫  ║
  ╚══════╝
    ║   ║
   ═╩═ ═╩═""",
        "sad": r"""
  ╔══════╗
  ║ ；△；  ║
  ║⚡🧲⚡║
  ║ ∫∫∫  ║
  ╚══════╝
    ║   ║
   ═╩═ ═╩═""",
    },
}

# ---------------------------------------------------------------------------
# ASCII 形象库 —— 氟氟（fluent_fox）
# ---------------------------------------------------------------------------

_SPRITES_FOX: dict[str, dict[str, str]] = {

    "baby": {
        "excited": r"""
   /\  /\
  (^▿^)ﾉ  ~~
   ) 🌊(
  (___)""",
        "happy": r"""
   /\  /\
  (*▿*)
   ) 🌊(
  (___)""",
        "normal": r"""
   /\  /\
  (·▿·)
   )  (
  (___)""",
        "hungry": r"""
   /\  /\
  (；Д；)
   )  (
  (___)
  ＊肚肚扁扁""",
        "sad": r"""
   /\  /\
  (；△；)
   )  (
  (___)
  ＊呜呜""",
    },

    "child": {
        "excited": r"""
   ∧∧∧∧
  (≧▽≦)ﾉ  💧
   | 🌊|
   (____)""",
        "happy": r"""
   ∧∧∧∧
  (*▿* )
   | 🌊|
   (____)""",
        "normal": r"""
   ∧∧∧∧
  (·▿·  )
   |   |
   (____)""",
        "hungry": r"""
   ∧∧∧∧
  (>Д<；)
   |   |
   (____)
  ～ 饿饿 ～""",
        "sad": r"""
   ∧∧∧∧
  (；△；)
   |   |
   (____)
  ～ 心情差""",
    },

    "adult": {
        "excited": r"""
   ╔════╗
   ║≧▽≦ ║  💧💧
   ║ 🌊 ║
   ╚════╝
   /|   |\
  (_)  (_)""",
        "happy": r"""
   ╔════╗
   ║^▿^ ║
   ║ 🌊 ║
   ╚════╝
   /|   |\
  (_)  (_)""",
        "normal": r"""
   ╔════╗
   ║·▿·  ║
   ║ 🌊 ║
   ╚════╝
   /|   |\
  (_)  (_)""",
        "hungry": r"""
   ╔════╗
   ║>Д<；║  ← 饿！
   ║ 🌊 ║
   ╚════╝
   /|   |\
  (_)  (_)""",
        "sad": r"""
   ╔════╗
   ║；△；  ║
   ║ 🌊 ║
   ╚════╝
   /|   |\
  (_)  (_)""",
    },

    "expert": {
        "excited": r"""
   ┌──────┐
   │≧▽≦ 💧│  Re→∞
   │🌊∥🌊│
   └──────┘
    /|    |\
  ~(_)  (_)~""",
        "happy": r"""
   ┌──────┐
   │^▿^ ★ │
   │🌊∥🌊│
   └──────┘
    /|    |\
  ~(_)  (_)~""",
        "normal": r"""
   ┌──────┐
   │·▿·    │
   │🌊∥🌊│
   └──────┘
    /|    |\
  ~(_)  (_)~""",
        "hungry": r"""
   ┌──────┐
   │>Д<；  │  ← 快饿晕了
   │🌊∥🌊│
   └──────┘
    /|    |\
  ~(_)  (_)~""",
        "sad": r"""
   ┌──────┐
   │；△；   │
   │🌊∥🌊│
   └──────┘
    /|    |\
  ~(_)  (_)~""",
    },

    "legend": {
        "excited": r"""
  ╔════════╗
  ║ ≧▽≦  ║  💧💧💧
  ║🌊∇·v🌊║  << CFD GOD >>
  ║  ~~~   ║
  ╚════════╝
    ║    ║
   ═╩═  ═╩═""",
        "happy": r"""
  ╔════════╗
  ║ ^▿^ ★ ║
  ║🌊∇·v🌊║
  ║  ~~~   ║
  ╚════════╝
    ║    ║
   ═╩═  ═╩═""",
        "normal": r"""
  ╔════════╗
  ║  ·▿·  ║
  ║🌊∇·v🌊║
  ║  ~~~   ║
  ╚════════╝
    ║    ║
   ═╩═  ═╩═""",
        "hungry": r"""
  ╔════════╗
  ║ >Д<；  ║  ← 传奇也要吃饭！
  ║🌊∇·v🌊║
  ║  ~~~   ║
  ╚════════╝
    ║    ║
   ═╩═  ═╩═""",
        "sad": r"""
  ╔════════╗
  ║  ；△；  ║
  ║🌊∇·v🌊║
  ║  ~~~   ║
  ╚════════╝
    ║    ║
   ═╩═  ═╩═""",
    },
}

# ---------------------------------------------------------------------------
# ASCII 形象库 —— 马普（mapdl_dog）
# ---------------------------------------------------------------------------

_SPRITES_DOG: dict[str, dict[str, str]] = {

    "baby": {
        "excited": r"""
  / \ / \
 (^∀^)ﾉ  ♪
  [ σ ]
  m   m""",
        "happy": r"""
  / \ / \
 (*∀* )
  [   ]
  m   m""",
        "normal": r"""
  / \ / \
 (・∀・)
  [   ]
  m   m""",
        "hungry": r"""
  / \ / \
 (；Д；)
  [   ]
  m   m
  ＊肚子叫""",
        "sad": r"""
  / \ / \
 (；△；)
  [   ]
  m   m
  ＊……""",
    },

    "child": {
        "excited": r"""
   ∪∪∪∪
  (≧∀≦)ﾉ  ✦
   | σ |
   m___m""",
        "happy": r"""
   ∪∪∪∪
  (*∀* )
   | σ |
   m___m""",
        "normal": r"""
   ∪∪∪∪
  (・∀・)
   |   |
   m___m""",
        "hungry": r"""
   ∪∪∪∪
  (>Д<；)
   |   |
   m___m
  ～ 饿饿 ～""",
        "sad": r"""
   ∪∪∪∪
  (；△；)
   |   |
   m___m
  ～ 心情低落""",
    },

    "adult": {
        "excited": r"""
   ╔════╗
   ║≧∀≦ ║  ✦✦
   ║[σσ]║
   ╚════╝
   /|   |\
  m(_) (_)m""",
        "happy": r"""
   ╔════╗
   ║^∀^ ║
   ║[σσ]║
   ╚════╝
   /|   |\
  m(_) (_)m""",
        "normal": r"""
   ╔════╗
   ║・∀・║
   ║[  ]║
   ╚════╝
   /|   |\
  m(_) (_)m""",
        "hungry": r"""
   ╔════╗
   ║>Д<；║  ← 饿！
   ║[  ]║
   ╚════╝
   /|   |\
  m(_) (_)m""",
        "sad": r"""
   ╔════╗
   ║；△；  ║
   ║[  ]║
   ╚════╝
   /|   |\
  m(_) (_)m""",
    },

    "expert": {
        "excited": r"""
   ┌──────┐
   │≧∀≦ σ│  FEA MAX
   │[σ∥σ]│
   └──────┘
    /|    |\
  m(_)  (_)m""",
        "happy": r"""
   ┌──────┐
   │^∀^ ★ │
   │[σ∥σ]│
   └──────┘
    /|    |\
  m(_)  (_)m""",
        "normal": r"""
   ┌──────┐
   │・∀・   │
   │[σ∥σ]│
   └──────┘
    /|    |\
  m(_)  (_)m""",
        "hungry": r"""
   ┌──────┐
   │>Д<；  │  ← 快饿晕了
   │[σ∥σ]│
   └──────┘
    /|    |\
  m(_)  (_)m""",
        "sad": r"""
   ┌──────┐
   │；△；   │
   │[σ∥σ]│
   └──────┘
    /|    |\
  m(_)  (_)m""",
    },

    "legend": {
        "excited": r"""
  ╔════════╗
  ║ ≧∀≦  ║  ✦✦✦
  ║[σ FEA σ]║  << MAPDL GOD >>
  ║  ∫∫∫   ║
  ╚════════╝
    ║    ║
   m╩m  m╩m""",
        "happy": r"""
  ╔════════╗
  ║ ^∀^ ★ ║
  ║[σ FEA σ]║
  ║  ∫∫∫   ║
  ╚════════╝
    ║    ║
   m╩m  m╩m""",
        "normal": r"""
  ╔════════╗
  ║  ・∀・ ║
  ║[σ FEA σ]║
  ║  ∫∫∫   ║
  ╚════════╝
    ║    ║
   m╩m  m╩m""",
        "hungry": r"""
  ╔════════╗
  ║ >Д<；  ║  ← 结构犬也要吃饭！
  ║[σ FEA σ]║
  ║  ∫∫∫   ║
  ╚════════╝
    ║    ║
   m╩m  m╩m""",
        "sad": r"""
  ╔════════╗
  ║  ；△；  ║
  ║[σ FEA σ]║
  ║  ∫∫∫   ║
  ╚════════╝
    ║    ║
   m╩m  m╩m""",
    },
}

# 统一索引：pet_type → sprites dict
_ALL_SPRITES: dict[str, dict] = {
    "maxwell_cat": _SPRITES,
    "fluent_fox":  _SPRITES_FOX,
    "mapdl_dog":   _SPRITES_DOG,
}

# ---------------------------------------------------------------------------
# 隐藏形象库  ——「量子 Maxwell」
# 通过 /bugpet 解锁，不在任何帮助/补全中显示
# 按 mood_key → ASCII 字符串
# ---------------------------------------------------------------------------

_SECRET_SPRITES: dict[str, str] = {
    "excited": r"""
        ✦   ✦   ✦
   ╔══════════════╗
   ║  ∯ B·dA = 0 ║  ✦
   ║  ╔══════╗   ║
   ║  ║≧▽≦ ✦║   ║  << QUANTUM MAXWELL >>
   ║  ║⚛ 🧲 ⚛║   ║
   ║  ║ ∇×E ║   ║
   ║  ╚══════╝   ║  ✦
   ║  ∮ H·dl = J ║
   ╚══════════════╝
      ╟──┘  └──╢
     ═╩═      ═╩═
   ～～～～～～～～～～""",

    "happy": r"""
        ✦       ✦
   ╔══════════════╗
   ║  ∯ B·dA = 0 ║
   ║  ╔══════╗   ║
   ║  ║^ω^ ★ ║   ║
   ║  ║⚛ 🧲 ⚛║   ║
   ║  ║ ∇×E ║   ║
   ║  ╚══════╝   ║
   ║  ∮ H·dl = J ║
   ╚══════════════╝
      ╟──┘  └──╢
     ═╩═      ═╩═""",

    "normal": r"""
   ╔══════════════╗
   ║  ∯ B·dA = 0 ║
   ║  ╔══════╗   ║
   ║  ║ ・ω・ ║   ║
   ║  ║⚛ 🧲 ⚛║   ║
   ║  ║ ∇×E ║   ║
   ║  ╚══════╝   ║
   ║  ∮ H·dl = J ║
   ╚══════════════╝
      ╟──┘  └──╢
     ═╩═      ═╩═""",

    "hungry": r"""
   ╔══════════════╗
   ║  ∯ B·dA = 0 ║
   ║  ╔══════╗   ║
   ║  ║ >Д<；║   ║  ← 量子态也会饿！
   ║  ║⚛ 🧲 ⚛║   ║
   ║  ║ ∇×E ║   ║
   ║  ╚══════╝   ║
   ║  ∮ H·dl = J ║
   ╚══════════════╝
      ╟──┘  └──╢
     ═╩═      ═╩═""",

    "sad": r"""
   ╔══════════════╗
   ║  ∯ B·dA = 0 ║
   ║  ╔══════╗   ║
   ║  ║ ；△； ║   ║
   ║  ║⚛ 🧲 ⚛║   ║
   ║  ║ ∇×E ║   ║
   ║  ╚══════╝   ║
   ║  ∮ H·dl = J ║
   ╚══════════════╝
      ╟──┘  └──╢
     ═╩═      ═╩═""",
}

# ---------------------------------------------------------------------------
# 隐藏形象库 ——「热力学混沌」氟氟
# 通过连续5天喂食解锁
# ---------------------------------------------------------------------------

_SECRET_SPRITES_FOX: dict[str, str] = {
    "excited": r"""
        💧  💧  💧
   ╔══════════════╗
   ║  ∂ρ/∂t+∇·(ρv)=0 ║  💧
   ║  ╔══════╗   ║
   ║  ║≧▽≦ 💧║   ║  << CHAOS FLUENT >>
   ║  ║🌊 🌀 🌊║   ║
   ║  ║ ∇·v=0║   ║
   ║  ╚══════╝   ║  💧
   ║  ∇p = μ∇²v  ║
   ╚══════════════╝
      ╟──┘  └──╢
     ═╩═      ═╩═
   ～～～～～～～～～～""",
    "happy": r"""
        💧       💧
   ╔══════════════╗
   ║  ∂ρ/∂t+∇·(ρv)=0 ║
   ║  ╔══════╗   ║
   ║  ║^▿^ ★ ║   ║
   ║  ║🌊 🌀 🌊║   ║
   ║  ║ ∇·v=0║   ║
   ║  ╚══════╝   ║
   ║  ∇p = μ∇²v  ║
   ╚══════════════╝
      ╟──┘  └──╢
     ═╩═      ═╩═""",
    "normal": r"""
   ╔══════════════╗
   ║  ∂ρ/∂t+∇·(ρv)=0 ║
   ║  ╔══════╗   ║
   ║  ║ ·▿·  ║   ║
   ║  ║🌊 🌀 🌊║   ║
   ║  ║ ∇·v=0║   ║
   ║  ╚══════╝   ║
   ║  ∇p = μ∇²v  ║
   ╚══════════════╝
      ╟──┘  └──╢
     ═╩═      ═╩═""",
    "hungry": r"""
   ╔══════════════╗
   ║  ∂ρ/∂t+∇·(ρv)=0 ║
   ║  ╔══════╗   ║
   ║  ║ >Д<；║   ║  ← 混沌态也会饿！
   ║  ║🌊 🌀 🌊║   ║
   ║  ║ ∇·v=0║   ║
   ║  ╚══════╝   ║
   ║  ∇p = μ∇²v  ║
   ╚══════════════╝
      ╟──┘  └──╢
     ═╩═      ═╩═""",
    "sad": r"""
   ╔══════════════╗
   ║  ∂ρ/∂t+∇·(ρv)=0 ║
   ║  ╔══════╗   ║
   ║  ║ ；△； ║   ║
   ║  ║🌊 🌀 🌊║   ║
   ║  ║ ∇·v=0║   ║
   ║  ╚══════╝   ║
   ║  ∇p = μ∇²v  ║
   ╚══════════════╝
      ╟──┘  └──╢
     ═╩═      ═╩═""",
}

# ---------------------------------------------------------------------------
# 隐藏形象库 ——「有限元之神」马普
# 通过累计200次仿真后摸摸解锁
# ---------------------------------------------------------------------------

_SECRET_SPRITES_DOG: dict[str, str] = {
    "excited": r"""
        ✦   ✦   ✦
   ╔══════════════╗
   ║ [K]{u} = {F} ║  ✦
   ║  ╔══════╗   ║
   ║  ║≧∀≦ ✦║   ║  << FEA GOD >>
   ║  ║[σ 🔱 σ]║   ║
   ║  ║ ∫σdV ║   ║
   ║  ╚══════╝   ║  ✦
   ║ε = ∇ˢu      ║
   ╚══════════════╝
      ╟──┘  └──╢
     m╩m      m╩m
   ～～～～～～～～～～""",
    "happy": r"""
        ✦       ✦
   ╔══════════════╗
   ║ [K]{u} = {F} ║
   ║  ╔══════╗   ║
   ║  ║^∀^ ★ ║   ║
   ║  ║[σ 🔱 σ]║   ║
   ║  ║ ∫σdV ║   ║
   ║  ╚══════╝   ║
   ║ε = ∇ˢu      ║
   ╚══════════════╝
      ╟──┘  └──╢
     m╩m      m╩m""",
    "normal": r"""
   ╔══════════════╗
   ║ [K]{u} = {F} ║
   ║  ╔══════╗   ║
   ║  ║ ・∀・ ║   ║
   ║  ║[σ 🔱 σ]║   ║
   ║  ║ ∫σdV ║   ║
   ║  ╚══════╝   ║
   ║ε = ∇ˢu      ║
   ╚══════════════╝
      ╟──┘  └──╢
     m╩m      m╩m""",
    "hungry": r"""
   ╔══════════════╗
   ║ [K]{u} = {F} ║
   ║  ╔══════╗   ║
   ║  ║ >Д<；║   ║  ← 神也要吃饭！
   ║  ║[σ 🔱 σ]║   ║
   ║  ║ ∫σdV ║   ║
   ║  ╚══════╝   ║
   ║ε = ∇ˢu      ║
   ╚══════════════╝
      ╟──┘  └──╢
     m╩m      m╩m""",
    "sad": r"""
   ╔══════════════╗
   ║ [K]{u} = {F} ║
   ║  ╔══════╗   ║
   ║  ║ ；△； ║   ║
   ║  ║[σ 🔱 σ]║   ║
   ║  ║ ∫σdV ║   ║
   ║  ╚══════╝   ║
   ║ε = ∇ˢu      ║
   ╚══════════════╝
      ╟──┘  └──╢
     m╩m      m╩m""",
}

# 解锁时播放的逐行动画文本（用于 /bugpet 触发时的特效）
_SECRET_UNLOCK_ANIMATION = [
    "",
    "  [dim]正在检测隐藏特征……[/dim]",
    "  [dim]发现未知能量波动……[/dim]",
    "  [yellow]⚠  警告：检测到麦克斯韦方程组共振！[/yellow]",
    "  [bold red]!! 超导态突破临界温度 !![/bold red]",
    "  [bold magenta]∇ × B = μ₀J + μ₀ε₀ ∂E/∂t[/bold magenta]",
    "  [bold cyan]▓▓▓▓▓▓▓▓▓▓ 量子化进行中…… ▓▓▓▓▓▓▓▓▓▓[/bold cyan]",
    "",
]

# 氟氟隐藏形象解锁动画
_SECRET_FOX_UNLOCK_ANIMATION = [
    "",
    "  [dim]氟氟连续五天都等你来喂食……[/dim]",
    "  [dim]湍流能量在氟氟体内积聚……[/dim]",
    "  [yellow]⚠  雷诺数突破临界值！[/yellow]",
    "  [bold red]!! 湍流突然转为混沌！！[/bold red]",
    "  [bold cyan]∂ρ/∂t + ∇·(ρv) = 0[/bold cyan]",
    "  [bold bright_blue]▓▓▓▓▓▓▓▓▓▓ 热力学混沌化进行中…… ▓▓▓▓▓▓▓▓▓▓[/bold bright_blue]",
    "",
]

# 马普隐藏形象解锁动画
_SECRET_DOG_UNLOCK_ANIMATION = [
    "",
    "  [dim]马普感受到了 200 次仿真的力量……[/dim]",
    "  [dim]刚度矩阵在颤动……[/dim]",
    "  [yellow]⚠  位移场发生奇异变化！[/yellow]",
    "  [bold red]!! [K]{u}={F} 的解已超越常规！！[/bold red]",
    "  [bold yellow]ε = ∇ˢu    σ = C:ε[/bold yellow]",
    "  [bold bright_yellow]▓▓▓▓▓▓▓▓▓▓ 有限元神化进行中…… ▓▓▓▓▓▓▓▓▓▓[/bold bright_yellow]",
    "",
]

# 隐藏形象专属台词
_SECRET_QUOTES_HAPPY = [
    "∇·B = 0，磁单极子不存在，但我存在。",
    "旋度、散度都懂了，你的仿真还有什么能难倒我？",
    "法拉第看了会哭泣，麦克斯韦看了会鼓掌。",
    "收敛！全部收敛！残差已降至机器精度！",
]
_SECRET_QUOTES_NORMAL = [
    "∮ H·dl = J_enc，主人，边界条件记得设好。",
    "我现在是量子态，薛定谔的猫是我弟弟。",
    "麦克斯韦方程组是宇宙的密码，而我是解密器。",
    "位移电流已就位，电磁波随时待命。",
    "气隙磁场已量子纠缠，请放心使用。",
]
_SECRET_QUOTES_HUNGRY = [
    "就算是量子态也需要能量……/pet feed 快！",
    "哈密顿量趋近于零了……快补充能量……",
    "真空涨落也救不了我，请喂我！",
]
_SECRET_QUOTES_SAD = [
    "麦克斯韦方程组都解不开寂寞……",
    "波函数坍缩了，坍缩成了孤独……",
    "连位移电流都在颤抖……",
]

# ---------------------------------------------------------------------------
# 食物 & 台词库
# ---------------------------------------------------------------------------

_FOOD_ITEMS = ["☕ 咖啡", "🍜 泡面", "⚡ 能量棒", "🧲 磁力糖", "🔋 锂电池", "🍱 便当", "🧃 电解质饮料"]

# ── 安安（傲娇学霸）台词 ──────────────────────────────────────────────────
_QUOTES_HAPPY = [
    "今天的转矩波形好漂亮！我帮你看着！",
    "网格剖好了吗？剖好我帮你数数！",
    "听说你又设计了一台新电机？给我看看！",
    "仿真收敛了！撒花！✨",
    "铁损不高，今天运气不错～",
    "主人真厉害，Maxwell 都为你臣服了！",
]
_QUOTES_HUNGRY = [
    "呜……肚子好饿，先去 /pet feed 喂我吧……",
    "饿得头晕了，算法都跑偏了……",
    "如果你不喂我，我就去啃永磁体……",
    "磁场再强也挡不住饥饿！！快喂我！",
]
_QUOTES_SAD = [
    "好久没人理我了……(；△；)",
    "你是不是把我忘了……",
    "我愿意帮你盯仿真，但你得先陪陪我……",
    "涡流损耗都没我心里的失落大……",
]
_QUOTES_NORMAL = [
    "Maxwell 今天有没有报错？",
    "记得检查边界条件哦～",
    "仿真跑完前，先来陪我玩一会儿？",
    "听说 optiSLang 能把电机优化到飞起？",
    "网格这种东西，细一点总没错的。",
    "气隙磁密波形平了吗？",
    "绕组系数算好了吗？",
]
_QUOTES_PAT_CAT = [
    "哼……才不是因为喜欢被摸才发出呼噜声的！心情 +{gain}！",
    "（假装冷漠但尾巴已经摇起来了）心情 +{gain}！",
    "不……不准摸！才没有觉得舒服！（却靠得更近了）心情 +{gain}！",
    "（努力维持傲娇人设失败）好吧……再摸一下也无所谓。心情 +{gain}！",
]

# ── 氟氟（元气话痨）台词 ──────────────────────────────────────────────────
_QUOTES_FOX_HAPPY = [
    "哇哇哇！Fluent 今天收敛超快！是因为主人在旁边吗！！",
    "湍流模型选对了！k-ε 果然是好朋友！",
    "网格！网格！光滑的网格是我的最爱！✨",
    "马赫数稳住了！今天超音速不来扰乱我们！",
    "CFD 后处理出图好漂亮！！主人快来看！！",
    "残差曲线像瀑布一样往下冲！爱了爱了！",
]
_QUOTES_FOX_HUNGRY = [
    "呜哇！肚子扁扁！流体都没力气流了！快喂我！！",
    "饥饿感比湍流还难控制啊喂！！/pet feed 快！",
    "Re 数归零！雷诺数归零！不对是我饿到头晕了！",
    "如果不喂我，我就把边界层变成拒马！！",
]
_QUOTES_FOX_SAD = [
    "呜呜……主人好久没来了，连湍流都安静了……",
    "好孤独哦……流体方程解出来了但没人分享……(；△；)",
    "是不是被 MAPDL 占据了所有时间……我也很重要的！",
    "我话变少了……这不正常……主人你在哪里……",
]
_QUOTES_FOX_NORMAL = [
    "今天的网格质量怎么样？歪斜度超过 0.9 了吗？",
    "听说湍动能 k 和耗散率 ε 最近在打架！",
    "壁面函数用 Enhanced Wall Treatment 了吗？",
    "Fluent 报错信息能看懂吗？我来帮你翻译！",
    "有没有遇到发散的残差曲线？放松松弛因子试试！",
    "非结构网格更灵活，但结构网格质量更好——怎么选呢？",
]
_QUOTES_FOX_PAT = [
    "嘿嘿嘿！主人摸我！！好开心！！心情 +{gain}！！",
    "耶耶耶！摸摸！！就喜欢被摸！！心情 +{gain}！",
    "（剧烈摇尾）摸摸我就会更努力仿真的！心情 +{gain}！",
    "再摸一次！再摸一次！！心情 +{gain}！！",
]

# ── 马普（憨厚可靠）台词 ──────────────────────────────────────────────────
_QUOTES_DOG_HAPPY = [
    "结构分析完成。应力分布良好。（摇尾）",
    "今天的网格……不错。我喜欢。",
    "位移场收敛了。主人很厉害。",
    "模态分析做完了，固有频率清晰，很好。",
    "非线性也收敛了。今天是个好日子。",
    "（安静地靠在主人身边）仿真跑着呢，不用担心。",
]
_QUOTES_DOG_HUNGRY = [
    "……饿。需要能量。请喂食。",
    "刚度矩阵快空了……不对，是肚子。喂我。",
    "迭代次数增加了……那是我肚子在咕咕叫。",
    "FEA 也要能量来源。主人，喂我。",
]
_QUOTES_DOG_SAD = [
    "……主人不在。网格质量也下降了。",
    "（趴在角落）没有仿真跑……没有互动……",
    "边界条件缺失……主人也缺失了……",
    "单元扭曲了……心情也扭曲了。",
]
_QUOTES_DOG_NORMAL = [
    "网格划分好了吗？四面体还是六面体？",
    "接触设置检查一下。摩擦系数定义了吗？",
    "MAPDL 的命令流清晰就是效率。",
    "预应力模态分析……要记得加载步骤。",
    "材料非线性会增加收敛难度。注意一下。",
    "DPF-Core 后处理可以批量出图，很方便。",
]
_QUOTES_DOG_PAT = [
    "（尾巴慢慢摇）……谢谢。心情 +{gain}。",
    "（低头靠近主人的手）……舒服。心情 +{gain}。",
    "这样……可以的。再一下也没关系。心情 +{gain}。",
    "（大眼睛望着主人）……下次也可以摸。心情 +{gain}。",
]

# ── 各宠物问候语模板 ──────────────────────────────────────────────────────
_QUOTES_GREET_TPL = [
    "哇，主人回来了！今天也要一起仿真吗？",
    "主人！快给我讲讲今天遇到了什么奇奇怪怪的边界条件！",
    "我等了好久了！有新项目吗？",
    "（{name}从代码堆里探出头来）主人早！",
    "叮！今日仿真能量已就绪，请放心使用本精灵！",
    "气隙磁场已就位，等你来仿真！",
]
_QUOTES_GREET_FOX = [
    "主人！！回来啦！！氟氟等你好久了！！",
    "哇哇哇主人！今天 CFD 又有新发现吗？！快跟我说！！",
    "（{name} 从流体域里蹦出来）主人来啦！！",
    "嘿嘿！今天的网格剖好了吗？！氟氟来帮你数！",
    "湍流平静下来了！主人，今天运气很好！",
]
_QUOTES_GREET_DOG = [
    "……主人回来了。（摇尾）",
    "（{name} 缓缓抬头）主人早。今天也要仿真吗。",
    "刚把节点都排好了。等你来。",
    "应力已就位。等你布置载荷。",
    "（靠近主人）……在呢。",
]

# 升段专属台词（各宠物）
_STAGE_UP_QUOTES_CAT = {
    "child":  "我长大了！以后叫我麦克斯韦学徒！⚡",
    "adult":  "哇，我进化了！电磁场都臣服于我！🧲",
    "expert": "我成为了永磁体守护神！谁敢说退磁？！✨",
    "legend": "传说中的 PMSM 仿真宗师……就是我！！╔═∞═╗",
}
_STAGE_UP_QUOTES_FOX = {
    "child":  "哇哇哇！氟氟长大啦！雷诺数已驯服！💧",
    "adult":  "进化！！湍流在我面前乖乖低头！！🌊",
    "expert": "我是网格诗人！！每一个单元都是艺术！✨",
    "legend": "CFD 天神降临……流体宇宙向我俯首！╔═∇═╗",
}
_STAGE_UP_QUOTES_DOG = {
    "child":  "……长大了。应力不会再难到我。",
    "adult":  "模态分析……全部通过。进化了。",
    "expert": "NVH 噪声……降下来了。我做到了。",
    "legend": "……结构力学祖师。嗯。（淡定摇尾）",
}

# 全宠物升段台词索引
_ALL_STAGE_UP_QUOTES: dict[str, dict[str, str]] = {
    "maxwell_cat": _STAGE_UP_QUOTES_CAT,
    "fluent_fox":  _STAGE_UP_QUOTES_FOX,
    "mapdl_dog":   _STAGE_UP_QUOTES_DOG,
}

# 兼容旧接口
_STAGE_UP_QUOTES = _STAGE_UP_QUOTES_CAT

# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

class PetState:
    """宠物状态，负责持久化读写。"""

    DEFAULT_NAME = "安安"

    def __init__(self) -> None:
        self.pet_type: str = "maxwell_cat"
        self.name: str = self.DEFAULT_NAME
        self.hunger: int = 100
        self.mood: int = 100
        self.stamina: int = 100
        self.sim_count: int = 0
        self.interact_count: int = 0
        self.birth_date: str = date.today().isoformat()
        self.last_feed: str = ""
        self.last_pat: str = ""
        self.last_interact_date: str = ""
        self.streak_days: int = 0
        self.play_count_today: int = 0
        self.last_play_date: str = ""
        self.skills: list[str] = []
        self.is_secret: bool = False
        self.is_secret_fox: bool = False
        self.is_secret_dog: bool = False
        self._path = _pet_save_path()
        self._load()

    # ------------------------------------------------------------------
    # 持久化
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                self.pet_type           = data.get("pet_type", "maxwell_cat")
                self.name               = data.get("name", self.DEFAULT_NAME)
                self.hunger             = int(data.get("hunger", 100))
                self.mood               = int(data.get("mood", 100))
                self.stamina            = int(data.get("stamina", 100))
                self.sim_count          = int(data.get("sim_count", 0))
                self.interact_count     = int(data.get("interact_count", 0))
                self.birth_date         = data.get("birth_date", date.today().isoformat())
                self.last_feed          = data.get("last_feed", "")
                self.last_pat           = data.get("last_pat", "")
                self.last_interact_date = data.get("last_interact_date", "")
                self.streak_days        = int(data.get("streak_days", 0))
                self.play_count_today   = int(data.get("play_count_today", 0))
                self.last_play_date     = data.get("last_play_date", "")
                self.skills             = data.get("skills", [])
                self.is_secret          = bool(data.get("is_secret", False))
                self.is_secret_fox      = bool(data.get("is_secret_fox", False))
                self.is_secret_dog      = bool(data.get("is_secret_dog", False))
                self._apply_time_decay(data.get("last_save", ""))
                self._reset_play_count_if_new_day()
            except Exception:
                pass

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "pet_type":           self.pet_type,
                "name":               self.name,
                "hunger":             self.hunger,
                "mood":               self.mood,
                "stamina":            self.stamina,
                "sim_count":          self.sim_count,
                "interact_count":     self.interact_count,
                "birth_date":         self.birth_date,
                "last_feed":          self.last_feed,
                "last_pat":           self.last_pat,
                "last_interact_date": self.last_interact_date,
                "streak_days":        self.streak_days,
                "play_count_today":   self.play_count_today,
                "last_play_date":     self.last_play_date,
                "skills":             self.skills,
                "is_secret":          self.is_secret,
                "is_secret_fox":      self.is_secret_fox,
                "is_secret_dog":      self.is_secret_dog,
                "last_save":          datetime.now().isoformat(),
            }
            self._path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def _apply_time_decay(self, last_save_str: str) -> None:
        """根据上次保存时间流逝，扣减饥饿/心情/精力（每小时 -3/-2/-1）。"""
        if not last_save_str:
            return
        try:
            last = datetime.fromisoformat(last_save_str)
            hours = min((datetime.now() - last).total_seconds() / 3600, 48)
            self.hunger  = max(0, self.hunger  - int(hours * 3))
            self.mood    = max(0, self.mood    - int(hours * 2))
            self.stamina = max(0, self.stamina - int(hours * 1))
        except Exception:
            pass

    def _reset_play_count_if_new_day(self) -> None:
        """如果已跨天，重置当天游戏次数。"""
        today = date.today().isoformat()
        if self.last_play_date != today:
            self.play_count_today = 0

    def _update_streak(self) -> None:
        """更新连续互动天数。"""
        today = date.today().isoformat()
        if not self.last_interact_date:
            self.streak_days = 1
        else:
            try:
                last = date.fromisoformat(self.last_interact_date)
                delta = (date.today() - last).days
                if delta == 0:
                    pass
                elif delta == 1:
                    self.streak_days += 1
                else:
                    self.streak_days = 1
            except Exception:
                self.streak_days = 1
        self.last_interact_date = today

    # ------------------------------------------------------------------
    # 状态计算
    # ------------------------------------------------------------------

    @property
    def pet_color(self) -> str:
        return PET_TYPES.get(self.pet_type, PET_TYPES["maxwell_cat"])["color"]

    @property
    def pet_emoji(self) -> str:
        return PET_TYPES.get(self.pet_type, PET_TYPES["maxwell_cat"])["emoji"]

    @property
    def mood_cap(self) -> int:
        """连续互动3天以上时心情上限提升到120。"""
        return 120 if self.streak_days >= 3 else 100

    @property
    def stage_key(self) -> str:
        key = "baby"
        for min_sim, skey, *_ in _STAGES:
            if self.sim_count >= min_sim:
                key = skey
        return key

    @property
    def stage(self) -> tuple[str, str]:
        """返回 (阶段名, 当前宠物对应称号)。"""
        idx_map = {"maxwell_cat": 3, "fluent_fox": 4, "mapdl_dog": 5}
        title_idx = idx_map.get(self.pet_type, 3)
        sname = _STAGES[0][2]
        stitle = _STAGES[0][title_idx]
        for row in _STAGES:
            if self.sim_count >= row[0]:
                sname  = row[2]
                stitle = row[title_idx]
        return sname, stitle

    @property
    def mood_key(self) -> str:
        if self.hunger < 20:
            return "hungry"
        if self.mood < 20:
            return "sad"
        if self.mood >= 90 and self.hunger >= 80:
            return "excited"
        if self.mood >= 60 and self.hunger >= 50:
            return "happy"
        return "normal"

    @property
    def stamina_label(self) -> str:
        if self.stamina >= 80: return "精力充沛 ⚡"
        if self.stamina >= 50: return "状态良好"
        if self.stamina >= 20: return "有点疲惫"
        return "精疲力竭！"

    @property
    def sprite(self) -> str:
        """返回当前形象对应的 ASCII 字符串（去掉首尾空行）。"""
        mk = self.mood_key
        if self.pet_type == "maxwell_cat":
            if self.is_secret:
                art = _SECRET_SPRITES.get(mk, _SECRET_SPRITES["normal"])
            else:
                stage_sprites = _SPRITES.get(self.stage_key, _SPRITES["baby"])
                art = stage_sprites.get(mk, stage_sprites["normal"])
        elif self.pet_type == "fluent_fox":
            if self.is_secret_fox:
                art = _SECRET_SPRITES_FOX.get(mk, _SECRET_SPRITES_FOX["normal"])
            else:
                stage_sprites = _SPRITES_FOX.get(self.stage_key, _SPRITES_FOX["baby"])
                art = stage_sprites.get(mk, stage_sprites["normal"])
        elif self.pet_type == "mapdl_dog":
            if self.is_secret_dog:
                art = _SECRET_SPRITES_DOG.get(mk, _SECRET_SPRITES_DOG["normal"])
            else:
                stage_sprites = _SPRITES_DOG.get(self.stage_key, _SPRITES_DOG["baby"])
                art = stage_sprites.get(mk, stage_sprites["normal"])
        else:
            stage_sprites = _SPRITES.get(self.stage_key, _SPRITES["baby"])
            art = stage_sprites.get(mk, stage_sprites["normal"])
        return art.strip("\n")

    @property
    def mood_label(self) -> str:
        if self.mood >= 110: return "爱意满满 💕"
        if self.mood >= 80:  return "超开心 ✨"
        if self.mood >= 60:  return "开心"
        if self.mood >= 40:  return "还好"
        if self.mood >= 20:  return "有点低落"
        return "很沮丧 😢"

    @property
    def hunger_label(self) -> str:
        if self.hunger >= 80: return "吃饱了 ✓"
        if self.hunger >= 50: return "有点饿"
        if self.hunger >= 20: return "饿了！"
        return "快饿晕了！！"

    @property
    def age_days(self) -> int:
        try:
            return (date.today() - date.fromisoformat(self.birth_date)).days
        except Exception:
            return 0

    def random_quote(self) -> str:
        if self.pet_type == "maxwell_cat":
            if self.is_secret:
                if self.hunger < 20:   return random.choice(_SECRET_QUOTES_HUNGRY)
                if self.mood < 30:     return random.choice(_SECRET_QUOTES_SAD)
                if self.mood >= 70:    return random.choice(_SECRET_QUOTES_HAPPY)
                return random.choice(_SECRET_QUOTES_NORMAL)
            if self.hunger < 20:   return random.choice(_QUOTES_HUNGRY)
            if self.mood < 30:     return random.choice(_QUOTES_SAD)
            if self.mood >= 70:    return random.choice(_QUOTES_HAPPY)
            return random.choice(_QUOTES_NORMAL)
        elif self.pet_type == "fluent_fox":
            if self.hunger < 20:   return random.choice(_QUOTES_FOX_HUNGRY)
            if self.mood < 30:     return random.choice(_QUOTES_FOX_SAD)
            if self.mood >= 70:    return random.choice(_QUOTES_FOX_HAPPY)
            return random.choice(_QUOTES_FOX_NORMAL)
        else:
            if self.hunger < 20:   return random.choice(_QUOTES_DOG_HUNGRY)
            if self.mood < 30:     return random.choice(_QUOTES_DOG_SAD)
            if self.mood >= 70:    return random.choice(_QUOTES_DOG_HAPPY)
            return random.choice(_QUOTES_DOG_NORMAL)

    # ------------------------------------------------------------------
    # 操作
    # ------------------------------------------------------------------

    def feed(self) -> tuple[str, str]:
        """喂食。返回 (sprite, 消息文本)。"""
        food = random.choice(_FOOD_ITEMS)
        gain = random.randint(20, 35)
        old = self.hunger
        self.hunger = min(100, self.hunger + gain)
        self.mood   = min(self.mood_cap, self.mood + 10)
        self.interact_count += 1
        self.last_feed = datetime.now().isoformat()
        self._update_streak()
        self._save()
        restored = self.hunger - old

        secret_event = self._check_fox_secret_unlock()

        if self.pet_type == "fluent_fox":
            reaction = f"「哇哇哇！{self.name} 一口吞下了 {food}！回复了 {restored} 点饱食度！！」"
        elif self.pet_type == "mapdl_dog":
            reaction = f"「……{self.name} 默默吃完了 {food}。回复了 {restored} 点饱食度。」"
        else:
            reaction = f"「{self.name} 收下了 {food}，回复了 {restored} 点饱食度！」"

        streak_tip = f"\n  🔥 连续互动 {self.streak_days} 天！{'（心情上限已提升！）' if self.streak_days >= 3 else ''}" if self.streak_days > 1 else ""
        msg = (
            f"{reaction}\n\n"
            f"  🍜 饱食度  {self._bar(self.hunger)}  {self.hunger}/100  {self.hunger_label}\n"
            f"  💛 心情值  {self._bar(self.mood)}  {self.mood}/{self.mood_cap}  {self.mood_label}"
            f"{streak_tip}"
        )
        if secret_event:
            msg += f"\n\n  ✨ {secret_event}"
        return self.sprite, msg

    def pat(self) -> tuple[str, str]:
        """抚摸。返回 (sprite, 消息文本)。"""
        gain = random.randint(10, 20)
        self.mood = min(self.mood_cap, self.mood + gain)
        self.interact_count += 1
        self.last_pat = datetime.now().isoformat()
        self._update_streak()

        secret_event = self._check_dog_secret_unlock()

        if self.pet_type == "fluent_fox":
            tpl = random.choice(_QUOTES_FOX_PAT)
            reaction = f"「{tpl.format(gain=gain)}」"
        elif self.pet_type == "mapdl_dog":
            tpl = random.choice(_QUOTES_DOG_PAT)
            reaction = f"「{tpl.format(gain=gain)}」"
        else:
            tpl = random.choice(_QUOTES_PAT_CAT)
            reaction = f"「{tpl.format(gain=gain)}」"

        self._save()
        streak_tip = f"\n  🔥 连续互动 {self.streak_days} 天！{'（心情上限已提升！）' if self.streak_days >= 3 else ''}" if self.streak_days > 1 else ""
        msg = (
            f"{reaction}\n\n"
            f"  💛 心情值  {self._bar(self.mood)}  {self.mood}/{self.mood_cap}  {self.mood_label}\n"
            f"  🍜 饱食度  {self._bar(self.hunger)}  {self.hunger}/100  {self.hunger_label}"
            f"{streak_tip}"
        )
        if secret_event:
            msg += f"\n\n  ✨ {secret_event}"
        return self.sprite, msg

    def rest(self) -> tuple[str, str]:
        """休息。精力 +40，心情 -5，宠物会抱怨。"""
        stamina_gain = min(100 - self.stamina, 40)
        self.stamina = min(100, self.stamina + 40)
        self.mood    = max(0, self.mood - 5)
        self.interact_count += 1
        self._save()
        if self.pet_type == "fluent_fox":
            reactions = [
                f"「呼……睡了一觉，精力 +{stamina_gain}！但是少陪了主人……心情 -5」",
                f"「（打了个大哈欠）好困哦……睡一下下！精力 +{stamina_gain}！」",
            ]
        elif self.pet_type == "mapdl_dog":
            reactions = [
                f"「……休息了。精力 +{stamina_gain}。」",
                f"「刚度矩阵充能中……精力 +{stamina_gain}。」",
            ]
        else:
            reactions = [
                f"「才不是困了！只是眯一会儿……精力 +{stamina_gain}，心情 -5」",
                f"「（蜷缩成一团）不许打扰……精力 +{stamina_gain}！」",
            ]
        msg = (
            f"{random.choice(reactions)}\n\n"
            f"  ⚡ 精力值  {self._bar(self.stamina)}  {self.stamina}/100  {self.stamina_label}\n"
            f"  💛 心情值  {self._bar(self.mood)}  {self.mood}/{self.mood_cap}  {self.mood_label}"
        )
        return self.sprite, msg

    def play(self) -> tuple[str, str, int]:
        """
        和宠物玩猜数字游戏。
        返回 (sprite, 提示消息, 目标数字)。
        每天最多3次。
        """
        self._reset_play_count_if_new_day()
        today = date.today().isoformat()
        if self.play_count_today >= 3:
            if self.pet_type == "fluent_fox":
                msg = f"「今天已经玩了 3 次了！！明天再来！！(>▽<)」"
            elif self.pet_type == "mapdl_dog":
                msg = f"「……今天玩够了。明天再来。」"
            else:
                msg = f"「哼，今天已经玩了 3 次了，不许再玩了！明天再说！」"
            return self.sprite, msg, -1

        target = random.randint(1, 10)
        self.play_count_today += 1
        self.last_play_date = today
        self._save()

        if self.pet_type == "fluent_fox":
            prompt = f"「来来来！！猜数字游戏！！我想了 1~10 的一个数，猜猜是几？！（今天还能玩 {3 - self.play_count_today} 次）」"
        elif self.pet_type == "mapdl_dog":
            prompt = f"「……猜数字。1 到 10。（今天还能玩 {3 - self.play_count_today} 次）」"
        else:
            prompt = f"「好吧，本精灵大发慈悲陪你玩！我想了 1~10 的一个数，猜对有奖励～（今天还能玩 {3 - self.play_count_today} 次）」"
        return self.sprite, prompt, target

    def play_result(self, guess: int, target: int) -> tuple[str, str]:
        """处理猜数字结果。返回 (sprite, 结果消息)。"""
        if guess == target:
            mood_gain = 25
            self.mood = min(self.mood_cap, self.mood + mood_gain)
            self.stamina = max(0, self.stamina - 10)
            self._save()
            if self.pet_type == "fluent_fox":
                msg = f"「哇哇哇！！猜对了！！就是 {target}！！心情 +{mood_gain}！！！(≧▽≦)/」"
            elif self.pet_type == "mapdl_dog":
                msg = f"「……猜对了。{target}。心情 +{mood_gain}。（摇尾）」"
            else:
                msg = f"「哇！居然猜对了！就是 {target}！心情 +{mood_gain}！（偷偷开心中）」"
        else:
            mood_gain = 5
            self.mood = min(self.mood_cap, self.mood + mood_gain)
            self.stamina = max(0, self.stamina - 5)
            self._save()
            if self.pet_type == "fluent_fox":
                msg = f"「哎呀猜错了！！是 {target} 啦！但主人参与了，心情还是 +{mood_gain}！」"
            elif self.pet_type == "mapdl_dog":
                msg = f"「……不对。是 {target}。但来玩就好。心情 +{mood_gain}。」"
            else:
                msg = f"「猜错了，是 {target}！不过……陪我玩也不错啦，心情 +{mood_gain}！」"
        msg += f"\n\n  💛 心情值  {self._bar(self.mood)}  {self.mood}/{self.mood_cap}  {self.mood_label}"
        return self.sprite, msg

    def choose_pet(self, type_key: str) -> tuple[bool, str]:
        """切换宠物种类。返回 (成功, 消息)。"""
        resolved = PET_TYPE_ALIASES.get(type_key.strip())
        if resolved is None:
            return False, f"找不到叫「{type_key}」的伙伴！可选：安安（猫）、氟氟（狐）、马普（狗）"
        if resolved == self.pet_type:
            return False, f"你现在陪伴的就是 {self.name} 哦！"
        old_name = self.name
        self.pet_type = resolved
        self.name = PET_TYPES[resolved]["name_default"]
        self._save()
        return True, f"已从 {old_name} 切换到 {self.name}！快用 /pet 看看新伙伴吧～"

    def rename(self, new_name: str) -> tuple[bool, str]:
        """重命名。返回 (成功, 消息)。"""
        new_name = new_name.strip()
        if not new_name:
            return False, "名字不能为空！"
        if len(new_name) > 16:
            return False, "名字太长了（最多 16 个字符）！"
        old = self.name
        self.name = new_name
        self._save()
        return True, f"已将 {old} 改名为 {new_name}！"

    def record_sim(self) -> str | None:
        """累计仿真次数。若升段，返回升段 key，否则返回 None。"""
        old_key = self.stage_key
        self.sim_count += 1
        stamina_cost = 5
        exp_mult = 1.5 if self.stamina >= 80 else (0.5 if self.stamina < 20 else 1.0)
        self.stamina = max(0, self.stamina - stamina_cost)
        self._save()
        new_key = self.stage_key
        new_skill = self._check_skill_unlock(new_key)
        if new_key != old_key:
            return new_key
        return None

    def _check_skill_unlock(self, stage_key: str) -> str | None:
        """检查并解锁当前宠物阶段对应技能，返回新技能名或 None。"""
        skill_map = _PET_SKILLS.get(self.pet_type, {})
        skill = skill_map.get(stage_key)
        if skill and skill not in self.skills:
            self.skills.append(skill)
            self._save()
            return skill
        return None

    def _check_fox_secret_unlock(self) -> str | None:
        """检查氟氟是否满足连续5天喂食解锁条件。"""
        if self.pet_type != "fluent_fox" or self.is_secret_fox:
            return None
        if self.streak_days >= 5:
            self.is_secret_fox = True
            self.hunger = 100
            self.mood = self.mood_cap
            self._save()
            return "氟氟触发了隐藏进化！热力学混沌形态解锁！🌀"
        return None

    def _check_dog_secret_unlock(self) -> str | None:
        """检查马普是否满足200次仿真后摸摸解锁条件。"""
        if self.pet_type != "mapdl_dog" or self.is_secret_dog:
            return None
        if self.sim_count >= 200:
            self.is_secret_dog = True
            self.hunger = 100
            self.mood = self.mood_cap
            self._save()
            return "马普触发了隐藏进化！有限元之神形态解锁！🔱"
        return None

    def unlock_secret(self) -> bool:
        """解锁安安隐藏形象「量子 Maxwell」。已解锁时返回 False，否则返回 True。"""
        if self.is_secret:
            return False
        self.is_secret = True
        self.hunger = 100
        self.mood   = 100
        self._save()
        return True

    # ------------------------------------------------------------------
    # 状态面板内容
    # ------------------------------------------------------------------

    def build_panel_content(self) -> str:
        """返回用于 Rich Panel 的完整面板内容（含 ASCII 形象 + 属性栏）。"""
        sprite_block = "\n".join("  " + l for l in self.sprite.splitlines())
        hunger_color  = "green"  if self.hunger  >= 50 else "red"
        mood_color    = "cyan"   if self.mood    >= 50 else "yellow"
        stamina_color = "green"  if self.stamina >= 50 else "red"
        streak_line   = f"  🔥 连续互动 {self.streak_days} 天{'（心情上限 +20！）' if self.streak_days >= 3 else ''}\n" if self.streak_days >= 2 else ""
        skills_line   = f"  🏅 已解锁技能  {' · '.join(self.skills)}\n" if self.skills else ""

        is_any_secret = (
            (self.pet_type == "maxwell_cat" and self.is_secret) or
            (self.pet_type == "fluent_fox"  and self.is_secret_fox) or
            (self.pet_type == "mapdl_dog"   and self.is_secret_dog)
        )

        if is_any_secret:
            if self.pet_type == "maxwell_cat":
                secret_label = "[bold bright_cyan]量子 Maxwell 形态[/bold bright_cyan]"
                secret_eq    = "[dim]∇ × E = -∂B/∂t   ∇ × H = J + ∂D/∂t[/dim]"
                quote_color  = "bright_cyan"
            elif self.pet_type == "fluent_fox":
                secret_label = "[bold bright_blue]热力学混沌形态[/bold bright_blue]"
                secret_eq    = "[dim]∂ρ/∂t + ∇·(ρv) = 0   ∇p = μ∇²v[/dim]"
                quote_color  = "bright_blue"
            else:
                secret_label = "[bold bright_yellow]有限元之神形态[/bold bright_yellow]"
                secret_eq    = "[dim][K]{{u}} = {{F}}   ε = ∇ˢu[/dim]"
                quote_color  = "bright_yellow"
            return (
                f"{sprite_block}\n"
                f"\n"
                f"  [bold]{self.name}[/bold]  ·  {secret_label}\n"
                f"  ✦  隐藏形象  {secret_eq}\n"
                f"\n"
                f"  🍜 饱食度   [{hunger_color}]{self._bar(self.hunger)}[/{hunger_color}]"
                f"  {self.hunger}/100  {self.hunger_label}\n"
                f"  💛 心情值   [{mood_color}]{self._bar(self.mood)}[/{mood_color}]"
                f"  {self.mood}/{self.mood_cap}  {self.mood_label}\n"
                f"  ⚡ 精力值   [{stamina_color}]{self._bar(self.stamina)}[/{stamina_color}]"
                f"  {self.stamina}/100  {self.stamina_label}\n"
                f"\n"
                f"  📅 年龄     {self.age_days} 天   🤝 互动 {self.interact_count} 次"
                f"   ⚙ 仿真 {self.sim_count} 次\n"
                f"{streak_line}{skills_line}"
                f"\n"
                f"  💬 [italic {quote_color}]{self.random_quote()}[/italic {quote_color}]"
            )

        stage_name, title = self.stage
        next_stage_info = ""
        for row in _STAGES:
            if self.sim_count < row[0]:
                need = row[0] - self.sim_count
                next_stage_info = f"\n  🎯 下一阶段  {row[2]}（还需 {need} 次仿真）"
                break

        return (
            f"{sprite_block}\n"
            f"\n"
            f"  [bold]{self.name}[/bold]  ·  [{self.pet_color}]{title}[/{self.pet_color}]\n"
            f"  🌱 成长阶段  {stage_name}（仿真 {self.sim_count} 次）{next_stage_info}\n"
            f"\n"
            f"  🍜 饱食度   [{hunger_color}]{self._bar(self.hunger)}[/{hunger_color}]"
            f"  {self.hunger}/100  {self.hunger_label}\n"
            f"  💛 心情值   [{mood_color}]{self._bar(self.mood)}[/{mood_color}]"
            f"  {self.mood}/{self.mood_cap}  {self.mood_label}\n"
            f"  ⚡ 精力值   [{stamina_color}]{self._bar(self.stamina)}[/{stamina_color}]"
            f"  {self.stamina}/100  {self.stamina_label}\n"
            f"\n"
            f"  📅 年龄     {self.age_days} 天   🤝 互动 {self.interact_count} 次\n"
            f"{streak_line}{skills_line}"
            f"\n"
            f"  💬 [italic yellow]{self.random_quote()}[/italic yellow]"
        )

    def build_action_panel(self, sprite: str, msg: str) -> str:
        """喂食/摸摸后的面板内容（形象 + 反馈消息）。"""
        sprite_block = "\n".join("  " + l for l in sprite.splitlines())
        return f"{sprite_block}\n\n{msg}"

    @staticmethod
    def _bar(value: int, width: int = 10) -> str:
        filled = round(value / 100 * width)
        return "█" * filled + "░" * (width - filled)


# ---------------------------------------------------------------------------
# 单例
# ---------------------------------------------------------------------------

_pet_instance: PetState | None = None


def get_pet() -> PetState:
    global _pet_instance
    if _pet_instance is None:
        _pet_instance = PetState()
    return _pet_instance


# ---------------------------------------------------------------------------
# 升段台词
# ---------------------------------------------------------------------------

def stage_up_quote(stage_key: str, pet_type: str = "maxwell_cat") -> str:
    quotes = _ALL_STAGE_UP_QUOTES.get(pet_type, _STAGE_UP_QUOTES_CAT)
    return quotes.get(stage_key, "我变强了！！")


def secret_unlock_animation() -> list[str]:
    """返回安安解锁动画的逐行文本列表，供 main.py 逐行打印。"""
    return list(_SECRET_UNLOCK_ANIMATION)


def secret_fox_unlock_animation() -> list[str]:
    """返回氟氟隐藏形象解锁动画列表。"""
    return list(_SECRET_FOX_UNLOCK_ANIMATION)


def secret_dog_unlock_animation() -> list[str]:
    """返回马普隐藏形象解锁动画列表。"""
    return list(_SECRET_DOG_UNLOCK_ANIMATION)


# ---------------------------------------------------------------------------
# 启动问候
# ---------------------------------------------------------------------------

def maybe_greet_on_startup(console: "Console") -> None:
    """约 15% 概率在启动时让宠物出来打招呼。"""
    if random.random() > 0.15:
        return
    pet = get_pet()
    if pet.hunger < 10:
        return
    from rich.panel import Panel
    if pet.pet_type == "fluent_fox":
        greet_pool = _QUOTES_GREET_FOX
    elif pet.pet_type == "mapdl_dog":
        greet_pool = _QUOTES_GREET_DOG
    else:
        greet_pool = _QUOTES_GREET_TPL
    tpl = random.choice(greet_pool)
    greeting = tpl.format(name=pet.name)
    content = (
        f"  {pet.sprite.splitlines()[0]}\n\n"
        f"  [bold]{pet.name}[/bold] 说：[italic yellow]{greeting}[/italic yellow]"
    )
    console.print(Panel(
        content,
        title=f"{pet.pet_emoji} {pet.name} 的问候",
        border_style=f"dim {pet.pet_color}",
        expand=False,
    ))
