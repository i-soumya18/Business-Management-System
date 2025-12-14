"""
Point of Sale (POS) API Routes

API endpoints for POS operations including cashier shifts, sales transactions,
returns, exchanges, and cash drawer management.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.pos import ShiftStatus, POSTransactionType
from app.repositories.pos import (
    CashierShiftRepository,
    CashDrawerRepository,
    POSTransactionRepository,
    ReturnExchangeRepository
)
from app.repositories.product import ProductVariantRepository
from app.repositories.inventory import InventoryLevelRepository
from app.services.pos import POSService
from app.schemas.pos import (
    CashierShiftCreate,
    CashierShiftClose,
    CashierShiftReconcile,
    CashierShiftResponse,
    CashierShiftSummary,
    CashDrawerResponse,
    CashMovement,
    POSTransactionCreate,
    POSTransactionResponse,
    POSSaleCreate,
    POSSaleResponse,
    ReturnExchangeCreate,
    ReturnExchangeResponse,
    ShiftAnalytics,
    ShiftSearchFilters,
    TransactionSearchFilters
)

router = APIRouter(prefix="/pos", tags=["Point of Sale"])


def get_pos_service(db: AsyncSession = Depends(get_db)) -> POSService:
    """Dependency to get POS service"""
    return POSService(
        db=db,
        shift_repo=CashierShiftRepository(db),
        drawer_repo=CashDrawerRepository(db),
        transaction_repo=POSTransactionRepository(db),
        return_repo=ReturnExchangeRepository(db),
        variant_repo=ProductVariantRepository(db),
        inventory_repo=InventoryLevelRepository(db)
    )


# ==================== Cashier Shift Endpoints ====================

@router.post("/shifts", response_model=CashierShiftResponse, status_code=status.HTTP_201_CREATED)
async def start_shift(
    shift_data: CashierShiftCreate,
    current_user: User = Depends(get_current_user),
    service: POSService = Depends(get_pos_service)
):
    """
    Start a new cashier shift
    
    - **register_number**: Register/POS terminal number
    - **opening_cash**: Starting cash amount in drawer
    - **opening_notes**: Optional notes about shift opening
    """
    try:
        shift = await service.start_shift(current_user.id, shift_data)
        return shift
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/shifts/active", response_model=Optional[CashierShiftResponse])
async def get_my_active_shift(
    current_user: User = Depends(get_current_user),
    service: POSService = Depends(get_pos_service)
):
    """Get current user's active shift"""
    shift = await service.get_active_shift_for_cashier(current_user.id)
    return shift


@router.get("/shifts", response_model=List[CashierShiftSummary])
async def list_shifts(
    status_filter: Optional[ShiftStatus] = Query(None, alias="status"),
    cashier_id: Optional[UUID] = None,
    register_number: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List cashier shifts with optional filters
    
    - **status**: Filter by shift status
    - **cashier_id**: Filter by specific cashier
    - **register_number**: Filter by register number
    - **date_from**: Start date for date range
    - **date_to**: End date for date range
    """
    shift_repo = CashierShiftRepository(db)
    
    if cashier_id:
        shifts = await shift_repo.get_shifts_by_cashier(
            cashier_id, status_filter, skip, limit
        )
    elif register_number and (date_from or date_to):
        shifts = await shift_repo.get_shifts_by_register(
            register_number, date_from, date_to
        )
    elif date_from and date_to:
        shifts = await shift_repo.get_shifts_by_date_range(
            date_from, date_to, status_filter
        )
    else:
        shifts = await shift_repo.list(skip=skip, limit=limit)
    
    return shifts


@router.get("/shifts/{shift_id}", response_model=CashierShiftResponse)
async def get_shift(
    shift_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get cashier shift by ID"""
    shift_repo = CashierShiftRepository(db)
    shift = await shift_repo.get(shift_id)
    
    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shift {shift_id} not found"
        )
    
    return shift


@router.post("/shifts/{shift_id}/close", response_model=CashierShiftResponse)
async def close_shift(
    shift_id: UUID,
    close_data: CashierShiftClose,
    current_user: User = Depends(get_current_user),
    service: POSService = Depends(get_pos_service)
):
    """
    Close a cashier shift
    
    - **closing_cash**: Actual cash count in drawer
    - **closing_notes**: Optional closing notes
    - **denomination_breakdown**: Optional cash denomination breakdown
    """
    try:
        shift = await service.close_shift(shift_id, close_data)
        return shift
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/shifts/{shift_id}/reconcile", response_model=CashierShiftResponse)
async def reconcile_shift(
    shift_id: UUID,
    reconcile_data: CashierShiftReconcile,
    current_user: User = Depends(get_current_user),
    service: POSService = Depends(get_pos_service)
):
    """
    Reconcile a closed shift
    
    Mark shift as reconciled after review.
    """
    try:
        shift = await service.reconcile_shift(
            shift_id,
            reconcile_data.reconciliation_notes
        )
        return shift
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/shifts/{shift_id}/analytics", response_model=ShiftAnalytics)
async def get_shift_analytics(
    shift_id: UUID,
    current_user: User = Depends(get_current_user),
    service: POSService = Depends(get_pos_service)
):
    """Get detailed analytics for a shift"""
    try:
        analytics = await service.get_shift_analytics(shift_id)
        return analytics
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ==================== Cash Drawer Endpoints ====================

@router.get("/shifts/{shift_id}/drawer", response_model=CashDrawerResponse)
async def get_drawer_status(
    shift_id: UUID,
    current_user: User = Depends(get_current_user),
    service: POSService = Depends(get_pos_service)
):
    """Get cash drawer status for a shift"""
    drawer = await service.get_drawer_status(shift_id)
    
    if not drawer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cash drawer not found for shift {shift_id}"
        )
    
    return drawer


@router.post("/shifts/{shift_id}/drawer/cash-in")
async def add_cash_to_drawer(
    shift_id: UUID,
    cash_movement: CashMovement,
    current_user: User = Depends(get_current_user),
    service: POSService = Depends(get_pos_service)
):
    """
    Add cash to drawer
    
    Used for cash deposits or adding starting cash.
    """
    try:
        result = await service.add_cash_to_drawer(shift_id, cash_movement)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/shifts/{shift_id}/drawer/cash-out")
async def remove_cash_from_drawer(
    shift_id: UUID,
    cash_movement: CashMovement,
    current_user: User = Depends(get_current_user),
    service: POSService = Depends(get_pos_service)
):
    """
    Remove cash from drawer
    
    Used for cash drops, payouts, or petty cash.
    """
    try:
        result = await service.remove_cash_from_drawer(shift_id, cash_movement)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ==================== Transaction Endpoints ====================

@router.post("/sales", response_model=POSSaleResponse, status_code=status.HTTP_201_CREATED)
async def create_sale(
    sale_data: POSSaleCreate,
    current_user: User = Depends(get_current_user),
    service: POSService = Depends(get_pos_service)
):
    """
    Process a POS sale
    
    - **items**: List of items being purchased
    - **payment_method**: Payment method (cash, card, upi, etc.)
    - **customer_name**: Optional customer name
    - **customer_phone**: Optional customer phone
    - **customer_email**: Optional customer email
    - **subtotal_discount**: Optional discount on subtotal
    - **amount_tendered**: Amount given by customer (for cash)
    - **notes**: Optional transaction notes
    """
    try:
        result = await service.process_sale(current_user.id, sale_data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/transactions", response_model=List[POSTransactionResponse])
async def list_transactions(
    shift_id: Optional[UUID] = None,
    transaction_type: Optional[POSTransactionType] = None,
    payment_method: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List POS transactions with optional filters
    
    - **shift_id**: Filter by specific shift
    - **transaction_type**: Filter by transaction type
    - **payment_method**: Filter by payment method
    - **date_from**: Start date for date range
    - **date_to**: End date for date range
    """
    transaction_repo = POSTransactionRepository(db)
    
    if shift_id:
        transactions = await transaction_repo.get_by_shift(
            shift_id, transaction_type, skip, limit
        )
    else:
        transactions = await transaction_repo.search_transactions(
            transaction_type=transaction_type,
            payment_method=payment_method,
            date_from=date_from,
            date_to=date_to,
            skip=skip,
            limit=limit
        )
    
    return transactions


@router.get("/transactions/{transaction_id}", response_model=POSTransactionResponse)
async def get_transaction(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get POS transaction by ID"""
    transaction_repo = POSTransactionRepository(db)
    transaction = await transaction_repo.get(transaction_id)
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {transaction_id} not found"
        )
    
    return transaction


@router.get("/transactions/number/{transaction_number}", response_model=POSTransactionResponse)
async def get_transaction_by_number(
    transaction_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get POS transaction by transaction number"""
    transaction_repo = POSTransactionRepository(db)
    transaction = await transaction_repo.get_by_transaction_number(transaction_number)
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {transaction_number} not found"
        )
    
    return transaction


# ==================== Return/Exchange Endpoints ====================

@router.post("/returns", response_model=ReturnExchangeResponse, status_code=status.HTTP_201_CREATED)
async def create_return(
    return_data: ReturnExchangeCreate,
    current_user: User = Depends(get_current_user),
    service: POSService = Depends(get_pos_service)
):
    """
    Process a product return or exchange
    
    - **is_exchange**: Whether this is an exchange (vs return)
    - **original_order_id**: Original order being returned
    - **new_order_id**: New order (required for exchanges)
    - **returned_items**: List of items being returned
    - **reason**: Return reason
    - **reason_description**: Detailed reason description
    - **restocking_fee**: Any restocking fee to charge
    - **notes**: Optional notes
    """
    try:
        result = await service.process_return(current_user.id, return_data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/returns", response_model=List[ReturnExchangeResponse])
async def list_returns(
    is_exchange: Optional[bool] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    restocked: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List returns/exchanges with optional filters
    
    - **is_exchange**: Filter by exchanges only
    - **date_from**: Start date for date range
    - **date_to**: End date for date range
    - **restocked**: Filter by restocking status
    """
    return_repo = ReturnExchangeRepository(db)
    
    returns = await return_repo.search_returns(
        is_exchange=is_exchange,
        date_from=date_from,
        date_to=date_to,
        restocked=restocked,
        skip=skip,
        limit=limit
    )
    
    return returns


@router.get("/returns/{return_id}", response_model=ReturnExchangeResponse)
async def get_return(
    return_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get return/exchange by ID"""
    return_repo = ReturnExchangeRepository(db)
    return_exchange = await return_repo.get(return_id)
    
    if not return_exchange:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Return {return_id} not found"
        )
    
    return return_exchange


@router.get("/returns/number/{return_number}", response_model=ReturnExchangeResponse)
async def get_return_by_number(
    return_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get return/exchange by return number"""
    return_repo = ReturnExchangeRepository(db)
    return_exchange = await return_repo.get_by_return_number(return_number)
    
    if not return_exchange:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Return {return_number} not found"
        )
    
    return return_exchange


@router.post("/returns/{return_id}/restock", response_model=ReturnExchangeResponse)
async def restock_return(
    return_id: UUID,
    location_id: UUID,
    current_user: User = Depends(get_current_user),
    service: POSService = Depends(get_pos_service)
):
    """
    Restock items from a return
    
    Updates inventory levels for returned items.
    """
    try:
        result = await service.restock_return_items(return_id, location_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/returns/order/{order_id}", response_model=List[ReturnExchangeResponse])
async def get_returns_for_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all returns/exchanges for an order"""
    return_repo = ReturnExchangeRepository(db)
    returns = await return_repo.get_by_original_order(order_id)
    
    return returns


# ==================== Analytics Endpoints ====================

@router.get("/analytics/daily-summary")
async def get_daily_summary(
    date: datetime = Query(default_factory=datetime.utcnow),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get daily POS summary
    
    Aggregated sales, returns, and payment method breakdown for a specific date.
    """
    shift_repo = CashierShiftRepository(db)
    transaction_repo = POSTransactionRepository(db)
    return_repo = ReturnExchangeRepository(db)
    
    # Get date range (full day)
    from datetime import timedelta
    date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    date_end = date_start + timedelta(days=1)
    
    # Get shifts for the day
    shifts = await shift_repo.get_shifts_by_date_range(date_start, date_end)
    
    # Calculate totals
    total_shifts = len(shifts)
    total_transactions = sum(s.total_transactions for s in shifts)
    gross_sales = sum(s.total_sales for s in shifts)
    total_returns = sum(s.total_returns for s in shifts)
    cash_sales = sum(s.cash_sales for s in shifts)
    card_sales = sum(s.card_sales for s in shifts)
    upi_sales = sum(s.upi_sales for s in shifts)
    
    net_sales = gross_sales - total_returns
    avg_transaction = gross_sales / total_transactions if total_transactions > 0 else 0
    
    # Get return statistics
    return_stats = await return_repo.get_return_statistics(date_start, date_end)
    
    return {
        "date": date,
        "total_shifts": total_shifts,
        "total_transactions": total_transactions,
        "gross_sales": gross_sales,
        "net_sales": net_sales,
        "total_returns": total_returns,
        "cash_sales": cash_sales,
        "card_sales": card_sales,
        "upi_sales": upi_sales,
        "average_transaction_value": avg_transaction,
        "return_statistics": return_stats
    }


@router.get("/analytics/shifts-with-variance")
async def get_shifts_with_variance(
    min_variance: Optional[float] = Query(None, description="Minimum variance threshold"),
    max_variance: Optional[float] = Query(None, description="Maximum variance threshold"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get shifts with cash variance
    
    Find shifts where actual cash doesn't match expected cash.
    Useful for identifying discrepancies and potential issues.
    """
    from decimal import Decimal
    
    shift_repo = CashierShiftRepository(db)
    
    shifts = await shift_repo.get_shifts_with_variance(
        min_variance=Decimal(str(min_variance)) if min_variance is not None else None,
        max_variance=Decimal(str(max_variance)) if max_variance is not None else None
    )
    
    return [
        {
            "shift_id": s.id,
            "shift_number": s.shift_number,
            "cashier_id": s.cashier_id,
            "register_number": s.register_number,
            "started_at": s.started_at,
            "ended_at": s.ended_at,
            "expected_cash": s.expected_cash,
            "closing_cash": s.closing_cash,
            "cash_variance": s.cash_variance,
            "variance_percentage": (
                (s.cash_variance / s.expected_cash * 100) if s.expected_cash > 0 else 0
            )
        }
        for s in shifts
    ]
