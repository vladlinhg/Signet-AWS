from typing import Dict, Any, List

def compute_integrity(items: List[Dict[str, Any]], payments: List[Dict[str, Any]], pdf_totals: Dict[str, Any]) -> Dict[str, Any]:
    items_sum = 0
    for it in items:
        f = it.get("fields", {})
        q = int(f.get("quantity", 0) or 0)
        u = int(f.get("unit_price", 0) or 0)
        items_sum += q * u

    payments_sum = 0
    for p in payments:
        amt = p.get("fields", {}).get("amount", 0)
        if isinstance(amt, (int, float)):
            payments_sum += int(amt)

    computed_balance = items_sum - payments_sum

    checks = []
    if pdf_totals.get("grand_total") is not None:
        checks.append({"name": "items_sum_equals_pdf_grand_total", "ok": items_sum == pdf_totals["grand_total"]})
    if pdf_totals.get("total_paid") is not None:
        checks.append({"name": "payments_sum_equals_pdf_total_paid", "ok": payments_sum == pdf_totals["total_paid"]})
    if pdf_totals.get("balance") is not None:
        checks.append({"name": "computed_balance_equals_pdf_balance", "ok": computed_balance == pdf_totals["balance"]})

    return {
        "pdf_totals": pdf_totals,
        "computed": {
            "items_sum": items_sum,
            "payments_sum": payments_sum,
            "computed_balance": computed_balance
        },
        "checks": checks
    }
