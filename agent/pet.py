"""
AnsysAgent 宠物系统 —— 彩蛋模块

一只住在终端里的仿真小精灵，陪你度过漫长的仿真时光。

功能：
  - 多套 ASCII 可视形象（按成长阶段 × 心情状态变化）
  - 隐藏形象「量子 Maxwell」（通过 /bugpet 解锁，不在补全提示中显示）
  - 状态持久化（心情、饥饿、互动次数、仿真次数、诞生日期、名字）
  - 随仿真次数成长（幼崽 → 少年 → 成年 → 专家 → 传奇）
  - 喂食、抚摸、重命名、查看状态
  - 每次启动有概率出来打招呼
"""

from __future__ import annotations

import json
import random
from datetime import date, datetime
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
# 成长阶段
# ---------------------------------------------------------------------------

# (最低仿真次数, 阶段key, 阶段名, 称号)
_STAGES = [
    (0,   "baby",   "幼崽期",   "仿真见习生"),
    (10,  "child",  "少年期",   "麦克斯韦学徒"),
    (50,  "adult",  "成年期",   "电磁场驯服者"),
    (150, "expert", "专家期",   "永磁体守护神"),
    (500, "legend", "传奇期",   "PMSM 仿真宗师"),
]

# ---------------------------------------------------------------------------
# ASCII 形象库
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

_QUOTES_GREET_TPL = [
    "哇，主人回来了！今天也要一起仿真吗？",
    "主人！快给我讲讲今天遇到了什么奇奇怪怪的边界条件！",
    "我等了好久了！有新项目吗？",
    "（{name}从代码堆里探出头来）主人早！",
    "叮！今日仿真能量已就绪，请放心使用本精灵！",
    "气隙磁场已就位，等你来仿真！",
]

# 升段专属台词
_STAGE_UP_QUOTES = {
    "child":  "我长大了！以后叫我麦克斯韦学徒！⚡",
    "adult":  "哇，我进化了！电磁场都臣服于我！🧲",
    "expert": "我成为了永磁体守护神！谁敢说退磁？！✨",
    "legend": "传说中的 PMSM 仿真宗师……就是我！！╔═∞═╗",
}

# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

class PetState:
    """宠物状态，负责持久化读写。"""

    DEFAULT_NAME = "安安"

    def __init__(self) -> None:
        self.name: str = self.DEFAULT_NAME
        self.hunger: int = 100
        self.mood: int = 100
        self.sim_count: int = 0
        self.interact_count: int = 0
        self.birth_date: str = date.today().isoformat()
        self.last_feed: str = ""
        self.last_pat: str = ""
        self.is_secret: bool = False   # 隐藏形象解锁标记
        self._path = _pet_save_path()
        self._load()

    # ------------------------------------------------------------------
    # 持久化
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                self.name           = data.get("name", self.DEFAULT_NAME)
                self.hunger         = int(data.get("hunger", 100))
                self.mood           = int(data.get("mood", 100))
                self.sim_count      = int(data.get("sim_count", 0))
                self.interact_count = int(data.get("interact_count", 0))
                self.birth_date     = data.get("birth_date", date.today().isoformat())
                self.last_feed      = data.get("last_feed", "")
                self.last_pat       = data.get("last_pat", "")
                self.is_secret      = bool(data.get("is_secret", False))
                self._apply_time_decay(data.get("last_save", ""))
            except Exception:
                pass

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "name":           self.name,
                "hunger":         self.hunger,
                "mood":           self.mood,
                "sim_count":      self.sim_count,
                "interact_count": self.interact_count,
                "birth_date":     self.birth_date,
                "last_feed":      self.last_feed,
                "last_pat":       self.last_pat,
                "is_secret":      self.is_secret,
                "last_save":      datetime.now().isoformat(),
            }
            self._path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def _apply_time_decay(self, last_save_str: str) -> None:
        """根据上次保存时间流逝，扣减饥饿/心情（每小时 -3/-2）。"""
        if not last_save_str:
            return
        try:
            last = datetime.fromisoformat(last_save_str)
            hours = min((datetime.now() - last).total_seconds() / 3600, 48)
            self.hunger = max(0, self.hunger - int(hours * 3))
            self.mood   = max(0, self.mood   - int(hours * 2))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 状态计算
    # ------------------------------------------------------------------

    @property
    def stage_key(self) -> str:
        key = "baby"
        for min_sim, skey, *_ in _STAGES:
            if self.sim_count >= min_sim:
                key = skey
        return key

    @property
    def stage(self) -> tuple[str, str]:
        """返回 (阶段名, 称号)。"""
        sname, stitle = _STAGES[0][2], _STAGES[0][3]
        for min_sim, _, name, title in _STAGES:
            if self.sim_count >= min_sim:
                sname, stitle = name, title
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
    def sprite(self) -> str:
        """返回当前形象对应的 ASCII 字符串（去掉首尾空行）。"""
        if self.is_secret:
            art = _SECRET_SPRITES.get(self.mood_key, _SECRET_SPRITES["normal"])
        else:
            stage_sprites = _SPRITES.get(self.stage_key, _SPRITES["baby"])
            art = stage_sprites.get(self.mood_key, stage_sprites["normal"])
        return art.strip("\n")

    @property
    def mood_label(self) -> str:
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
        if self.is_secret:
            if self.hunger < 20:
                return random.choice(_SECRET_QUOTES_HUNGRY)
            if self.mood < 30:
                return random.choice(_SECRET_QUOTES_SAD)
            if self.mood >= 70:
                return random.choice(_SECRET_QUOTES_HAPPY)
            return random.choice(_SECRET_QUOTES_NORMAL)
        if self.hunger < 20:
            return random.choice(_QUOTES_HUNGRY)
        if self.mood < 30:
            return random.choice(_QUOTES_SAD)
        if self.mood >= 70:
            return random.choice(_QUOTES_HAPPY)
        return random.choice(_QUOTES_NORMAL)

    # ------------------------------------------------------------------
    # 操作
    # ------------------------------------------------------------------

    def feed(self) -> tuple[str, str]:
        """喂食。返回 (sprite, 消息文本)。"""
        food = random.choice(_FOOD_ITEMS)
        gain = random.randint(20, 35)
        old = self.hunger
        self.hunger = min(100, self.hunger + gain)
        self.mood   = min(100, self.mood   + 10)
        self.interact_count += 1
        self.last_feed = datetime.now().isoformat()
        self._save()
        restored = self.hunger - old
        msg = (
            f"「{self.name} 收下了 {food}，回复了 {restored} 点饱食度！」\n\n"
            f"  🍜 饱食度  {self._bar(self.hunger)}  {self.hunger}/100  {self.hunger_label}\n"
            f"  💛 心情值  {self._bar(self.mood)}  {self.mood}/100  {self.mood_label}"
        )
        return self.sprite, msg

    def pat(self) -> tuple[str, str]:
        """抚摸。返回 (sprite, 消息文本)。"""
        gain = random.randint(10, 20)
        self.mood = min(100, self.mood + gain)
        self.interact_count += 1
        self.last_pat = datetime.now().isoformat()
        self._save()
        reactions = [
            f"「哇！{self.name} 喜欢被摸头！心情 +{gain}！」(≧∇≦)/",
            f"「嗯嗯嗯！好舒服～心情 +{gain}！」(*≧▽≦)",
            f"「喵～（{self.name} 蹭了蹭你的手）心情 +{gain}！」",
            f"「主人对 {self.name} 好好哦！心情 +{gain}！」",
        ]
        msg = (
            f"{random.choice(reactions)}\n\n"
            f"  💛 心情值  {self._bar(self.mood)}  {self.mood}/100  {self.mood_label}\n"
            f"  🍜 饱食度  {self._bar(self.hunger)}  {self.hunger}/100  {self.hunger_label}"
        )
        return self.sprite, msg

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
        self._save()
        new_key = self.stage_key
        return new_key if new_key != old_key else None

    def unlock_secret(self) -> bool:
        """解锁隐藏形象「量子 Maxwell」。已解锁时返回 False，否则返回 True。"""
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
        hunger_color = "green" if self.hunger >= 50 else "red"
        mood_color   = "cyan"  if self.mood   >= 50 else "yellow"

        if self.is_secret:
            return (
                f"{sprite_block}\n"
                f"\n"
                f"  [bold]{self.name}[/bold]  ·  [bold bright_cyan]量子 Maxwell 形态[/bold bright_cyan]\n"
                f"  ⚛  隐藏形象  [dim]∇ × E = -∂B/∂t   ∇ × H = J + ∂D/∂t[/dim]\n"
                f"\n"
                f"  🍜 饱食度   [{hunger_color}]{self._bar(self.hunger)}[/{hunger_color}]"
                f"  {self.hunger}/100  {self.hunger_label}\n"
                f"  💛 心情值   [{mood_color}]{self._bar(self.mood)}[/{mood_color}]"
                f"  {self.mood}/100  {self.mood_label}\n"
                f"\n"
                f"  📅 年龄     {self.age_days} 天   🤝 互动 {self.interact_count} 次"
                f"   ⚡ 仿真 {self.sim_count} 次\n"
                f"\n"
                f"  💬 [italic bright_cyan]{self.random_quote()}[/italic bright_cyan]"
            )

        stage_name, title = self.stage
        next_stage_info = ""
        for min_sim, _, sname, _ in _STAGES:
            if self.sim_count < min_sim:
                need = min_sim - self.sim_count
                next_stage_info = f"\n  🎯 下一阶段  {sname}（还需 {need} 次仿真）"
                break

        return (
            f"{sprite_block}\n"
            f"\n"
            f"  [bold]{self.name}[/bold]  ·  [cyan]{title}[/cyan]\n"
            f"  🌱 成长阶段  {stage_name}（仿真 {self.sim_count} 次）{next_stage_info}\n"
            f"\n"
            f"  🍜 饱食度   [{hunger_color}]{self._bar(self.hunger)}[/{hunger_color}]"
            f"  {self.hunger}/100  {self.hunger_label}\n"
            f"  💛 心情值   [{mood_color}]{self._bar(self.mood)}[/{mood_color}]"
            f"  {self.mood}/100  {self.mood_label}\n"
            f"\n"
            f"  📅 年龄     {self.age_days} 天   🤝 互动 {self.interact_count} 次\n"
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

def stage_up_quote(stage_key: str) -> str:
    return _STAGE_UP_QUOTES.get(stage_key, "我变强了！！")


def secret_unlock_animation() -> list[str]:
    """返回解锁动画的逐行文本列表，供 main.py 逐行打印。"""
    return list(_SECRET_UNLOCK_ANIMATION)


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
    tpl = random.choice(_QUOTES_GREET_TPL)
    greeting = tpl.format(name=pet.name)
    content = (
        f"  {pet.sprite.splitlines()[0]}\n\n"  # 只取第一行做迷你预览
        f"  [bold]{pet.name}[/bold] 说：[italic yellow]{greeting}[/italic yellow]"
    )
    console.print(Panel(
        content,
        title=f"🐾 {pet.name} 的问候",
        border_style="dim magenta",
        expand=False,
    ))
