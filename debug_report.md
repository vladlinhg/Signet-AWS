# Debug Report: Invoice Admin Issues

**Date**: 2026-02-06
**Reporter**: System Agent
**Subject**: Missing Features & UI Elements in Invoice Admin for Sales Users

## 1. Issue Analysis

### A. Missing Invoice Payment Section
**Observation**: The "Invoice Payments" section is missing from the Sales Dashboard/Admin.
**Root Cause**:
-   **Permissions**: The "Sales" user role likely lacks the `view_invoicepayment`, `add_invoicepayment`, or `change_invoicepayment` permissions. In Django Admin, inlines require access rights to the child model.
-   **Configuration**: `InvoicePaymentInline` is correctly configured in code (`extra=0`), so it should appear if permissions are granted.

### B. "Can't Attach Supporting Document"
**Observation**: The interface uses a basic multi-select box, which is unwieldy.
**Root Cause**:
-   **Widget Type**: Default Django `ManyToManyField` widget is a simple list.
-   **Missing Add Button**: The ability to "Upload/Attach" (Create new) on the fly depends on the `add_supportingdocument` permission. If missing, the green `+` icon disappears.

### C. Missing CRUD Options (Tour Booking, Flight Ticket, etc.)
**Observation**: `Client` field behaves correctly (Add/Edit buttons), but `Tour Booking` and others do not.
**Root Cause**:
-   **Permissions**: Django Admin automatically hides the Add `+`, Edit `pencil`, and View `eye` icons if the user does not have the corresponding permissions for the related model.
-   **Missing Registration**: The models must be registered in the Admin site (which `TourBooking` is, but permissions block access).

## 2. Recommendation

To resolve these issues, we need to:
1.  **Grant Permissions**: Update the "Sales" Group/Role to include `add`, `change`, `view` permissions for:
    -   `InvoicePayment`
    -   `TourBooking`
    -   `FlightTicket`
    -   `AddonService`
    -   `Coupon`
    -   `SupportingDocument`
2.  **Enhance UI**:
    -   Update `InvoiceAdmin` to use `filter_horizontal` for `supporting_documents` (easier selection).
    -   (Optional) Use `autocomplete_fields` for `TourBooking` if the list becomes too long.

## 3. Next Steps
-   Update `implementation_plan.md` with specific code changes.
-   Apply permissions updates.
-   Modify `admin.py`.
