import cv2
import time
from core.hand_detector import HandDetector
from core.gesture_recognizer import GestureRecognizer
from core.event_engine import EventEngine
from core.system_controller import SystemController
from core.action_mapper import ActionMapper
from ml.classifier import GestureClassifier

def main():
    # 1. Initialization
    wCam, hCam = 640, 480
    cap = cv2.VideoCapture(0)
    cap.set(3, wCam)
    cap.set(4, hCam)

    detector = HandDetector(max_num_hands=2) # Support 2 hands
    recognizer = GestureRecognizer(detector)
    ai_classifier = GestureClassifier()
    engine = EventEngine(confidence_threshold=0.65)
    sys_ctrl = SystemController()
    mapper = ActionMapper(engine, sys_ctrl)

    pTime = 0
    frame_count = 0
    process_nth_frame = 1 # Optimization: 1 means every frame, 2 means skip 1

    print("🌌 Aether Platform v3.0 | Running with AI + Multi-hand Support")
    
    while True:
        success, img = cap.read()
        if not success: break
        
        frame_count += 1
        if frame_count % process_nth_frame != 0:
            continue

        img = cv2.flip(img, 1)
        img = detector.process_frame(img, draw=True)
        
        # Support for multiple hands
        all_hands_data = []
        lm_all = detector.get_multi_landmarks(img) # Need to implement/verify this
        
        if lm_all:
            for hand in lm_all:
                lmList = hand['lmList']
                center = hand['center']
                
                # AI Inference
                ai_label, confidence = ai_classifier.predict(lmList)
                
                # Fallback to rules if AI is uncertain or not loaded
                if ai_label is None or confidence < 0.5:
                    label = recognizer.get_raw_gesture(lmList)
                    confidence = 1.0 # Rules are deterministic
                else:
                    label = ai_label
                
                # Update Engine
                state, conf = engine.update(label, confidence, center, lmList)
                all_hands_data.append({'center': center, 'state': state})
            
            # Multi-hand interactions (Zoom, Rotate)
            if len(all_hands_data) == 2:
                engine.update_multi(all_hands_data)

        # UI Overlay
        cTime = time.time()
        fps = 1 / (cTime - pTime) if (cTime - pTime) > 0 else 0
        pTime = cTime
        
        cv2.putText(img, f"FPS: {int(fps)}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        if lm_all:
            cv2.putText(img, f"Gesture: {label} ({int(confidence*100)}%)", (10, 60), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow("Aether Advanced", img)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
