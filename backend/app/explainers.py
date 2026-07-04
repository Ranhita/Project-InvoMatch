import numpy as np
from app.ml_model import predict_match_probability, FEATURE_KEYS

# Perfect baseline representing a clean, ideal invoice-PO match
BASELINE_MATCH = {
    "vendor_similarity": 1.0,
    "sku_similarity": 1.0,
    "description_similarity": 1.0,
    "qty_difference_rel": 0.0,
    "price_difference_rel": 0.0,
    "total_difference_rel": 0.0,
    "date_difference_days": 0.0,
    "historical_avg_diff": 0.0
}

def calculate_shap_values(vector: dict) -> dict:
    # Computes perturbation-based Shapley value contributions for each feature in InvoMatch
    
    # 1. Base prediction
    base_prob = predict_match_probability(vector)
    
    contributions = {}
    total_impact = 0.0
    
    # 2. Permute each feature individually to its ideal baseline state
    for key in FEATURE_KEYS:
        temp_vector = vector.copy()
        temp_vector[key] = BASELINE_MATCH[key]
        
        # Calculate probability shift
        permuted_prob = predict_match_probability(temp_vector)
        
        # Marginal impact: how much did this feature pull down the match probability?
        impact = permuted_prob - base_prob
        
        # We only track positive impacts (features that reduced the match probability)
        # to focus explanations on why it was flagged or rejected
        if impact > 0.001:
            contributions[key] = float(impact)
            total_impact += impact
        else:
            contributions[key] = 0.0
            
    # 3. Normalize to percentages
    shap_percentages = {}
    for key in FEATURE_KEYS:
        if total_impact > 0:
            shap_percentages[key] = float((contributions.get(key, 0.0) / total_impact) * 100.0)
        else:
            shap_percentages[key] = 0.0
            
    return {
        "base_probability": base_prob,
        "contributions": contributions,
        "importances": shap_percentages
    }

def generate_ai_explanation(vector: dict, rules_triggered: list) -> str:
    # Generates a clear, user-friendly explanation of why a match was flagged
    shap_results = calculate_shap_values(vector)
    importances = shap_results["importances"]
    
    # Find the top features that contributed to the discrepancy
    sorted_features = sorted(importances.items(), key=lambda x: x[1], reverse=True)
    top_contributors = [f for f in sorted_features if f[1] > 5.0]
    
    explanation_parts = []
    
    # Check for rule triggers first for explicit descriptions
    for rule in rules_triggered:
        if rule["rule"] == "duplicate_invoice":
            explanation_parts.append("A duplicate invoice exists in transaction logs.")
        elif rule["rule"] == "price_increase":
            price_dev = float(vector.get("price_difference_rel", 0.0) * 100)
            explanation_parts.append(f"Unit price is {price_dev:.1f}% above standard PO values.")
        elif rule["rule"] == "quantity_difference":
            qty_dev = float(vector.get("qty_difference_rel", 0.0) * 100)
            explanation_parts.append(f"Billing quantity variance is {qty_dev:.1f}% off PO specs.")
            
    # Fallback to feature importance if rules explanation is sparse
    if not explanation_parts and top_contributors:
        for feat, imp in top_contributors[:2]:
            feat_name = feat.replace("_", " ").title()
            explanation_parts.append(f"Discrepancy in {feat_name} (contributed {imp:.0f}% of anomaly score).")
            
    if not explanation_parts:
        return "Invoice metrics correspond to normal boundaries. No anomalies detected."
        
    return " ".join(explanation_parts)
