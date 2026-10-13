#!/usr/bin/env python3
"""
AIKO eyes_v3.py — система емоцій
Специфікація: AIKO Emotion Specification
Canvas: 480x320, pygame + SDL2
Дисплей: luma.lcd (ILI9488) або fallback pygame-вікно
Переходи між емоціями — МИТТЄВІ (без lerp/interpolation)
Центри очей і рота НІКОЛИ не змінюються по Y
"""

import os
import sys
import math
import time
import random

import pygame
import numpy as np
from PIL import Image, ImageFilter

# ── luma.lcd ──────────────────────────────────────────────────────────────────
try:
    from luma.lcd.device import ili9488
    from luma.core.interface.serial import spi as luma_spi
    LUMA_AVAILABLE = True
except ImportError:
    LUMA_AVAILABLE = False

# ─────────────────────────────────────────────
# КОНСТАНТИ
# ─────────────────────────────────────────────
WIDTH, HEIGHT = 480, 320
FPS = 30
BG_COLOR       = (0, 0, 0)
BG_COLOR_ANGRY = (58, 0, 0)   # #3A0000 статичний

# Геометрія очей — Y НІКОЛИ НЕ ЗМІНЮЄТЬСЯ
EYE_LEFT_CENTER  = (155, 160)
EYE_RIGHT_CENTER = (325, 160)
EYE_W, EYE_H     = 130, 120
EYE_RADIUS       = 35

# Iris / Pupil
IRIS_R_DEFAULT  = 38
PUPIL_R_DEFAULT = 20
HIGHLIGHT_R     = 7
HIGHLIGHT_OFFSET = (12, -14)

# Кольори
COLOR_SCLERA    = (255, 255, 255)
COLOR_OUTLINE   = (0, 191, 255)      # #00BFFF
COLOR_IRIS      = (0, 191, 255)
COLOR_PUPIL     = (0, 0, 0)
COLOR_HIGHLIGHT = (255, 255, 255)
COLOR_ANGRY     = (255, 34, 0)       # #FF2200
COLOR_LOVE      = (255, 79, 163)     # #FF4FA3
COLOR_TEAR      = (127, 223, 255)    # #7FDFFF
COLOR_ZZZ       = (0, 191, 255)
COLOR_FORMULA   = (0, 191, 255)

# Рот
MOUTH_CENTER = (240, 245)

# ─────────────────────────────────────────────
# ПАРАМЕТРИ ЕМОЦІЙ (миттєві, без lerp)
# top_lid / bot_lid  — частка висоти ока (0.0–1.0)
# lid_tilt_l/r       — кут нахилу повіки в градусах
# pupil_offset_l/r   — (x, y) пікселів від центру
# eye_scale_l/r      — масштаб від центру ока
# outline_color      — (R, G, B)
# outline_alpha      — 0.0–1.0
# mouth_type         — 'smile'|'frown'|'line'|'open'|'zigzag'|'wavy'|'sleep_oval'
# mouth_width, mouth_curve, mouth_open
# iris_r, pupil_r
# bg_color           — колір фону
# sclera_color       — колір білка
# ─────────────────────────────────────────────
EMOTION_PARAMS = {
    "neutral": {
        "top_lid_l": 0.0,  "bot_lid_l": 0.0,
        "top_lid_r": 0.0,  "bot_lid_r": 0.0,
        "lid_tilt_l": 0.0, "lid_tilt_r": 0.0,
        "pupil_offset_l": (0, 0), "pupil_offset_r": (0, 0),
        "eye_scale_l": 1.0, "eye_scale_r": 1.0,
        "outline_color": COLOR_OUTLINE,
        "outline_alpha": 1.0,
        "iris_r": IRIS_R_DEFAULT, "pupil_r": PUPIL_R_DEFAULT,
        "mouth_type": "smile",
        "mouth_width": 50, "mouth_curve": 4, "mouth_open": 0.0,
        "bg_color": BG_COLOR,
        "sclera_color": COLOR_SCLERA,
        "heart_eyes": False,
    },
    "happy": {
        "top_lid_l": 0.0,  "bot_lid_l": 0.10,
        "top_lid_r": 0.0,  "bot_lid_r": 0.10,
        "lid_tilt_l": 0.0, "lid_tilt_r": 0.0,
        "pupil_offset_l": (0, 0), "pupil_offset_r": (0, 0),
        "eye_scale_l": 1.0, "eye_scale_r": 1.0,
        "outline_color": COLOR_OUTLINE,
        "outline_alpha": 1.0,
        "iris_r": IRIS_R_DEFAULT, "pupil_r": PUPIL_R_DEFAULT,
        "mouth_type": "smile",
        "mouth_width": 70, "mouth_curve": 18, "mouth_open": 0.0,
        "bg_color": BG_COLOR,
        "sclera_color": COLOR_SCLERA,
        "heart_eyes": False,
    },
    "surprised": {
        "top_lid_l": 0.0,  "bot_lid_l": 0.0,
        "top_lid_r": 0.0,  "bot_lid_r": 0.0,
        "lid_tilt_l": 0.0, "lid_tilt_r": 0.0,
        "pupil_offset_l": (0, 0), "pupil_offset_r": (0, 0),
        "eye_scale_l": 1.12, "eye_scale_r": 1.12,
        "outline_color": COLOR_OUTLINE,
        "outline_alpha": 1.0,
        "iris_r": 30, "pupil_r": 14,
        "mouth_type": "open",
        "mouth_width": 22, "mouth_curve": 0, "mouth_open": 1.0,
        "bg_color": BG_COLOR,
        "sclera_color": COLOR_SCLERA,
        "heart_eyes": False,
    },
    "sad": {
        "top_lid_l": 0.35, "bot_lid_l": 0.0,
        "top_lid_r": 0.35, "bot_lid_r": 0.0,
        # outer corner lower → від'ємний кут
        "lid_tilt_l": -10.0, "lid_tilt_r": -10.0,
        "pupil_offset_l": (0, 12), "pupil_offset_r": (0, 12),
        "eye_scale_l": 1.0, "eye_scale_r": 1.0,
        "outline_color": COLOR_OUTLINE,
        "outline_alpha": 0.7,
        "iris_r": IRIS_R_DEFAULT, "pupil_r": PUPIL_R_DEFAULT,
        "mouth_type": "frown",
        "mouth_width": 50, "mouth_curve": -12, "mouth_open": 0.0,
        "bg_color": BG_COLOR,
        "sclera_color": COLOR_SCLERA,
        "heart_eyes": False,
    },
    "angry": {
        "top_lid_l": 0.40, "bot_lid_l": 0.0,
        "top_lid_r": 0.40, "bot_lid_r": 0.0,
        # inner corner lower → додатній кут
        "lid_tilt_l": 20.0, "lid_tilt_r": 20.0,
        "pupil_offset_l": (6, 0),  "pupil_offset_r": (-6, 0),
        "eye_scale_l": 1.0, "eye_scale_r": 1.0,
        "outline_color": COLOR_ANGRY,
        "outline_alpha": 1.0,
        "iris_r": IRIS_R_DEFAULT, "pupil_r": PUPIL_R_DEFAULT,
        "mouth_type": "zigzag",
        "mouth_width": 60, "mouth_curve": 0, "mouth_open": 0.0,
        "bg_color": BG_COLOR_ANGRY,
        "sclera_color": (255, 232, 228),   # #FFE8E4 злегка рожевий
        "heart_eyes": False,
    },
    "thinking": {
        "top_lid_l": 0.0,  "bot_lid_l": 0.0,
        "top_lid_r": 0.0,  "bot_lid_r": 0.30,
        "lid_tilt_l": 0.0, "lid_tilt_r": 0.0,
        "pupil_offset_l": (14, -14), "pupil_offset_r": (14, -14),
        "eye_scale_l": 1.0, "eye_scale_r": 1.0,
        "outline_color": COLOR_OUTLINE,
        "outline_alpha": 1.0,
        "iris_r": IRIS_R_DEFAULT, "pupil_r": PUPIL_R_DEFAULT,
        "mouth_type": "line",
        "mouth_width": 35, "mouth_curve": 0, "mouth_open": 0.0,
        "bg_color": BG_COLOR,
        "sclera_color": COLOR_SCLERA,
        "heart_eyes": False,
    },
    "love": {
        "top_lid_l": 0.0,  "bot_lid_l": 0.10,
        "top_lid_r": 0.0,  "bot_lid_r": 0.10,
        "lid_tilt_l": 0.0, "lid_tilt_r": 0.0,
        "pupil_offset_l": (0, 0), "pupil_offset_r": (0, 0),
        "eye_scale_l": 1.0, "eye_scale_r": 1.0,
        "outline_color": COLOR_LOVE,
        "outline_alpha": 1.0,
        "iris_r": IRIS_R_DEFAULT, "pupil_r": PUPIL_R_DEFAULT,
        "mouth_type": "smile",
        "mouth_width": 60, "mouth_curve": 14, "mouth_open": 0.0,
        "bg_color": BG_COLOR,
        "sclera_color": COLOR_SCLERA,
        "heart_eyes": True,
    },
    "confused": {
        "top_lid_l": 0.0,  "bot_lid_l": 0.0,
        "top_lid_r": 0.25, "bot_lid_r": 0.0,
        "lid_tilt_l": 0.0, "lid_tilt_r": 8.0,
        "pupil_offset_l": (-10, -8), "pupil_offset_r": (8, 6),
        "eye_scale_l": 1.08, "eye_scale_r": 1.0,
        "outline_color": COLOR_OUTLINE,
        "outline_alpha": 1.0,
        "iris_r": IRIS_R_DEFAULT, "pupil_r": PUPIL_R_DEFAULT,
        "mouth_type": "wavy",
        "mouth_width": 55, "mouth_curve": 0, "mouth_open": 0.0,
        "bg_color": BG_COLOR,
        "sclera_color": COLOR_SCLERA,
        "heart_eyes": False,
    },
    "sleep": {
        "top_lid_l": 1.0,  "bot_lid_l": 1.0,
        "top_lid_r": 1.0,  "bot_lid_r": 1.0,
        "lid_tilt_l": 0.0, "lid_tilt_r": 0.0,
        "pupil_offset_l": (0, 0), "pupil_offset_r": (0, 0),
        "eye_scale_l": 1.0, "eye_scale_r": 1.0,
        "outline_color": COLOR_OUTLINE,
        "outline_alpha": 0.4,
        "iris_r": IRIS_R_DEFAULT, "pupil_r": PUPIL_R_DEFAULT,
        "mouth_type": "sleep_oval",
        "mouth_width": 18, "mouth_curve": 0, "mouth_open": 0.35,
        "bg_color": BG_COLOR,
        "sclera_color": COLOR_SCLERA,
        "heart_eyes": False,
    },
    "listening": {
        "top_lid_l": 0.0,  "bot_lid_l": 0.0,
        "top_lid_r": 0.0,  "bot_lid_r": 0.0,
        "lid_tilt_l": 0.0, "lid_tilt_r": 0.0,
        "pupil_offset_l": (0, 0), "pupil_offset_r": (0, 0),
        "eye_scale_l": 1.05, "eye_scale_r": 1.05,
        "outline_color": COLOR_OUTLINE,
        "outline_alpha": 1.0,
        "iris_r": 41, "pupil_r": PUPIL_R_DEFAULT,
        "mouth_type": "smile",
        "mouth_width": 30, "mouth_curve": 2, "mouth_open": 0.0,
        "bg_color": BG_COLOR,
        "sclera_color": COLOR_SCLERA,
        "heart_eyes": False,
    },
    "speaking": {
        "top_lid_l": 0.0,  "bot_lid_l": 0.0,
        "top_lid_r": 0.0,  "bot_lid_r": 0.0,
        "lid_tilt_l": 0.0, "lid_tilt_r": 0.0,
        "pupil_offset_l": (0, 0), "pupil_offset_r": (0, 0),
        "eye_scale_l": 1.0, "eye_scale_r": 1.0,
        "outline_color": COLOR_OUTLINE,
        "outline_alpha": 1.0,
        "iris_r": IRIS_R_DEFAULT, "pupil_r": PUPIL_R_DEFAULT,
        "mouth_type": "open",
        "mouth_width": 45, "mouth_curve": 0, "mouth_open": 0.5,
        "bg_color": BG_COLOR,
        "sclera_color": COLOR_SCLERA,
        "heart_eyes": False,
    },
}

# ─────────────────────────────────────────────
# GLOW CACHE — рендеримо blur один раз при старті
# ─────────────────────────────────────────────
class GlowCache:
    """Кешує розмиті glow-поверхні для різних кольорів і радіусів."""

    def __init__(self):
        self._cache = {}

    def get(self, color, size, blur_radius=12):
        """
        Повертає pygame.Surface з glow-кільцем.
        color: (R, G, B)
        size: (w, h) прямокутника або радіус кола
        """
        key = (color, size, blur_radius)
        if key in self._cache:
            return self._cache[key]

        w, h = size if isinstance(size, tuple) else (size * 2 + blur_radius * 2,
                                                      size * 2 + blur_radius * 2)
        pad = blur_radius * 2
        pil_w, pil_h = w + pad, h + pad

        pil = Image.new("RGBA", (pil_w, pil_h), (0, 0, 0, 0))
        from PIL import ImageDraw
        draw = ImageDraw.Draw(pil)
        draw.rectangle(
            [pad // 2, pad // 2, pil_w - pad // 2, pil_h - pad // 2],
            outline=color + (255,), width=4
        )
        pil = pil.filter(ImageFilter.GaussianBlur(radius=blur_radius))

        raw = np.array(pil)
        surf = pygame.Surface((pil_w, pil_h), pygame.SRCALPHA)
        pygame.surfarray.blit_array(surf, raw.transpose(1, 0, 2))

        self._cache[key] = surf
        return surf


GLOW_CACHE = None   # ініціалізується в main() після pygame.init()

# ─────────────────────────────────────────────
# КЛАС СТАНУ ЕМОЦІЙ (МИТТЄВЕ перемикання)
# ─────────────────────────────────────────────
class EmotionState:
    def __init__(self, start_emotion="neutral"):
        self.current_name   = start_emotion
        self.current_params = dict(EMOTION_PARAMS[start_emotion])

    def set_emotion(self, name):
        if name not in EMOTION_PARAMS:
            print(f"[WARN] Невідома емоція: {name}")
            return
        self.current_name   = name
        self.current_params = dict(EMOTION_PARAMS[name])
        print(f"[EMOTION] → {name}")

    def get(self):
        return self.current_params

# ─────────────────────────────────────────────
# BLINK — overlay-анімація поверх поточної емоції
# ─────────────────────────────────────────────
class BlinkAnimation:
    CLOSE_MS = 80
    HOLD_MS  = 50
    OPEN_MS  = 120
    TOTAL_MS = CLOSE_MS + HOLD_MS + OPEN_MS

    def __init__(self):
        self.active   = False
        self.elapsed  = 0.0
        self.next_blink = random.uniform(3000, 6000)

    def trigger(self):
        if not self.active:
            self.active  = True
            self.elapsed = 0.0

    def update(self, dt_ms, emotion_name):
        # Авто-бліп тільки для нейтральних емоцій
        if emotion_name in ("neutral", "happy", "thinking", "listening"):
            self.next_blink -= dt_ms
            if self.next_blink <= 0:
                self.trigger()
                self.next_blink = random.uniform(3000, 6000)

        if not self.active:
            return None

        self.elapsed += dt_ms
        if self.elapsed >= self.TOTAL_MS:
            self.active = False
            return None

        if self.elapsed < self.CLOSE_MS:
            t = self.elapsed / self.CLOSE_MS
        elif self.elapsed < self.CLOSE_MS + self.HOLD_MS:
            t = 1.0
        else:
            t = 1.0 - (self.elapsed - self.CLOSE_MS - self.HOLD_MS) / self.OPEN_MS

        return t   # 0.0 = відкрито, 1.0 = закрито

# ─────────────────────────────────────────────
# ЕФЕКТИ
# ─────────────────────────────────────────────

class TearManager:
    """Сльози для Sad."""
    def __init__(self):
        self.tears = []   # [{x, y, vy, alpha, eye}]
        self.timer_l = random.uniform(1500, 2000)
        self.timer_r = random.uniform(1800, 2500)

    def reset(self):
        self.tears = []
        self.timer_l = random.uniform(1500, 2000)
        self.timer_r = random.uniform(1800, 2500)

    def update(self, dt_ms, active):
        if not active:
            self.tears = []
            return
        self.timer_l -= dt_ms
        self.timer_r -= dt_ms
        if self.timer_l <= 0:
            # Outer corner of left eye
            self.tears.append({"x": 155 + 40, "y": 160 + 60,
                                "vy": 1.2, "alpha": 255, "eye": "l"})
            self.timer_l = random.uniform(1500, 2000)
        if self.timer_r <= 0:
            self.tears.append({"x": 325 + 40, "y": 160 + 60,
                                "vy": 1.2, "alpha": 255, "eye": "r"})
            self.timer_r = random.uniform(1800, 2500)

        for t in self.tears:
            t["y"] += t["vy"] * dt_ms * 0.05
            if t["y"] > 300:
                t["alpha"] = max(0, t["alpha"] - dt_ms * 0.8)
        self.tears = [t for t in self.tears if t["alpha"] > 0]

    def draw(self, surface):
        for t in self.tears:
            alpha = int(t["alpha"])
            s = pygame.Surface((8, 14), pygame.SRCALPHA)
            pygame.draw.ellipse(s, COLOR_TEAR + (alpha,), s.get_rect())
            # highlight
            pygame.draw.circle(s, (255, 255, 255, min(alpha, 200)), (3, 3), 2)
            surface.blit(s, (int(t["x"]) - 4, int(t["y"])))


class ZzzManager:
    """«z z z» для Sleep."""
    def __init__(self):
        self.letters = []   # [{x, y, size, alpha, phase}]
        self.timer   = 0.0
        self.sizes   = [14, 18, 22]
        self.idx     = 0
        self._font_cache = {}

    def reset(self):
        self.letters = []
        self.timer   = 0.0
        self.idx     = 0

    def _get_font(self, size):
        if size not in self._font_cache:
            self._font_cache[size] = pygame.font.SysFont("monospace", size, bold=True)
        return self._font_cache[size]

    def update(self, dt_ms, active):
        if not active:
            self.letters = []
            return
        self.timer -= dt_ms
        if self.timer <= 0:
            sz = self.sizes[self.idx % 3]
            self.letters.append({
                "x": 380 + self.idx * 12,
                "y": 110,
                "size": sz,
                "alpha": 255,
                "vx": 0.3,
                "vy": -0.4,
            })
            self.idx  = (self.idx + 1) % 3
            self.timer = 1000.0

        for l in self.letters:
            l["x"] += l["vx"] * dt_ms * 0.05
            l["y"] += l["vy"] * dt_ms * 0.05
            l["alpha"] = max(0, l["alpha"] - dt_ms * 0.12)
        self.letters = [l for l in self.letters if l["alpha"] > 0]

    def draw(self, surface):
        for l in self.letters:
            font   = self._get_font(l["size"])
            txt    = font.render("z", True, COLOR_ZZZ)
            txt.set_alpha(int(l["alpha"]))
            surface.blit(txt, (int(l["x"]), int(l["y"])))


class FormulaManager:
    """Формули для Thinking."""
    SYMBOLS = ["π", "∑", "x²", "√", "∫", "?", "E=mc²"]

    def __init__(self):
        self.items  = []   # [{x, y, symbol, alpha, vy, font_size}]
        self.timer  = 0.0
        self._fonts = {}

    def reset(self):
        self.items = []
        self.timer = 0.0

    def _get_font(self, size):
        if size not in self._fonts:
            self._fonts[size] = pygame.font.SysFont("monospace", size)
        return self._fonts[size]

    def update(self, dt_ms, active):
        if not active:
            self.items = []
            return
        self.timer -= dt_ms
        if self.timer <= 0 and len(self.items) < 4:
            sz  = random.randint(16, 22)
            sym = random.choice(self.SYMBOLS)
            self.items.append({
                "x": random.randint(30, 430),
                "y": random.randint(30, 90),
                "symbol": sym,
                "alpha": 0,
                "vy": -0.25,
                "font_size": sz,
                "phase": "in",
                "phase_t": 0.0,
            })
            self.timer = random.uniform(400, 700)

        for it in self.items:
            it["y"] += it["vy"] * dt_ms * 0.05
            it["phase_t"] += dt_ms
            if it["phase"] == "in":
                it["alpha"] = min(153, it["alpha"] + dt_ms * 0.4)
                if it["alpha"] >= 153:
                    it["phase"]   = "hold"
                    it["phase_t"] = 0.0
            elif it["phase"] == "hold":
                if it["phase_t"] >= 800:
                    it["phase"]   = "out"
                    it["phase_t"] = 0.0
            elif it["phase"] == "out":
                it["alpha"] = max(0, it["alpha"] - dt_ms * 0.3)

        self.items = [it for it in self.items if not (it["phase"] == "out" and it["alpha"] <= 0)]

    def draw(self, surface):
        for it in self.items:
            font = self._get_font(it["font_size"])
            txt  = font.render(it["symbol"], True, COLOR_FORMULA)
            txt.set_alpha(int(it["alpha"]))
            surface.blit(txt, (int(it["x"]), int(it["y"])))


class SparkManager:
    """Іскри для Surprised — спалахують при вході."""
    def __init__(self):
        self.sparks = []   # [{x, y, angle, length, alpha}]
        self.active = False

    def trigger(self):
        self.sparks = []
        # По 3 іскри з кожного боку очей
        for cx, cy in [(155, 160), (325, 160)]:
            for _ in range(3):
                angle = random.uniform(0, 2 * math.pi)
                self.sparks.append({
                    "x": cx + random.randint(-70, 70),
                    "y": cy + random.randint(-60, 60),
                    "angle": angle,
                    "length": random.randint(10, 20),
                    "alpha": 255,
                })

    def update(self, dt_ms):
        for s in self.sparks:
            s["alpha"] = max(0, s["alpha"] - dt_ms * 1.3)
        self.sparks = [s for s in self.sparks if s["alpha"] > 0]

    def draw(self, surface):
        for s in self.sparks:
            alpha = int(s["alpha"])
            ex = int(s["x"] + math.cos(s["angle"]) * s["length"])
            ey = int(s["y"] + math.sin(s["angle"]) * s["length"])
            # Малюємо через Surface для alpha
            tmp = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.line(tmp, COLOR_OUTLINE + (alpha,),
                             (int(s["x"]), int(s["y"])), (ex, ey), 2)
            surface.blit(tmp, (0, 0))


class HeartManager:
    """Серця та рум'янець для Love."""
    def __init__(self):
        self.hearts = []
        self.timer  = 0.0
        self.pulse  = 0.0   # 0–2π для пульсації

    def reset(self):
        self.hearts = []
        self.timer  = 0.0

    def _draw_heart(self, surface, cx, cy, size, color, alpha):
        """Малює серце як полігон."""
        points = []
        for i in range(360):
            rad = math.radians(i)
            x = 16 * (math.sin(rad) ** 3)
            y = -(13 * math.cos(rad) - 5 * math.cos(2*rad)
                  - 2 * math.cos(3*rad) - math.cos(4*rad))
            points.append((cx + x * size / 16, cy + y * size / 16))
        if len(points) > 2:
            tmp = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.polygon(tmp, color + (alpha,), points)
            surface.blit(tmp, (0, 0))

    def update(self, dt_ms, active):
        if not active:
            self.hearts = []
            return
        self.pulse += dt_ms * 0.0073   # ~70 bpm
        self.timer -= dt_ms
        if self.timer <= 0 and len(self.hearts) < 3:
            side = random.choice([-1, 1])
            cx = 155 if side == -1 else 325
            self.hearts.append({
                "x": cx + random.randint(-20, 20),
                "y": 160,
                "alpha": 255,
                "size": random.randint(10, 16),
            })
            self.timer = random.uniform(600, 1200)
        for h in self.hearts:
            h["y"]    -= dt_ms * 0.03
            h["alpha"] = max(0, h["alpha"] - dt_ms * 0.18)
        self.hearts = [h for h in self.hearts if h["alpha"] > 0]

    def draw_blush(self, surface):
        """Рум'янець під очима."""
        for bx, by in [(120, 228), (360, 228)]:
            s = pygame.Surface((40, 14), pygame.SRCALPHA)
            pygame.draw.ellipse(s, COLOR_LOVE + (89,), s.get_rect())   # 35% of 255
            surface.blit(s, (bx - 20, by - 7))

    def draw_hearts(self, surface):
        for h in self.hearts:
            self._draw_heart(surface, int(h["x"]), int(h["y"]),
                             h["size"], COLOR_LOVE, int(h["alpha"]))

    def draw_eye_hearts(self, surface, eye_center, scale):
        """Серце замість iris у Love."""
        pulse_scale = 1.0 + 0.10 * abs(math.sin(self.pulse))
        size = int(35 * scale * pulse_scale)
        cx, cy = eye_center
        self._draw_heart(surface, cx, cy, size, COLOR_LOVE, 255)
        # Highlight у серці
        pygame.draw.circle(surface, COLOR_HIGHLIGHT,
                           (cx + 8, cy - 10), HIGHLIGHT_R)


class QuestionMarkManager:
    """Знак '?' для Confused."""
    def __init__(self):
        self.phase = 0.0
        self._font = None

    def reset(self):
        self.phase = 0.0

    def update(self, dt_ms, active):
        if active:
            self.phase += dt_ms * 0.004   # 1.5s cycle

    def draw(self, surface, active):
        if not active:
            return
        if self._font is None:
            self._font = pygame.font.SysFont("monospace", 28, bold=True)
        angle  = math.sin(self.phase) * 8   # ±8°
        txt    = self._font.render("?", True, COLOR_FORMULA)
        txt    = pygame.transform.rotate(txt, angle)
        surface.blit(txt, (370 - txt.get_width() // 2,
                           70  - txt.get_height() // 2))


class LoudnessBars:
    """Смужки гучності для Listening."""
    BAR_COUNT = 5
    BAR_W     = 6
    BAR_GAP   = 8
    BAR_MIN_H = 4
    BAR_MAX_H = 24
    CENTER    = (240, 290)

    def __init__(self):
        self.heights = [self.BAR_MIN_H] * self.BAR_COUNT
        self.loudness = 0.0

    def set_loudness(self, value):
        """value: 0.0–1.0"""
        self.loudness = max(0.0, min(1.0, value))

    def update(self, dt_ms, active):
        if not active:
            self.heights = [self.BAR_MIN_H] * self.BAR_COUNT
            return
        # Симуляція без аудіо — случайне «дихання»
        for i in range(self.BAR_COUNT):
            center_boost = 1.0 - abs(i - self.BAR_COUNT // 2) * 0.2
            target = self.BAR_MIN_H + int(
                (self.BAR_MAX_H - self.BAR_MIN_H)
                * self.loudness
                * center_boost
                * random.uniform(0.7, 1.0)
            )
            self.heights[i] += int((target - self.heights[i]) * 0.3)

    def draw(self, surface, active):
        if not active:
            return
        cx, cy = self.CENTER
        total_w = self.BAR_COUNT * self.BAR_W + (self.BAR_COUNT - 1) * self.BAR_GAP
        x0 = cx - total_w // 2
        for i in range(self.BAR_COUNT):
            bx = x0 + i * (self.BAR_W + self.BAR_GAP)
            bh = max(self.BAR_MIN_H, self.heights[i])
            rect = pygame.Rect(bx, cy - bh // 2, self.BAR_W, bh)
            pygame.draw.rect(surface, COLOR_OUTLINE, rect, border_radius=3)


# ─────────────────────────────────────────────
# МАЛЮВАННЯ
# ─────────────────────────────────────────────

def _eyelid_polygon(cx, cy, eye_w, eye_h, lid_frac, is_top, tilt_deg):
    """
    Повертає список точок полігону нахиленої повіки.
    lid_frac — частка висоти ока (0.0–1.0)
    is_top   — True = верхня повіка, False = нижня
    tilt_deg — кут нахилу лінії повіки в градусах
      Для top_lid: >0 → inner corner нижче (Angry), <0 → outer corner нижче (Sad)
      Для bot_lid: аналогічно
    """
    half_w = eye_w // 2
    half_h = eye_h // 2
    lid_h  = int(eye_h * lid_frac)

    tilt_dy = int(half_w * math.tan(math.radians(abs(tilt_deg))))

    if is_top:
        top_y = cy - half_h
        if tilt_deg > 0:   # inner (лівий край для лівого ока) нижче
            left_lid_y  = top_y + lid_h + tilt_dy
            right_lid_y = top_y + lid_h - tilt_dy
        elif tilt_deg < 0:  # outer (правий край для лівого ока) нижче
            left_lid_y  = top_y + lid_h - tilt_dy
            right_lid_y = top_y + lid_h + tilt_dy
        else:
            left_lid_y  = top_y + lid_h
            right_lid_y = top_y + lid_h
        return [
            (cx - half_w, top_y),
            (cx + half_w, top_y),
            (cx + half_w, right_lid_y),
            (cx - half_w, left_lid_y),
        ]
    else:
        bot_y = cy + half_h
        if tilt_deg > 0:
            left_lid_y  = bot_y - lid_h - tilt_dy
            right_lid_y = bot_y - lid_h + tilt_dy
        elif tilt_deg < 0:
            left_lid_y  = bot_y - lid_h + tilt_dy
            right_lid_y = bot_y - lid_h - tilt_dy
        else:
            left_lid_y  = bot_y - lid_h
            right_lid_y = bot_y - lid_h
        return [
            (cx - half_w, left_lid_y),
            (cx + half_w, right_lid_y),
            (cx + half_w, bot_y),
            (cx - half_w, bot_y),
        ]


def draw_eye(surface, center, params, side="left",
             blink_t=None, heart_mgr=None, bg_color=BG_COLOR):
    """
    Малює одне око.
    blink_t: None або 0.0–1.0 (blink override)
    heart_mgr: HeartManager або None
    """
    cx, cy = center
    scale  = params["eye_scale_l"] if side == "left" else params["eye_scale_r"]
    w = int(EYE_W * scale)
    h = int(EYE_H * scale)

    top_lid  = params["top_lid_l"]  if side == "left" else params["top_lid_r"]
    bot_lid  = params["bot_lid_l"]  if side == "left" else params["bot_lid_r"]
    tilt     = params["lid_tilt_l"] if side == "left" else params["lid_tilt_r"]
    px, py   = params["pupil_offset_l"] if side == "left" else params["pupil_offset_r"]

    # Blink override — повністю закриває повіку
    if blink_t is not None:
        top_lid = blink_t * 0.5
        bot_lid = blink_t * 0.5
        tilt    = 0.0

    sclera = params.get("sclera_color", COLOR_SCLERA)
    oc     = params["outline_color"]
    alpha  = params["outline_alpha"]
    outline_color = tuple(int(c * alpha) for c in oc)

    eye_rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)

    # ── Sclera ──
    pygame.draw.rect(surface, sclera, eye_rect, border_radius=EYE_RADIUS)

    # ── Outline ──
    pygame.draw.rect(surface, outline_color, eye_rect, width=4, border_radius=EYE_RADIUS)

    # ── Iris / Pupil / Highlight  або  Heart ──
    iris_r   = int(params["iris_r"])
    pupil_r  = int(params["pupil_r"])
    pupil_cx = cx + int(px)
    pupil_cy = cy + int(py)

    if params.get("heart_eyes") and heart_mgr is not None:
        heart_mgr.draw_eye_hearts(surface, (pupil_cx, pupil_cy), scale)
    else:
        pygame.draw.circle(surface, COLOR_IRIS, (pupil_cx, pupil_cy), iris_r)
        pygame.draw.circle(surface, COLOR_PUPIL, (pupil_cx, pupil_cy), pupil_r)
        hx = pupil_cx + HIGHLIGHT_OFFSET[0]
        hy = pupil_cy + HIGHLIGHT_OFFSET[1]
        pygame.draw.circle(surface, COLOR_HIGHLIGHT, (hx, hy), HIGHLIGHT_R)

    # ── Верхня повіка (нахилений полігон) ──
    if top_lid > 0.001:
        poly = _eyelid_polygon(cx, cy, w, h, top_lid, True, tilt)
        pygame.draw.polygon(surface, bg_color, poly)

    # ── Нижня повіка ──
    if bot_lid > 0.001:
        poly = _eyelid_polygon(cx, cy, w, h, bot_lid, False, tilt)
        pygame.draw.polygon(surface, bg_color, poly)

    # Sleep: тонка лінія замість ока
    if top_lid >= 0.9 and bot_lid >= 0.9:
        line_y = cy
        pygame.draw.rect(surface, bg_color, eye_rect)
        line_color = tuple(int(c * params["outline_alpha"]) for c in COLOR_OUTLINE)
        pygame.draw.line(surface, line_color,
                         (cx - 55, line_y), (cx + 55, line_y), 4)

    return eye_rect


def draw_mouth(surface, params, sleep_open=0.35, wavy_phase=0.0, bg_color=BG_COLOR):
    """
    Малює рот відповідно до mouth_type.
    wavy_phase: фаза хвилі для 'wavy' (Confused)
    """
    mx, my      = MOUTH_CENTER
    w           = int(params["mouth_width"])
    curve       = params["mouth_curve"]
    open_       = params["mouth_open"]
    mtype       = params.get("mouth_type", "smile")
    mouth_color = (255, 255, 255)
    line_width  = 5

    # Thinking: рот зміщений вправо
    if mtype == "line" and params.get("mouth_width") == 35:
        mx = 255

    # ── Відкритий овал (Speaking, Surprised) ──
    if mtype == "open" and open_ > 0.05:
        ow = max(w, 10)
        oh = max(int(open_ * 40), 6)
        rect = pygame.Rect(mx - ow // 2, my - oh // 2, ow, oh)
        pygame.draw.ellipse(surface, mouth_color, rect, line_width)
        return rect

    # ── Sleep oval ──
    if mtype == "sleep_oval":
        ow = max(w, 10)
        oh = max(int(sleep_open * 40), 6)
        rect = pygame.Rect(mx - ow // 2, my - oh // 2, ow, oh)
        pygame.draw.ellipse(surface, mouth_color, rect, line_width)
        return rect

    # ── Zigzag (Angry) ──
    if mtype == "zigzag":
        teeth = 4
        seg_w = w // teeth
        y0    = my - 6
        y1    = my + 6
        pts   = []
        x     = mx - w // 2
        for i in range(teeth + 1):
            pts.append((x + i * seg_w, y0 if i % 2 == 0 else y1))
        pygame.draw.lines(surface, mouth_color, False, pts, line_width)
        return pygame.Rect(mx - w // 2, my - 8, w, 16)

    # ── Wavy (Confused) ──
    if mtype == "wavy":
        pts = []
        steps = 40
        for i in range(steps + 1):
            t = i / steps
            x = mx - w // 2 + int(t * w)
            y = my + int(5 * math.sin(t * 2 * math.pi * 2 + wavy_phase))
            pts.append((x, y))
        if len(pts) > 1:
            pygame.draw.lines(surface, mouth_color, False, pts, line_width)
        return pygame.Rect(mx - w // 2 - 5, my - 10, w + 10, 20)

    # ── Пряма лінія ──
    if mtype == "line" or abs(curve) < 1:
        pygame.draw.line(surface, mouth_color,
                         (mx - w // 2, my), (mx + w // 2, my), line_width)
        return pygame.Rect(mx - w // 2, my - 3, w, 6)

    # ── Smile / Frown (крива) ──
    pts   = []
    steps = 20
    for i in range(steps + 1):
        t  = i / steps
        x  = mx - w // 2 + int(t * w)
        y  = my + int(curve * math.sin(t * math.pi))
        pts.append((x, y))
    if len(pts) > 1:
        pygame.draw.lines(surface, mouth_color, False, pts, line_width)

    return pygame.Rect(mx - w // 2 - 5, my - abs(int(curve)) - 5,
                       w + 10, abs(int(curve)) * 2 + 15)


# ─────────────────────────────────────────────
# МІСТ: pygame surface → luma.lcd
# Увага: ILI9488 з bgr=True сам робить swap,
# тому передаємо RGB без додаткового [:, :, ::-1]
# ─────────────────────────────────────────────
def surface_to_luma(surface, luma_device):
    raw     = pygame.surfarray.array3d(surface)
    raw     = raw.transpose(1, 0, 2)
    pil_img = Image.fromarray(raw.astype("uint8"), "RGB")
    luma_device.display(pil_img)


# ─────────────────────────────────────────────
# ГОЛОВНИЙ ЦИКЛ
# ─────────────────────────────────────────────
def main():
    global GLOW_CACHE

    # ── luma.lcd ──────────────────────────────────────────────────────────
    luma_device = None
    USE_LUMA    = False

    if LUMA_AVAILABLE:
        try:
            serial      = luma_spi(port=0, device=0,
                                   gpio_DC=25, gpio_RST=17,
                                   bus_speed_hz=32000000)
            luma_device = ili9488(serial, width=480, height=320,
                                  rotate=0, bgr=True)
            luma_device.backlight(True)
            USE_LUMA = True
            print("[DISPLAY] luma.lcd ILI9488 ✅")
        except Exception as e:
            print(f"[DISPLAY] luma недоступна → режим вікна ({e})")

    # ── Pygame — SDL_VIDEODRIVER мусить бути встановлений ДО pygame.init() ──
    if USE_LUMA:
        os.environ["SDL_VIDEODRIVER"] = "offscreen"

    pygame.init()
    GLOW_CACHE = GlowCache()

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("AIKO Eyes v3")
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()

    emotion    = EmotionState("neutral")
    blink_anim = BlinkAnimation()

    # Менеджери ефектів
    tear_mgr    = TearManager()
    zzz_mgr     = ZzzManager()
    formula_mgr = FormulaManager()
    spark_mgr   = SparkManager()
    heart_mgr   = HeartManager()
    qmark_mgr   = QuestionMarkManager()
    bars        = LoudnessBars()

    # Авто-тест
    TEST_EMOTIONS = list(EMOTION_PARAMS.keys())
    test_idx      = 0
    test_timer    = 0.0
    TEST_INTERVAL = 3000

    # Анімація дихання Sleep
    breath_phase = 0.0
    sleep_open   = 0.35

    # Хвиля Confused
    wavy_phase = 0.0

    # Попередня емоція для скидання ефектів
    prev_emotion = "neutral"

    running = True
    while running:
        dt = clock.tick(FPS)

        # ── Події ──────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                keys = list(EMOTION_PARAMS.keys())
                for i, k in enumerate(keys):
                    if event.key == getattr(pygame, f"K_{i+1}", None):
                        emotion.set_emotion(k)
                        if k == "surprised":
                            spark_mgr.trigger()

        # ── Авто-тест ──────────────────────────────────────────────────
        test_timer += dt
        if test_timer >= TEST_INTERVAL:
            test_timer = 0.0
            test_idx   = (test_idx + 1) % len(TEST_EMOTIONS)
            new_e      = TEST_EMOTIONS[test_idx]
            emotion.set_emotion(new_e)
            if new_e == "surprised":
                spark_mgr.trigger()

        current_name = emotion.current_name

        # Скидання ефектів при зміні емоції
        if current_name != prev_emotion:
            if prev_emotion == "sad":
                tear_mgr.reset()
            if prev_emotion == "sleep":
                zzz_mgr.reset()
            if prev_emotion == "thinking":
                formula_mgr.reset()
            if prev_emotion == "love":
                heart_mgr.reset()
            if prev_emotion == "confused":
                qmark_mgr.reset()
            prev_emotion = current_name

        p = emotion.get()

        # ── Оновлення анімацій ─────────────────────────────────────────
        blink_t = blink_anim.update(dt, current_name)

        # Sleep breath
        if current_name == "sleep":
            breath_phase += dt * 0.00157   # 4s cycle
            sleep_open    = 0.35 + 0.10 * math.sin(breath_phase)
        else:
            breath_phase = 0.0
            sleep_open   = 0.35

        # Confused wavy
        wavy_phase += dt * 0.003

        # Ефекти
        tear_mgr.update(dt,    current_name == "sad")
        zzz_mgr.update(dt,     current_name == "sleep")
        formula_mgr.update(dt, current_name == "thinking")
        spark_mgr.update(dt)
        heart_mgr.update(dt,   current_name == "love")
        qmark_mgr.update(dt,   current_name == "confused")
        bars.update(dt,        current_name == "listening")

        # ── Малювання ──────────────────────────────────────────────────
        bg = p.get("bg_color", BG_COLOR)
        screen.fill(bg)

        rect_l = draw_eye(screen, EYE_LEFT_CENTER,  p, side="left",
                          blink_t=blink_t, heart_mgr=heart_mgr, bg_color=bg)
        rect_r = draw_eye(screen, EYE_RIGHT_CENTER, p, side="right",
                          blink_t=blink_t, heart_mgr=heart_mgr, bg_color=bg)
        rect_m = draw_mouth(screen, p,
                            sleep_open=sleep_open,
                            wavy_phase=wavy_phase,
                            bg_color=bg)

        # Ефекти поверх очей
        tear_mgr.draw(screen)
        zzz_mgr.draw(screen)
        formula_mgr.draw(screen)
        spark_mgr.draw(screen)

        if current_name == "love":
            heart_mgr.draw_blush(screen)
            heart_mgr.draw_hearts(screen)

        qmark_mgr.draw(screen, current_name == "confused")
        bars.draw(screen, current_name == "listening")

        if USE_LUMA:
            surface_to_luma(screen, luma_device)
        else:
            pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
