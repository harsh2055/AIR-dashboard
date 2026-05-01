import csv
import os
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import pickle

def train_model(csv_path='ml/gestures.csv', model_path='ml/model.pkl'):
    if not os.path.exists(csv_path):
        print(f"❌ Dataset not found at {csv_path}")
        return

    X = []
    y = []
    
    with open(csv_path, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row: continue
            label = row[0]
            features = [float(x) for x in row[1:]]
            X.append(features)
            y.append(label)
            
    X = np.array(X)
    y = np.array(y)
    
    classes = list(np.unique(y))
    print(f"Training on {len(X)} samples across classes: {classes}")
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = RandomForestClassifier(n_estimators=100)
    model.fit(X_train, y_train)
    
    score = model.score(X_test, y_test)
    print(f"✅ Model trained with accuracy: {score*100:.2f}%")
    
    with open(model_path, 'wb') as f:
        pickle.dump({'model': model, 'classes': classes}, f)
    print(f"✅ Model saved to {model_path}")

if __name__ == "__main__":
    # Placeholder for running directly
    train_model()
