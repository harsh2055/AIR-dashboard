import cv2
import csv
import os
import numpy as np
from core.hand_detector import HandDetector

def collect_data(label, num_samples=100):
    cap = cv2.VideoCapture(0)
    detector = HandDetector(max_num_hands=1)
    
    csv_path = 'ml/gestures.csv'
    count = 0
    
    print(f"Collecting {num_samples} samples for label: '{label}'")
    print("Prepare your hand... Starting in 3 seconds.")
    cv2.waitKey(3000)
    
    with open(csv_path, 'a', newline='') as f:
        writer = csv.writer(f)
        
        while count < num_samples:
            success, img = cap.read()
            if not success: break
            
            img = detector.process_frame(img)
            lmList, _ = detector.get_landmarks(img)
            
            if lmList:
                # Preprocess (Normalization logic copied for standalone script)
                coords = np.array([[lm[1], lm[2]] for lm in lmList])
                base = coords[0]
                centered = coords - base
                max_dist = np.max(np.linalg.norm(centered, axis=1))
                if max_dist > 0:
                    normalized = (centered / max_dist).flatten()
                    writer.writerow([label] + normalized.tolist())
                    count += 1
                    cv2.putText(img, f"Captured: {count}/{num_samples}", (50, 50), 
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            cv2.imshow("Data Collection", img)
            if cv2.waitKey(1) & 0xFF == ord('q'): break
            
    cap.release()
    cv2.destroyAllWindows()
    print(f"✅ Data collection complete for '{label}'")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        collect_data(sys.argv[1])
    else:
        print("Usage: python scripts/collect_data.py <label>")
