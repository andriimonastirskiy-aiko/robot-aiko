# AIKO: Emotion Specification

## 1. General rules

These rules apply to every emotion. Most important: the vertical center of the eyes is always y = 160 and never changes.

**Canvas:** 480×320 px, background #000000.

**Eye height.** Any change of eye shape (squint, closing, sadness) is done with eyelid masks (top and bottom) sliding over the eye, never by moving the eye itself. Enlarging an eye (as in Surprised) scales from its center, so the center stays put.

### Base eye geometry

| Parameter | Value |
| --- | --- |
| Left eye center | (155, 160) |
| Right eye center | (325, 160) |
| Size | 130×120 px, corner radius \~35 px |
| Sclera | white #FFFFFF |
| Outline | 4 px, #00BFFF, neon glow (blur \~12 px) |
| Iris | circle R = 38 px, #00BFFF, slightly darker toward the edge |
| Pupil | circle R = 20 px, #000000 |
| Highlight | white circle R = 7 px, offset (+12, −14) from pupil center, one per eye |

### Mouth

Center (240, 245), white 5 px line with round caps and a soft glow. The mouth is parametric so it can morph smoothly between shapes:

- `width` — width (default 70 px)
- `curve` — bend: positive = smile, negative = frown, 0 = straight line
- `open` — openness (0 = line, 1 = round «o»)

**Eyebrows:** none in any emotion.

### Smooth transitions

- All parameters interpolate together between emotions: eyelids, pupil offset, iris size, mouth parameters, colors, eye scale.
- Duration 350 ms, ease-in-out curve.
- Extra effects (tears, formulas, red background) fade in over 300 ms and fade out over 300 ms when leaving the emotion.
- Eye height never changes during a transition.

### Neutral base state

Recommended rest state: eyes open, pupils centered, mouth a faint smile (`curve` +4, `width` 50). Every emotion returns here when the agent expresses nothing.

### Rendering on Raspberry Pi Zero 2 W

The face is drawn in code in real time, not from sprites, so transitions between any two emotions stay smooth without per-pair frames.

- **Stack:** Python + pygame (SDL2, offscreen) → PIL Image → luma.lcd (ili9488) → SPI display. Target 30 fps.
- **Display driver:** luma.lcd with ili9488 driver over SPI (port=0, device=0, DC=GPIO25, RST=GPIO17, bus_speed=32 MHz). pygame renders to an offscreen surface, which is converted to PIL Image via `surfarray` and sent to the physical display via `luma.lcd.display()`. fbcp-ili9341 is **NOT** used. **Important:** ILI9488 operates in BGR mode. The `bgr=True` parameter in luma.lcd is not sufficient — R and B channels must be swapped manually via `raw[:, :, ::-1]` before converting to PIL Image.
- **Glow:** blur is the most expensive operation. Render the glow once at startup (e.g. Pillow GaussianBlur) for each color and size, cache it as surfaces, and only blit it each frame.
- **Eyelids:** background-colored polygons drawn over the eye and clipped to the eye shape. The eye never moves; only the lids do.
- **Time, not frames:** all durations in milliseconds, interpolation by delta time. Frame rate depends on how much of the screen changes (see «SPI display limits»); animations never slow down because of it.
- **Mouth in Speaking:** driven by audio loudness (RMS every \~30 ms with smoothing), no phoneme sync.

### SPI display limits (3.5\")

SPI is the bottleneck: a full 480×320 frame in 16-bit color is \~300 KB, so full-screen refresh gives only \~13 fps at 32 MHz SPI and \~19 fps at 48 MHz. Smoothness comes from updating only the part of the screen that changed each frame.

- **Driver:** luma.lcd (ili9488) is the confirmed working driver for this hardware. It sends the full frame via `display()` call. For higher frame rates, dirty-rectangle optimisation can be added by rendering only changed regions and blitting them manually via luma's `draw` interface.
- **Black background helps:** in most emotions only the eyes (two \~150×140 px areas) and the mouth change, about 20–25% of the screen. Target a steady 25–30 fps.
- **Full-screen effects are expensive.** The red background pulse in Angry changes the whole screen every frame. Fix: use a static dark-red background #3A0000 instead of pulsing, or limit the glow to an ellipse around the eyes.
- **Color depth:** these displays usually run in RGB565, so smooth glow gradients can band. Keep the glow short (blur 8–12 px) and add light dithering to the cached glow surfaces if needed.
- **Moving effects** (tears, formulas, hearts, «z z z»): draw as small sprites and update only their rectangles, old and new positions.

## 2. Emotions

Six emotions from the reference image, adjusted to the rules: no eyebrows, a mouth in every emotion.

### Happy

- **Eyes:** fully open, bottom lids raised slightly (10% of eye height) for a smiling squint.
- **Pupils:** centered, bright highlights.
- **Mouth:** smile, `width` 70, `curve` +18.
- **Idle animation:** gentle eye «breathing» (scale from center 1.00 ↔ 1.02, 2 s cycle); a short highlight twinkle every 4–6 s.

### Blink

A transition animation, not a full emotion. It plays on top of whatever emotion is current.

- **Eyes:** top and bottom lids meet exactly at y = 160; each eye becomes a horizontal line 110×4 px, #00BFFF with glow.
- **Mouth:** unchanged, kept from the current emotion.
- **Timing:** close 80 ms → hold 50 ms → open 120 ms.
- **Automatic:** randomly every 3–6 s in Neutral, Happy, Thinking.
- **As a standalone Sleep state:** see the Sleep section below.

### Surprised

- **Eyes:** scaled from center to 1.12 with a quick pop (1.0 → 1.18 → 1.12 over 250 ms).
- **Pupils:** smaller (iris R 30, pupil R 14), centered; one highlight per eye.
- **Mouth:** small round «o», `open` = 1, 22 px diameter.
- **Extra:** on entering the emotion, 3 small spark rays flash beside the eyes (#00BFFF, 200 ms).
- **No eyebrows** (the reference had them; they are removed).

### Sad

- **Eyes:** top lids lowered to 35% of eye height; lid line tilted with the outer corner lower than the inner (≈10°).
- **Pupils:** shifted down by +12 px.
- **Outline:** dimmed (#00BFFF at 70% brightness).
- **Mouth:** frown arc, `width` 50, `curve` −12.
- **Tears:** drops #7FDFFF with a white highlight appear under the bottom edge of each eye near the outer corner, run down to y ≈ 300 and fade. One drop per 1.5–2 s, left and right eyes out of sync.
- **Crying mode:** drops more often (every 0.5 s) plus a slight mouth tremble.

### Angry

- **Eyes:** top lids lowered to 40% of eye height, lid line tilted with the inner corner down (≈20°); this creates the angry look without eyebrows.
- **Pupils:** centered, shifted 6 px inward (toward the nose).
- **Color:** outline and glow #FF2200, stronger glow (blur \~18 px); sclera slightly pink #FFE8E4. Iris stays blue, or optionally turns red #FF4422.
- **Background:** static dark-red #3A0000 (no pulsing — saves SPI bandwidth). Radial gradient is optional but not required.
- **Mouth:** clenched zigzag line (4 teeth), `width` 60. The reference had no mouth; it is added.
- **Idle animation:** every 2–3 s a short horizontal shake of the eyes ±2 px (vertical never changes).

### Thinking

- **Eyes:** left eye open normally; right eye squinted, bottom lid raised to 30% of eye height.
- **Pupils:** both look up-right, offset (+14, −14).
- **Mouth:** short straight line shifted sideways (center x = 255), `width` 35, slightly tilted, a «hmm» expression. The reference had no mouth; it is added.
- **Formulas:** above the eyes (zone y = 30–90, clear of the eyes) symbols appear: `π`, `∑`, `x²`, `√`, `∫`, `?`, `E=mc²`. Color #00BFFF at 60% opacity, size 16–22 px. Each symbol fades in, rises 15–20 px and fades out over 1.5–2 s; 2–4 symbols on screen at once.
- **Idle animation:** every 2 s the pupils drift slightly within the upper-right zone (±3 px).

### Additional emotions

Five states beyond the reference. Listening and Speaking are service states of a voice agent: switch them on automatically when AIKO is recording the mic and when it is talking.

### Love

- **Eyes:** fully open, bottom lids raised 10% (as in Happy).
- **Pupils:** iris and pupil replaced by a heart (≈70×64 px), color #FF4FA3 with pink glow; the white highlight stays in the heart's upper-left. Transition: the iris circle morphs into the heart over 350 ms.
- **Pulse:** hearts pulse from center 1.00 → 1.10 → 1.00 with a double beat, like a heartbeat (\~70 bpm).
- **Mouth:** soft smile, `width` 60, `curve` +14.
- **Blush:** two pink ovals 40×14 px (#FF4FA3, 35% opacity) under the eyes at (120, 228) and (360, 228).
- **Extra:** small hearts (10–16 px) float up beside the eyes and fade over 1.5 s; 1–3 hearts at once.

### Confused

- **Eyes:** asymmetric: left eye open and slightly enlarged (scale from center 1.08); right eye squinted, top lid lowered 25%, tilted 8°.
- **Pupils:** looking different ways: left (−10, −8), right (+8, +6). Every 2 s they slowly swap directions («searching for an answer»).
- **Mouth:** wavy line (sine wave, 2 periods, 5 px amplitude), `width` 55; the wave slowly travels along the line.
- **Extra:** a «?» 28 px, #00BFFF above the right eye (≈(370, 70)); it pops in and sways ±8° on a 1.5 s cycle.

### Sleep

- **Eyes:** fully closed, as in Blink: a 110×4 px line at y = 160, but the outline dimmed to 40% brightness.
- **Breathing:** the line glow pulses 40% ↔ 60% on a 4 s cycle.
- **Mouth:** small oval, openness breathes in sync: `open` 0.3 ↔ 0.5, width 18 px.
- **Extra:** «z z z» drift from the right eye up and to the right (start ≈(380, 110)), sizes 14 / 18 / 22 px, each letter appears in turn and fades; 3 s cycle.
- **Transitions:** falling asleep is slow (lids close over 1.2 s); waking is fast (300 ms) followed by one blink.

### Listening

Active while AIKO records the user's voice.

- **Eyes:** open, slightly enlarged (scale from center 1.05), an attentive look.
- **Pupils:** centered; iris widens slightly (R 38 → 41 px). Blinks less often (every 5–8 s).
- **Mouth:** small straight line, `width` 30, `curve` +2.
- **Sound indicator:** 5 vertical bars below the mouth (center (240, 290), 6 px wide, 8 px gap, #00BFFF). Each bar's height, 4–24 px, follows mic loudness; the middle bar is tallest.

### Speaking

Active while AIKO plays its reply. Layered on top of the current emotion: the eyes come from that emotion, only the mouth changes.

- **Eyes:** from the current emotion (default Neutral or Happy).
- **Mouth:** oval; openness `open` 0 → 0.8 follows audio loudness (RMS every \~30 ms, \~60 ms smoothing so the mouth doesn't jitter). Width 40–50 px; in silence the mouth closes to a line over 120 ms.
- **Extra:** every few sentences a light pupil nod down and up by 4 px (emphasis); blinks more often in pauses between phrases.

## 3. Parameter summary

Eyelid values are percentages of eye height; pupil offsets are pixels from the eye center.

| Emotion | Top lid | Bottom lid | Lid tilt | Pupils (x, y) | Eye scale | Outline color | Mouth | Extra |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Neutral | 0% | 0% | 0° | (0, 0) | 1.0 | #00BFFF | curve +4 | — |
| Happy | 0% | 10% | 0° | (0, 0) | 1.0–1.02 | #00BFFF | curve +18 | highlight twinkle |
| Blink | 50% | 50% | 0° | — | 1.0 | #00BFFF | unchanged | — |
| Surprised | 0% | 0% | 0° | (0, 0), smaller | 1.12 | #00BFFF | round «o» | sparks |
| Sad | 35% | 0% | outer down 10° | (0, +12) | 1.0 | #00BFFF 70% | curve −12 | tears |
| Angry | 40% | 0% | inner down 20° | (±6 inward, 0) | 1.0 | #FF2200 | zigzag | static bg #3A0000, shake |
| Thinking | 0% | L 0% / R 30% | 0° | (+14, −14) | 1.0 | #00BFFF | sideways line | formulas |
| Love | 0% | 10% | 0° | hearts centered | 1.0 | #00BFFF, hearts #FF4FA3 | curve +14 | pulse, blush, hearts |
| Confused | L 0% / R 25% | 0% | R 8° | L (−10, −8), R (+8, +6) | L 1.08 / R 1.0 | #00BFFF | wavy line | «?» sign |
| Sleep | 50% | 50% | 0° | — | 1.0 | #00BFFF 40% | oval, open 0.3–0.5 | breathing, «z z z» |
| Listening | 0% | 0% | 0° | (0, 0), wider iris | 1.05 | #00BFFF | line width 30 | loudness bars |
| Speaking | from emotion | from emotion | from emotion | from emotion | from emotion | from emotion | oval, open 0–0.8 from audio | emphasis nods |
