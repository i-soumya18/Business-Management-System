"""
Accounts Payable API Endpoints

REST API endpoints for bills, vendor payments, and expense management.
Provides comprehensive accounts payable functionality with approval workflows,
payment processing, and detailed reporting.
"""

from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.finance import BillStatus, ExpenseCategory, PaymentRecordStatus
from app.services.accounts_payable import AccountsPayableService
from app.schemas.accounts_payable import (
    # Bill schemas
    BillCreate,
    BillUpdate,
    BillStatusUpdate,
    BillApproval,
    BillResponse,
    BillWithSupplier,
    BillWithPayments,
    BillSearchParams,
    # Payment schemas
    VendorPaymentCreate,
    VendorPaymentUpdate,
    VendorPaymentResponse,
    VendorPaymentWithBill,
    VendorPaymentSearchParams,
    # Reporting schemas
    AgingReportParams,
    AgingReportResponse,
    ExpenseReportParams,
    ExpenseReportResponse,
    VendorPerformance,
    AccountsPayableDashboard,
    # Bulk operations
    BulkBillApproval,
    BulkBillStatusUpdate,
    BulkOperationResponse
)

router = APIRouter(prefix="/accounts-payable", tags=["Accounts Payable"])


# ==================== Bill Endpoints ====================

@router.post("/bills", response_model=BillResponse, status_code=status.HTTP_201_CREATED)
async def create_bill(
    bill_data: BillCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new bill
    
    Creates a new supplier bill/invoice in DRAFT status.
    Requires:
    - Supplier ID (must exist and be active)
    - Description and category
    - Financial details (subtotal, tax, total)
    - Bill and due dates
    """
    service = AccountsPayableService(db)
    try:
        bill = await service.create_bill(bill_data, created_by_id=current_user.id)
        return bill
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/bills/{bill_id}", response_model=BillWithSupplier)
async def get_bill(
    bill_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get bill by ID
    
    Returns bill details including supplier information.
    """
    service = AccountsPayableService(db)
    bill = await service.bill_repo.get_with_supplier(bill_id)
    
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    
    # Attach supplier info
    response_data = BillWithSupplier.model_validate(bill)
    if bill.supplier:
        response_data.supplier_name = bill.supplier.name
        response_data.supplier_code = bill.supplier.code
        response_data.supplier_email = bill.supplier.email
    
    return response_data


@router.get("/bills/{bill_id}/with-payments", response_model=BillWithPayments)
async def get_bill_with_payments(
    bill_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get bill with payment history
    
    Returns bill details including all associated payments.
    """
    service = AccountsPayableService(db)
    bill = await service.bill_repo.get_with_payments(bill_id)
    
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    
    return bill


@router.get("/bills/by-number/{bill_number}", response_model=BillResponse)
async def get_bill_by_number(
    bill_number: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get bill by bill number
    
    Lookup bill using its unique bill number.
    """
    service = AccountsPayableService(db)
    bill = await service.bill_repo.get_by_bill_number(bill_number)
    
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    
    return bill


@router.put("/bills/{bill_id}", response_model=BillResponse)
async def update_bill(
    bill_id: UUID,
    bill_data: BillUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update bill
    
    Update bill details. Only DRAFT and PENDING bills can be fully edited.
    """
    service = AccountsPayableService(db)
    try:
        bill = await service.update_bill(bill_id, bill_data)
        return bill
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/bills/{bill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bill(
    bill_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete bill
    
    Permanently delete a bill. Only DRAFT bills can be deleted.
    """
    service = AccountsPayableService(db)
    bill = await service.bill_repo.get(bill_id)
    
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    
    if bill.status != BillStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete bill in status: {bill.status.value}"
        )
    
    await service.bill_repo.delete(bill_id)
    await db.commit()


@router.post("/bills/{bill_id}/submit-for-approval", response_model=BillResponse)
async def submit_bill_for_approval(
    bill_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit bill for approval
    
    Submit a DRAFT bill for approval. Moves bill to PENDING status.
    """
    service = AccountsPayableService(db)
    try:
        bill = await service.submit_for_approval(bill_id)
        return bill
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/bills/{bill_id}/approve", response_model=BillResponse)
async def approve_bill(
    bill_id: UUID,
    approval_data: BillApproval,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Approve bill for payment
    
    Approve a PENDING bill. Moves bill to APPROVED status, ready for payment.
    """
    service = AccountsPayableService(db)
    try:
        bill = await service.approve_bill(
            bill_id,
            approved_by_id=current_user.id,
            notes=approval_data.notes
        )
        return bill
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/bills/{bill_id}/cancel", response_model=BillResponse)
async def cancel_bill(
    bill_id: UUID,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel bill
    
    Cancel a bill. Cannot cancel PAID bills or bills with payments.
    """
    service = AccountsPayableService(db)
    try:
        bill = await service.cancel_bill(bill_id, reason=reason)
        return bill
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/bills", response_model=dict)
async def search_bills(
    status: Optional[BillStatus] = None,
    supplier_id: Optional[UUID] = None,
    category: Optional[ExpenseCategory] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    bill_date_from: Optional[str] = None,
    bill_date_to: Optional[str] = None,
    due_date_from: Optional[str] = None,
    due_date_to: Optional[str] = None,
    is_overdue: Optional[bool] = None,
    search: Optional[str] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Search bills
    
    Search and filter bills with various criteria:
    - Status, supplier, category
    - Amount range
    - Date ranges
    - Overdue status
    - Text search (bill number, supplier bill number, description)
    
    Returns paginated results with total count.
    """
    service = AccountsPayableService(db)
    
    # Parse dates
    from datetime import datetime
    bill_date_from_parsed = datetime.fromisoformat(bill_date_from).date() if bill_date_from else None
    bill_date_to_parsed = datetime.fromisoformat(bill_date_to).date() if bill_date_to else None
    due_date_from_parsed = datetime.fromisoformat(due_date_from).date() if due_date_from else None
    due_date_to_parsed = datetime.fromisoformat(due_date_to).date() if due_date_to else None
    
    from decimal import Decimal
    min_amount_decimal = Decimal(str(min_amount)) if min_amount is not None else None
    max_amount_decimal = Decimal(str(max_amount)) if max_amount is not None else None
    
    bills, total = await service.bill_repo.search_bills(
        status=status,
        supplier_id=supplier_id,
        category=category,
        min_amount=min_amount_decimal,
        max_amount=max_amount_decimal,
        bill_date_from=bill_date_from_parsed,
        bill_date_to=bill_date_to_parsed,
        due_date_from=due_date_from_parsed,
        due_date_to=due_date_to_parsed,
        is_overdue=is_overdue,
        search=search,
        skip=skip,
        limit=limit
    )
    
    # Format response with supplier info
    bills_data = []
    for bill in bills:
        bill_dict = BillWithSupplier.model_validate(bill).model_dump()
        if bill.supplier:
            bill_dict["supplier_name"] = bill.supplier.name
            bill_dict["supplier_code"] = bill.supplier.code
        bills_data.append(bill_dict)
    
    return {
        "items": bills_data,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/bills/overdue", response_model=List[BillWithSupplier])
async def get_overdue_bills(
    supplier_id: Optional[UUID] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get overdue bills
    
    Returns bills that are past their due date and not fully paid.
    """
    service = AccountsPayableService(db)
    bills = await service.bill_repo.get_overdue_bills(supplier_id=supplier_id, skip=skip, limit=limit)
    
    # Format with supplier info
    results = []
    for bill in bills:
        bill_data = BillWithSupplier.model_validate(bill)
        if bill.supplier:
            bill_data.supplier_name = bill.supplier.name
            bill_data.supplier_code = bill.supplier.code
        results.append(bill_data)
    
    return results


@router.get("/bills/due-soon", response_model=List[BillWithSupplier])
async def get_bills_due_soon(
    days: int = Query(default=7, ge=1, le=90),
    supplier_id: Optional[UUID] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get bills due soon
    
    Returns bills due within specified number of days.
    Default is 7 days.
    """
    service = AccountsPayableService(db)
    bills = await service.bill_repo.get_due_soon(days=days, supplier_id=supplier_id, skip=skip, limit=limit)
    
    # Format with supplier info
    results = []
    for bill in bills:
        bill_data = BillWithSupplier.model_validate(bill)
        if bill.supplier:
            bill_data.supplier_name = bill.supplier.name
            bill_data.supplier_code = bill.supplier.code
        results.append(bill_data)
    
    return results


@router.get("/bills/pending-approval", response_model=List[BillWithSupplier])
async def get_pending_approval_bills(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get bills pending approval
    
    Returns all bills in PENDING status awaiting approval.
    """
    service = AccountsPayableService(db)
    bills = await service.bill_repo.get_pending_approval(skip=skip, limit=limit)
    
    # Format with supplier info
    results = []
    for bill in bills:
        bill_data = BillWithSupplier.model_validate(bill)
        if bill.supplier:
            bill_data.supplier_name = bill.supplier.name
            bill_data.supplier_code = bill.supplier.code
        results.append(bill_data)
    
    return results


@router.get("/bills/supplier/{supplier_id}", response_model=List[BillResponse])
async def get_bills_by_supplier(
    supplier_id: UUID,
    status: Optional[BillStatus] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get bills by supplier
    
    Returns all bills for a specific supplier, optionally filtered by status.
    """
    service = AccountsPayableService(db)
    bills = await service.bill_repo.get_by_supplier(supplier_id, status=status, skip=skip, limit=limit)
    return bills


# ==================== Vendor Payment Endpoints ====================

@router.post("/payments", response_model=VendorPaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_vendor_payment(
    payment_data: VendorPaymentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create vendor payment
    
    Record a payment against a bill. Automatically updates bill status:
    - Partially paid if payment < balance due
    - Paid if payment = balance due
    
    Validates:
    - Bill exists and is not cancelled
    - Payment amount <= balance due
    - Payment amount > 0
    """
    service = AccountsPayableService(db)
    try:
        payment = await service.create_payment(payment_data, created_by_id=current_user.id)
        return payment
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/payments/{payment_id}", response_model=VendorPaymentWithBill)
async def get_vendor_payment(
    payment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get vendor payment by ID
    
    Returns payment details including associated bill and supplier information.
    """
    service = AccountsPayableService(db)
    payment = await service.payment_repo.get_with_bill(payment_id)
    
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    
    # Format with bill info
    response_data = VendorPaymentWithBill.model_validate(payment)
    if payment.bill:
        response_data.bill_number = payment.bill.bill_number
        response_data.bill_total = payment.bill.total_amount
        if payment.bill.supplier:
            response_data.supplier_name = payment.bill.supplier.name
    
    return response_data


@router.get("/payments/by-number/{payment_number}", response_model=VendorPaymentResponse)
async def get_payment_by_number(
    payment_number: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get payment by payment number
    
    Lookup payment using its unique payment number.
    """
    service = AccountsPayableService(db)
    payment = await service.payment_repo.get_by_payment_number(payment_number)
    
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    
    return payment


@router.put("/payments/{payment_id}", response_model=VendorPaymentResponse)
async def update_vendor_payment(
    payment_id: UUID,
    payment_data: VendorPaymentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update vendor payment
    
    Update payment details. Cannot update amount or bill_id.
    """
    service = AccountsPayableService(db)
    payment = await service.payment_repo.get(payment_id)
    
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    
    # Update allowed fields
    update_data = payment_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(payment, key, value)
    
    await db.commit()
    await db.refresh(payment)
    
    return payment


@router.post("/payments/{payment_id}/cancel", response_model=VendorPaymentResponse)
async def cancel_vendor_payment(
    payment_id: UUID,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel vendor payment
    
    Cancel a payment and reverse it from the bill. Updates bill status accordingly.
    """
    service = AccountsPayableService(db)
    try:
        payment = await service.cancel_payment(payment_id, reason=reason)
        return payment
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/payments", response_model=dict)
async def search_vendor_payments(
    bill_id: Optional[UUID] = None,
    supplier_id: Optional[UUID] = None,
    status: Optional[PaymentRecordStatus] = None,
    payment_method: Optional[str] = None,
    payment_date_from: Optional[str] = None,
    payment_date_to: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    search: Optional[str] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Search vendor payments
    
    Search and filter payments with various criteria:
    - Bill ID, supplier, status, payment method
    - Amount range, date range
    - Text search (payment number, transaction reference, check number)
    
    Returns paginated results with total count.
    """
    service = AccountsPayableService(db)
    
    # Parse dates
    from datetime import datetime
    payment_date_from_parsed = datetime.fromisoformat(payment_date_from).date() if payment_date_from else None
    payment_date_to_parsed = datetime.fromisoformat(payment_date_to).date() if payment_date_to else None
    
    from decimal import Decimal
    min_amount_decimal = Decimal(str(min_amount)) if min_amount is not None else None
    max_amount_decimal = Decimal(str(max_amount)) if max_amount is not None else None
    
    payments, total = await service.payment_repo.search_payments(
        bill_id=bill_id,
        supplier_id=supplier_id,
        status=status,
        payment_method=payment_method,
        payment_date_from=payment_date_from_parsed,
        payment_date_to=payment_date_to_parsed,
        min_amount=min_amount_decimal,
        max_amount=max_amount_decimal,
        search=search,
        skip=skip,
        limit=limit
    )
    
    # Format with bill/supplier info
    payments_data = []
    for payment in payments:
        payment_dict = VendorPaymentWithBill.model_validate(payment).model_dump()
        if payment.bill:
            payment_dict["bill_number"] = payment.bill.bill_number
            payment_dict["bill_total"] = float(payment.bill.total_amount)
            if payment.bill.supplier:
                payment_dict["supplier_name"] = payment.bill.supplier.name
        payments_data.append(payment_dict)
    
    return {
        "items": payments_data,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/payments/bill/{bill_id}", response_model=List[VendorPaymentResponse])
async def get_payments_by_bill(
    bill_id: UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get payments for a bill
    
    Returns all payments associated with a specific bill.
    """
    service = AccountsPayableService(db)
    payments = await service.payment_repo.get_by_bill_id(bill_id, skip=skip, limit=limit)
    return payments


# ==================== Reporting & Analytics Endpoints ====================

@router.get("/reports/aging", response_model=AgingReportResponse)
async def get_aging_report(
    supplier_id: Optional[UUID] = None,
    category: Optional[ExpenseCategory] = None,
    as_of_date: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get aging report
    
    Comprehensive aging analysis showing:
    - Aging buckets (Current, 1-30, 31-60, 61-90, 90+ days)
    - Total outstanding and overdue amounts
    - Breakdown by supplier
    
    Helps identify overdue payables and cash flow planning.
    """
    service = AccountsPayableService(db)
    
    # Parse date
    from datetime import datetime
    as_of_date_parsed = datetime.fromisoformat(as_of_date).date() if as_of_date else None
    
    report = await service.get_aging_report(
        supplier_id=supplier_id,
        category=category,
        as_of_date=as_of_date_parsed
    )
    return report


@router.get("/reports/expenses", response_model=ExpenseReportResponse)
async def get_expense_report(
    category: Optional[ExpenseCategory] = None,
    supplier_id: Optional[UUID] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get expense report
    
    Comprehensive expense analysis showing:
    - Total expenses, paid, and outstanding amounts
    - Breakdown by expense category
    - Top suppliers by spend
    
    Defaults to current month if no date range specified.
    """
    service = AccountsPayableService(db)
    
    # Parse dates
    from datetime import datetime
    date_from_parsed = datetime.fromisoformat(date_from).date() if date_from else None
    date_to_parsed = datetime.fromisoformat(date_to).date() if date_to else None
    
    report = await service.get_expense_report(
        category=category,
        supplier_id=supplier_id,
        date_from=date_from_parsed,
        date_to=date_to_parsed
    )
    return report


@router.get("/reports/vendor-performance/{supplier_id}", response_model=VendorPerformance)
async def get_vendor_performance(
    supplier_id: UUID,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get vendor performance metrics
    
    Comprehensive vendor/supplier performance analysis:
    - Total bills and amounts (total, paid, outstanding)
    - Payment timing metrics (average days to pay, on-time rate)
    - Status breakdown (draft, pending, approved, paid, overdue)
    
    Helps evaluate vendor relationships and payment patterns.
    """
    service = AccountsPayableService(db)
    
    # Parse dates
    from datetime import datetime
    date_from_parsed = datetime.fromisoformat(date_from).date() if date_from else None
    date_to_parsed = datetime.fromisoformat(date_to).date() if date_to else None
    
    try:
        performance = await service.get_vendor_performance(
            supplier_id=supplier_id,
            date_from=date_from_parsed,
            date_to=date_to_parsed
        )
        return performance
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/dashboard", response_model=AccountsPayableDashboard)
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get AP dashboard data
    
    Comprehensive dashboard with:
    - Summary metrics (outstanding, overdue, due soon)
    - Status breakdown
    - Category breakdown (last 30 days)
    - Aging summary
    - Recent activity
    
    Provides quick overview of accounts payable health.
    """
    service = AccountsPayableService(db)
    dashboard = await service.get_dashboard_data()
    return dashboard


# ==================== Bulk Operations Endpoints ====================

@router.post("/bills/bulk-approve", response_model=BulkOperationResponse)
async def bulk_approve_bills(
    data: BulkBillApproval,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Bulk approve bills
    
    Approve multiple bills at once. Returns summary of successes and failures.
    """
    service = AccountsPayableService(db)
    result = await service.bulk_approve_bills(
        bill_ids=data.bill_ids,
        approved_by_id=current_user.id,
        notes=data.notes
    )
    return BulkOperationResponse(**result)


@router.post("/bills/bulk-update-status", response_model=BulkOperationResponse)
async def bulk_update_bill_status(
    data: BulkBillStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Bulk update bill status
    
    Update status for multiple bills at once. Returns summary of successes and failures.
    """
    service = AccountsPayableService(db)
    result = await service.bulk_update_status(
        bill_ids=data.bill_ids,
        status=data.status,
        notes=data.notes
    )
    return BulkOperationResponse(**result)
