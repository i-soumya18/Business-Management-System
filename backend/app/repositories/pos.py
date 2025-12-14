"""
Point of Sale (POS) Repository

Data access layer for POS operations including cashier shifts, cash drawer management,
transactions, and return/exchange processing.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.pos import (
    CashierShift,
    CashDrawer,
    POSTransaction,
    ReturnExchange,
    ShiftStatus,
    CashDrawerStatus,
    POSTransactionType
)
from app.repositories.base import BaseRepository


class CashierShiftRepository(BaseRepository[CashierShift]):
    """Repository for cashier shift operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(CashierShift, db)
    
    async def get_by_shift_number(self, shift_number: str) -> Optional[CashierShift]:
        """Get shift by shift number"""
        result = await self.db.execute(
            select(CashierShift).where(CashierShift.shift_number == shift_number)
        )
        return result.scalar_one_or_none()
    
    async def get_active_shifts(self) -> List[CashierShift]:
        """Get all active shifts"""
        result = await self.db.execute(
            select(CashierShift)
            .where(CashierShift.status == ShiftStatus.ACTIVE)
            .order_by(CashierShift.started_at.desc())
        )
        return list(result.scalars().all())
    
    async def get_active_shift_for_cashier(
        self,
        cashier_id: UUID
    ) -> Optional[CashierShift]:
        """Get active shift for a specific cashier"""
        result = await self.db.execute(
            select(CashierShift).where(
                and_(
                    CashierShift.cashier_id == cashier_id,
                    CashierShift.status == ShiftStatus.ACTIVE
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_shifts_by_cashier(
        self,
        cashier_id: UUID,
        status: Optional[ShiftStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[CashierShift]:
        """Get shifts for a specific cashier"""
        query = select(CashierShift).where(CashierShift.cashier_id == cashier_id)
        
        if status:
            query = query.where(CashierShift.status == status)
        
        query = query.order_by(CashierShift.started_at.desc()).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_shifts_by_register(
        self,
        register_number: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[CashierShift]:
        """Get shifts for a specific register"""
        query = select(CashierShift).where(
            CashierShift.register_number == register_number
        )
        
        if date_from:
            query = query.where(CashierShift.started_at >= date_from)
        if date_to:
            query = query.where(CashierShift.started_at <= date_to)
        
        query = query.order_by(CashierShift.started_at.desc())
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_shifts_by_date_range(
        self,
        date_from: datetime,
        date_to: datetime,
        status: Optional[ShiftStatus] = None
    ) -> List[CashierShift]:
        """Get shifts within a date range"""
        query = select(CashierShift).where(
            and_(
                CashierShift.started_at >= date_from,
                CashierShift.started_at <= date_to
            )
        )
        
        if status:
            query = query.where(CashierShift.status == status)
        
        query = query.order_by(CashierShift.started_at.desc())
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_shifts_with_variance(
        self,
        min_variance: Optional[Decimal] = None,
        max_variance: Optional[Decimal] = None
    ) -> List[CashierShift]:
        """Get shifts with cash variance within specified range"""
        query = select(CashierShift).where(
            CashierShift.status.in_([ShiftStatus.CLOSED, ShiftStatus.RECONCILED])
        )
        
        if min_variance is not None:
            query = query.where(CashierShift.cash_variance >= min_variance)
        if max_variance is not None:
            query = query.where(CashierShift.cash_variance <= max_variance)
        
        query = query.order_by(CashierShift.started_at.desc())
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def update_shift_totals(
        self,
        shift_id: UUID,
        transaction_amount: Decimal,
        transaction_type: POSTransactionType,
        payment_method: str
    ) -> CashierShift:
        """Update shift totals after a transaction"""
        shift = await self.get(shift_id)
        if not shift:
            raise ValueError(f"Shift {shift_id} not found")
        
        # Update transaction count
        shift.total_transactions += 1
        
        # Update totals based on transaction type
        if transaction_type == POSTransactionType.SALE:
            shift.total_sales += transaction_amount
        elif transaction_type == POSTransactionType.RETURN:
            shift.total_returns += transaction_amount
        elif transaction_type == POSTransactionType.EXCHANGE:
            shift.total_exchanges += transaction_amount
        
        # Update payment method totals
        payment_lower = payment_method.lower()
        if payment_lower == "cash":
            shift.cash_sales += transaction_amount
        elif payment_lower in ["card", "credit_card", "debit_card"]:
            shift.card_sales += transaction_amount
        elif payment_lower == "upi":
            shift.upi_sales += transaction_amount
        else:
            shift.other_sales += transaction_amount
        
        await self.db.commit()
        await self.db.refresh(shift)
        return shift
    
    async def generate_shift_number(self) -> str:
        """Generate unique shift number"""
        today = datetime.utcnow().strftime("%Y%m%d")
        
        # Get count of shifts today
        result = await self.db.execute(
            select(func.count(CashierShift.id)).where(
                func.date(CashierShift.started_at) == datetime.utcnow().date()
            )
        )
        count = result.scalar() or 0
        
        return f"SH-{today}-{count + 1:04d}"


class CashDrawerRepository(BaseRepository[CashDrawer]):
    """Repository for cash drawer operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(CashDrawer, db)
    
    async def get_by_shift(self, shift_id: UUID) -> Optional[CashDrawer]:
        """Get cash drawer for a specific shift"""
        result = await self.db.execute(
            select(CashDrawer).where(CashDrawer.shift_id == shift_id)
        )
        return result.scalar_one_or_none()
    
    async def update_balance(
        self,
        drawer_id: UUID,
        amount: Decimal,
        is_addition: bool = True
    ) -> CashDrawer:
        """Update cash drawer balance"""
        drawer = await self.get(drawer_id)
        if not drawer:
            raise ValueError(f"Cash drawer {drawer_id} not found")
        
        if is_addition:
            drawer.current_balance += amount
        else:
            drawer.current_balance -= amount
        
        drawer.last_transaction_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(drawer)
        return drawer
    
    async def close_drawer(
        self,
        drawer_id: UUID,
        final_balance: Decimal,
        expected_balance: Decimal
    ) -> CashDrawer:
        """Close cash drawer and set status"""
        drawer = await self.get(drawer_id)
        if not drawer:
            raise ValueError(f"Cash drawer {drawer_id} not found")
        
        drawer.current_balance = final_balance
        
        # Determine status based on variance
        variance = final_balance - expected_balance
        if variance > Decimal("0.00"):
            drawer.status = CashDrawerStatus.OVER
        elif variance < Decimal("0.00"):
            drawer.status = CashDrawerStatus.SHORT
        else:
            drawer.status = CashDrawerStatus.BALANCED
        
        await self.db.commit()
        await self.db.refresh(drawer)
        return drawer


class POSTransactionRepository(BaseRepository[POSTransaction]):
    """Repository for POS transaction operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(POSTransaction, db)
    
    async def get_by_transaction_number(
        self,
        transaction_number: str
    ) -> Optional[POSTransaction]:
        """Get transaction by transaction number"""
        result = await self.db.execute(
            select(POSTransaction).where(
                POSTransaction.transaction_number == transaction_number
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_receipt_number(
        self,
        receipt_number: str
    ) -> Optional[POSTransaction]:
        """Get transaction by receipt number"""
        result = await self.db.execute(
            select(POSTransaction).where(
                POSTransaction.receipt_number == receipt_number
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_shift(
        self,
        shift_id: UUID,
        transaction_type: Optional[POSTransactionType] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[POSTransaction]:
        """Get transactions for a specific shift"""
        query = select(POSTransaction).where(POSTransaction.shift_id == shift_id)
        
        if transaction_type:
            query = query.where(POSTransaction.transaction_type == transaction_type)
        
        query = query.order_by(POSTransaction.transaction_at.desc()).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_by_order(self, order_id: UUID) -> Optional[POSTransaction]:
        """Get transaction by order ID"""
        result = await self.db.execute(
            select(POSTransaction).where(POSTransaction.order_id == order_id)
        )
        return result.scalar_one_or_none()
    
    async def search_transactions(
        self,
        shift_id: Optional[UUID] = None,
        transaction_type: Optional[POSTransactionType] = None,
        payment_method: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        min_amount: Optional[Decimal] = None,
        max_amount: Optional[Decimal] = None,
        customer_phone: Optional[str] = None,
        customer_email: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[POSTransaction]:
        """Search transactions with filters"""
        query = select(POSTransaction)
        
        filters = []
        
        if shift_id:
            filters.append(POSTransaction.shift_id == shift_id)
        if transaction_type:
            filters.append(POSTransaction.transaction_type == transaction_type)
        if payment_method:
            filters.append(POSTransaction.payment_method == payment_method)
        if date_from:
            filters.append(POSTransaction.transaction_at >= date_from)
        if date_to:
            filters.append(POSTransaction.transaction_at <= date_to)
        if min_amount is not None:
            filters.append(POSTransaction.amount >= min_amount)
        if max_amount is not None:
            filters.append(POSTransaction.amount <= max_amount)
        if customer_phone:
            filters.append(POSTransaction.customer_phone.ilike(f"%{customer_phone}%"))
        if customer_email:
            filters.append(POSTransaction.customer_email.ilike(f"%{customer_email}%"))
        
        if filters:
            query = query.where(and_(*filters))
        
        query = query.order_by(POSTransaction.transaction_at.desc()).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_shift_summary(self, shift_id: UUID) -> dict:
        """Get transaction summary for a shift"""
        result = await self.db.execute(
            select(
                func.count(POSTransaction.id).label("total_transactions"),
                func.sum(
                    func.case(
                        (POSTransaction.transaction_type == POSTransactionType.SALE, POSTransaction.amount),
                        else_=0
                    )
                ).label("total_sales"),
                func.sum(
                    func.case(
                        (POSTransaction.transaction_type == POSTransactionType.RETURN, POSTransaction.amount),
                        else_=0
                    )
                ).label("total_returns"),
                func.sum(
                    func.case(
                        (POSTransaction.payment_method == "cash", POSTransaction.amount),
                        else_=0
                    )
                ).label("cash_amount"),
                func.sum(
                    func.case(
                        (POSTransaction.payment_method.in_(["card", "credit_card", "debit_card"]), POSTransaction.amount),
                        else_=0
                    )
                ).label("card_amount"),
                func.sum(
                    func.case(
                        (POSTransaction.payment_method == "upi", POSTransaction.amount),
                        else_=0
                    )
                ).label("upi_amount")
            ).where(POSTransaction.shift_id == shift_id)
        )
        
        row = result.first()
        
        return {
            "total_transactions": row.total_transactions or 0,
            "total_sales": row.total_sales or Decimal("0.00"),
            "total_returns": row.total_returns or Decimal("0.00"),
            "cash_amount": row.cash_amount or Decimal("0.00"),
            "card_amount": row.card_amount or Decimal("0.00"),
            "upi_amount": row.upi_amount or Decimal("0.00")
        }
    
    async def generate_transaction_number(self) -> str:
        """Generate unique transaction number"""
        today = datetime.utcnow().strftime("%Y%m%d")
        
        # Get count of transactions today
        result = await self.db.execute(
            select(func.count(POSTransaction.id)).where(
                func.date(POSTransaction.transaction_at) == datetime.utcnow().date()
            )
        )
        count = result.scalar() or 0
        
        return f"TXN-{today}-{count + 1:06d}"
    
    async def generate_receipt_number(self) -> str:
        """Generate unique receipt number"""
        today = datetime.utcnow().strftime("%Y%m%d")
        
        # Get count of receipts today
        result = await self.db.execute(
            select(func.count(POSTransaction.id)).where(
                and_(
                    POSTransaction.receipt_generated == True,
                    func.date(POSTransaction.transaction_at) == datetime.utcnow().date()
                )
            )
        )
        count = result.scalar() or 0
        
        return f"RCP-{today}-{count + 1:06d}"


class ReturnExchangeRepository(BaseRepository[ReturnExchange]):
    """Repository for return/exchange operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(ReturnExchange, db)
    
    async def get_by_return_number(
        self,
        return_number: str
    ) -> Optional[ReturnExchange]:
        """Get return/exchange by return number"""
        result = await self.db.execute(
            select(ReturnExchange).where(
                ReturnExchange.return_number == return_number
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_original_order(
        self,
        order_id: UUID
    ) -> List[ReturnExchange]:
        """Get all returns/exchanges for an original order"""
        result = await self.db.execute(
            select(ReturnExchange)
            .where(ReturnExchange.original_order_id == order_id)
            .order_by(ReturnExchange.returned_at.desc())
        )
        return list(result.scalars().all())
    
    async def get_pending_restocking(self) -> List[ReturnExchange]:
        """Get returns that need to be restocked"""
        result = await self.db.execute(
            select(ReturnExchange)
            .where(ReturnExchange.restocked == False)
            .order_by(ReturnExchange.returned_at.asc())
        )
        return list(result.scalars().all())
    
    async def search_returns(
        self,
        is_exchange: Optional[bool] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        processed_by: Optional[UUID] = None,
        restocked: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ReturnExchange]:
        """Search returns/exchanges with filters"""
        query = select(ReturnExchange)
        
        filters = []
        
        if is_exchange is not None:
            filters.append(ReturnExchange.is_exchange == is_exchange)
        if date_from:
            filters.append(ReturnExchange.returned_at >= date_from)
        if date_to:
            filters.append(ReturnExchange.returned_at <= date_to)
        if processed_by:
            filters.append(ReturnExchange.processed_by_id == processed_by)
        if restocked is not None:
            filters.append(ReturnExchange.restocked == restocked)
        
        if filters:
            query = query.where(and_(*filters))
        
        query = query.order_by(ReturnExchange.returned_at.desc()).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def generate_return_number(self) -> str:
        """Generate unique return number"""
        today = datetime.utcnow().strftime("%Y%m%d")
        
        # Get count of returns today
        result = await self.db.execute(
            select(func.count(ReturnExchange.id)).where(
                func.date(ReturnExchange.returned_at) == datetime.utcnow().date()
            )
        )
        count = result.scalar() or 0
        
        return f"RTN-{today}-{count + 1:05d}"
    
    async def get_return_statistics(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> dict:
        """Get return statistics for a period"""
        query = select(
            func.count(ReturnExchange.id).label("total_returns"),
            func.sum(
                func.case((ReturnExchange.is_exchange == True, 1), else_=0)
            ).label("total_exchanges"),
            func.sum(ReturnExchange.refund_amount).label("total_refunded"),
            func.sum(ReturnExchange.restocking_fee).label("total_restocking_fees")
        )
        
        filters = []
        if date_from:
            filters.append(ReturnExchange.returned_at >= date_from)
        if date_to:
            filters.append(ReturnExchange.returned_at <= date_to)
        
        if filters:
            query = query.where(and_(*filters))
        
        result = await self.db.execute(query)
        row = result.first()
        
        return {
            "total_returns": row.total_returns or 0,
            "total_exchanges": row.total_exchanges or 0,
            "total_refunded": row.total_refunded or Decimal("0.00"),
            "total_restocking_fees": row.total_restocking_fees or Decimal("0.00")
        }
