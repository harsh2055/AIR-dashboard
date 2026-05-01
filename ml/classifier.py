import numpy as np
import pickle
import os

class GestureClassifier:
    def __init__(self, model_path='ml/model.pkl'):
        self.model_path = model_path
        self.model = None
        self.classes = []
        self.load_model()

    def load_model(self):
        if os.path.exists(self.model_path):
            with open(self.model_path, 'rb') as f:
                data = pickle.load(f)
                self.model = data['model']
                self.classes = data['classes']
            print(f"✅ AI Model loaded from {self.model_path}")
        else:
            print("⚠️ No AI model found. Running in rule-based fallback mode.")

    def preprocess(self, lmList):
        """Normalize landmarks: shift to origin and scale."""
        if not lmList: return None
        
        # Convert to numpy array
        coords = np.array([[lm[1], lm[2]] for lm in lmList])
        
        # Center: subtract wrist (index 0)
        base = coords[0]
        centered = coords - base
        
        # Scale: divide by max distance from wrist
        max_dist = np.max(np.linalg.norm(centered, axis=1))
        if max_dist == 0: return None
        normalized = centered / max_dist
        
        return normalized.flatten()

    def predict(self, lmList):
        """Predict gesture and return label + confidence."""
        if self.model is None:
            return None, 0.0
            
        features = self.preprocess(lmList)
        if features is None: return None, 0.0
        
        # Predict probability
        probs = self.model.predict_proba([features])[0]
        max_idx = np.argmax(probs)
        confidence = probs[max_idx]
        label = self.classes[max_idx]
        
        return label, confidence
