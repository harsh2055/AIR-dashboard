import cv2
import mediapipe as mp

class HandDetector:
    def __init__(self, mode=False, max_num_hands=2, model_complexity=1, detection_confidence=0.5, tracking_confidence=0.5):
        self.mode = mode
        self.max_hands = max_num_hands
        self.complexity = model_complexity
        self.detection_con = detection_confidence
        self.tracking_con = tracking_confidence

        self.mpHands = mp.solutions.hands
        self.hands = self.mpHands.Hands(self.mode, self.max_hands, self.complexity, 
                                        self.detection_con, self.tracking_con)
        self.mpDraw = mp.solutions.drawing_utils

    def process_frame(self, img, draw=True):
        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.results = self.hands.process(imgRGB)
        
        if self.results.multi_hand_landmarks and draw:
            for handLms in self.results.multi_hand_landmarks:
                # Custom aesthetic drawing
                self.mpDraw.draw_landmarks(img, handLms, self.mpHands.HAND_CONNECTIONS,
                                          self.mpDraw.DrawingSpec(color=(88, 166, 255), thickness=2, circle_radius=2),
                                          self.mpDraw.DrawingSpec(color=(255, 255, 255), thickness=2, circle_radius=1))
        return img

    def get_landmarks(self, img, hand_no=0):
        lmList = []
        center = None
        if self.results.multi_hand_landmarks:
            if len(self.results.multi_hand_landmarks) > hand_no:
                myHand = self.results.multi_hand_landmarks[hand_no]
                h, w, c = img.shape
                x_vals, y_vals = [], []
                for id, lm in enumerate(myHand.landmark):
                    px, py = int(lm.x * w), int(lm.y * h)
                    lmList.append([id, px, py])
                    x_vals.append(px)
                    y_vals.append(py)
                
                # Bounding box and center
                xmin, xmax = min(x_vals), max(x_vals)
                ymin, ymax = min(y_vals), max(y_vals)
                center = ((xmin + xmax) // 2, (ymin + ymax) // 2)
                
        return lmList, center

    def get_multi_landmarks(self, img):
        all_hands = []
        if self.results.multi_hand_landmarks:
            for handLms in self.results.multi_hand_landmarks:
                lmList = []
                x_vals, y_vals = [], []
                h, w, c = img.shape
                for id, lm in enumerate(handLms.landmark):
                    px, py = int(lm.x * w), int(lm.y * h)
                    lmList.append([id, px, py])
                    x_vals.append(px)
                    y_vals.append(py)
                center = ((min(x_vals) + max(x_vals)) // 2, (min(y_vals) + max(y_vals)) // 2)
                all_hands.append({'lmList': lmList, 'center': center})
        return all_hands

    def get_fingers_up(self, lmList):
        if not lmList: return [0,0,0,0,0]
        fingers = []
        # Thumb
        if lmList[4][1] > lmList[3][1]: fingers.append(1)
        else: fingers.append(0)
        # Fingers
        for id in range(1, 5):
            tip = [8, 12, 16, 20][id-1]
            if lmList[tip][2] < lmList[tip - 2][2]: fingers.append(1)
            else: fingers.append(0)
        return fingers
