"""
Accounts Receivable Repositories

Data access layer for invoices, payments, credit notes, and payment reminders.
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from decimal import Decimal
from datetime import datetime, date, timedelta

from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.finance import (
    Invoice,
    InvoiceItem,
    PaymentRecord,
    CreditNote,
    PaymentReminder,
    InvoiceStatus,
    PaymentRecordStatus,
    CreditNoteReason,
    ReminderType
)
from app.repositories.base import BaseRepository


class InvoiceRepository(BaseRepository[Invoice]):
    """Repository for Invoice operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Invoice, db)
    
    async def get_by_invoice_number(self, invoice_number: str) -> Optional[Invoice]:
        """Get invoice by invoice number"""
        query = select(Invoice).where(Invoice.invoice_number == invoice_number)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_with_items(self, invoice_id: UUID) -> Optional[Invoice]:
        """Get invoice with all items loaded"""
        query = (
            select(Invoice)
            .options(selectinload(Invoice.items))
            .where(Invoice.id == invoice_id)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_order_id(self, order_id: UUID) -> List[Invoice]:
        """Get all invoices for an order"""
        query = (
            select(Invoice)
            .where(Invoice.order_id == order_id)
            .order_by(Invoice.created_at.desc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_by_customer(
        self,
        wholesale_customer_id: Optional[UUID] = None,
        retail_customer_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Invoice]:
        """Get invoices by customer"""
        filters = []
        if wholesale_customer_id:
            filters.append(Invoice.wholesale_customer_id == wholesale_customer_id)
        if retail_customer_id:
            filters.append(Invoice.retail_customer_id == retail_customer_id)
        
        query = (
            select(Invoice)
            .where(or_(*filters))
            .order_by(Invoice.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def search_invoices(
        self,
        status: Optional[InvoiceStatus] = None,
        wholesale_customer_id: Optional[UUID] = None,
        retail_customer_id: Optional[UUID] = None,
        is_overdue: Optional[bool] = None,
        min_amount: Optional[Decimal] = None,
        max_amount: Optional[Decimal] = None,
        invoice_date_from: Optional[date] = None,
        invoice_date_to: Optional[date] = None,
        due_date_from: Optional[date] = None,
        due_date_to: Optional[date] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[Invoice], int]:
        """Search invoices with filters"""
        filters = []
        
        if status:
            filters.append(Invoice.status == status)
        if wholesale_customer_id:
            filters.append(Invoice.wholesale_customer_id == wholesale_customer_id)
        if retail_customer_id:
            filters.append(Invoice.retail_customer_id == retail_customer_id)
        if is_overdue is not None:
            filters.append(Invoice.is_overdue_flag == is_overdue)
        if min_amount is not None:
            filters.append(Invoice.total_amount >= min_amount)
        if max_amount is not None:
            filters.append(Invoice.total_amount <= max_amount)
        if invoice_date_from:
            filters.append(Invoice.invoice_date >= invoice_date_from)
        if invoice_date_to:
            filters.append(Invoice.invoice_date <= invoice_date_to)
        if due_date_from:
            filters.append(Invoice.due_date >= due_date_from)
        if due_date_to:
            filters.append(Invoice.due_date <= due_date_to)
        if search:
            search_filter = or_(
                Invoice.invoice_number.ilike(f"%{search}%"),
                Invoice.customer_name.ilike(f"%{search}%"),
                Invoice.customer_email.ilike(f"%{search}%")
            )
            filters.append(search_filter)
        
        # Count query
        count_query = select(func.count(Invoice.id)).where(and_(*filters))
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()
        
        # Data query
        query = (
            select(Invoice)
            .where(and_(*filters))
            .order_by(Invoice.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        invoices = list(result.scalars().all())
        
        return invoices, total
    
    async def get_overdue_invoices(self, days_overdue: Optional[int] = None) -> List[Invoice]:
        """Get all overdue invoices"""
        filters = [
            Invoice.is_overdue_flag == True,
            Invoice.status.notin_([InvoiceStatus.PAID, InvoiceStatus.CANCELLED, InvoiceStatus.VOID])
        ]
        
        if days_overdue is not None:
            cutoff_date = date.today() - timedelta(days=days_overdue)
            filters.append(Invoice.due_date <= cutoff_date)
        
        query = (
            select(Invoice)
            .where(and_(*filters))
            .order_by(Invoice.due_date.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_aging_report_data(self) -> List[Dict[str, Any]]:
        """Get data for aging report"""
        query = (
            select(Invoice)
            .where(
                and_(
                    Invoice.status.notin_([InvoiceStatus.PAID, InvoiceStatus.CANCELLED, InvoiceStatus.VOID]),
                    Invoice.amount_due > 0
                )
            )
            .order_by(Invoice.due_date.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def update_overdue_flags(self) -> int:
        """Update overdue flags for all invoices"""
        today = date.today()
        
        # Mark overdue
        update_query = (
            Invoice.__table__.update()
            .where(
                and_(
                    Invoice.due_date < today,
                    Invoice.status.notin_([InvoiceStatus.PAID, InvoiceStatus.CANCELLED, InvoiceStatus.VOID]),
                    Invoice.is_overdue_flag == False
                )
            )
            .values(is_overdue_flag=True, status=InvoiceStatus.OVERDUE)
        )
        result = await self.db.execute(update_query)
        await self.db.commit()
        return result.rowcount
    
    async def generate_invoice_number(self) -> str:
        """Generate unique invoice number"""
        today = datetime.utcnow()
        prefix = f"INV-{today.strftime('%Y%m%d')}"
        
        # Get count of invoices created today
        query = select(func.count(Invoice.id)).where(
            Invoice.invoice_number.like(f"{prefix}%")
        )
        result = await self.db.execute(query)
        count = result.scalar_one()
        
        return f"{prefix}-{count + 1:04d}"
    
    async def get_customer_summary(
        self,
        wholesale_customer_id: Optional[UUID] = None,
        retail_customer_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Get invoice summary for a customer"""
        filters = []
        if wholesale_customer_id:
            filters.append(Invoice.wholesale_customer_id == wholesale_customer_id)
        if retail_customer_id:
            filters.append(Invoice.retail_customer_id == retail_customer_id)
        
        query = select(
            func.count(Invoice.id).label("total_invoices"),
            func.sum(Invoice.total_amount).label("total_amount"),
            func.sum(Invoice.amount_paid).label("total_paid"),
            func.sum(Invoice.amount_due).label("total_outstanding")
        ).where(and_(*filters))
        
        result = await self.db.execute(query)
        row = result.one()
        
        return {
            "total_invoices": row.total_invoices or 0,
            "total_amount": row.total_amount or Decimal("0.00"),
            "total_paid": row.total_paid or Decimal("0.00"),
            "total_outstanding": row.total_outstanding or Decimal("0.00")
        }


class InvoiceItemRepository(BaseRepository[InvoiceItem]):
    """Repository for Invoice Item operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(InvoiceItem, db)
    
    async def get_by_invoice(self, invoice_id: UUID) -> List[InvoiceItem]:
        """Get all items for an invoice"""
        query = (
            select(InvoiceItem)
            .where(InvoiceItem.invoice_id == invoice_id)
            .order_by(InvoiceItem.created_at.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def bulk_create(self, items: List[InvoiceItem]) -> List[InvoiceItem]:
        """Bulk create invoice items"""
        self.db.add_all(items)
        await self.db.flush()
        return items


class PaymentRecordRepository(BaseRepository[PaymentRecord]):
    """Repository for Payment Record operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(PaymentRecord, db)
    
    async def get_by_payment_number(self, payment_number: str) -> Optional[PaymentRecord]:
        """Get payment by payment number"""
        query = select(PaymentRecord).where(PaymentRecord.payment_number == payment_number)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_invoice(self, invoice_id: UUID) -> List[PaymentRecord]:
        """Get all payments for an invoice"""
        query = (
            select(PaymentRecord)
            .where(PaymentRecord.invoice_id == invoice_id)
            .order_by(PaymentRecord.payment_date.desc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_by_customer(
        self,
        wholesale_customer_id: Optional[UUID] = None,
        retail_customer_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[PaymentRecord]:
        """Get payments by customer"""
        filters = []
        if wholesale_customer_id:
            filters.append(PaymentRecord.wholesale_customer_id == wholesale_customer_id)
        if retail_customer_id:
            filters.append(PaymentRecord.retail_customer_id == retail_customer_id)
        
        query = (
            select(PaymentRecord)
            .where(or_(*filters))
            .order_by(PaymentRecord.payment_date.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def search_payments(
        self,
        status: Optional[PaymentRecordStatus] = None,
        payment_method: Optional[str] = None,
        is_reconciled: Optional[bool] = None,
        wholesale_customer_id: Optional[UUID] = None,
        retail_customer_id: Optional[UUID] = None,
        payment_date_from: Optional[date] = None,
        payment_date_to: Optional[date] = None,
        min_amount: Optional[Decimal] = None,
        max_amount: Optional[Decimal] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[PaymentRecord], int]:
        """Search payments with filters"""
        filters = []
        
        if status:
            filters.append(PaymentRecord.status == status)
        if payment_method:
            filters.append(PaymentRecord.payment_gateway == payment_method)
        if is_reconciled is not None:
            filters.append(PaymentRecord.is_reconciled == is_reconciled)
        if wholesale_customer_id:
            filters.append(PaymentRecord.wholesale_customer_id == wholesale_customer_id)
        if retail_customer_id:
            filters.append(PaymentRecord.retail_customer_id == retail_customer_id)
        if payment_date_from:
            filters.append(PaymentRecord.payment_date >= payment_date_from)
        if payment_date_to:
            filters.append(PaymentRecord.payment_date <= payment_date_to)
        if min_amount is not None:
            filters.append(PaymentRecord.amount >= min_amount)
        if max_amount is not None:
            filters.append(PaymentRecord.amount <= max_amount)
        
        # Count query
        count_query = select(func.count(PaymentRecord.id)).where(and_(*filters))
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()
        
        # Data query
        query = (
            select(PaymentRecord)
            .where(and_(*filters))
            .order_by(PaymentRecord.payment_date.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        payments = list(result.scalars().all())
        
        return payments, total
    
    async def get_unreconciled_payments(self) -> List[PaymentRecord]:
        """Get all unreconciled payments"""
        query = (
            select(PaymentRecord)
            .where(
                and_(
                    PaymentRecord.is_reconciled == False,
                    PaymentRecord.status == PaymentRecordStatus.COMPLETED
                )
            )
            .order_by(PaymentRecord.payment_date.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def generate_payment_number(self) -> str:
        """Generate unique payment number"""
        today = datetime.utcnow()
        prefix = f"PAY-{today.strftime('%Y%m%d')}"
        
        # Get count of payments created today
        query = select(func.count(PaymentRecord.id)).where(
            PaymentRecord.payment_number.like(f"{prefix}%")
        )
        result = await self.db.execute(query)
        count = result.scalar_one()
        
        return f"{prefix}-{count + 1:04d}"
    
    async def get_payment_summary(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Get payment summary statistics"""
        filters = [PaymentRecord.status == PaymentRecordStatus.COMPLETED]
        
        if start_date:
            filters.append(PaymentRecord.payment_date >= start_date)
        if end_date:
            filters.append(PaymentRecord.payment_date <= end_date)
        
        query = select(
            func.count(PaymentRecord.id).label("total_payments"),
            func.sum(PaymentRecord.amount).label("total_amount"),
            func.sum(PaymentRecord.gateway_fee).label("total_fees")
        ).where(and_(*filters))
        
        result = await self.db.execute(query)
        row = result.one()
        
        # Get reconciliation stats
        recon_query = select(
            func.count(PaymentRecord.id).filter(PaymentRecord.is_reconciled == True).label("reconciled"),
            func.count(PaymentRecord.id).filter(PaymentRecord.is_reconciled == False).label("pending")
        ).where(and_(*filters))
        
        recon_result = await self.db.execute(recon_query)
        recon_row = recon_result.one()
        
        return {
            "total_payments": row.total_payments or 0,
            "total_amount": row.total_amount or Decimal("0.00"),
            "total_fees": row.total_fees or Decimal("0.00"),
            "reconciled_count": recon_row.reconciled or 0,
            "pending_count": recon_row.pending or 0
        }


class CreditNoteRepository(BaseRepository[CreditNote]):
    """Repository for Credit Note operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(CreditNote, db)
    
    async def get_by_credit_note_number(self, credit_note_number: str) -> Optional[CreditNote]:
        """Get credit note by number"""
        query = select(CreditNote).where(CreditNote.credit_note_number == credit_note_number)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_invoice(self, invoice_id: UUID) -> List[CreditNote]:
        """Get all credit notes for an invoice"""
        query = (
            select(CreditNote)
            .where(CreditNote.invoice_id == invoice_id)
            .order_by(CreditNote.issue_date.desc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_by_customer(
        self,
        wholesale_customer_id: Optional[UUID] = None,
        retail_customer_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[CreditNote]:
        """Get credit notes by customer"""
        filters = []
        if wholesale_customer_id:
            filters.append(CreditNote.wholesale_customer_id == wholesale_customer_id)
        if retail_customer_id:
            filters.append(CreditNote.retail_customer_id == retail_customer_id)
        
        query = (
            select(CreditNote)
            .where(or_(*filters))
            .order_by(CreditNote.issue_date.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_available_credits(
        self,
        wholesale_customer_id: Optional[UUID] = None,
        retail_customer_id: Optional[UUID] = None
    ) -> List[CreditNote]:
        """Get available (unused/partially used) credit notes for a customer"""
        filters = [
            CreditNote.amount_remaining > 0,
            CreditNote.is_expired == False
        ]
        
        if wholesale_customer_id:
            filters.append(CreditNote.wholesale_customer_id == wholesale_customer_id)
        if retail_customer_id:
            filters.append(CreditNote.retail_customer_id == retail_customer_id)
        
        query = (
            select(CreditNote)
            .where(and_(*filters))
            .order_by(CreditNote.issue_date.asc())  # FIFO
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def search_credit_notes(
        self,
        reason: Optional[CreditNoteReason] = None,
        is_applied: Optional[bool] = None,
        is_expired: Optional[bool] = None,
        wholesale_customer_id: Optional[UUID] = None,
        retail_customer_id: Optional[UUID] = None,
        issue_date_from: Optional[date] = None,
        issue_date_to: Optional[date] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[CreditNote], int]:
        """Search credit notes with filters"""
        filters = []
        
        if reason:
            filters.append(CreditNote.reason == reason)
        if is_applied is not None:
            filters.append(CreditNote.is_applied == is_applied)
        if is_expired is not None:
            filters.append(CreditNote.is_expired == is_expired)
        if wholesale_customer_id:
            filters.append(CreditNote.wholesale_customer_id == wholesale_customer_id)
        if retail_customer_id:
            filters.append(CreditNote.retail_customer_id == retail_customer_id)
        if issue_date_from:
            filters.append(CreditNote.issue_date >= issue_date_from)
        if issue_date_to:
            filters.append(CreditNote.issue_date <= issue_date_to)
        
        # Count query
        count_query = select(func.count(CreditNote.id)).where(and_(*filters))
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()
        
        # Data query
        query = (
            select(CreditNote)
            .where(and_(*filters))
            .order_by(CreditNote.issue_date.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        credit_notes = list(result.scalars().all())
        
        return credit_notes, total
    
    async def generate_credit_note_number(self) -> str:
        """Generate unique credit note number"""
        today = datetime.utcnow()
        prefix = f"CN-{today.strftime('%Y%m%d')}"
        
        # Get count of credit notes created today
        query = select(func.count(CreditNote.id)).where(
            CreditNote.credit_note_number.like(f"{prefix}%")
        )
        result = await self.db.execute(query)
        count = result.scalar_one()
        
        return f"{prefix}-{count + 1:04d}"
    
    async def update_expired_credits(self) -> int:
        """Mark expired credit notes"""
        today = date.today()
        
        update_query = (
            CreditNote.__table__.update()
            .where(
                and_(
                    CreditNote.expiry_date < today,
                    CreditNote.is_expired == False
                )
            )
            .values(is_expired=True)
        )
        result = await self.db.execute(update_query)
        await self.db.commit()
        return result.rowcount


class PaymentReminderRepository(BaseRepository[PaymentReminder]):
    """Repository for Payment Reminder operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(PaymentReminder, db)
    
    async def get_by_invoice(self, invoice_id: UUID) -> List[PaymentReminder]:
        """Get all reminders for an invoice"""
        query = (
            select(PaymentReminder)
            .where(PaymentReminder.invoice_id == invoice_id)
            .order_by(PaymentReminder.sent_at.desc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_latest_reminder(self, invoice_id: UUID) -> Optional[PaymentReminder]:
        """Get latest reminder for an invoice"""
        query = (
            select(PaymentReminder)
            .where(PaymentReminder.invoice_id == invoice_id)
            .order_by(PaymentReminder.sent_at.desc())
            .limit(1)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_invoices_needing_reminders(
        self,
        reminder_type: ReminderType
    ) -> List[UUID]:
        """Get invoice IDs that need reminders of specified type"""
        # Define reminder rules
        reminder_rules = {
            ReminderType.FRIENDLY: (-3, 0),  # 3 days before due date
            ReminderType.FIRST: (1, 7),      # 1-7 days overdue
            ReminderType.SECOND: (8, 30),    # 8-30 days overdue
            ReminderType.FINAL: (31, 60),    # 31-60 days overdue
            ReminderType.LEGAL: (61, None),  # 61+ days overdue
        }
        
        min_days, max_days = reminder_rules.get(reminder_type, (0, None))
        today = date.today()
        
        # Subquery to get last reminder type for each invoice
        last_reminder_subq = (
            select(
                PaymentReminder.invoice_id,
                func.max(PaymentReminder.sent_at).label("last_sent")
            )
            .group_by(PaymentReminder.invoice_id)
            .subquery()
        )
        
        filters = [
            Invoice.status.in_([InvoiceStatus.SENT, InvoiceStatus.OVERDUE, InvoiceStatus.PARTIALLY_PAID]),
            Invoice.amount_due > 0
        ]
        
        # Calculate date range based on reminder type
        if max_days is None:
            filters.append(Invoice.due_date <= (today - timedelta(days=min_days)))
        else:
            filters.append(
                and_(
                    Invoice.due_date <= (today - timedelta(days=min_days)),
                    Invoice.due_date >= (today - timedelta(days=max_days))
                )
            )
        
        query = (
            select(Invoice.id)
            .outerjoin(last_reminder_subq, Invoice.id == last_reminder_subq.c.invoice_id)
            .where(
                and_(
                    *filters,
                    or_(
                        last_reminder_subq.c.last_sent.is_(None),
                        last_reminder_subq.c.last_sent < (datetime.utcnow() - timedelta(days=7))
                    )
                )
            )
        )
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_unacknowledged_reminders(self, days: int = 7) -> List[PaymentReminder]:
        """Get unacknowledged reminders older than specified days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = (
            select(PaymentReminder)
            .where(
                and_(
                    PaymentReminder.is_acknowledged == False,
                    PaymentReminder.sent_at < cutoff_date
                )
            )
            .order_by(PaymentReminder.sent_at.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
