'use strict';

// ── Canvas setup ─────────────────────────────────────────────
const camCanvas   = document.getElementById('camCanvas');
const drawCanvas  = document.getElementById('drawCanvas');
const camCtx      = camCanvas.getContext('2d');
const drawCtx     = drawCanvas.getContext('2d');
const videoEl     = document.getElementById('inputVideo');
const canvasArea  = document.getElementById('canvasArea');

function resizeCanvases() {
    const w = canvasArea.clientWidth;
    const h = canvasArea.clientHeight;
    [camCanvas, drawCanvas].forEach(c => { c.width = w; c.height = h; });
}
resizeCanvases();
window.addEventListener('resize', () => { resizeCanvases(); redrawAllStrokes(); });

// ── State ─────────────────────────────────────────────────────
const state = {
    mode: 'draw',            // 'draw' | 'erase'
    color: '#ffffff',
    brushSize: 6,
    opacity: 1.0,
    isDrawing: false,
    lastX: 0, lastY: 0,
    smoothX: 0, smoothY: 0,
    smoothFactor: 5,
    pinchThreshold: 45,
    showCam: true,
    showSkeleton: true,
    strokes: [],             // [{color, size, opacity, points:[{x,y}]}]
    currentStroke: null,
    colorIdx: 0,
    lastGesture: '',
    gestureHistory: [],
    historySize: 8,
    handCount: 0,
    fistHeld: false,
    fistTimer: null,
    thumbsHeld: false,
    peaceHeld: false,
    gestureDebounce: {},
};

const COLORS = ['#ffffff','#f87171','#fb923c','#facc15','#4ade80','#22d3ee','#60a5fa','#a78bfa','#f472b6','#000000'];

// ── Gesture recognition ──────────────────────────────────────
function recognizeGesture(lms) {
    const tips   = [8, 12, 16, 20];
    const pips   = [6, 10, 14, 18];
    
    // Robust curl detection: tip is further from wrist than PIP
    const fingers = tips.map((t, i) => {
        const tipDist = Math.hypot(lms[t].x - lms[0].x, lms[t].y - lms[0].y);
        const pipDist = Math.hypot(lms[pips[i]].x - lms[0].x, lms[pips[i]].y - lms[0].y);
        return tipDist > pipDist ? 1 : 0;
    });

    const pinchDist = Math.hypot(lms[4].x - lms[8].x, lms[4].y - lms[8].y) * camCanvas.width;
    const thumbUp   = lms[4].y < lms[3].y;
    const sum = fingers.reduce((a, b) => a + b, 0);

    // Dynamic threshold based on hand distance (palm size)
    const palmSize = Math.hypot(lms[0].x - lms[9].x, lms[0].y - lms[9].y) * camCanvas.width;
    const dynamicThreshold = state.pinchThreshold * (palmSize / 100);

    // If pinch distance is small, it's a pinch. Period.
    if (pinchDist < dynamicThreshold) {
        return { name: 'Pinch', conf: mapConf(pinchDist, 0, dynamicThreshold), icon: '🤏' };
    }

    if (sum === 4 && thumbUp)  return { name: 'OpenPalm', conf: 0.95, icon: '🖐' };
    if (sum === 0 && !thumbUp) return { name: 'Fist',     conf: 0.95, icon: '✊' };
    if (fingers[0] === 1 && sum === 2 && fingers[1] === 1) return { name: 'Peace',    conf: 0.9, icon: '✌️' };
    if (sum === 0 && thumbUp)  return { name: 'ThumbsUp', conf: 0.9, icon: '👍' };
    if (fingers[0] === 1 && sum === 1) return { name: 'Point',  conf: 0.85, icon: '☝️' };

    return { name: 'Unknown', conf: 0.3, icon: '❓' };
}

function mapConf(val, lo, hi) {
    return 1 - Math.min(1, Math.max(0, (val - lo) / (hi - lo)));
}

// Temporal smoothing — majority vote
function smoothedGesture(raw) {
    state.gestureHistory.push(raw.name);
    if (state.gestureHistory.length > state.historySize) state.gestureHistory.shift();
    const freq = {};
    let best = raw.name, bestN = 0;
    state.gestureHistory.forEach(g => {
        freq[g] = (freq[g] || 0) + 1;
        if (freq[g] > bestN) { bestN = freq[g]; best = g; }
    });
    return best;
}

// ── Drawing logic ─────────────────────────────────────────────
function startStroke(x, y) {
    state.currentStroke = {
        color: state.mode === 'erase' ? '#000000' : state.color,
        size:  state.mode === 'erase' ? state.brushSize * 6 : state.brushSize,
        opacity: state.mode === 'erase' ? 1 : state.opacity,
        erase: state.mode === 'erase',
        points: [{ x, y }],
    };
    state.isDrawing = true;
}

function continueStroke(x, y) {
    if (!state.isDrawing || !state.currentStroke) return;
    state.currentStroke.points.push({ x, y });
    renderLastSegment(state.currentStroke);
}

function endStroke() {
    if (!state.isDrawing || !state.currentStroke) return;
    if (state.currentStroke.points.length > 1) {
        state.strokes.push(state.currentStroke);
        document.getElementById('statStrokes').textContent = state.strokes.length;
    }
    state.currentStroke = null;
    state.isDrawing = false;
}

function renderLastSegment(stroke) {
    const pts = stroke.points;
    if (pts.length < 2) return;
    const p1 = pts[pts.length - 2];
    const p2 = pts[pts.length - 1];

    drawCtx.globalCompositeOperation = stroke.erase ? 'destination-out' : 'source-over';
    drawCtx.globalAlpha = stroke.opacity;
    drawCtx.strokeStyle = stroke.color;
    drawCtx.lineWidth = stroke.size;
    drawCtx.lineCap = 'round';
    drawCtx.lineJoin = 'round';

    drawCtx.beginPath();
    drawCtx.moveTo(p1.x, p1.y);
    drawCtx.lineTo(p2.x, p2.y);
    drawCtx.stroke();
    drawCtx.globalCompositeOperation = 'source-over';
    drawCtx.globalAlpha = 1;
}

function redrawAllStrokes() {
    drawCtx.clearRect(0, 0, drawCanvas.width, drawCanvas.height);
    state.strokes.forEach(stroke => {
        if (stroke.points.length < 2) return;
        drawCtx.globalCompositeOperation = stroke.erase ? 'destination-out' : 'source-over';
        drawCtx.globalAlpha = stroke.opacity;
        drawCtx.strokeStyle = stroke.color;
        drawCtx.lineWidth  = stroke.size;
        drawCtx.lineCap    = 'round';
        drawCtx.lineJoin   = 'round';
        drawCtx.beginPath();
        drawCtx.moveTo(stroke.points[0].x, stroke.points[0].y);
        for (let i = 1; i < stroke.points.length; i++) {
            drawCtx.lineTo(stroke.points[i].x, stroke.points[i].y);
        }
        drawCtx.stroke();
        drawCtx.globalCompositeOperation = 'source-over';
        drawCtx.globalAlpha = 1;
    });
}

function undo() {
    if (!state.strokes.length) return;
    state.strokes.pop();
    redrawAllStrokes();
    document.getElementById('statStrokes').textContent = state.strokes.length;
    logEvent('↩ Undo last stroke', 'ev-undo');
    showToast('Stroke undone');
}

function clearCanvas() {
    state.strokes = [];
    drawCtx.clearRect(0, 0, drawCanvas.width, drawCanvas.height);
    document.getElementById('statStrokes').textContent = '0';
    logEvent('🗑 Canvas cleared', 'ev-clear');
    showToast('Canvas cleared');
    // Flash overlay
    const flash = document.createElement('div');
    flash.className = 'clear-flash';
    canvasArea.appendChild(flash);
    setTimeout(() => flash.remove(), 400);
}

// ── Cursor ───────────────────────────────────────────────────
const cursorRing = document.getElementById('cursorRing');

function moveCursor(x, y) {
    state.smoothX = state.smoothX + (x - state.smoothX) / state.smoothFactor;
    state.smoothY = state.smoothY + (y - state.smoothY) / state.smoothFactor;
    cursorRing.style.left = state.smoothX + 'px';
    cursorRing.style.top  = state.smoothY + 'px';
    cursorRing.classList.add('visible');
}

// ── MediaPipe onResults ───────────────────────────────────────
let lastFrameTime = performance.now();

function onResults(results) {
    const now = performance.now();
    const fps = Math.round(1000 / (now - lastFrameTime));
    lastFrameTime = now;
    document.getElementById('fpsBadge').textContent = fps + ' FPS';

    // Draw camera frame
    camCtx.save();
    camCtx.clearRect(0, 0, camCanvas.width, camCanvas.height);

    if (state.showCam) {
        camCtx.save();
        camCtx.scale(-1, 1); // mirror
        camCtx.drawImage(results.image, -camCanvas.width, 0, camCanvas.width, camCanvas.height);
        camCtx.restore();
    } else {
        camCtx.fillStyle = '#0a0c10';
        camCtx.fillRect(0, 0, camCanvas.width, camCanvas.height);
    }

    const hands = results.multiHandLandmarks || [];
    document.getElementById('statHands').textContent = hands.length;

    if (hands.length === 0) {
        endStroke();
        cursorRing.classList.remove('visible');
        updateGestureUI({ name: 'None', conf: 0, icon: '—' });
        document.getElementById('gestureDot').className = 'gesture-dot';
        document.getElementById('gestureLabel').textContent = 'No hand detected';
        state.lastGesture = '';
    } else {
        document.getElementById('camOff').style.display = 'none';

        const lms = hands[0].map(lm => ({ ...lm, x: 1 - lm.x }));

        // Draw skeleton on camCanvas
        if (state.showSkeleton) {
            try {
                drawConnectors(camCtx, lms, HAND_CONNECTIONS,
                    { color: 'rgba(88,166,255,0.6)', lineWidth: 2 });
                drawLandmarks(camCtx, lms,
                    { color: '#ffffff', lineWidth: 1, radius: 3 });
            } catch(e) {}
        }

        // Map landmark 8 (index tip) to canvas coords
        const raw = {
            x: lms[8].x * camCanvas.width,
            y: lms[8].y * camCanvas.height,
        };

        moveCursor(raw.x, raw.y);

        const gesture  = recognizeGesture(lms);
        const smoothed = smoothedGesture(gesture);
        const conf     = gesture.conf;

        updateGestureUI({ name: smoothed, conf, icon: gesture.icon });
        handleGestureActions(smoothed, raw.x, raw.y);
        state.lastGesture = smoothed;
    }

    camCtx.restore();
}

// ── Gesture → Actions ─────────────────────────────────────────
function handleGestureActions(gesture, x, y) {
    const dot = document.getElementById('gestureDot');

    if (gesture === 'Pinch') {
        dot.className = 'gesture-dot drawing';
        cursorRing.className = 'visible drawing';
        if (!state.isDrawing) startStroke(x, y);
        else continueStroke(x, y);
        state.fistHeld = false;
        state.thumbsHeld = false;
        state.peaceHeld = false;
    } else {
        if (state.isDrawing) endStroke();
        cursorRing.className = 'visible' + (state.mode === 'erase' ? ' erasing' : '');
        dot.className = 'gesture-dot active';
    }

    // Fist → clear (hold for 0.8s)
    if (gesture === 'Fist') {
        if (!state.fistHeld) {
            state.fistHeld = true;
            state.fistTimer = setTimeout(() => {
                if (state.fistHeld) clearCanvas();
            }, 800);
        }
    } else {
        state.fistHeld = false;
        clearTimeout(state.fistTimer);
    }

    // ThumbsUp → undo (debounced)
    if (gesture === 'ThumbsUp') {
        if (!state.thumbsHeld) {
            state.thumbsHeld = true;
            undo();
        }
    } else {
        state.thumbsHeld = false;
    }

    // Peace → next color (debounced)
    if (gesture === 'Peace') {
        if (!state.peaceHeld) {
            state.peaceHeld = true;
            cycleColor();
        }
    } else {
        state.peaceHeld = false;
    }
}

// ── UI updates ────────────────────────────────────────────────
const gestureIcons = {
    Pinch: '🤏', Fist: '✊', OpenPalm: '🖐', Peace: '✌️',
    ThumbsUp: '👍', Point: '☝️', Unknown: '❓', None: '—',
};

function updateGestureUI({ name, conf }) {
    document.getElementById('gestureLabel').textContent =
        name === 'None' ? 'No hand detected' : `Gesture: ${name}`;
    document.getElementById('statGesture').textContent = name;
    document.getElementById('statConf').textContent = name === 'None' ? '—' : Math.round(conf * 100) + '%';

    const bar = document.getElementById('confBar');
    bar.style.width = Math.round(conf * 100) + '%';
    bar.style.background = conf > 0.7 ? 'var(--success)' : conf > 0.4 ? 'var(--warning)' : 'var(--danger)';
}

function cycleColor() {
    state.colorIdx = (state.colorIdx + 1) % COLORS.length;
    state.color = COLORS[state.colorIdx];
    // Update UI
    document.querySelectorAll('.color-swatch').forEach((s, i) => {
        s.classList.toggle('active', i === state.colorIdx);
        if (i === state.colorIdx) {
            s.classList.add('ping');
            setTimeout(() => s.classList.remove('ping'), 300);
        }
    });
    logEvent('🎨 Color → ' + state.color, 'ev-color');
    showToast('Color changed');
}

// ── Event log ─────────────────────────────────────────────────
function logEvent(msg, cls = '') {
    const ul = document.getElementById('eventLog');
    const li = document.createElement('li');
    const t  = new Date().toLocaleTimeString('en', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    li.textContent = `${t} ${msg}`;
    if (cls) li.className = cls;
    ul.prepend(li);
    while (ul.children.length > 12) ul.lastChild.remove();
}

// ── Toast ─────────────────────────────────────────────────────
let toastTimer;
function showToast(msg) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove('show'), 2000);
}

// ── Toolbar bindings ──────────────────────────────────────────
document.querySelectorAll('[data-mode]').forEach(btn => {
    btn.addEventListener('click', () => {
        state.mode = btn.dataset.mode;
        document.querySelectorAll('[data-mode]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById('statMode').textContent = state.mode === 'erase' ? 'Erase' : 'Draw';
    });
});

document.querySelectorAll('.color-swatch').forEach((swatch, idx) => {
    swatch.addEventListener('click', () => {
        state.color = swatch.dataset.color;
        state.colorIdx = idx;
        document.querySelectorAll('.color-swatch').forEach(s => s.classList.remove('active'));
        swatch.classList.add('active');
    });
});

const brushSlider = document.getElementById('brushSize');
brushSlider.addEventListener('input', () => {
    state.brushSize = +brushSlider.value;
    document.getElementById('brushSizeLabel').textContent = brushSlider.value;
});

const opacitySlider = document.getElementById('opacity');
opacitySlider.addEventListener('input', () => {
    state.opacity = +opacitySlider.value / 100;
    document.getElementById('opacityLabel').textContent = opacitySlider.value + '%';
});

document.getElementById('undoBtn').addEventListener('click', undo);
document.getElementById('clearBtn').addEventListener('click', clearCanvas);
document.getElementById('saveBtn').addEventListener('click', () => {
    // Composite cam + draw
    const out = document.createElement('canvas');
    out.width  = camCanvas.width;
    out.height = camCanvas.height;
    const ctx = out.getContext('2d');
    ctx.drawImage(camCanvas,  0, 0);
    ctx.drawImage(drawCanvas, 0, 0);
    const a = document.createElement('a');
    a.download = 'aether-drawing-' + Date.now() + '.png';
    a.href = out.toDataURL();
    a.click();
    showToast('Drawing saved!');
    logEvent('💾 Image saved');
});

// Keyboard shortcuts
document.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'z') undo();
    if ((e.ctrlKey || e.metaKey) && e.key === 'Delete') clearCanvas();
    if (e.key === 'e') document.getElementById('btn-erase').click();
    if (e.key === 'd') document.getElementById('btn-draw').click();
});

// ── Modals ────────────────────────────────────────────────────
function openModal(id) { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }

document.getElementById('helpBtn').addEventListener('click', () => openModal('helpModal'));
document.getElementById('helpClose').addEventListener('click', () => closeModal('helpModal'));
document.getElementById('helpStart').addEventListener('click', () => closeModal('helpModal'));

document.getElementById('settingsBtn').addEventListener('click', () => openModal('settingsModal'));
document.getElementById('settingsClose').addEventListener('click', () => closeModal('settingsModal'));

document.getElementById('setPinchThresh').addEventListener('input', function() {
    document.getElementById('setPinchVal').textContent = this.value;
});
document.getElementById('setSmooth').addEventListener('input', function() {
    document.getElementById('setSmoothVal').textContent = this.value;
});

document.getElementById('settingsSave').addEventListener('click', () => {
    state.pinchThreshold = +document.getElementById('setPinchThresh').value;
    state.smoothFactor   = +document.getElementById('setSmooth').value;
    state.showCam        = document.getElementById('setShowCam').checked;
    state.showSkeleton   = document.getElementById('setShowSkeleton').checked;
    closeModal('settingsModal');
    showToast('Settings saved');
});

// Close modal on backdrop click
document.querySelectorAll('.modal-backdrop').forEach(bd => {
    bd.addEventListener('click', e => {
        if (e.target === bd) bd.classList.remove('open');
    });
});

// ── MediaPipe setup ───────────────────────────────────────────
const hands = new Hands({
    locateFile: f => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${f}`
});

hands.setOptions({
    maxNumHands: 1,
    modelComplexity: 1,
    minDetectionConfidence: 0.7,
    minTrackingConfidence: 0.6,
});

hands.onResults(onResults);

const camera = new Camera(videoEl, {
    onFrame: async () => { await hands.send({ image: videoEl }); },
    width: 1280, height: 720
});

camera.start().then(() => {
    document.getElementById('camOff').style.display = 'none';
    logEvent('📷 Camera started');
    openModal('helpModal');
}).catch(err => {
    document.getElementById('camOff').querySelector('p').textContent = 'Camera access denied';
    document.getElementById('camOff').querySelector('.sub').textContent = 'Please allow camera access and reload.';
    console.error(err);
});

logEvent('✦ Aether Air Whiteboard ready');
