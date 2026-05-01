import cv2
import time
import numpy as np
import pyautogui
from hand_detector import HandDetector
from gesture_detector import GestureDetector
from utils import SystemController

def main():
    # Setup Camera
    wCam, hCam = 640, 480
    cap = cv2.VideoCapture(0)
    cap.set(3, wCam)
    cap.set(4, hCam)

    # Initialize Modules
    detector = HandDetector(max_num_hands=1, min_detection_confidence=0.7, min_tracking_confidence=0.7)
    gesture_recognizer = GestureDetector(detector)
    sys_controller = SystemController()

    # Screen dimensions for Mouse Control
    wScr, hScr = pyautogui.size()
    
    # State variables
    pTime = 0
    smooth_x, smooth_y = 0, 0
    volBar, volPer = 400, 0
    click_debounce = 0

    print("Starting interactive hand tracking system...")
    print("Commands:")
    print(" - 'Peace' sign: Virtual Mouse Mode (move with index finger, pinch to click)")
    print(" - 'Fist': Volume Control Mode (pinch to change volume)")
    print(" - 'q' to Quit")

    current_mode = "None"

    while True:
        success, img = cap.read()
        if not success:
            break

        # Flip horizontally for natural mirror effect
        img = cv2.flip(img, 1)

        # Find hand landmarks
        img = detector.find_hands(img, draw=True)
        lmList = detector.find_position(img, draw=False)

        gesture = "None"
        
        if len(lmList) != 0:
            gesture = gesture_recognizer.get_gesture(lmList)
            fingers = detector.fingers_up()
            
            # --- MODE SELECTION LOGIC ---
            if gesture == "Peace":
                current_mode = "Mouse Control"
            elif gesture == "Fist":
                current_mode = "Volume Control"
            elif gesture == "Open Palm":
                current_mode = "None"

            # --- VIRTUAL MOUSE LOGIC ---
            if current_mode == "Mouse Control":
                # Index finger tip is landmark 8
                x1, y1 = lmList[8][1], lmList[8][2]
                
                # Draw boundary box for mapping
                cv2.rectangle(img, (100, 100), (wCam - 100, hCam - 100), (255, 0, 255), 2)
                
                # Move mouse if index is up
                if fingers[1] == 1 and fingers[2] == 1:
                    # we use the raw x1,y1 because image is already flipped
                    smooth_x, smooth_y = sys_controller.move_mouse(x1, y1, wCam, hCam, wScr, hScr, smooth_x, smooth_y)
                    cv2.circle(img, (x1, y1), 15, (255, 0, 255), cv2.FILLED)

                # Click logic: if Pinch is detected while in Mouse Mode
                length, img, lineInfo = detector.find_distance(4, 8, img, draw=True)
                if length < 40 and click_debounce == 0:
                    cv2.circle(img, (lineInfo[4], lineInfo[5]), 15, (0, 255, 0), cv2.FILLED)
                    sys_controller.click_mouse()
                    click_debounce = 10  # Wait 10 frames before allowing another click
            
            # --- VOLUME CONTROL LOGIC ---
            elif current_mode == "Volume Control":
                # Find distance between thumb and index
                length, img, lineInfo = detector.find_distance(4, 8, img, draw=True)
                volBar, volPer = sys_controller.set_volume(length)

        # Decrease click debounce timer
        if click_debounce > 0:
            click_debounce -= 1

        # Calculate FPS
        cTime = time.time()
        fps = 1 / (cTime - pTime) if pTime != 0 else 0
        pTime = cTime

        # UI Overlays
        cv2.putText(img, f'FPS: {int(fps)}', (20, 50), cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 2)
        cv2.putText(img, f'Gesture: {gesture}', (20, 90), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 2)
        cv2.putText(img, f'Mode: {current_mode}', (20, 130), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 255), 2)

        if current_mode == "Volume Control":
            cv2.rectangle(img, (50, 150), (85, 400), (0, 255, 0), 3)
            cv2.rectangle(img, (50, int(volBar)), (85, 400), (0, 255, 0), cv2.FILLED)
            cv2.putText(img, f'{int(volPer)} %', (40, 450), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 2)

        cv2.imshow("Hand Tracking System", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()