class GestureRecognizer:
    def __init__(self, hand_detector):
        self.detector = hand_detector

    def get_raw_gesture(self, lmList):
        """Returns a string label for the raw (unfiltered) detected gesture."""
        if len(lmList) == 0:
            return "None"
        
        fingers = self.detector.get_fingers_up()
        
        # Pinch
        length, _ = self.detector.find_distance(4, 8)
        if length < 40:
            return "Pinch"
            
        # Two Hand Zoom (Pinch logic can be extended here if two hands are tracked)
        # Using simple rule-based approach
        if fingers == [1, 1, 1, 1, 1]:
            return "OpenPalm"
        elif fingers == [0, 0, 0, 0, 0]:
            return "Fist"
        elif fingers == [0, 1, 1, 0, 0] or fingers == [1, 1, 1, 0, 0]:
            return "Peace"
        elif fingers == [1, 0, 0, 0, 0] or fingers == [1, 0, 0, 0, 1]:  
            return "ThumbsUp"
        elif fingers == [0, 1, 0, 0, 0] or fingers == [1, 1, 0, 0, 0]:
            return "Point"
        
        return "Unknown"
