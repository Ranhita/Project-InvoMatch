import csv
import io
from sqlalchemy.orm import Session
from datetime import datetime
from app.models import Invoice, PurchaseOrder, Match, Flag, AuditLog, User

def generate_csv_report(db: Session, report_type: str) -> str:
    # Generates exportable CSV report content for different audit business sectors
    output = io.StringIO()
    writer = csv.writer(output)
    
    if report_type == "monthly":
        writer.writerow(["Month", "Invoices Uploaded", "Purchase Orders Uploaded", "Total Invoice Value ($)", "Matches Approved"])
        
        # Programmatically aggregate monthly data
        invoices = db.query(Invoice).all()
        pos = db.query(PurchaseOrder).all()
        matches = db.query(Match).all()
        
        months = {}
        for inv in invoices:
            m_key = inv.uploaded_at.strftime("%Y-%m (%B)") if inv.uploaded_at else "Unknown Month"
            if m_key not in months:
                months[m_key] = {"inv": 0, "po": 0, "val": 0.0, "approved": 0}
            months[m_key]["inv"] += 1
            months[m_key]["val"] += (inv.total_amount or 0.0)
            
        for po in pos:
            m_key = po.uploaded_at.strftime("%Y-%m (%B)") if po.uploaded_at else "Unknown Month"
            if m_key not in months:
                months[m_key] = {"inv": 0, "po": 0, "val": 0.0, "approved": 0}
            months[m_key]["po"] += 1
            
        for m in matches:
            if m.status == "approved":
                inv = db.query(Invoice).filter(Invoice.id == m.invoice_id).first()
                if inv:
                    m_key = inv.uploaded_at.strftime("%Y-%m (%B)") if inv.uploaded_at else "Unknown Month"
                    if m_key in months:
                        months[m_key]["approved"] += 1
                        
        for m_key, data in sorted(months.items()):
            writer.writerow([m_key, data["inv"], data["po"], f"{data['val']:.2f}", data["approved"]])
            
    elif report_type == "vendor":
        writer.writerow(["Vendor Name", "Invoices Billed", "Average Match Score (%)", "Average Risk Score (%)", "Total Billed Amount ($)"])
        
        matches = db.query(Match).all()
        vendor_data = {}
        for m in matches:
            inv = db.query(Invoice).filter(Invoice.id == m.invoice_id).first()
            if inv:
                vendor = inv.vendor_name or "Unknown Vendor"
                if vendor not in vendor_data:
                    vendor_data[vendor] = {"scores": [], "risks": [], "amount": 0.0}
                vendor_data[vendor]["scores"].append(m.match_score)
                vendor_data[vendor]["risks"].append(m.risk_score)
                vendor_data[vendor]["amount"] += (inv.total_amount or 0.0)
                
        for vendor, data in sorted(vendor_data.items()):
            avg_score = (sum(data["scores"]) / len(data["scores"])) * 100.0 if data["scores"] else 0.0
            avg_risk = sum(data["risks"]) / len(data["risks"]) if data["risks"] else 0.0
            writer.writerow([vendor, len(data["scores"]), f"{avg_score:.1f}", f"{avg_risk:.1f}", f"{data['amount']:.2f}"])
            
    elif report_type == "anomaly":
        writer.writerow(["Flag ID", "Invoice ID", "Invoice Number", "Vendor Name", "Flag Type", "Severity", "Description", "AI Explanation", "Resolved"])
        
        flags = db.query(Flag).all()
        for f in flags:
            inv = db.query(Invoice).filter(Invoice.id == f.invoice_id).first()
            writer.writerow([
                f.id,
                f.invoice_id,
                inv.invoice_number if inv else "N/A",
                inv.vendor_name if inv else "N/A",
                f.flag_type,
                f.severity,
                f.description,
                f.explained_by_ai or "None",
                "Yes" if f.is_resolved else "No"
            ])
            
    elif report_type == "audit":
        writer.writerow(["Log ID", "Executor ID", "Executor Username", "Action", "Details", "Timestamp"])
        
        logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).all()
        for l in logs:
            user = db.query(User).filter(User.id == l.user_id).first()
            writer.writerow([
                l.id,
                l.user_id,
                user.username if user else "System",
                l.action,
                l.details,
                l.created_at.strftime("%Y-%m-%d %H:%M:%S") if l.created_at else "N/A"
            ])
            
    elif report_type == "finance":
        writer.writerow(["Billing Metric Category", "Invoice Count", "Aggregated Value ($)"])
        
        matches = db.query(Match).all()
        invoices = db.query(Invoice).all()
        
        # 1. Total billing uploads
        tot_val = sum(inv.total_amount for inv in invoices if inv.total_amount)
        writer.writerow(["Total Billed Invoices", len(invoices), f"{tot_val:.2f}"])
        
        # 2. Approved Match totals
        approved_invs = [m for m in matches if m.status == "approved"]
        app_val = 0.0
        for m in approved_invs:
            inv = db.query(Invoice).filter(Invoice.id == m.invoice_id).first()
            if inv and inv.total_amount:
                app_val += inv.total_amount
        writer.writerow(["Approved AP Payments", len(approved_invs), f"{app_val:.2f}"])
        
        # 3. Pending Review matches
        pending_invs = [m for m in matches if m.status == "pending"]
        pen_val = 0.0
        for m in pending_invs:
            inv = db.query(Invoice).filter(Invoice.id == m.invoice_id).first()
            if inv and inv.total_amount:
                pen_val += inv.total_amount
        writer.writerow(["Pending Matching Approvals", len(pending_invs), f"{pen_val:.2f}"])
        
        # 4. Critical High Risk Matches
        critical_invs = [m for m in matches if m.risk_score >= 61.0]
        crit_val = 0.0
        for m in critical_invs:
            inv = db.query(Invoice).filter(Invoice.id == m.invoice_id).first()
            if inv and inv.total_amount:
                crit_val += inv.total_amount
        writer.writerow(["Flagged Critical Risk Invoices", len(critical_invs), f"{crit_val:.2f}"])
        
    else:
        writer.writerow(["Error", "Invalid report type specified"])
        
    return output.getvalue()

def generate_html_report(db: Session, report_type: str) -> str:
    # Generates a premium print-ready HTML page for finance auditing reports
    csv_str = generate_csv_report(db, report_type)
    reader = csv.reader(io.StringIO(csv_str))
    
    rows = list(reader)
    header = rows[0] if rows else []
    data_rows = rows[1:] if len(rows) > 1 else []
    
    # Beautiful responsive glassmorphism reporting layout
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>InvoMatch Audit Report - {report_type.title()}</title>
    <style>
        body {{
            background-color: #0F172A;
            color: #E2E8F0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            padding: 40px;
            margin: 0;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: rgba(30, 41, 59, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2);
            backdrop-filter: blur(10px);
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-b: 1px solid rgba(255, 255, 255, 0.1);
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        h1 {{
            font-size: 24px;
            font-weight: 800;
            margin: 0;
            background: linear-gradient(135deg, #06B6D4 0%, #6366F1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .timestamp {{
            font-size: 11px;
            color: #94A3B8;
            font-family: monospace;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            font-size: 13px;
        }}
        th {{
            background: rgba(15, 23, 42, 0.6);
            color: #94A3B8;
            font-weight: 700;
            text-transform: uppercase;
            font-size: 10px;
            letter-spacing: 0.1em;
            padding: 12px;
            border-bottom: 2px solid rgba(255, 255, 255, 0.05);
            text-align: left;
        }}
        td {{
            padding: 12px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.03);
            color: #D1D5DB;
        }}
        tr:hover td {{
            background: rgba(255, 255, 255, 0.01);
        }}
        .btn-print {{
            background: #6366F1;
            color: white;
            border: none;
            padding: 8px 16px;
            font-size: 12px;
            font-weight: bold;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .btn-print:hover {{
            background: #4F46E5;
        }}
        @media print {{
            body {{
                background-color: white;
                color: black;
                padding: 0;
            }}
            .container {{
                background: none;
                border: none;
                box-shadow: none;
                padding: 0;
                max-width: 100%;
            }}
            .btn-print {{
                display: none;
            }}
            th {{
                background: #F1F5F9;
                color: #475569;
                border-bottom: 2px solid #E2E8F0;
            }}
            td {{
                color: #334155;
                border-bottom: 1px solid #E2E8F0;
            }}
            h1 {{
                -webkit-text-fill-color: initial;
                color: black;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>InvoMatch Finance Report</h1>
                <p style="margin: 5px 0 0 0; font-size: 12px; color: #94A3B8;">Sector: {report_type.upper()} SUMMARY</p>
            </div>
            <div style="text-align: right;">
                <button class="btn-print" onclick="window.print()">Print PDF</button>
                <div class="timestamp" style="margin-top: 10px;">Generated: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC</div>
            </div>
        </div>
        
        <table>
            <thead>
                <tr>
                    {"".join(f"<th>{col}</th>" for col in header)}
                </tr>
            </thead>
            <tbody>
                {"".join(f"<tr>{''.join(f'<td>{cell}</td>' for cell in row)}</tr>" for row in data_rows)}
            </tbody>
        </table>
    </div>
</body>
</html>"""
    return html
