import numpy as np
from collections import deque

class EventEngine:
    def __init__(self, buffer_size=8, confidence_threshold=0.7):
        self.history = deque(maxlen=buffer_size)
        self.state = "None"
        self.subscribers = {}
        self.conf_threshold = confidence_threshold
        
        # Multi-hand support
        self.hand_data = {} # {hand_id: {'state': str, 'center': tuple, 'lm': list}}
        
        # Velocity for swipes
        self.prev_center = None

    def subscribe(self, event, callback):
        if event not in self.subscribers:
            self.subscribers[event] = []
        self.subscribers[event].append(callback)

    def emit(self, event, data=None):
        if event in self.subscribers:
            for cb in self.subscribers[event]:
                cb(data)

    def update(self, raw_gesture, confidence, center, lmList):
        """Single hand update with smoothing and confidence check."""
        # 1. Confidence Filter
        if confidence < self.conf_threshold:
            effective_gesture = "None"
        else:
            effective_gesture = raw_gesture

        # 2. Temporal Smoothing (Majority Vote)
        self.history.append(effective_gesture)
        smoothed_gesture = max(set(self.history), key=self.history.count)

        # 3. Dynamic Gesture (Swipe Detection)
        if center and self.prev_center:
            dx = center[0] - self.prev_center[0]
            if abs(dx) > 50: # Speed threshold
                if dx > 0: self.emit("onSwipeRight")
                else: self.emit("onSwipeLeft")
        self.prev_center = center

        # 4. State Transitions
        if smoothed_gesture != self.state:
            if self.state != "None":
                self.emit(f"on{self.state}End")
            
            self.state = smoothed_gesture
            
            if self.state != "None":
                self.emit(f"on{self.state}Start")

        if self.state != "None":
            # Pass lmList for continuous actions (like mouse move or volume)
            self.emit(f"on{self.state}Hold", {"center": center, "lm": lmList})

        return self.state, confidence

    def update_multi(self, hands_results):
        """Advanced Multi-hand event processing."""
        if len(hands_results) == 2:
            h1 = hands_results[0]['center']
            h2 = hands_results[1]['center']
            dist = np.linalg.norm(np.array(h1) - np.array(h2))
            
            # Emit Zoom event based on distance change
            if hasattr(self, 'prev_multi_dist'):
                delta = dist - self.prev_multi_dist
                if abs(delta) > 5:
                    self.emit("onTwoHandZoom", {"delta": delta, "dist": dist})
            self.prev_multi_dist = dist
            
            # Emit Rotate event based on angle
            angle = np.degrees(np.arctan2(h2[1]-h1[1], h2[0]-h1[0]))
            if hasattr(self, 'prev_multi_angle'):
                d_angle = angle - self.prev_multi_angle
                if abs(d_angle) > 2:
                    self.emit("onTwoHandRotate", {"delta": d_angle, "angle": angle})
            self.prev_multi_angle = angle
