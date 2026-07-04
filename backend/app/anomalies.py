from sqlalchemy.orm import Session
from sqlalchemy import func
from sklearn.ensemble import IsolationForest
import numpy as np
import logging
from app.models import Invoice, PurchaseOrder, Match, Flag

logger = logging.getLogger(__name__)

def check_duplicate_invoice(db: Session, invoice: Invoice) -> bool:
    # Check if there is another invoice with the same vendor name, invoice number, and total amount
    duplicate = db.query(Invoice).\
        filter(Invoice.id != invoice.id).\
        filter(Invoice.vendor_name == invoice.vendor_name).\
        filter(Invoice.invoice_number == invoice.invoice_number).\
        filter(Invoice.total_amount == invoice.total_amount).\
        first()
    return duplicate is not None

def run_isolation_forest_anomaly(features_list: list) -> float:
    # Computes structural out-of-bounds anomaly scoring using Isolation Forest
    if not features_list:
        return 0.0
        
    # Extract numerical comparison values from line feature vectors:
    # 1. sku_similarity
    # 2. qty_difference_rel
    # 3. price_difference_rel
    # 4. total_difference_rel
    data = []
    for match in features_list:
        vector = match["vector"]
        data.append([
            float(vector.get("sku_similarity", 1.0)),
            float(vector.get("qty_difference_rel", 0.0)),
            float(vector.get("price_difference_rel", 0.0)),
            float(vector.get("total_difference_rel", 0.0))
        ])
        
    X = np.array(data, dtype=np.float32)
    
    # If there are fewer than 3 comparison points, fit a default model or return baseline
    if len(X) < 3:
        # Check if there is any line discrepancy
        max_price_diff = max(row[2] for row in data) if data else 0.0
        return 25.0 if max_price_diff > 0.05 else 0.0
        
    try:
        # Fit Isolation Forest (contamination=0.1)
        # Note: fit_predict returns -1 for outliers, 1 for inliers.
        # decision_function returns float values (lower is more anomalous)
        clf = IsolationForest(n_estimators=50, contamination=0.1, random_state=42)
        clf.fit(X)
        scores = clf.decision_function(X)
        
        # Take the minimum decision score across all lines (the worst outlier)
        min_score = float(np.min(scores))
        
        # Map min_score (typically ranges from -0.5 to 0.5) to a 0-40 points scale
        # Outlier score < 0 maps to higher points
        if min_score < 0:
            if min_score < -0.2:
                return 40.0
            return 20.0 + abs(min_score) * 100.0
        return 0.0
    except Exception as e:
        logger.error(f"Failed to fit Isolation Forest: {e}")
        return 0.0

def calculate_invoice_risk(db: Session, invoice_id: str, po_id: str, line_matches: list) -> dict:
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    
    if not invoice or not po:
        return {"risk_score": 0.0, "severity": "Low", "rules_triggered": []}
        
    risk_points = 0.0
    rules_triggered = []
    
    # Rule 1: Duplicate Invoice Check (40 pts)
    if check_duplicate_invoice(db, invoice):
        risk_points += 40.0
        rules_triggered.append({
            "rule": "duplicate_invoice",
            "severity": "critical",
            "message": "Duplicate invoice details: identical vendor, invoice number, and billing amount exist in history."
        })
        
    # Rule 2: Price Increase check (25 pts)
    # Scan matches to see if unit price exceeds PO price by > 5%
    price_deviation = False
    qty_deviation = False
    partial_shipment = False
    missing_sku = False
    
    for match in line_matches:
        rules = match["rules"]
        if rules["price_diff_percent"] > 5.0:
            price_deviation = True
        if rules["qty_diff_percent"] > 2.0:
            qty_deviation = True
            
        inv_line = db.query(Invoice.lines.property.mapper.class_).filter_by(id=match["invoice_line_id"]).first()
        po_line = db.query(PurchaseOrder.lines.property.mapper.class_).filter_by(id=match["po_line_id"]).first()
        
        if inv_line and po_line:
            if inv_line.quantity < po_line.quantity:
                partial_shipment = True
            if not inv_line.sku or inv_line.sku == "ITEM-MISC":
                missing_sku = True

    if price_deviation:
        risk_points += 25.0
        rules_triggered.append({
            "rule": "price_increase",
            "severity": "high",
            "message": "Pricing anomaly: line unit price exceeds the purchase order baseline by more than 5%."
        })
        
    # Rule 3: Quantity Mismatch check (20 pts)
    if qty_deviation:
        risk_points += 20.0
        rules_triggered.append({
            "rule": "quantity_difference",
            "severity": "medium",
            "message": "Quantity mismatch: invoice quantity differs from standard PO allocations."
        })
        
    # Rule 4: Missing SKU fields (15 pts)
    if missing_sku:
        risk_points += 15.0
        rules_triggered.append({
            "rule": "missing_sku",
            "severity": "medium",
            "message": "Missing SKU reference: items are parsed as miscellaneous lines without a distinct item code."
        })
        
    # Rule 5: Partial Shipment check (10 pts)
    if partial_shipment:
        risk_points += 10.0
        rules_triggered.append({
            "rule": "partial_shipment",
            "severity": "low",
            "message": "Partial shipment indicator: billed quantity is lower than ordered purchase order quantity."
        })

    # Rule 6: Unexpected high tax (15 pts)
    # Assume tax is unexpected if no lines but amount differs, or we can check if total differs from lines total by > 20%
    lines_sum = sum(line.total_price for line in invoice.lines)
    if invoice.total_amount > 0 and lines_sum > 0:
        tax_ratio = (invoice.total_amount - lines_sum) / invoice.total_amount
        if tax_ratio > 0.20:
            risk_points += 15.0
            rules_triggered.append({
                "rule": "unexpected_tax",
                "severity": "medium",
                "message": f"Unexpected tax or high surcharge: difference between invoice total and lines subtotal exceeds 20% ({tax_ratio*100:.1f}%)."
            })

    # 2. Run Isolation Forest structural outlier detection (40 pts max)
    if line_matches:
        iforest_score = run_isolation_forest_anomaly(line_matches)
        risk_points += iforest_score
        if iforest_score > 0:
            rules_triggered.append({
                "rule": "isolation_forest_outlier",
                "severity": "medium" if iforest_score <= 20 else "high",
                "message": f"Isolation Forest structural outlier: matching features represent a statistically anomalous pattern."
            })
            
    # Cap final risk score at 100
    final_risk_score = float(min(100.0, risk_points))
    
    # 3. Map severity
    if final_risk_score >= 81.0:
        severity = "Critical"
    elif final_risk_score >= 61.0:
        severity = "High"
    elif final_risk_score >= 31.0:
        severity = "Medium"
    else:
        severity = "Low"
        
    return {
        "risk_score": final_risk_score,
        "severity": severity,
        "rules_triggered": rules_triggered
    }
