from rapidfuzz import fuzz
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
import math

from app.models import InvoiceLine, Invoice, PurchaseOrder
from app.cleaning import standardize_vendor

def compute_string_similarity(str1: str, str2: str) -> float:
    # Normalized score between 0.0 and 1.0
    if not str1 or not str2:
        return 0.0
    return float(fuzz.token_sort_ratio(str1, str2) / 100.0)

def compute_relative_difference(val1: float, val2: float) -> float:
    if val1 == 0.0 and val2 == 0.0:
        return 0.0
    return float(abs(val1 - val2) / max(val1, val2, 0.0001))

def compute_historical_vendor_average(db: Session, vendor_name: str, sku: str, default_price: float) -> float:
    # Query database to find running average unit price of this SKU for this vendor
    std_vendor = standardize_vendor(vendor_name)
    
    avg_price = db.query(func.avg(InvoiceLine.unit_price)).\
        join(Invoice, InvoiceLine.invoice_id == Invoice.id).\
        filter(Invoice.vendor_name == std_vendor).\
        filter(InvoiceLine.sku == sku).\
        scalar()
        
    if avg_price is not None:
        return float(avg_price)
    return float(default_price)

def generate_line_feature_vector(
    db: Session,
    inv_line: dict,
    po_line: dict,
    inv_date: date,
    po_date: date,
    inv_vendor: str,
    po_vendor: str
) -> dict:
    # 1. Vendor Name similarity (fuzzy matching score)
    vendor_sim = compute_string_similarity(inv_vendor, po_vendor)
    
    # 2. SKU similarity (token sort ratio or exact match indicator)
    sku_sim = compute_string_similarity(inv_line.get("sku", ""), po_line.get("sku", ""))
    
    # 3. Description similarity
    desc_sim = compute_string_similarity(inv_line.get("description", ""), po_line.get("description", ""))
    
    # 4. Quantity difference (relative and absolute)
    inv_qty = float(inv_line.get("quantity", 0.0))
    po_qty = float(po_line.get("quantity", 0.0))
    qty_diff_abs = float(abs(inv_qty - po_qty))
    qty_diff_rel = compute_relative_difference(inv_qty, po_qty)
    
    # 5. Price difference (relative and absolute unit price)
    inv_price = float(inv_line.get("unit_price", 0.0))
    po_price = float(po_line.get("unit_price", 0.0))
    price_diff_abs = float(abs(inv_price - po_price))
    price_diff_rel = compute_relative_difference(inv_price, po_price)
    
    # 6. Total price difference
    inv_total = float(inv_line.get("total_price", 0.0))
    po_total = float(po_line.get("total_price", 0.0))
    total_diff_abs = float(abs(inv_total - po_total))
    total_diff_rel = compute_relative_difference(inv_total, po_total)

    # 7. Date difference in days
    date_diff_days = float(abs((inv_date - po_date).days))
    
    # 8. Historical unit price averages
    hist_avg = compute_historical_vendor_average(db, inv_vendor, inv_line.get("sku", ""), po_price)
    hist_avg_diff = float(abs(inv_price - hist_avg))
    
    return {
        "vendor_similarity": vendor_sim,
        "sku_similarity": sku_sim,
        "description_similarity": desc_sim,
        "qty_difference_abs": qty_diff_abs,
        "qty_difference_rel": qty_diff_rel,
        "price_difference_abs": price_diff_abs,
        "price_difference_rel": price_diff_rel,
        "total_difference_abs": total_diff_abs,
        "total_difference_rel": total_diff_rel,
        "date_difference_days": date_diff_days,
        "historical_vendor_avg": hist_avg,
        "historical_avg_diff": hist_avg_diff
    }

def get_document_similarities(db: Session, invoice_id: str, po_id: str) -> list:
    # Computes lines-level similarity combinations between a given Invoice and PO
    from app.models import Invoice, PurchaseOrder
    from app.explainers import calculate_shap_values
    
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    
    if not inv or not po:
        return []
        
    features_list = []
    
    for inv_line in inv.lines:
        for po_line in po.lines:
            vector = generate_line_feature_vector(
                db,
                {"sku": inv_line.sku, "description": inv_line.description, "quantity": inv_line.quantity, "unit_price": inv_line.unit_price, "total_price": inv_line.total_price},
                {"sku": po_line.sku, "description": po_line.description, "quantity": po_line.quantity, "unit_price": po_line.unit_price, "total_price": po_line.total_price},
                inv.invoice_date,
                po.po_date,
                inv.vendor_name,
                po.vendor_name
            )
            shap_data = calculate_shap_values(vector)
            features_list.append({
                "invoice_line_id": inv_line.id,
                "invoice_line_number": inv_line.line_number,
                "po_line_id": po_line.id,
                "po_line_number": po_line.line_number,
                "vector": vector,
                "shap_importances": shap_data["importances"]
            })
            
    return features_list
