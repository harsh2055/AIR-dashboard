# ✦ Aether Gesture Platform v3.1

**Production-grade hand-gesture interaction system — now with Air Whiteboard!**

Draw in mid-air, control your OS with gestures, and build custom gesture apps — all from a standard webcam.

---

## 🎨 NEW: Air Whiteboard

The flagship feature of v3.1. Draw anything in the air using just your hand and a webcam.

### Run it (Python)
```bash
pip install -r requirements.txt
python air_whiteboard.py
```

### Run it (Browser)
```bash
cd web_version
python -m http.server 8000
# Open http://localhost:8000
```

### ✋ Gesture Controls

| Gesture | Action |
|---|---|
| ☝️ **Point** (index up) | Move cursor |
| 🤏 **Pinch** (thumb + index close) | **Draw** a stroke |
| ✊ **Fist** (hold 1 second) | **Clear** entire canvas |
| 👍 **Thumbs Up** | **Undo** last stroke |
| ✌️ **Peace Sign** | **Cycle** to next color |
| 🖐 **Open Palm** | Hover / pause |

### ⌨️ Keyboard Shortcuts (Python app)

| Key | Action |
|---|---|
| `Q` / `ESC` | Quit |
| `Z` | Undo |
| `C` | Clear canvas |
| `E` | Toggle eraser |
| `S` | Save screenshot |
| `1`–`9`, `0` | Select color |
| `+` / `-` | Brush size |
| `H` | Toggle HUD |
| `V` | Toggle camera feed |

---

## 🚀 Full Platform (v3.0+)

The core platform (`main.py`) turns your webcam into a full OS controller:

```bash
python main.py
```

| Gesture | Action |
|---|---|
| Point | Mouse move |
| Pinch | Left click |
| Fist | Drag & drop |
| Peace | Scroll |
| Thumbs Up | Right click |
| Swipe L/R | Prev / next slide |

---

## 📦 Installation

```bash
# Clone / unzip the project
pip install -r requirements.txt

# Or install as a package
pip install -e .

# Then run from anywhere:
aether-whiteboard    # Air Whiteboard (Python)
aether               # Full gesture OS controller
```

**Windows users** (volume control):
```bash
pip install pycaw comtypes
```

---

## 🧠 Train Custom Gestures

```bash
# 1. Collect 100 samples for your gesture
python scripts/collect_data.py my_gesture

# 2. Train the Random Forest model
python ml/train.py

# 3. The model auto-loads next time you run main.py
```

---

## 🏗 Project Structure

```
aether/
├── air_whiteboard.py        ← 🆕 Air Whiteboard (Python)
├── main.py                  ← Full gesture OS controller
├── app.py                   ← Simple single-hand demo
├── web_version/
│   ├── index.html           ← 🆕 Air Whiteboard (Browser)
│   ├── app.js               ← Gesture engine + drawing logic
│   └── style.css            ← Premium dark UI
├── core/
│   ├── hand_detector.py     ← MediaPipe wrapper
│   ├── gesture_recognizer.py← Rule-based recognizer
│   ├── event_engine.py      ← Pub-sub, smoothing, swipe
│   ├── action_mapper.py     ← Plugin loader (config.json)
│   ├── system_controller.py ← OS actions
│   └── utils.py             ← 🆕 Platform helpers (fixed)
├── ml/
│   ├── classifier.py        ← Random Forest wrapper
│   └── train.py             ← Training script
├── scripts/
│   └── collect_data.py      ← Data collection tool
├── requirements.txt         ← Updated with versions
└── setup.py                 ← Fixed CLI entry points
```

---

## 🔧 What's New in v3.1

- **Air Whiteboard** — browser + Python apps with full gesture drawing
- **Fixed `core/utils.py`** — missing file that caused import errors
- **Fixed `setup.py`** — `aether-whiteboard` and `aether` CLI commands now work
- **Updated `requirements.txt`** — pinned versions, optional Windows deps
- **Upgraded web UI** — dark theme, event log, confidence bar, settings modal, save to PNG
- **Gesture debouncing** — no accidental triggers when holding gestures

---

## 📄 License

MIT © Aether Team
