from sqlalchemy.orm import Session
from datetime import date
import logging
from app.models import Invoice, PurchaseOrder, Match, Flag, AuditLog
from app.features import generate_line_feature_vector
from app.ml_model import predict_match_probability
from app.cleaning import standardize_vendor
from app.anomalies import calculate_invoice_risk
from app.explainers import generate_ai_explanation

logger = logging.getLogger(__name__)

def evaluate_line_rules(inv_line, po_line) -> dict:
    # STEP 1: Exact Matching rules
    exact_sku = inv_line.sku == po_line.sku
    exact_price = inv_line.unit_price == po_line.unit_price
    exact_qty = inv_line.quantity == po_line.quantity
    
    exact_match = exact_sku and exact_price and exact_qty
    
    # STEP 2: Tolerance rules matching
    price_diff_rel = 0.0
    if inv_line.unit_price > 0 or po_line.unit_price > 0:
        price_diff_rel = abs(inv_line.unit_price - po_line.unit_price) / max(inv_line.unit_price, po_line.unit_price, 0.0001)
        
    qty_diff_rel = 0.0
    if inv_line.quantity > 0 or po_line.quantity > 0:
        qty_diff_rel = abs(inv_line.quantity - po_line.quantity) / max(inv_line.quantity, po_line.quantity, 0.0001)
        
    within_price_tolerance = price_diff_rel <= 0.05   # ±5%
    within_qty_tolerance = qty_diff_rel <= 0.02       # ±2%
    
    tolerance_match = exact_sku and within_price_tolerance and within_qty_tolerance
    
    return {
        "exact_match": exact_match,
        "tolerance_match": tolerance_match,
        "price_diff_percent": float(price_diff_rel * 100),
        "qty_diff_percent": float(qty_diff_rel * 100),
        "exact_sku": exact_sku
    }

def rank_po_candidates(db: Session, invoice: Invoice, limit: int = 10) -> list:
    # STEP 4: Candidate Ranking
    pos = db.query(PurchaseOrder).all()
    candidates = []
    
    for po in pos:
        # Check overall vendor similarity as a primary filter
        vendor_sim = 1.0 if invoice.vendor_name == po.vendor_name else 0.0
        
        # Calculate line-level matchups
        line_matches = []
        for inv_line in invoice.lines:
            best_line_prob = 0.0
            best_po_line = None
            best_vector = None
            
            for po_line in po.lines:
                # Calculate feature vector (Phase 4)
                vector = generate_line_feature_vector(
                    db,
                    {"sku": inv_line.sku, "description": inv_line.description, "quantity": inv_line.quantity, "unit_price": inv_line.unit_price, "total_price": inv_line.total_price},
                    {"sku": po_line.sku, "description": po_line.description, "quantity": po_line.quantity, "unit_price": po_line.unit_price, "total_price": po_line.total_price},
                    invoice.invoice_date,
                    po.po_date,
                    invoice.vendor_name,
                    po.vendor_name
                )
                
                # Predict probability via LightGBM (Phase 6)
                prob = predict_match_probability(vector)
                
                if prob > best_line_prob:
                    best_line_prob = prob
                    best_po_line = po_line
                    best_vector = vector
                    
            if best_po_line:
                line_matches.append({
                    "invoice_line_id": inv_line.id,
                    "po_line_id": best_po_line.id,
                    "probability": best_line_prob,
                    "rules": evaluate_line_rules(inv_line, best_po_line),
                    "vector": best_vector
                })
        
        # Calculate overall score for PO candidate
        if line_matches:
            avg_prob = sum(m["probability"] for m in line_matches) / len(line_matches)
        else:
            avg_prob = 0.0
            
        candidates.append({
            "po_id": po.id,
            "po_number": po.po_number,
            "vendor_name": po.vendor_name,
            "total_amount": po.total_amount,
            "match_score": avg_prob,
            "line_matches": line_matches
        })
        
    # Sort candidates and return Top 10
    candidates.sort(key=lambda x: x["match_score"], reverse=True)
    return candidates[:limit]

def reconcile_invoice(db: Session, invoice_id: str) -> dict:
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise ValueError(f"Invoice {invoice_id} not found.")
        
    # Clear existing matches and flags for this invoice
    db.query(Match).filter(Match.invoice_id == invoice_id).delete()
    db.query(Flag).filter(Flag.invoice_id == invoice_id).delete()
    
    # 1. Rank candidate POs
    candidates = rank_po_candidates(db, invoice, limit=10)
    
    if not candidates:
        invoice.status = "processed"
        db.commit()
        return {"status": "no_candidates", "message": "No purchase orders found to compare."}
        
    # 2. Extract best match (highest match score)
    best_candidate = candidates[0]
    match_score = best_candidate["match_score"]
    
    # Threshold check for auto-linking (e.g. 60%)
    matched = match_score >= 0.60
    
    if matched:
        # 3. Run anomaly risk engine (Phase 7)
        risk_data = calculate_invoice_risk(db, invoice.id, best_candidate["po_id"], best_candidate["line_matches"])
        
        # Create match entry in DB with risk score
        new_match = Match(
            invoice_id=invoice.id,
            po_id=best_candidate["po_id"],
            match_score=float(match_score),
            risk_score=float(risk_data["risk_score"]),
            matched_by="ml_ranking",
            status="pending"
        )
        db.add(new_match)
        
        invoice_status = "matched"
        has_anomalies = False
        
        # Add flags from rule triggers first
        for rule in risk_data["rules_triggered"]:
            if rule["rule"] in ["duplicate_invoice", "unexpected_tax"]:
                flag = Flag(
                    invoice_id=invoice.id,
                    flag_type=rule["rule"],
                    severity=rule["severity"],
                    description=rule["message"],
                    explained_by_ai="Threshold rule triggered: " + rule["message"]
                )
                db.add(flag)
                has_anomalies = True
        
        for match in best_candidate["line_matches"]:
            rules = match["rules"]
            inv_line = db.query(Invoice.lines.property.mapper.class_).filter_by(id=match["invoice_line_id"]).first()
            po_line = db.query(PurchaseOrder.lines.property.mapper.class_).filter_by(id=match["po_line_id"]).first()
            
            # Generate AI Explanation via Shapley explainer (Phase 8)
            ai_exp = generate_ai_explanation(match["vector"], risk_data["rules_triggered"])
            
            # Check price discrepancy flag (Tolerances rule: ±5%)
            if not rules["exact_sku"]:
                # SKU mismatch flag
                flag = Flag(
                    invoice_id=invoice.id,
                    flag_type="sku_mismatch",
                    severity="high",
                    description=f"SKU mismatch on Line {inv_line.line_number}: Invoice SKU '{inv_line.sku}' vs PO SKU '{po_line.sku}'",
                    explained_by_ai=ai_exp or "Fuzzy matching detected line association but SKU text differs. Review item code mapping."
                )
                db.add(flag)
                has_anomalies = True
            else:
                # Check price tolerance
                if not rules["exact_match"] and rules["price_diff_percent"] > 5.0:
                    flag = Flag(
                        invoice_id=invoice.id,
                        flag_type="pricing_anomaly",
                        severity="medium" if rules["price_diff_percent"] <= 15.0 else "high",
                        description=f"Pricing discrepancy on SKU '{inv_line.sku}': Invoice ${inv_line.unit_price:.2f} vs PO ${po_line.unit_price:.2f} (Variation: +{rules['price_diff_percent']:.1f}%)",
                        explained_by_ai=ai_exp or "Unit price exceeds 5% tolerance rules defined by standard purchase agreement."
                    )
                    db.add(flag)
                    has_anomalies = True
                    
                # Check quantity tolerance (Tolerances rule: ±2%)
                if not rules["exact_match"] and rules["qty_diff_percent"] > 2.0:
                    flag = Flag(
                        invoice_id=invoice.id,
                        flag_type="quantity_mismatch",
                        severity="medium",
                        description=f"Quantity mismatch on SKU '{inv_line.sku}': Invoice {inv_line.quantity} units vs PO {po_line.quantity} units (Variation: +{rules['qty_diff_percent']:.1f}%)",
                        explained_by_ai=ai_exp or "Billed quantity exceeds 2% tolerance rules defined by standard purchasing logistics guidelines."
                    )
                    db.add(flag)
                    has_anomalies = True

        # Check vendor name fuzzy matching flag
        vendor_similarity = best_candidate["line_matches"][0]["vector"]["vendor_similarity"] if best_candidate["line_matches"] else 1.0
        if vendor_similarity < 0.95:
            flag = Flag(
                invoice_id=invoice.id,
                flag_type="vendor_mismatch",
                severity="low",
                description=f"Vendor name fuzzy match warning: Invoice '{invoice.vendor_name}' vs PO '{best_candidate['vendor_name']}' (Sim: {vendor_similarity*100:.0f}%)",
                explained_by_ai="Vendor spelling mismatch. Standardized names resolved, but fuzzy text comparison is under 95%."
            )
            db.add(flag)
            has_anomalies = True
            
        if has_anomalies:
            invoice_status = "anomaly"
            
        invoice.status = invoice_status
        
        # Add Audit Log
        audit = AuditLog(
            user_id=invoice.uploaded_by,
            action="AUTO_MATCH",
            details=f"Invoice {invoice.id} auto-matched with PO {best_candidate['po_id']} (confidence: {match_score:.2f}, status: {invoice_status})"
        )
        db.add(audit)
        
    else:
        invoice.status = "processed"
        # Add audit log for no match found
        audit = AuditLog(
            user_id=invoice.uploaded_by,
            action="AUTO_MATCH_FAILED",
            details=f"No matching PO candidate found for Invoice {invoice.id} above 60% confidence."
        )
        db.add(audit)

    db.commit()
    
    return {
        "status": "matched" if matched else "unmatched",
        "confidence_score": float(match_score),
        "best_candidate_po": best_candidate["po_id"],
        "candidates": candidates
    }
