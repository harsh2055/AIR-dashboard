class GestureDetector:
    def __init__(self, hand_detector):
        self.detector = hand_detector

    def get_gesture(self, lmList):
        """Returns a string label for the detected gesture based on hand landmarks."""
        if len(lmList) == 0:
            return "None"
        
        fingers = self.detector.fingers_up()
        
        # Check Pinch first (Thumb and Index close)
        length, _, _ = self.detector.find_distance(4, 8, draw=False)
        if length < 40:
            return "Pinch"

        # Check standard gestures
        if fingers == [1, 1, 1, 1, 1]:
            return "Open Palm"
        elif fingers == [0, 0, 0, 0, 0]:
            return "Fist"
        elif fingers == [0, 1, 1, 0, 0]:
            return "Peace"
        elif fingers == [1, 0, 0, 0, 0] or fingers == [1, 0, 0, 0, 1]:  
            return "Thumbs Up"
        
        return "Unknown"
