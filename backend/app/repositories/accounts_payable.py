"""
Accounts Payable Repositories

Data access layer for bills, vendor payments, and expense management.
"""

from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from decimal import Decimal
from datetime import datetime, date, timedelta

from sqlalchemy import select, func, and_, or_, desc, asc, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.models.finance import (
    Bill,
    VendorPayment,
    BillStatus,
    ExpenseCategory,
    PaymentRecordStatus
)
from app.models.supplier import Supplier
from app.repositories.base import BaseRepository


class BillRepository(BaseRepository[Bill]):
    """Repository for Bill operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Bill, db)
    
    async def get_by_bill_number(self, bill_number: str) -> Optional[Bill]:
        """Get bill by bill number"""
        query = select(Bill).where(Bill.bill_number == bill_number)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_with_supplier(self, bill_id: UUID) -> Optional[Bill]:
        """Get bill with supplier details loaded"""
        query = (
            select(Bill)
            .options(joinedload(Bill.supplier))
            .where(Bill.id == bill_id)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_with_payments(self, bill_id: UUID) -> Optional[Bill]:
        """Get bill with all payments loaded"""
        query = (
            select(Bill)
            .options(
                selectinload(Bill.payments),
                joinedload(Bill.supplier)
            )
            .where(Bill.id == bill_id)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_supplier(
        self,
        supplier_id: UUID,
        status: Optional[BillStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Bill]:
        """Get bills by supplier"""
        filters = [Bill.supplier_id == supplier_id]
        if status:
            filters.append(Bill.status == status)
        
        query = (
            select(Bill)
            .where(and_(*filters))
            .order_by(Bill.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_by_status(
        self,
        status: BillStatus,
        skip: int = 0,
        limit: int = 100
    ) -> List[Bill]:
        """Get bills by status"""
        query = (
            select(Bill)
            .where(Bill.status == status)
            .order_by(Bill.due_date.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_overdue_bills(
        self,
        supplier_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Bill]:
        """Get overdue bills"""
        today = date.today()
        filters = [
            Bill.status.in_([
                BillStatus.PENDING,
                BillStatus.APPROVED,
                BillStatus.PARTIALLY_PAID
            ]),
            Bill.due_date < today
        ]
        
        if supplier_id:
            filters.append(Bill.supplier_id == supplier_id)
        
        query = (
            select(Bill)
            .where(and_(*filters))
            .order_by(Bill.due_date.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_due_soon(
        self,
        days: int = 7,
        supplier_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Bill]:
        """Get bills due within specified days"""
        today = date.today()
        future_date = today + timedelta(days=days)
        
        filters = [
            Bill.status.in_([
                BillStatus.PENDING,
                BillStatus.APPROVED,
                BillStatus.PARTIALLY_PAID
            ]),
            Bill.due_date >= today,
            Bill.due_date <= future_date
        ]
        
        if supplier_id:
            filters.append(Bill.supplier_id == supplier_id)
        
        query = (
            select(Bill)
            .where(and_(*filters))
            .order_by(Bill.due_date.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def search_bills(
        self,
        status: Optional[BillStatus] = None,
        supplier_id: Optional[UUID] = None,
        category: Optional[ExpenseCategory] = None,
        min_amount: Optional[Decimal] = None,
        max_amount: Optional[Decimal] = None,
        bill_date_from: Optional[date] = None,
        bill_date_to: Optional[date] = None,
        due_date_from: Optional[date] = None,
        due_date_to: Optional[date] = None,
        is_overdue: Optional[bool] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Bill], int]:
        """Search bills with filters"""
        filters = []
        
        if status:
            filters.append(Bill.status == status)
        if supplier_id:
            filters.append(Bill.supplier_id == supplier_id)
        if category:
            filters.append(Bill.category == category)
        if min_amount is not None:
            filters.append(Bill.total_amount >= min_amount)
        if max_amount is not None:
            filters.append(Bill.total_amount <= max_amount)
        if bill_date_from:
            filters.append(Bill.bill_date >= bill_date_from)
        if bill_date_to:
            filters.append(Bill.bill_date <= bill_date_to)
        if due_date_from:
            filters.append(Bill.due_date >= due_date_from)
        if due_date_to:
            filters.append(Bill.due_date <= due_date_to)
        if is_overdue is not None:
            today = date.today()
            if is_overdue:
                filters.append(and_(
                    Bill.status.in_([
                        BillStatus.PENDING,
                        BillStatus.APPROVED,
                        BillStatus.PARTIALLY_PAID
                    ]),
                    Bill.due_date < today
                ))
            else:
                filters.append(or_(
                    Bill.status.in_([BillStatus.PAID, BillStatus.CANCELLED]),
                    Bill.due_date >= today
                ))
        
        if search:
            filters.append(or_(
                Bill.bill_number.ilike(f"%{search}%"),
                Bill.supplier_bill_number.ilike(f"%{search}%"),
                Bill.description.ilike(f"%{search}%")
            ))
        
        # Count query
        count_query = select(func.count(Bill.id)).where(and_(*filters))
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()
        
        # Data query with supplier
        query = (
            select(Bill)
            .options(joinedload(Bill.supplier))
            .where(and_(*filters))
            .order_by(Bill.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        bills = list(result.scalars().unique().all())
        
        return bills, total
    
    async def get_by_category(
        self,
        category: ExpenseCategory,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Bill]:
        """Get bills by category"""
        filters = [Bill.category == category]
        
        if date_from:
            filters.append(Bill.bill_date >= date_from)
        if date_to:
            filters.append(Bill.bill_date <= date_to)
        
        query = (
            select(Bill)
            .where(and_(*filters))
            .order_by(Bill.bill_date.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_pending_approval(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[Bill]:
        """Get bills pending approval"""
        query = (
            select(Bill)
            .where(Bill.status == BillStatus.PENDING)
            .order_by(Bill.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def calculate_total_outstanding(
        self,
        supplier_id: Optional[UUID] = None,
        category: Optional[ExpenseCategory] = None
    ) -> Decimal:
        """Calculate total outstanding amount"""
        filters = [
            Bill.status.in_([
                BillStatus.PENDING,
                BillStatus.APPROVED,
                BillStatus.PARTIALLY_PAID
            ])
        ]
        
        if supplier_id:
            filters.append(Bill.supplier_id == supplier_id)
        if category:
            filters.append(Bill.category == category)
        
        query = select(func.sum(Bill.balance_due)).where(and_(*filters))
        result = await self.db.execute(query)
        total = result.scalar_one_or_none()
        return total or Decimal("0.00")
    
    async def calculate_total_overdue(
        self,
        supplier_id: Optional[UUID] = None
    ) -> Decimal:
        """Calculate total overdue amount"""
        today = date.today()
        filters = [
            Bill.status.in_([
                BillStatus.PENDING,
                BillStatus.APPROVED,
                BillStatus.PARTIALLY_PAID
            ]),
            Bill.due_date < today
        ]
        
        if supplier_id:
            filters.append(Bill.supplier_id == supplier_id)
        
        query = select(func.sum(Bill.balance_due)).where(and_(*filters))
        result = await self.db.execute(query)
        total = result.scalar_one_or_none()
        return total or Decimal("0.00")
    
    async def get_aging_report(
        self,
        supplier_id: Optional[UUID] = None,
        category: Optional[ExpenseCategory] = None,
        as_of_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Get aging report with buckets"""
        reference_date = as_of_date or date.today()
        
        filters = [
            Bill.status.in_([
                BillStatus.PENDING,
                BillStatus.APPROVED,
                BillStatus.PARTIALLY_PAID
            ])
        ]
        
        if supplier_id:
            filters.append(Bill.supplier_id == supplier_id)
        if category:
            filters.append(Bill.category == category)
        
        # Define aging buckets
        aging_case = case(
            (Bill.due_date >= reference_date, "Current"),
            (Bill.due_date >= reference_date - timedelta(days=30), "1-30 days"),
            (Bill.due_date >= reference_date - timedelta(days=60), "31-60 days"),
            (Bill.due_date >= reference_date - timedelta(days=90), "61-90 days"),
            else_="90+ days"
        ).label("aging_bucket")
        
        query = (
            select(
                aging_case,
                func.count(Bill.id).label("count"),
                func.sum(Bill.balance_due).label("total")
            )
            .where(and_(*filters))
            .group_by(aging_case)
        )
        
        result = await self.db.execute(query)
        return [
            {
                "bucket": row.aging_bucket,
                "count": row.count,
                "total_amount": row.total or Decimal("0.00")
            }
            for row in result.all()
        ]
    
    async def get_expense_summary(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        supplier_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Get expense summary by category"""
        filters = []
        
        if date_from:
            filters.append(Bill.bill_date >= date_from)
        if date_to:
            filters.append(Bill.bill_date <= date_to)
        if supplier_id:
            filters.append(Bill.supplier_id == supplier_id)
        
        query = (
            select(
                Bill.category,
                func.count(Bill.id).label("bill_count"),
                func.sum(Bill.total_amount).label("total_amount"),
                func.sum(Bill.paid_amount).label("paid_amount"),
                func.sum(Bill.balance_due).label("outstanding_amount")
            )
            .where(and_(*filters) if filters else True)
            .group_by(Bill.category)
            .order_by(desc("total_amount"))
        )
        
        result = await self.db.execute(query)
        return [
            {
                "category": row.category,
                "bill_count": row.bill_count,
                "total_amount": row.total_amount or Decimal("0.00"),
                "paid_amount": row.paid_amount or Decimal("0.00"),
                "outstanding_amount": row.outstanding_amount or Decimal("0.00")
            }
            for row in result.all()
        ]
    
    async def get_by_status_counts(self) -> Dict[str, int]:
        """Get bill counts by status"""
        query = (
            select(
                Bill.status,
                func.count(Bill.id).label("count")
            )
            .group_by(Bill.status)
        )
        
        result = await self.db.execute(query)
        return {row.status.value: row.count for row in result.all()}


class VendorPaymentRepository(BaseRepository[VendorPayment]):
    """Repository for Vendor Payment operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(VendorPayment, db)
    
    async def get_by_payment_number(self, payment_number: str) -> Optional[VendorPayment]:
        """Get vendor payment by payment number"""
        query = select(VendorPayment).where(VendorPayment.payment_number == payment_number)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_bill_id(
        self,
        bill_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[VendorPayment]:
        """Get all payments for a bill"""
        query = (
            select(VendorPayment)
            .where(VendorPayment.bill_id == bill_id)
            .order_by(VendorPayment.payment_date.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_with_bill(self, payment_id: UUID) -> Optional[VendorPayment]:
        """Get payment with bill details"""
        query = (
            select(VendorPayment)
            .options(
                joinedload(VendorPayment.bill).joinedload(Bill.supplier)
            )
            .where(VendorPayment.id == payment_id)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def search_payments(
        self,
        bill_id: Optional[UUID] = None,
        supplier_id: Optional[UUID] = None,
        status: Optional[PaymentRecordStatus] = None,
        payment_method: Optional[str] = None,
        payment_date_from: Optional[date] = None,
        payment_date_to: Optional[date] = None,
        min_amount: Optional[Decimal] = None,
        max_amount: Optional[Decimal] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[VendorPayment], int]:
        """Search vendor payments with filters"""
        filters = []
        
        if bill_id:
            filters.append(VendorPayment.bill_id == bill_id)
        if status:
            filters.append(VendorPayment.status == status)
        if payment_method:
            filters.append(VendorPayment.payment_method == payment_method)
        if payment_date_from:
            filters.append(VendorPayment.payment_date >= payment_date_from)
        if payment_date_to:
            filters.append(VendorPayment.payment_date <= payment_date_to)
        if min_amount is not None:
            filters.append(VendorPayment.amount >= min_amount)
        if max_amount is not None:
            filters.append(VendorPayment.amount <= max_amount)
        
        # Handle supplier filter
        if supplier_id:
            filters.append(Bill.supplier_id == supplier_id)
        
        if search:
            filters.append(or_(
                VendorPayment.payment_number.ilike(f"%{search}%"),
                VendorPayment.transaction_reference.ilike(f"%{search}%"),
                VendorPayment.check_number.ilike(f"%{search}%")
            ))
        
        # Count query
        count_query = (
            select(func.count(VendorPayment.id))
            .join(Bill, VendorPayment.bill_id == Bill.id)
            .where(and_(*filters))
        )
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()
        
        # Data query
        query = (
            select(VendorPayment)
            .join(Bill, VendorPayment.bill_id == Bill.id)
            .options(
                joinedload(VendorPayment.bill).joinedload(Bill.supplier)
            )
            .where(and_(*filters))
            .order_by(VendorPayment.payment_date.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        payments = list(result.scalars().unique().all())
        
        return payments, total
    
    async def get_payment_summary(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> Dict[str, Any]:
        """Get payment summary statistics"""
        filters = []
        
        if date_from:
            filters.append(VendorPayment.payment_date >= date_from)
        if date_to:
            filters.append(VendorPayment.payment_date <= date_to)
        
        query = select(
            func.count(VendorPayment.id).label("count"),
            func.sum(VendorPayment.amount).label("total"),
            func.avg(VendorPayment.amount).label("average")
        ).where(and_(*filters) if filters else True)
        
        result = await self.db.execute(query)
        row = result.one()
        
        return {
            "payment_count": row.count or 0,
            "total_payments": row.total or Decimal("0.00"),
            "average_payment": row.average or Decimal("0.00")
        }
    
    async def get_by_method_summary(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> Dict[str, Decimal]:
        """Get payment summary by method"""
        filters = [VendorPayment.status == PaymentRecordStatus.COMPLETED]
        
        if date_from:
            filters.append(VendorPayment.payment_date >= date_from)
        if date_to:
            filters.append(VendorPayment.payment_date <= date_to)
        
        query = (
            select(
                VendorPayment.payment_method,
                func.sum(VendorPayment.amount).label("total")
            )
            .where(and_(*filters))
            .group_by(VendorPayment.payment_method)
        )
        
        result = await self.db.execute(query)
        return {row.payment_method: row.total or Decimal("0.00") for row in result.all()}
    
    async def get_recent_payments(
        self,
        days: int = 7,
        limit: int = 10
    ) -> List[VendorPayment]:
        """Get recent payments"""
        cutoff_date = date.today() - timedelta(days=days)
        
        query = (
            select(VendorPayment)
            .options(
                joinedload(VendorPayment.bill).joinedload(Bill.supplier)
            )
            .where(VendorPayment.payment_date >= cutoff_date)
            .order_by(VendorPayment.payment_date.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().unique().all())
