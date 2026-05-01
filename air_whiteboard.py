"""
Aether Air Whiteboard — Python (OpenCV + MediaPipe)
====================================================
Draw in the air with your webcam!

Gesture Controls:
  ☝️  Point (index up)   → move cursor
  🤏  Pinch               → draw stroke
  ✊  Fist (hold 1s)      → clear canvas
  👍  Thumbs up           → undo last stroke
  ✌️  Peace sign          → cycle to next color
  🖐   Open palm           → hover / pause drawing

Keyboard shortcuts:
  Q / ESC    quit
  C          clear canvas
  Z          undo
  E          toggle eraser
  S          save screenshot
  1-9        select color
  +/-        brush size
"""

import cv2
import numpy as np
import mediapipe as mp
import time
import os
from collections import deque
from datetime import datetime


# ── Palette ───────────────────────────────────────────────────
COLORS_BGR = [
    (255, 255, 255),  # 1 white
    (113, 113, 248),  # 2 red
    (60,  147, 251),  # 3 orange
    (21,  204, 250),  # 4 yellow
    (128, 222,  74),  # 5 green
    (238, 211,  34),  # 6 cyan
    (250, 165,  96),  # 7 blue
    (250, 139, 167),  # 8 violet
    (180, 114, 244),  # 9 pink
    (0,     0,   0),  # 0 black
]

COLOR_NAMES = ['White','Red','Orange','Yellow','Green','Cyan','Blue','Violet','Pink','Black']


class HandDetector:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.mp_draw  = mp.solutions.drawing_utils
        self.mp_styles = mp.solutions.drawing_styles
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            model_complexity=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.6,
        )
        self.results = None

    def process(self, frame_rgb):
        self.results = self.hands.process(frame_rgb)
        return self.results

    def draw_skeleton(self, frame):
        if self.results and self.results.multi_hand_landmarks:
            for hlm in self.results.multi_hand_landmarks:
                self.mp_draw.draw_landmarks(
                    frame, hlm, self.mp_hands.HAND_CONNECTIONS,
                    self.mp_draw.DrawingSpec(color=(88, 166, 255), thickness=2, circle_radius=3),
                    self.mp_draw.DrawingSpec(color=(200, 200, 255), thickness=2),
                )
        return frame

    def get_landmarks(self, frame_w, frame_h):
        if not (self.results and self.results.multi_hand_landmarks):
            return None
        hlm = self.results.multi_hand_landmarks[0]
        lms = []
        for lm in hlm.landmark:
            lms.append((int(lm.x * frame_w), int(lm.y * frame_h), lm.x, lm.y))
        return lms  # list of (px, py, nx, ny)


class GestureRecognizer:
    TIP_IDS   = [8, 12, 16, 20]
    BASE_IDS  = [6, 10, 14, 18]

    def __init__(self, pinch_threshold=40, history_size=8):
        self.pinch_threshold = pinch_threshold
        self.history = deque(maxlen=history_size)

    def recognize(self, lms, frame_w):
        """Returns (gesture_name, confidence)."""
        if not lms:
            return 'None', 0.0

        # Robust curl detection: tip is further from wrist than PIP
        fingers = []
        for i in range(4):
            tip_idx = self.TIP_IDS[i]
            pip_idx = self.BASE_IDS[i]
            tip_dist = np.hypot(lms[tip_idx][0] - lms[0][0], lms[tip_idx][1] - lms[0][1])
            pip_dist = np.hypot(lms[pip_idx][0] - lms[0][0], lms[pip_idx][1] - lms[0][1])
            fingers.append(1 if tip_dist > pip_dist else 0)

        thumb_up = lms[4][0] < lms[3][0]  # thumb tip x < thumb IP x (mirrored)
        f_sum = sum(fingers)

        # Dynamic threshold based on hand distance (palm size)
        palm_dx = (lms[0][2] - lms[9][2]) * frame_w
        palm_dy = (lms[0][3] - lms[9][3]) * frame_w
        palm_size = np.hypot(palm_dx, palm_dy)
        dynamic_threshold = self.pinch_threshold * (palm_size / 100.0)

        # Pinch distance in pixels
        dx = (lms[4][2] - lms[8][2]) * frame_w
        dy = (lms[4][3] - lms[8][3]) * frame_w
        pinch_dist = np.hypot(dx, dy)

        # If pinch distance is small, it's a pinch. Period.
        if pinch_dist < dynamic_threshold:
            conf = 1.0 - pinch_dist / dynamic_threshold
            return 'Pinch', float(np.clip(conf, 0, 1))

        if f_sum == 4 and thumb_up:           return 'OpenPalm', 0.95
        if f_sum == 0 and not thumb_up:       return 'Fist',     0.95
        if fingers[0] and fingers[1] and f_sum == 2:
                                               return 'Peace',    0.90
        if f_sum == 0 and thumb_up:           return 'ThumbsUp', 0.90
        if fingers[0] and f_sum == 1:         return 'Point',    0.85

        return 'Unknown', 0.30

    def smooth(self, gesture):
        self.history.append(gesture)
        freq = {}
        best, best_n = gesture, 0
        for g in self.history:
            freq[g] = freq.get(g, 0) + 1
            if freq[g] > best_n:
                best_n = freq[g]
                best = g
        return best


class AirWhiteboard:
    SAVE_DIR = 'drawings'

    def __init__(self, cam_index=0, width=1280, height=720):
        self.W, self.H = width, height
        self.cap = cv2.VideoCapture(cam_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  self.W)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.H)

        self.detector   = HandDetector()
        self.recognizer = GestureRecognizer(pinch_threshold=40)

        # Drawing state
        self.canvas       = np.zeros((self.H, self.W, 3), dtype=np.uint8)
        self.strokes      = []  # list of stroke dicts {color, size, points}
        self.cur_stroke   = None
        self.is_drawing   = False
        self.eraser_mode  = False
        self.color_idx    = 0
        self.brush_size   = 8
        self.show_cam     = True
        self.show_hud     = True

        # Cursor smoothing
        self.sx, self.sy  = 0, 0
        self.smoothing    = 5

        # Gesture debounce
        self.fist_start   = None
        self.fist_clear_delay = 0.8
        self.undo_debounce  = 0.0
        self.color_debounce = 0.0

        # FPS
        self.fps_buf = deque(maxlen=30)
        self.ptime   = time.time()

        os.makedirs(self.SAVE_DIR, exist_ok=True)

    # ── Stroke management ─────────────────────────────────────
    def start_stroke(self, x, y):
        color = (0, 0, 0) if self.eraser_mode else COLORS_BGR[self.color_idx]
        size  = self.brush_size * 5 if self.eraser_mode else self.brush_size
        self.cur_stroke = {'color': color, 'size': size,
                           'erase': self.eraser_mode, 'points': [(x, y)]}
        self.is_drawing = True

    def continue_stroke(self, x, y):
        if not self.is_drawing or not self.cur_stroke:
            return
        pts = self.cur_stroke['points']
        pts.append((x, y))
        self._render_segment(self.cur_stroke, pts[-2], pts[-1])

    def end_stroke(self):
        if not self.is_drawing or not self.cur_stroke:
            return
        if len(self.cur_stroke['points']) > 1:
            self.strokes.append(self.cur_stroke)
        self.cur_stroke = None
        self.is_drawing = False

    def _render_segment(self, stroke, p1, p2):
        if stroke['erase']:
            cv2.line(self.canvas, p1, p2, (0, 0, 0), stroke['size'] * 2, cv2.LINE_AA)
        else:
            cv2.line(self.canvas, p1, p2, stroke['color'], stroke['size'], cv2.LINE_AA)

    def undo(self):
        if not self.strokes:
            return
        self.strokes.pop()
        self._redraw_all()

    def _redraw_all(self):
        self.canvas[:] = 0
        for s in self.strokes:
            pts = s['points']
            for i in range(1, len(pts)):
                self._render_segment(s, pts[i-1], pts[i])

    def clear(self):
        self.strokes.clear()
        self.canvas[:] = 0

    def save(self):
        fname = os.path.join(
            self.SAVE_DIR,
            f'aether_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
        )
        # Composite
        out = self.current_frame.copy() if self.show_cam else \
              np.zeros((self.H, self.W, 3), dtype=np.uint8)
        cv2.addWeighted(out, 1.0, self.canvas, 1.0, 0, out)
        cv2.imwrite(fname, out)
        print(f'[Aether] Saved → {fname}')
        return fname

    # ── HUD drawing ───────────────────────────────────────────
    def _draw_hud(self, frame, gesture, conf, fps):
        h, w = frame.shape[:2]

        # Top bar background
        cv2.rectangle(frame, (0, 0), (w, 60), (15, 18, 28), -1)
        cv2.line(frame, (0, 60), (w, 60), (40, 50, 70), 1)

        # FPS
        cv2.putText(frame, f'{int(fps)} FPS', (w - 110, 38),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 120, 160), 1, cv2.LINE_AA)

        # Gesture label + confidence bar
        gest_icons = {
            'Pinch': 'DRAWING', 'Fist': 'FIST (clear?)', 'OpenPalm': 'HOVER',
            'Peace': 'PEACE (color)', 'ThumbsUp': 'THUMBS UP (undo)',
            'Point': 'POINT (move)', 'Unknown': 'UNKNOWN', 'None': 'NO HAND',
        }
        label = gest_icons.get(gesture, gesture)
        col   = (74, 222, 128) if gesture == 'Pinch' else \
                (88, 166, 255) if gesture == 'Point'  else (180, 180, 200)
        cv2.putText(frame, label, (14, 38),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, col, 2, cv2.LINE_AA)

        # Confidence bar
        bar_x, bar_y, bar_w, bar_h = 14, 48, 200, 5
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (40, 50, 70), -1)
        fill = int(bar_w * conf)
        bar_col = (74, 222, 128) if conf > 0.7 else (250, 200, 50) if conf > 0.4 else (113, 113, 248)
        if fill > 0:
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill, bar_y + bar_h), bar_col, -1)

        # Bottom HUD
        bh = h - 50
        cv2.rectangle(frame, (0, bh), (w, h), (15, 18, 28), -1)
        cv2.line(frame, (0, bh), (w, bh), (40, 50, 70), 1)

        # Color palette
        px = 14
        for i, c in enumerate(COLORS_BGR):
            x1, y1 = px, bh + 8
            x2, y2 = px + 26, bh + 38
            cv2.rectangle(frame, (x1, y1), (x2, y2), c, -1)
            if i == self.color_idx:
                cv2.rectangle(frame, (x1 - 2, y1 - 2), (x2 + 2, y2 + 2), (255, 255, 255), 2)
            px += 32

        # Mode label
        mode_txt = '🧹 ERASER' if self.eraser_mode else f'✏  {COLOR_NAMES[self.color_idx].upper()}'
        cv2.putText(frame, mode_txt, (px + 10, bh + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 190, 220), 1, cv2.LINE_AA)

        # Stroke count
        cv2.putText(frame, f'Strokes: {len(self.strokes)}', (w - 150, bh + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (100, 120, 160), 1, cv2.LINE_AA)

        # Keyboard hint strip
        hints = 'Q:quit  Z:undo  C:clear  E:eraser  S:save  +/-:size  1-0:color'
        cv2.putText(frame, hints, (14, h - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (60, 70, 90), 1, cv2.LINE_AA)

    def _draw_cursor(self, frame, x, y, gesture):
        if gesture == 'Pinch':
            cv2.circle(frame, (x, y), self.brush_size + 4,  (74, 222, 128), 2, cv2.LINE_AA)
            cv2.circle(frame, (x, y), 3, (74, 222, 128), -1, cv2.LINE_AA)
        elif self.eraser_mode:
            cv2.circle(frame, (x, y), self.brush_size * 5 + 4, (113, 113, 248), 2, cv2.LINE_AA)
        else:
            cv2.circle(frame, (x, y), self.brush_size + 4, (88, 166, 255), 2, cv2.LINE_AA)
            cv2.circle(frame, (x, y), 3, (200, 220, 255), -1, cv2.LINE_AA)

    # ── Main loop ─────────────────────────────────────────────
    def run(self):
        print('\n✦ Aether Air Whiteboard — Python Edition')
        print('─' * 45)
        print('  Pinch to draw  |  Fist (hold) to clear')
        print('  Thumbs Up to undo  |  Peace to cycle color')
        print('  Press Q to quit, S to save')
        print('─' * 45 + '\n')

        cv2.namedWindow('Aether Air Whiteboard', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Aether Air Whiteboard', 1280, 720)

        while True:
            ret, frame = self.cap.read()
            if not ret:
                print('[Aether] Camera read failed — exiting')
                break

            frame = cv2.flip(frame, 1)
            frame = cv2.resize(frame, (self.W, self.H))
            self.current_frame = frame.copy()
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # ── Hand detection ───────────────────────────────
            results = self.detector.process(frame_rgb)
            lms     = self.detector.get_landmarks(self.W, self.H)

            # ── Gesture ──────────────────────────────────────
            raw_gest, conf = self.recognizer.recognize(lms, self.W)
            gesture        = self.recognizer.smooth(raw_gest)

            now = time.time()

            if lms:
                # Cursor position = index fingertip (landmark 8)
                tx, ty = lms[8][0], lms[8][1]
                # Smooth
                self.sx = int(self.sx + (tx - self.sx) / self.smoothing)
                self.sy = int(self.sy + (ty - self.sy) / self.smoothing)

                # ── Pinch → draw ─────────────────────────────
                if gesture == 'Pinch':
                    if not self.is_drawing:
                        self.start_stroke(self.sx, self.sy)
                    else:
                        self.continue_stroke(self.sx, self.sy)
                    self.fist_start = None
                else:
                    self.end_stroke()

                # ── Fist → clear (hold 0.8s) ─────────────────
                if gesture == 'Fist':
                    if self.fist_start is None:
                        self.fist_start = now
                    elif now - self.fist_start >= self.fist_clear_delay:
                        self.clear()
                        self.fist_start = now + 999  # prevent repeat
                        print('[Aether] Canvas cleared by gesture')
                else:
                    self.fist_start = None

                # ── ThumbsUp → undo ───────────────────────────
                if gesture == 'ThumbsUp' and now > self.undo_debounce:
                    self.undo()
                    self.undo_debounce = now + 1.0
                    print('[Aether] Undo')

                # ── Peace → cycle color ───────────────────────
                if gesture == 'Peace' and now > self.color_debounce:
                    self.color_idx = (self.color_idx + 1) % len(COLORS_BGR)
                    self.color_debounce = now + 1.2
                    print(f'[Aether] Color → {COLOR_NAMES[self.color_idx]}')
            else:
                gesture = 'None'
                conf    = 0.0
                self.end_stroke()
                self.fist_start = None

            # ── Compose frame ─────────────────────────────────
            display = frame.copy() if self.show_cam else \
                      np.zeros((self.H, self.W, 3), dtype=np.uint8)

            # Overlay skeleton on display
            if self.show_cam and lms:
                self.detector.draw_skeleton(display)

            # Blend canvas (drawing layer)
            mask = cv2.cvtColor(self.canvas, cv2.COLOR_BGR2GRAY)
            _, mask = cv2.threshold(mask, 1, 255, cv2.THRESH_BINARY)
            display = cv2.bitwise_and(display, display,
                                      mask=cv2.bitwise_not(mask))
            display = cv2.add(display, self.canvas)

            # Draw cursor
            if lms:
                self._draw_cursor(display, self.sx, self.sy, gesture)

            # HUD
            if self.show_hud:
                fps = self._calc_fps()
                self._draw_hud(display, gesture, conf, fps)

            cv2.imshow('Aether Air Whiteboard', display)

            # ── Keyboard ──────────────────────────────────────
            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), 27):          # Q / ESC
                break
            elif key == ord('c'):
                self.clear(); print('[Aether] Canvas cleared')
            elif key == ord('z'):
                self.undo();  print('[Aether] Undo')
            elif key == ord('e'):
                self.eraser_mode = not self.eraser_mode
                print(f'[Aether] Eraser: {self.eraser_mode}')
            elif key == ord('s'):
                fname = self.save()
                print(f'[Aether] Saved: {fname}')
            elif key == ord('h'):
                self.show_hud = not self.show_hud
            elif key == ord('v'):
                self.show_cam = not self.show_cam
            elif ord('1') <= key <= ord('9'):
                self.color_idx = key - ord('1')
            elif key == ord('0'):
                self.color_idx = 9
            elif key == ord('+') or key == ord('='):
                self.brush_size = min(self.brush_size + 2, 60)
            elif key == ord('-'):
                self.brush_size = max(self.brush_size - 2, 2)

        self.cap.release()
        cv2.destroyAllWindows()
        print('[Aether] Goodbye!')

    def _calc_fps(self):
        now = time.time()
        self.fps_buf.append(1.0 / max(now - self.ptime, 1e-9))
        self.ptime = now
        return np.mean(self.fps_buf)


# ── Entry point ───────────────────────────────────────────────
def main():
    wb = AirWhiteboard(cam_index=0)
    wb.run()


if __name__ == '__main__':
    main()
