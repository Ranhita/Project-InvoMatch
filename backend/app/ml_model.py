import os
import numpy as np
import lightgbm as lgb
import logging

logger = logging.getLogger(__name__)

# Feature keys in order
FEATURE_KEYS = [
    "vendor_similarity",
    "sku_similarity",
    "description_similarity",
    "qty_difference_rel",
    "price_difference_rel",
    "total_difference_rel",
    "date_difference_days",
    "historical_avg_diff"
]

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lightgbm_ranker.txt")
_model = None

def generate_synthetic_data(num_samples: int = 100):
    # Generates balanced positive (matching) and negative (mismatched) synthetic samples
    np.random.seed(42)
    
    # 1. Positive matches (label = 1)
    pos_vendor = np.random.uniform(0.85, 1.0, num_samples)
    pos_sku = np.random.choice([1.0, 0.9, 0.0], num_samples, p=[0.7, 0.2, 0.1])
    pos_desc = np.random.uniform(0.70, 1.0, num_samples)
    pos_qty_rel = np.random.exponential(0.01, num_samples)  # very small diff
    pos_price_rel = np.random.exponential(0.02, num_samples) # very small diff
    pos_total_rel = pos_qty_rel + pos_price_rel
    pos_date_diff = np.random.randint(0, 5, num_samples)
    pos_hist_diff = np.random.exponential(1.5, num_samples)
    
    X_pos = np.column_stack([
        pos_vendor, pos_sku, pos_desc, pos_qty_rel,
        pos_price_rel, pos_total_rel, pos_date_diff, pos_hist_diff
    ])
    y_pos = np.ones(num_samples)
    
    # 2. Negative matches (label = 0)
    neg_vendor = np.random.uniform(0.1, 0.6, num_samples)
    neg_sku = np.random.choice([0.0, 0.1, 0.5], num_samples, p=[0.8, 0.15, 0.05])
    neg_desc = np.random.uniform(0.0, 0.40, num_samples)
    neg_qty_rel = np.random.uniform(0.2, 2.0, num_samples)  # large diff
    neg_price_rel = np.random.uniform(0.2, 1.5, num_samples) # large diff
    neg_total_rel = np.random.uniform(0.4, 3.5, num_samples)
    neg_date_diff = np.random.randint(10, 120, num_samples)
    neg_hist_diff = np.random.uniform(20.0, 150.0, num_samples)
    
    X_neg = np.column_stack([
        neg_vendor, neg_sku, neg_desc, neg_qty_rel,
        neg_price_rel, neg_total_rel, neg_date_diff, neg_hist_diff
    ])
    y_neg = np.zeros(num_samples)
    
    X = np.vstack([X_pos, X_neg])
    y = np.concatenate([y_pos, y_neg])
    return X, y

def train_and_save_model():
    logger.info("Initializing synthetic dataset to train InvoMatch LightGBM Match Ranker...")
    X, y = generate_synthetic_data(250)
    
    # Create LightGBM Dataset
    train_data = lgb.Dataset(X, label=y)
    
    params = {
        'objective': 'binary',
        'metric': 'binary_logloss',
        'boosting_type': 'gbdt',
        'learning_rate': 0.1,
        'num_leaves': 15,
        'min_data_in_leaf': 10,
        'verbose': -1
    }
    
    # Train booster
    booster = lgb.train(
        params,
        train_data,
        num_boost_round=50
    )
    
    # Save booster to file
    booster.save_model(MODEL_PATH)
    logger.info(f"LightGBM Match Ranker model successfully trained and saved to: {MODEL_PATH}")
    return booster

def load_model():
    global _model
    if _model is not None:
        return _model
        
    if not os.path.exists(MODEL_PATH):
        _model = train_and_save_model()
    else:
        logger.info(f"Loading InvoMatch LightGBM Match Ranker from: {MODEL_PATH}")
        _model = lgb.Booster(model_file=MODEL_PATH)
    return _model

def predict_match_probability(vector: dict) -> float:
    # Predict match probability (0.0 to 1.0) using LightGBM model for a comparison feature vector
    model = load_model()
    
    # Convert feature vector dict to array in matching order
    features = []
    for key in FEATURE_KEYS:
        features.append(float(vector.get(key, 0.0)))
        
    # Format for inference
    input_arr = np.array([features], dtype=np.float32)
    
    # Run prediction (returns probability of class 1)
    prob = model.predict(input_arr)[0]
    return float(prob)

# Auto-load or bootstrap model on module import
try:
    load_model()
except Exception as e:
    logger.error(f"Error bootstrapping LightGBM model: {e}")
