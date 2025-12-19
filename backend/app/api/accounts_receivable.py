"""
Accounts Receivable API Endpoints

Complete API for invoice management, payment processing, credit notes, and AR analytics.
"""

from typing import List, Optional
from uuid import UUID
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.finance import InvoiceStatus, PaymentRecordStatus, CreditNoteReason, ReminderType
from app.services.accounts_receivable import AccountsReceivableService
from app.schemas.accounts_receivable import (
    # Invoice schemas
    InvoiceCreate,
    InvoiceUpdate,
    InvoiceResponse,
    InvoiceDetail,
    InvoiceList,
    InvoiceFilter,
    # Payment schemas
    PaymentRecordCreate,
    PaymentRecordResponse,
    PaymentFilter,
    # Credit Note schemas
    CreditNoteCreate,
    CreditNoteResponse,
    CreditNoteFilter,
    # Payment Reminder schemas
    PaymentReminderCreate,
    PaymentReminderResponse,
    # Analytics schemas
    AgingReport,
    InvoiceSummary,
    PaymentSummary
)

router = APIRouter(prefix="/api/ar", tags=["Accounts Receivable"])


# ========== Invoice Endpoints ==========

@router.post("/invoices", response_model=InvoiceDetail, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    data: InvoiceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new invoice"""
    service = AccountsReceivableService(db)
    try:
        invoice = await service.create_invoice(data, current_user.id)
        return invoice
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/invoices/{invoice_id}", response_model=InvoiceDetail)
async def get_invoice(
    invoice_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get invoice by ID with all items"""
    service = AccountsReceivableService(db)
    invoice = await service.invoice_repo.get_with_items(invoice_id)
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    return invoice


@router.put("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: UUID,
    data: InvoiceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update invoice details"""
    service = AccountsReceivableService(db)
    try:
        invoice = await service.update_invoice(invoice_id, data)
        return invoice
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/invoices/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete invoice (soft delete)"""
    service = AccountsReceivableService(db)
    await service.invoice_repo.delete(invoice_id)
    await db.commit()


@router.post("/invoices/{invoice_id}/send", response_model=InvoiceResponse)
async def send_invoice(
    invoice_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send invoice to customer"""
    service = AccountsReceivableService(db)
    try:
        invoice = await service.send_invoice(invoice_id)
        return invoice
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/invoices/{invoice_id}/void", response_model=InvoiceResponse)
async def void_invoice(
    invoice_id: UUID,
    reason: str = Query(..., description="Reason for voiding invoice"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Void an invoice"""
    service = AccountsReceivableService(db)
    try:
        invoice = await service.void_invoice(invoice_id, reason)
        return invoice
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/invoices", response_model=List[InvoiceResponse])
async def list_invoices(
    status_filter: Optional[InvoiceStatus] = Query(None, alias="status"),
    wholesale_customer_id: Optional[UUID] = None,
    retail_customer_id: Optional[UUID] = None,
    is_overdue: Optional[bool] = None,
    invoice_date_from: Optional[date] = None,
    invoice_date_to: Optional[date] = None,
    due_date_from: Optional[date] = None,
    due_date_to: Optional[date] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List invoices with filters and pagination"""
    service = AccountsReceivableService(db)
    
    invoices, total = await service.invoice_repo.search_invoices(
        status=status_filter,
        wholesale_customer_id=wholesale_customer_id,
        retail_customer_id=retail_customer_id,
        is_overdue=is_overdue,
        invoice_date_from=invoice_date_from,
        invoice_date_to=invoice_date_to,
        due_date_from=due_date_from,
        due_date_to=due_date_to,
        search=search,
        skip=skip,
        limit=limit
    )
    
    return PaginatedResponse(
        items=invoices,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/invoices/order/{order_id}", response_model=List[InvoiceResponse])
async def get_invoices_by_order(
    order_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all invoices for an order"""
    service = AccountsReceivableService(db)
    invoices = await service.invoice_repo.get_by_order_id(order_id)
    return invoices


@router.get("/invoices/customer/summary", response_model=dict)
async def get_customer_invoice_summary(
    wholesale_customer_id: Optional[UUID] = None,
    retail_customer_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get invoice summary for customer"""
    if not wholesale_customer_id and not retail_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either wholesale_customer_id or retail_customer_id required"
        )
    
    service = AccountsReceivableService(db)
    summary = await service.invoice_repo.get_customer_summary(
        wholesale_customer_id,
        retail_customer_id
    )
    return summary


# ========== Payment Endpoints ==========

@router.post("/payments", response_model=PaymentRecordResponse, status_code=status.HTTP_201_CREATED)
async def record_payment(
    data: PaymentRecordCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Record a payment against an invoice"""
    service = AccountsReceivableService(db)
    try:
        payment, invoice = await service.record_payment(data, current_user.id)
        return payment
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/payments/{payment_id}", response_model=PaymentRecordResponse)
async def get_payment(
    payment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get payment record by ID"""
    service = AccountsReceivableService(db)
    payment = await service.payment_repo.get(payment_id)
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    return payment


@router.get("/payments", response_model=List[PaymentRecordResponse])
async def list_payments(
    status_filter: Optional[PaymentRecordStatus] = Query(None, alias="status"),
    payment_method: Optional[str] = None,
    is_reconciled: Optional[bool] = None,
    wholesale_customer_id: Optional[UUID] = None,
    retail_customer_id: Optional[UUID] = None,
    payment_date_from: Optional[date] = None,
    payment_date_to: Optional[date] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List payments with filters and pagination"""
    service = AccountsReceivableService(db)
    
    payments, total = await service.payment_repo.search_payments(
        status=status_filter,
        payment_method=payment_method,
        is_reconciled=is_reconciled,
        wholesale_customer_id=wholesale_customer_id,
        retail_customer_id=retail_customer_id,
        payment_date_from=payment_date_from,
        payment_date_to=payment_date_to,
        skip=skip,
        limit=limit
    )
    
    return PaginatedResponse(
        items=payments,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/payments/invoice/{invoice_id}", response_model=List[PaymentRecordResponse])
async def get_payments_by_invoice(
    invoice_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all payments for an invoice"""
    service = AccountsReceivableService(db)
    payments = await service.payment_repo.get_by_invoice(invoice_id)
    return payments


@router.post("/payments/{payment_id}/reconcile", response_model=PaymentRecordResponse)
async def reconcile_payment(
    payment_id: UUID,
    invoice_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark payment as reconciled"""
    service = AccountsReceivableService(db)
    try:
        payment = await service.reconcile_payment(
            payment_id,
            current_user.id,
            data.notes
        )
        return payment
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/payments/{payment_id}/refund", response_model=dict)
async def refund_payment(
    payment_id: UUID,
    invoice_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Process payment refund"""
    service = AccountsReceivableService(db)
    try:
        payment, credit_note = await service.refund_payment(
            payment_id,
            data.refund_amount,
            data.reason,
            current_user.id
        )
        return {
            "payment": payment,
            "credit_note": credit_note
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/payments/unreconciled", response_model=List[PaymentRecordResponse])
async def get_unreconciled_payments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all unreconciled payments"""
    service = AccountsReceivableService(db)
    payments = await service.payment_repo.get_unreconciled_payments()
    return payments


@router.post("/payments/bulk/reconcile", response_model=dict)
async def bulk_reconcile_payments(
    invoice_ids: List[UUID],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Bulk reconcile multiple payments"""
    service = AccountsReceivableService(db)
    results = {"success": [], "failed": []}
    
    for payment_id in data.payment_ids:
        try:
            await service.reconcile_payment(payment_id, current_user.id, data.notes)
            results["success"].append(str(payment_id))
        except Exception as e:
            results["failed"].append({"payment_id": str(payment_id), "error": str(e)})
    
    await db.commit()
    return results


# ========== Credit Note Endpoints ==========

@router.post("/credit-notes", response_model=CreditNoteResponse, status_code=status.HTTP_201_CREATED)
async def create_credit_note(
    data: CreditNoteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new credit note"""
    service = AccountsReceivableService(db)
    try:
        credit_note = await service.create_credit_note(data, current_user.id)
        return credit_note
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/credit-notes/{credit_note_id}", response_model=CreditNoteResponse)
async def get_credit_note(
    credit_note_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get credit note by ID"""
    service = AccountsReceivableService(db)
    credit_note = await service.credit_note_repo.get(credit_note_id)
    
    if not credit_note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credit note not found"
        )
    
    return credit_note


@router.get("/credit-notes", response_model=List[CreditNoteResponse])
async def list_credit_notes(
    reason: Optional[CreditNoteReason] = None,
    is_applied: Optional[bool] = None,
    is_expired: Optional[bool] = None,
    wholesale_customer_id: Optional[UUID] = None,
    retail_customer_id: Optional[UUID] = None,
    issue_date_from: Optional[date] = None,
    issue_date_to: Optional[date] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List credit notes with filters and pagination"""
    service = AccountsReceivableService(db)
    
    credit_notes, total = await service.credit_note_repo.search_credit_notes(
        reason=reason,
        is_applied=is_applied,
        is_expired=is_expired,
        wholesale_customer_id=wholesale_customer_id,
        retail_customer_id=retail_customer_id,
        issue_date_from=issue_date_from,
        issue_date_to=issue_date_to,
        skip=skip,
        limit=limit
    )
    
    return PaginatedResponse(
        items=credit_notes,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/credit-notes/invoice/{invoice_id}", response_model=List[CreditNoteResponse])
async def get_credit_notes_by_invoice(
    invoice_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all credit notes for an invoice"""
    service = AccountsReceivableService(db)
    credit_notes = await service.credit_note_repo.get_by_invoice(invoice_id)
    return credit_notes


@router.get("/credit-notes/customer/available", response_model=List[CreditNoteResponse])
async def get_available_credits(
    wholesale_customer_id: Optional[UUID] = None,
    retail_customer_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get available credit notes for customer"""
    if not wholesale_customer_id and not retail_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either wholesale_customer_id or retail_customer_id required"
        )
    
    service = AccountsReceivableService(db)
    credit_notes = await service.credit_note_repo.get_available_credits(
        wholesale_customer_id,
        retail_customer_id
    )
    return credit_notes


@router.post("/credit-notes/{credit_note_id}/approve", response_model=CreditNoteResponse)
async def approve_credit_note(
    credit_note_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Approve a credit note"""
    service = AccountsReceivableService(db)
    try:
        credit_note = await service.approve_credit_note(credit_note_id, current_user.id)
        return credit_note
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/credit-notes/apply", response_model=dict)
async def apply_credit_note(
    credit_note_id: UUID, invoice_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Apply credit note to invoice"""
    service = AccountsReceivableService(db)
    try:
        credit_note, invoice = await service.apply_credit_note(data, current_user.id)
        return {
            "credit_note": credit_note,
            "invoice": invoice
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ========== Payment Reminder Endpoints ==========

@router.post("/reminders", response_model=PaymentReminderResponse, status_code=status.HTTP_201_CREATED)
async def send_payment_reminder(
    data: PaymentReminderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send payment reminder"""
    service = AccountsReceivableService(db)
    try:
        reminder = await service.send_payment_reminder(
            data.invoice_id,
            data.reminder_type,
            current_user.id,
            data.custom_message
        )
        return reminder
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/reminders/invoice/{invoice_id}", response_model=List[PaymentReminderResponse])
async def get_reminders_by_invoice(
    invoice_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all reminders for an invoice"""
    service = AccountsReceivableService(db)
    reminders = await service.reminder_repo.get_by_invoice(invoice_id)
    return reminders


@router.post("/reminders/{reminder_id}/acknowledge", response_model=PaymentReminderResponse)
async def acknowledge_reminder(
    reminder_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Acknowledge payment reminder"""
    service = AccountsReceivableService(db)
    
    reminder = await service.reminder_repo.update(
        reminder_id,
        {
            "is_acknowledged": True,
            "acknowledged_at": data.acknowledged_at,
            "acknowledged_by": data.acknowledged_by
        }
    )
    await db.commit()
    
    return reminder


@router.post("/reminders/process-automated", response_model=dict)
async def process_automated_reminders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Process automated payment reminders for all overdue invoices"""
    service = AccountsReceivableService(db)
    results = await service.process_automated_reminders()
    
    return {
        "processed_at": datetime.utcnow().isoformat(),
        "results": {str(k): v for k, v in results.items()}
    }


# ========== Analytics & Reporting Endpoints ==========

@router.get("/analytics/aging-report", response_model=AgingReport)
async def get_aging_report(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get accounts receivable aging report"""
    service = AccountsReceivableService(db)
    report = await service.get_aging_report()
    return report


@router.get("/analytics/invoice-summary", response_model=InvoiceSummary)
async def get_invoice_summary(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get invoice summary statistics"""
    service = AccountsReceivableService(db)
    summary = await service.get_invoice_summary(start_date, end_date)
    return summary


@router.get("/analytics/payment-summary", response_model=PaymentSummary)
async def get_payment_summary(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get payment summary statistics"""
    service = AccountsReceivableService(db)
    summary = await service.get_payment_summary(start_date, end_date)
    return summary


@router.get("/analytics/customer-aging", response_model=AgingReport)
async def get_customer_aging_summary(
    wholesale_customer_id: Optional[UUID] = None,
    retail_customer_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get aging summary for specific customer"""
    if not wholesale_customer_id and not retail_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either wholesale_customer_id or retail_customer_id required"
        )
    
    service = AccountsReceivableService(db)
    summary = await service.get_customer_aging_summary(
        wholesale_customer_id,
        retail_customer_id
    )
    return summary


@router.get("/analytics/dashboard", response_model=dict)
async def get_ar_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive AR dashboard data"""
    service = AccountsReceivableService(db)
    dashboard = await service.get_ar_dashboard()
    return dashboard


# ========== Maintenance Endpoints ==========

@router.post("/maintenance/update-overdue", response_model=dict)
async def update_overdue_invoices(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update overdue flags for all invoices"""
    service = AccountsReceivableService(db)
    count = await service.update_overdue_invoices()
    
    return {
        "updated_count": count,
        "updated_at": datetime.utcnow().isoformat()
    }


@router.post("/maintenance/update-expired-credits", response_model=dict)
async def update_expired_credits(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark expired credit notes"""
    service = AccountsReceivableService(db)
    count = await service.update_expired_credits()
    
    return {
        "updated_count": count,
        "updated_at": datetime.utcnow().isoformat()
    }
