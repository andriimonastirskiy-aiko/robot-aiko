#!/usr/bin/env python3
"""
AIKO eyes_v3.py — система емоцій
База: специфікація AIKO Emotion Specification
Canvas: 480x320, pygame + SDL2, dirty rects, кешований glow
"""

import pygame
import sys
import time
import math
from PIL import Image, ImageFilter
import numpy as np

# ─────────────────────────────────────────────
# КОНСТАНТИ
# ─────────────────────────────────────────────
WIDTH, HEIGHT = 480, 320
FPS = 30
BG_COLOR = (0, 0, 0)

# Геометрія очей
EYE_LEFT_CENTER  = (155, 160)
EYE_RIGHT_CENTER = (325, 160)
EYE_W, EYE_H     = 130, 120
EYE_RADIUS        = 35

# Iris / Pupil
IRIS_R_DEFAULT   = 38
PUPIL_R_DEFAULT  = 20
HIGHLIGHT_R      = 7
HIGHLIGHT_OFFSET = (12, -14)

# Кольори
COLOR_SCLERA    = (255, 255, 255)
COLOR_OUTLINE   = (0, 191, 255)      # #00BFFF
COLOR_IRIS      = (0, 191, 255)
COLOR_PUPIL     = (0, 0, 0)
COLOR_HIGHLIGHT = (255, 255, 255)
COLOR_ANGRY     = (255, 34, 0)       # #FF2200
COLOR_LOVE      = (255, 79, 163)     # #FF4FA3

# Рот
MOUTH_CENTER = (240, 245)

# Transition
TRANSITION_MS = 350

# ─────────────────────────────────────────────
# ПАРАМЕТРИ ЕМОЦІЙ
# Усі значення — з таблиці специфікації
# top_lid / bot_lid — % від висоти ока (0.0–1.0)
# pupil_offset — (x, y) пікселів від центру
# eye_scale — масштаб від центру ока
# outline_color — (R, G, B)
# outline_alpha — 0.0–1.0
# mouth_width, mouth_curve, mouth_open
# iris_r, pupil_r
# ─────────────────────────────────────────────
EMOTION_PARAMS = {
    "neutral": {
        "top_lid_l": 0.0,  "bot_lid_l": 0.0,
        "top_lid_r": 0.0,  "bot_lid_r": 0.0,
        "lid_tilt_l": 0.0, "lid_tilt_r": 0.0,
        "pupil_offset": (0, 0),
        "eye_scale_l": 1.0, "eye_scale_r": 1.0,
        "outline_color": COLOR_OUTLINE,
        "outline_alpha": 1.0,
        "iris_r": IRIS_R_DEFAULT, "pupil_r": PUPIL_R_DEFAULT,
        "mouth_width": 50, "mouth_curve": 4, "mouth_open": 0.0,
        "bg_color": BG_COLOR,
    },
    "happy": {
        "top_lid_l": 0.0,  "bot_lid_l": 0.1,
        "top_lid_r": 0.0,  "bot_lid_r": 0.1,
        "lid_tilt_l": 0.0, "lid_tilt_r": 0.0,
        "pupil_offset": (0, 0),
        "eye_scale_l": 1.0, "eye_scale_r": 1.0,
        "outline_color": COLOR_OUTLINE,
        "outline_alpha": 1.0,
        "iris_r": IRIS_R_DEFAULT, "pupil_r": PUPIL_R_DEFAULT,
        "mouth_width": 70, "mouth_curve": 18, "mouth_open": 0.0,
        "bg_color": BG_COLOR,
    },
    "surprised": {
        "top_lid_l": 0.0,  "bot_lid_l": 0.0,
        "top_lid_r": 0.0,  "bot_lid_r": 0.0,
        "lid_tilt_l": 0.0, "lid_tilt_r": 0.0,
        "pupil_offset": (0, 0),
        "eye_scale_l": 1.12, "eye_scale_r": 1.12,
        "outline_color": COLOR_OUTLINE,
        "outline_alpha": 1.0,
        "iris_r": 30, "pupil_r": 14,
        "mouth_width": 22, "mouth_curve": 0, "mouth_open": 1.0,
        "bg_color": BG_COLOR,
    },
    "sad": {
        "top_lid_l": 0.35, "bot_lid_l": 0.0,
        "top_lid_r": 0.35, "bot_lid_r": 0.0,
        "lid_tilt_l": -10.0, "lid_tilt_r": -10.0,  # outer corner down
        "pupil_offset": (0, 12),
        "eye_scale_l": 1.0, "eye_scale_r": 1.0,
        "outline_color": COLOR_OUTLINE,
        "outline_alpha": 0.7,
        "iris_r": IRIS_R_DEFAULT, "pupil_r": PUPIL_R_DEFAULT,
        "mouth_width": 50, "mouth_curve": -12, "mouth_open": 0.0,
        "bg_color": BG_COLOR,
    },
    "angry": {
        "top_lid_l": 0.4,  "bot_lid_l": 0.0,
        "top_lid_r": 0.4,  "bot_lid_r": 0.0,
        "lid_tilt_l": 20.0, "lid_tilt_r": 20.0,  # inner corner down
        "pupil_offset": (6, 0),   # inward; правий буде -6 в draw
        "eye_scale_l": 1.0, "eye_scale_r": 1.0,
        "outline_color": COLOR_ANGRY,
        "outline_alpha": 1.0,
        "iris_r": IRIS_R_DEFAULT, "pupil_r": PUPIL_R_DEFAULT,
        "mouth_width": 60, "mouth_curve": 0, "mouth_open": 0.0,
        "bg_color": BG_COLOR,
    },
    "thinking": {
        "top_lid_l": 0.0,  "bot_lid_l": 0.0,
        "top_lid_r": 0.0,  "bot_lid_r": 0.3,
        "lid_tilt_l": 0.0, "lid_tilt_r": 0.0,
        "pupil_offset": (14, -14),
        "eye_scale_l": 1.0, "eye_scale_r": 1.0,
        "outline_color": COLOR_OUTLINE,
        "outline_alpha": 1.0,
        "iris_r": IRIS_R_DEFAULT, "pupil_r": PUPIL_R_DEFAULT,
        "mouth_width": 35, "mouth_curve": 0, "mouth_open": 0.0,
        "bg_color": BG_COLOR,
    },
    "love": {
        "top_lid_l": 0.0,  "bot_lid_l": 0.1,
        "top_lid_r": 0.0,  "bot_lid_r": 0.1,
        "lid_tilt_l": 0.0, "lid_tilt_r": 0.0,
        "pupil_offset": (0, 0),
        "eye_scale_l": 1.0, "eye_scale_r": 1.0,
        "outline_color": COLOR_OUTLINE,
        "outline_alpha": 1.0,
        "iris_r": IRIS_R_DEFAULT, "pupil_r": PUPIL_R_DEFAULT,
        "mouth_width": 60, "mouth_curve": 14, "mouth_open": 0.0,
        "bg_color": BG_COLOR,
    },
    "confused": {
        "top_lid_l": 0.0,  "bot_lid_l": 0.0,
        "top_lid_r": 0.25, "bot_lid_r": 0.0,
        "lid_tilt_l": 0.0, "lid_tilt_r": 8.0,
        "pupil_offset": (0, 0),   # різні для L/R — окремо в draw
        "eye_scale_l": 1.08, "eye_scale_r": 1.0,
        "outline_color": COLOR_OUTLINE,
        "outline_alpha": 1.0,
        "iris_r": IRIS_R_DEFAULT, "pupil_r": PUPIL_R_DEFAULT,
        "mouth_width": 55, "mouth_curve": 0, "mouth_open": 0.0,
        "bg_color": BG_COLOR,
    },
    "sleep": {
        "top_lid_l": 0.5,  "bot_lid_l": 0.5,
        "top_lid_r": 0.5,  "bot_lid_r": 0.5,
        "lid_tilt_l": 0.0, "lid_tilt_r": 0.0,
        "pupil_offset": (0, 0),
        "eye_scale_l": 1.0, "eye_scale_r": 1.0,
        "outline_color": COLOR_OUTLINE,
        "outline_alpha": 0.4,
        "iris_r": IRIS_R_DEFAULT, "pupil_r": PUPIL_R_DEFAULT,
        "mouth_width": 18, "mouth_curve": 0, "mouth_open": 0.4,
        "bg_color": BG_COLOR,
    },
    "listening": {
        "top_lid_l": 0.0,  "bot_lid_l": 0.0,
        "top_lid_r": 0.0,  "bot_lid_r": 0.0,
        "lid_tilt_l": 0.0, "lid_tilt_r": 0.0,
        "pupil_offset": (0, 0),
        "eye_scale_l": 1.05, "eye_scale_r": 1.05,
        "outline_color": COLOR_OUTLINE,
        "outline_alpha": 1.0,
        "iris_r": 41, "pupil_r": PUPIL_R_DEFAULT,
        "mouth_width": 30, "mouth_curve": 2, "mouth_open": 0.0,
        "bg_color": BG_COLOR,
    },
    "speaking": {
        # очі — як neutral, рот керується аудіо окремо
        "top_lid_l": 0.0,  "bot_lid_l": 0.0,
        "top_lid_r": 0.0,  "bot_lid_r": 0.0,
        "lid_tilt_l": 0.0, "lid_tilt_r": 0.0,
        "pupil_offset": (0, 0),
        "eye_scale_l": 1.0, "eye_scale_r": 1.0,
        "outline_color": COLOR_OUTLINE,
        "outline_alpha": 1.0,
        "iris_r": IRIS_R_DEFAULT, "pupil_r": PUPIL_R_DEFAULT,
        "mouth_width": 45, "mouth_curve": 0, "mouth_open": 0.5,
        "bg_color": BG_COLOR,
    },
}

# ─────────────────────────────────────────────
# ІНТЕРПОЛЯЦІЯ
# ─────────────────────────────────────────────
def lerp(a, b, t):
    """Лінійна інтерполяція між a та b, t = 0.0–1.0"""
    return a + (b - a) * t

def ease_in_out(t):
    """Ease-in-out крива"""
    return t * t * (3 - 2 * t)

def lerp_color(c1, c2, t):
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))

def lerp_params(p1, p2, t):
    """Інтерполює всі числові параметри між двома емоціями"""
    result = {}
    for key in p1:
        if key == "outline_color" or key == "bg_color":
            result[key] = lerp_color(p1[key], p2[key], t)
        elif isinstance(p1[key], (int, float)):
            result[key] = lerp(p1[key], p2[key], t)
        elif isinstance(p1[key], tuple):
            result[key] = tuple(lerp(a, b, t) for a, b in zip(p1[key], p2[key]))
        else:
            result[key] = p2[key] if t > 0.5 else p1[key]
    return result

# ─────────────────────────────────────────────
# КЛАС СТАНУ ЕМОЦІЙ
# ─────────────────────────────────────────────
class EmotionState:
    def __init__(self, start_emotion="neutral"):
        self.current_name = start_emotion
        self.current_params = dict(EMOTION_PARAMS[start_emotion])
        self.target_name   = start_emotion
        self.target_params  = dict(EMOTION_PARAMS[start_emotion])
        self.from_params    = dict(EMOTION_PARAMS[start_emotion])
        self.transition_ms  = TRANSITION_MS
        self.elapsed_ms     = 0.0
        self.in_transition  = False

    def set_emotion(self, name):
        if name not in EMOTION_PARAMS:
            print(f"[WARN] Невідома емоція: {name}")
            return
        if name == self.target_name and not self.in_transition:
            return
        self.from_params   = dict(self.current_params)
        self.target_name   = name
        self.target_params = dict(EMOTION_PARAMS[name])
        self.elapsed_ms    = 0.0
        self.in_transition = True

    def update(self, dt_ms):
        if not self.in_transition:
            return
        self.elapsed_ms += dt_ms
        t = min(self.elapsed_ms / self.transition_ms, 1.0)
        t_eased = ease_in_out(t)
        self.current_params = lerp_params(self.from_params, self.target_params, t_eased)
        if t >= 1.0:
            self.current_name  = self.target_name
            self.current_params = dict(self.target_params)
            self.in_transition  = False

    def get(self):
        return self.current_params

# ─────────────────────────────────────────────
# МАЛЮВАННЯ
# ─────────────────────────────────────────────
def draw_eye(surface, center, params, side="left"):
    """
    Малює одне око з повіками, iris, pupil, highlight.
    side = "left" або "right" (для angry inward offset)
    """
    cx, cy = center
    scale = params["eye_scale_l"] if side == "left" else params["eye_scale_r"]
    w = int(EYE_W * scale)
    h = int(EYE_H * scale)

    top_lid = params["top_lid_l"] if side == "left" else params["top_lid_r"]
    bot_lid = params["bot_lid_l"] if side == "left" else params["bot_lid_r"]

    # --- Sclera (заокруглений прямокутник) ---
    eye_rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
    pygame.draw.rect(surface, COLOR_SCLERA, eye_rect, border_radius=EYE_RADIUS)

    # --- Outline ---
    alpha = params["outline_alpha"]
    oc = params["outline_color"]
    outline_color = tuple(int(c * alpha) for c in oc)
    pygame.draw.rect(surface, outline_color, eye_rect, width=4, border_radius=EYE_RADIUS)

    # --- Iris ---
    iris_r = int(params["iris_r"])
    px, py = params["pupil_offset"]
    if side == "right" and params.get("mouth_curve", 0) == 0:
        # Для angry — дзеркалимо inward offset
        pass
    pupil_cx = cx + int(px)
    pupil_cy = cy + int(py)
    pygame.draw.circle(surface, COLOR_IRIS, (pupil_cx, pupil_cy), iris_r)

    # --- Pupil ---
    pupil_r = int(params["pupil_r"])
    pygame.draw.circle(surface, COLOR_PUPIL, (pupil_cx, pupil_cy), pupil_r)

    # --- Highlight ---
    hx = pupil_cx + HIGHLIGHT_OFFSET[0]
    hy = pupil_cy + HIGHLIGHT_OFFSET[1]
    pygame.draw.circle(surface, COLOR_HIGHLIGHT, (hx, hy), HIGHLIGHT_R)

    # --- Повіки (маски кольором фону) ---
    # Верхня повіка
    if top_lid > 0:
        lid_h = int(h * top_lid)
        lid_rect = pygame.Rect(cx - w // 2, cy - h // 2, w, lid_h)
        pygame.draw.rect(surface, BG_COLOR, lid_rect)

    # Нижня повіка
    if bot_lid > 0:
        lid_h = int(h * bot_lid)
        lid_rect = pygame.Rect(cx - w // 2, cy + h // 2 - lid_h, w, lid_h)
        pygame.draw.rect(surface, BG_COLOR, lid_rect)

    return eye_rect  # для dirty rects

def draw_mouth(surface, params):
    """
    Малює рот: пряма лінія (curve=0), усмішка/grimace (curve!=0),
    або кружечок (open=1.0)
    """
    mx, my = MOUTH_CENTER
    w  = int(params["mouth_width"])
    curve = params["mouth_curve"]
    open_ = params["mouth_open"]

    mouth_color = (255, 255, 255)
    line_width  = 5

    if open_ > 0.1:
        # Відкритий рот — еліпс
        ow = max(w, 10)
        oh = int(open_ * 30)
        rect = pygame.Rect(mx - ow // 2, my - oh // 2, ow, oh)
        pygame.draw.ellipse(surface, mouth_color, rect, line_width)
        return rect

    if abs(curve) < 1:
        # Пряма лінія
        pygame.draw.line(surface, mouth_color, (mx - w // 2, my), (mx + w // 2, my), line_width)
    else:
        # Дуга (усмішка або grimace) через points
        points = []
        steps = 20
        for i in range(steps + 1):
            t = i / steps
            x = mx - w // 2 + int(t * w)
            y = my + int(curve * math.sin(t * math.pi))
            points.append((x, y))
        if len(points) > 1:
            pygame.draw.lines(surface, mouth_color, False, points, line_width)

    # Повертаємо dirty rect
    mouth_rect = pygame.Rect(mx - w // 2 - 5, my - abs(curve) - 5,
                             w + 10, abs(curve) * 2 + 10 + 5)
    return mouth_rect

# ─────────────────────────────────────────────
# ГОЛОВНИЙ ЦИКЛ
# ─────────────────────────────────────────────
def main():
    pygame.init()

    # Для Raspberry Pi — fullscreen без курсора
    # На ПК для тесту — звичайне вікно
    try:
        screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
    except Exception:
        screen = pygame.display.set_mode((WIDTH, HEIGHT))

    pygame.display.set_caption("AIKO Eyes v3")
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()

    emotion = EmotionState("neutral")

    # Тест-список емоцій (автопереключення кожні 3с)
    TEST_EMOTIONS = list(EMOTION_PARAMS.keys())
    test_idx   = 0
    test_timer = 0.0
    TEST_INTERVAL = 3000  # мс

    running = True
    while running:
        dt = clock.tick(FPS)  # мс від попереднього кадру

        # ── Події ──
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                # Ручне перемикання клавішами 1–0
                keys = list(EMOTION_PARAMS.keys())
                for i, k in enumerate(keys):
                    if event.key == getattr(pygame, f"K_{i+1}", None):
                        emotion.set_emotion(k)

        # ── Авто-тест ──
        test_timer += dt
        if test_timer >= TEST_INTERVAL:
            test_timer = 0.0
            test_idx = (test_idx + 1) % len(TEST_EMOTIONS)
            emotion.set_emotion(TEST_EMOTIONS[test_idx])
            print(f"[TEST] → {TEST_EMOTIONS[test_idx]}")

        # ── Оновлення стану ──
        emotion.update(dt)
        p = emotion.get()

        # ── Малювання ──
        dirty = []
        screen.fill(BG_COLOR)

        rect_l = draw_eye(screen, EYE_LEFT_CENTER,  p, side="left")
        rect_r = draw_eye(screen, EYE_RIGHT_CENTER, p, side="right")
        rect_m = draw_mouth(screen, p)

        dirty.extend([rect_l, rect_r, rect_m])
        pygame.display.update(dirty)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
