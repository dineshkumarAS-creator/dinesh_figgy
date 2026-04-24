import os
import pandas as pd
from xgboost import XGBRegressor
from sklearn.model_selection import cross_val_score
import joblib

def train_model():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, "training_data.csv")
    
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found. Run generate_training_data.py first.")
        return
        
    df = pd.read_csv(csv_path)
    X = df.drop(columns=["weekly_premium"])
    y = df["weekly_premium"]
    
    # Train robust model
    model = XGBRegressor(n_estimators=100, max_depth=3, learning_rate=0.1, random_state=42)
    
    # Cross Validation Check
    scores = cross_val_score(model, X, y, cv=5, scoring="neg_root_mean_squared_error")
    rmse = -scores.mean()
    print(f"Cross-validated RMSE: Rs. {rmse:.2f} (Target < Rs. 8)")
    
    model.fit(X, y)
    
    # Display Feature Importances
    print("\nFeature Importances:")
    for col, imp in zip(X.columns, model.feature_importances_):
        print(f"- {col}: {imp:.4f}")
        
    # Save the model
    model_dir = os.path.join(script_dir, "..", "models")
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, "premium_model.pkl")
    
    joblib.dump(model, model_path)
    print(f"\nModel saved successfully to {model_path}")

if __name__ == "__main__":
    train_model()
