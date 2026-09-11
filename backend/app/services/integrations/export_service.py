import csv
import io
import json
from typing import List
from app.models import Invoice, Client


def export_invoices_to_csv(invoices: List[Invoice]) -> str:
    """Generate CSV string of invoices."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Invoice Number",
        "Client Name",
        "Client Email",
        "Amount",
        "Currency",
        "Status",
        "Issued Date",
        "Due Date",
        "Paid Date",
        "Description",
    ])
    for inv in invoices:
        writer.writerow([
            inv.invoice_number,
            inv.client.name if inv.client else "",
            inv.client.email if inv.client else "",
            f"{float(inv.amount):.2f}",
            inv.currency or "USD",
            inv.status,
            inv.issued_date.strftime("%Y-%m-%d"),
            inv.due_date.strftime("%Y-%m-%d"),
            inv.paid_date.strftime("%Y-%m-%d") if inv.paid_date else "",
            inv.description or "",
        ])
    return output.getvalue()


def export_clients_to_csv(clients: List[Client]) -> str:
    """Generate CSV string of clients."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Name", "Email", "Company", "Phone", "Risk Score", "Risk Tier", "Notes"])
    for c in clients:
        writer.writerow([
            c.id,
            c.name,
            c.email,
            c.company or "",
            c.phone or "",
            f"{c.risk_score:.1f}",
            c.risk_tier,
            c.notes or "",
        ])
    return output.getvalue()
