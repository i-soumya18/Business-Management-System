"""
Accounts Receivable Service

Business logic for invoice management, payment processing, credit notes, and collections.
"""

from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from decimal import Decimal
from datetime import datetime, date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance import (
    Invoice,
    InvoiceItem,
    PaymentRecord,
    CreditNote,
    PaymentReminder,
    InvoiceStatus,
    PaymentRecordStatus,
    PaymentGateway,
    CreditNoteReason,
    ReminderType
)
from app.models.order import Order
from app.models.wholesale import WholesaleCustomer
from app.models.retail_customer import RetailCustomer
from app.repositories.accounts_receivable import (
    InvoiceRepository,
    InvoiceItemRepository,
    PaymentRecordRepository,
    CreditNoteRepository,
    PaymentReminderRepository
)
from app.schemas.accounts_receivable import (
    InvoiceCreate,
    InvoiceUpdate,
    PaymentRecordCreate,
    CreditNoteCreate,
    ApplyCreditNote,
    AgingBucket,
    AgingReport,
    InvoiceSummary,
    PaymentSummary,
    CustomerAgingSummary,
    ARDashboard
)


class AccountsReceivableService:
    """Service for managing accounts receivable operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.invoice_repo = InvoiceRepository(db)
        self.invoice_item_repo = InvoiceItemRepository(db)
        self.payment_repo = PaymentRecordRepository(db)
        self.credit_note_repo = CreditNoteRepository(db)
        self.reminder_repo = PaymentReminderRepository(db)
    
    # ========== Invoice Management ==========
    
    async def create_invoice(
        self,
        data: InvoiceCreate,
        created_by_id: UUID
    ) -> Invoice:
        """Create new invoice with items"""
        # Generate invoice number
        invoice_number = await self.invoice_repo.generate_invoice_number()
        
        # Calculate totals
        subtotal = sum(item.line_total for item in data.items)
        tax_amount = subtotal * (data.tax_rate / Decimal("100"))
        total_amount = subtotal + tax_amount - (data.discount_amount or Decimal("0"))
        
        # Create invoice
        invoice = Invoice(
            invoice_number=invoice_number,
            order_id=data.order_id,
            wholesale_customer_id=data.wholesale_customer_id,
            retail_customer_id=data.retail_customer_id,
            invoice_date=data.invoice_date or date.today(),
            due_date=data.due_date,
            status=InvoiceStatus.DRAFT,
            subtotal=subtotal,
            tax_rate=data.tax_rate,
            tax_amount=tax_amount,
            discount_amount=data.discount_amount or Decimal("0"),
            total_amount=total_amount,
            amount_paid=Decimal("0"),
            amount_due=total_amount,
            customer_name=data.customer_name,
            customer_email=data.customer_email,
            customer_phone=data.customer_phone,
            billing_address_line1=data.billing_address_line1,
            billing_address_line2=data.billing_address_line2,
            billing_city=data.billing_city,
            billing_state=data.billing_state,
            billing_postal_code=data.billing_postal_code,
            billing_country=data.billing_country,
            shipping_address=data.shipping_address,
            payment_terms=data.payment_terms,
            notes=data.notes,
            created_by_id=created_by_id
        )
        
        invoice = await self.invoice_repo.create(invoice)
        
        # Create invoice items
        items = []
        for item_data in data.items:
            item = InvoiceItem(
                invoice_id=invoice.id,
                product_id=item_data.product_id,
                description=item_data.description,
                quantity=item_data.quantity,
                unit_price=item_data.unit_price,
                line_total=item_data.line_total,
                tax_rate=item_data.tax_rate,
                discount_amount=item_data.discount_amount
            )
            items.append(item)
        
        await self.invoice_item_repo.bulk_create(items)
        await self.db.commit()
        
        return await self.invoice_repo.get_with_items(invoice.id)
    
    async def create_invoice_from_order(
        self,
        order_id: UUID,
        created_by_id: UUID
    ) -> Invoice:
        """Automatically create invoice from order"""
        # Get order with items (would need to implement this query)
        # For now, simplified version
        
        # This would fetch order details and create invoice
        # Implementation depends on Order model structure
        pass
    
    async def update_invoice(
        self,
        invoice_id: UUID,
        data: InvoiceUpdate
    ) -> Invoice:
        """Update invoice details"""
        invoice = await self.invoice_repo.get(invoice_id)
        if not invoice:
            raise ValueError("Invoice not found")
        
        if invoice.status != InvoiceStatus.DRAFT:
            raise ValueError("Can only update draft invoices")
        
        # Update allowed fields
        update_data = data.model_dump(exclude_unset=True)
        
        # Recalculate if items changed
        if "items" in update_data:
            # Would need to handle item updates
            pass
        
        invoice = await self.invoice_repo.update(invoice_id, update_data)
        await self.db.commit()
        
        return invoice
    
    async def send_invoice(self, invoice_id: UUID) -> Invoice:
        """Mark invoice as sent"""
        invoice = await self.invoice_repo.get(invoice_id)
        if not invoice:
            raise ValueError("Invoice not found")
        
        if invoice.status != InvoiceStatus.DRAFT:
            raise ValueError("Can only send draft invoices")
        
        invoice = await self.invoice_repo.update(
            invoice_id,
            {
                "status": InvoiceStatus.SENT,
                "is_sent": True,
                "sent_at": datetime.utcnow()
            }
        )
        await self.db.commit()
        
        return invoice
    
    async def void_invoice(self, invoice_id: UUID, reason: str) -> Invoice:
        """Void an invoice"""
        invoice = await self.invoice_repo.get(invoice_id)
        if not invoice:
            raise ValueError("Invoice not found")
        
        if invoice.status == InvoiceStatus.PAID:
            raise ValueError("Cannot void paid invoices")
        
        invoice = await self.invoice_repo.update(
            invoice_id,
            {
                "status": InvoiceStatus.VOID,
                "notes": f"{invoice.notes or ''}\nVoided: {reason}"
            }
        )
        await self.db.commit()
        
        return invoice
    
    # ========== Payment Processing ==========
    
    async def record_payment(
        self,
        data: PaymentRecordCreate,
        created_by_id: UUID
    ) -> Tuple[PaymentRecord, Invoice]:
        """Record payment against invoice"""
        # Get invoice
        invoice = await self.invoice_repo.get(data.invoice_id)
        if not invoice:
            raise ValueError("Invoice not found")
        
        if invoice.amount_due <= 0:
            raise ValueError("Invoice is already paid")
        
        if data.amount > invoice.amount_due:
            raise ValueError("Payment amount exceeds amount due")
        
        # Generate payment number
        payment_number = await self.payment_repo.generate_payment_number()
        
        # Create payment record
        payment = PaymentRecord(
            payment_number=payment_number,
            invoice_id=data.invoice_id,
            wholesale_customer_id=invoice.wholesale_customer_id,
            retail_customer_id=invoice.retail_customer_id,
            amount=data.amount,
            payment_date=data.payment_date or date.today(),
            payment_gateway=data.payment_gateway,
            payment_method=data.payment_method,
            transaction_id=data.transaction_id,
            gateway_fee=data.gateway_fee or Decimal("0"),
            reference_number=data.reference_number,
            status=PaymentRecordStatus.COMPLETED,
            notes=data.notes,
            created_by_id=created_by_id
        )
        
        payment = await self.payment_repo.create(payment)
        
        # Update invoice
        new_amount_paid = invoice.amount_paid + data.amount
        new_amount_due = invoice.total_amount - new_amount_paid
        
        new_status = InvoiceStatus.PAID if new_amount_due <= 0 else InvoiceStatus.PARTIALLY_PAID
        
        invoice = await self.invoice_repo.update(
            invoice.id,
            {
                "amount_paid": new_amount_paid,
                "amount_due": new_amount_due,
                "status": new_status,
                "paid_at": datetime.utcnow() if new_status == InvoiceStatus.PAID else None
            }
        )
        
        await self.db.commit()
        
        return payment, invoice
    
    async def reconcile_payment(
        self,
        payment_id: UUID,
        reconciled_by_id: UUID,
        notes: Optional[str] = None
    ) -> PaymentRecord:
        """Mark payment as reconciled"""
        payment = await self.payment_repo.get(payment_id)
        if not payment:
            raise ValueError("Payment not found")
        
        if payment.is_reconciled:
            raise ValueError("Payment already reconciled")
        
        payment = await self.payment_repo.update(
            payment_id,
            {
                "is_reconciled": True,
                "reconciled_at": datetime.utcnow(),
                "reconciled_by_id": reconciled_by_id,
                "reconciliation_notes": notes
            }
        )
        await self.db.commit()
        
        return payment
    
    async def refund_payment(
        self,
        payment_id: UUID,
        refund_amount: Decimal,
        reason: str,
        created_by_id: UUID
    ) -> Tuple[PaymentRecord, CreditNote]:
        """Process payment refund"""
        payment = await self.payment_repo.get(payment_id)
        if not payment:
            raise ValueError("Payment not found")
        
        if payment.status == PaymentRecordStatus.REFUNDED:
            raise ValueError("Payment already refunded")
        
        if refund_amount > payment.amount:
            raise ValueError("Refund amount exceeds payment amount")
        
        # Update payment status
        payment = await self.payment_repo.update(
            payment_id,
            {
                "status": PaymentRecordStatus.REFUNDED,
                "refunded_at": datetime.utcnow(),
                "refund_amount": refund_amount,
                "refund_reason": reason
            }
        )
        
        # Create credit note
        credit_note = await self.create_credit_note(
            CreditNoteCreate(
                invoice_id=payment.invoice_id,
                wholesale_customer_id=payment.wholesale_customer_id,
                retail_customer_id=payment.retail_customer_id,
                amount=refund_amount,
                reason=CreditNoteReason.REFUND,
                description=f"Refund for payment {payment.payment_number}: {reason}"
            ),
            created_by_id
        )
        
        await self.db.commit()
        
        return payment, credit_note
    
    # ========== Credit Note Management ==========
    
    async def create_credit_note(
        self,
        data: CreditNoteCreate,
        created_by_id: UUID
    ) -> CreditNote:
        """Create credit note"""
        # Generate credit note number
        credit_note_number = await self.credit_note_repo.generate_credit_note_number()
        
        # Calculate expiry date (default 1 year)
        expiry_date = data.expiry_date or (date.today() + timedelta(days=365))
        
        credit_note = CreditNote(
            credit_note_number=credit_note_number,
            invoice_id=data.invoice_id,
            wholesale_customer_id=data.wholesale_customer_id,
            retail_customer_id=data.retail_customer_id,
            amount=data.amount,
            amount_used=Decimal("0"),
            amount_remaining=data.amount,
            reason=data.reason,
            description=data.description,
            issue_date=data.issue_date or date.today(),
            expiry_date=expiry_date,
            requires_approval=data.requires_approval or False,
            is_approved=not data.requires_approval,
            created_by_id=created_by_id
        )
        
        credit_note = await self.credit_note_repo.create(credit_note)
        await self.db.commit()
        
        return credit_note
    
    async def approve_credit_note(
        self,
        credit_note_id: UUID,
        approved_by_id: UUID
    ) -> CreditNote:
        """Approve credit note"""
        credit_note = await self.credit_note_repo.get(credit_note_id)
        if not credit_note:
            raise ValueError("Credit note not found")
        
        if not credit_note.requires_approval:
            raise ValueError("Credit note does not require approval")
        
        if credit_note.is_approved:
            raise ValueError("Credit note already approved")
        
        credit_note = await self.credit_note_repo.update(
            credit_note_id,
            {
                "is_approved": True,
                "approved_by_id": approved_by_id,
                "approved_at": datetime.utcnow()
            }
        )
        await self.db.commit()
        
        return credit_note
    
    async def apply_credit_note(
        self,
        data: ApplyCreditNote,
        applied_by_id: UUID
    ) -> Tuple[CreditNote, Invoice]:
        """Apply credit note to invoice"""
        credit_note = await self.credit_note_repo.get(data.credit_note_id)
        if not credit_note:
            raise ValueError("Credit note not found")
        
        if not credit_note.is_approved:
            raise ValueError("Credit note not approved")
        
        if credit_note.is_expired:
            raise ValueError("Credit note has expired")
        
        if credit_note.amount_remaining < data.amount_to_apply:
            raise ValueError("Insufficient credit remaining")
        
        invoice = await self.invoice_repo.get(data.invoice_id)
        if not invoice:
            raise ValueError("Invoice not found")
        
        if invoice.amount_due < data.amount_to_apply:
            raise ValueError("Credit amount exceeds invoice due amount")
        
        # Update credit note
        new_amount_used = credit_note.amount_used + data.amount_to_apply
        new_amount_remaining = credit_note.amount - new_amount_used
        
        credit_note = await self.credit_note_repo.update(
            credit_note.id,
            {
                "amount_used": new_amount_used,
                "amount_remaining": new_amount_remaining,
                "is_applied": True,
                "applied_at": datetime.utcnow(),
                "applied_to_invoice_id": invoice.id
            }
        )
        
        # Update invoice
        new_amount_due = invoice.amount_due - data.amount_to_apply
        new_credit_applied = (invoice.credit_applied or Decimal("0")) + data.amount_to_apply
        
        new_status = InvoiceStatus.PAID if new_amount_due <= 0 else invoice.status
        
        invoice = await self.invoice_repo.update(
            invoice.id,
            {
                "amount_due": new_amount_due,
                "credit_applied": new_credit_applied,
                "status": new_status,
                "paid_at": datetime.utcnow() if new_status == InvoiceStatus.PAID else None
            }
        )
        
        await self.db.commit()
        
        return credit_note, invoice
    
    # ========== Payment Reminders ==========
    
    async def send_payment_reminder(
        self,
        invoice_id: UUID,
        reminder_type: ReminderType,
        sent_by_id: UUID,
        custom_message: Optional[str] = None
    ) -> PaymentReminder:
        """Send payment reminder for invoice"""
        invoice = await self.invoice_repo.get(invoice_id)
        if not invoice:
            raise ValueError("Invoice not found")
        
        if invoice.status in [InvoiceStatus.PAID, InvoiceStatus.CANCELLED, InvoiceStatus.VOID]:
            raise ValueError("Cannot send reminder for paid/cancelled/void invoices")
        
        # Create reminder
        reminder = PaymentReminder(
            invoice_id=invoice_id,
            reminder_type=reminder_type,
            sent_at=datetime.utcnow(),
            sent_by_id=sent_by_id,
            message=custom_message or self._get_default_reminder_message(reminder_type, invoice)
        )
        
        reminder = await self.reminder_repo.create(reminder)
        
        # Update invoice reminder count
        await self.invoice_repo.update(
            invoice_id,
            {"reminder_count": invoice.reminder_count + 1}
        )
        
        await self.db.commit()
        
        return reminder
    
    async def process_automated_reminders(self) -> Dict[ReminderType, int]:
        """Process automated reminders for all overdue invoices"""
        results = {}
        
        for reminder_type in ReminderType:
            invoice_ids = await self.reminder_repo.get_invoices_needing_reminders(reminder_type)
            count = 0
            
            for invoice_id in invoice_ids:
                try:
                    # In production, this would integrate with email service
                    await self.send_payment_reminder(
                        invoice_id,
                        reminder_type,
                        sent_by_id=None  # System generated
                    )
                    count += 1
                except Exception as e:
                    # Log error but continue processing
                    print(f"Error sending reminder for invoice {invoice_id}: {e}")
            
            results[reminder_type] = count
        
        return results
    
    def _get_default_reminder_message(
        self,
        reminder_type: ReminderType,
        invoice: Invoice
    ) -> str:
        """Get default reminder message based on type"""
        messages = {
            ReminderType.FRIENDLY: f"This is a friendly reminder that invoice {invoice.invoice_number} is due on {invoice.due_date}.",
            ReminderType.FIRST: f"Your payment for invoice {invoice.invoice_number} is now overdue. Please remit payment at your earliest convenience.",
            ReminderType.SECOND: f"REMINDER: Invoice {invoice.invoice_number} is seriously overdue. Immediate payment is required.",
            ReminderType.FINAL: f"FINAL NOTICE: Invoice {invoice.invoice_number} is {invoice.days_overdue} days overdue. Pay immediately to avoid legal action.",
            ReminderType.LEGAL: f"LEGAL NOTICE: Invoice {invoice.invoice_number} has been forwarded to collections. Legal proceedings may commence."
        }
        return messages.get(reminder_type, "Payment reminder")
    
    # ========== Analytics & Reporting ==========
    
    async def get_aging_report(self) -> AgingReport:
        """Generate accounts receivable aging report"""
        invoices = await self.invoice_repo.get_aging_report_data()
        
        # Initialize buckets
        current = Decimal("0")
        days_1_30 = Decimal("0")
        days_31_60 = Decimal("0")
        days_61_90 = Decimal("0")
        over_90 = Decimal("0")
        
        # Categorize invoices
        for invoice in invoices:
            if invoice.days_current > 0:
                current += invoice.amount_due
            elif invoice.days_overdue_1_30 > 0:
                days_1_30 += invoice.amount_due
            elif invoice.days_overdue_31_60 > 0:
                days_31_60 += invoice.amount_due
            elif invoice.days_overdue_61_90 > 0:
                days_61_90 += invoice.amount_due
            else:
                over_90 += invoice.amount_due
        
        total = current + days_1_30 + days_31_60 + days_61_90 + over_90
        
        return AgingReport(
            report_date=date.today(),
            total_outstanding=total,
            current=AgingBucket(amount=current, count=sum(1 for i in invoices if i.days_current > 0)),
            days_1_30=AgingBucket(amount=days_1_30, count=sum(1 for i in invoices if i.days_overdue_1_30 > 0)),
            days_31_60=AgingBucket(amount=days_31_60, count=sum(1 for i in invoices if i.days_overdue_31_60 > 0)),
            days_61_90=AgingBucket(amount=days_61_90, count=sum(1 for i in invoices if i.days_overdue_61_90 > 0)),
            over_90_days=AgingBucket(amount=over_90, count=sum(1 for i in invoices if i.days_overdue > 90))
        )
    
    async def get_invoice_summary(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> InvoiceSummary:
        """Get invoice summary statistics"""
        filters = {}
        if start_date:
            filters["invoice_date_from"] = start_date
        if end_date:
            filters["invoice_date_to"] = end_date
        
        invoices, _ = await self.invoice_repo.search_invoices(**filters, limit=10000)
        
        total_invoiced = sum(i.total_amount for i in invoices)
        total_paid = sum(i.amount_paid for i in invoices)
        total_outstanding = sum(i.amount_due for i in invoices)
        
        overdue_invoices = [i for i in invoices if i.is_overdue_flag]
        
        return InvoiceSummary(
            total_invoices=len(invoices),
            total_invoiced=total_invoiced,
            total_paid=total_paid,
            total_outstanding=total_outstanding,
            overdue_count=len(overdue_invoices),
            overdue_amount=sum(i.amount_due for i in overdue_invoices)
        )
    
    async def get_payment_summary(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> PaymentSummary:
        """Get payment summary statistics"""
        return await self.payment_repo.get_payment_summary(start_date, end_date)
    
    async def get_ar_dashboard(self) -> ARDashboard:
        """Get comprehensive AR dashboard data"""
        # Get current period data (this month)
        today = date.today()
        first_of_month = date(today.year, today.month, 1)
        
        invoice_summary = await self.get_invoice_summary(first_of_month, today)
        payment_summary = await self.get_payment_summary(first_of_month, today)
        aging_report = await self.get_aging_report()
        
        # Get overdue invoices
        overdue_invoices = await self.invoice_repo.get_overdue_invoices()
        
        # Get unreconciled payments
        unreconciled_payments = await self.payment_repo.get_unreconciled_payments()
        
        return ARDashboard(
            report_date=today,
            invoice_summary=invoice_summary,
            payment_summary=payment_summary,
            aging_report=aging_report,
            overdue_invoice_count=len(overdue_invoices),
            overdue_total_amount=sum(i.amount_due for i in overdue_invoices),
            unreconciled_payment_count=len(unreconciled_payments),
            collection_effectiveness=(
                (payment_summary["total_amount"] / invoice_summary.total_invoiced * 100)
                if invoice_summary.total_invoiced > 0 else Decimal("0")
            )
        )
    
    async def get_customer_aging_summary(
        self,
        wholesale_customer_id: Optional[UUID] = None,
        retail_customer_id: Optional[UUID] = None
    ) -> CustomerAgingSummary:
        """Get aging summary for specific customer"""
        invoices = await self.invoice_repo.get_by_customer(
            wholesale_customer_id,
            retail_customer_id,
            limit=10000
        )
        
        # Calculate aging buckets
        current = Decimal("0")
        days_1_30 = Decimal("0")
        days_31_60 = Decimal("0")
        days_61_90 = Decimal("0")
        over_90 = Decimal("0")
        
        for invoice in invoices:
            if invoice.status in [InvoiceStatus.PAID, InvoiceStatus.CANCELLED, InvoiceStatus.VOID]:
                continue
                
            if invoice.days_current > 0:
                current += invoice.amount_due
            elif invoice.days_overdue_1_30 > 0:
                days_1_30 += invoice.amount_due
            elif invoice.days_overdue_31_60 > 0:
                days_31_60 += invoice.amount_due
            elif invoice.days_overdue_61_90 > 0:
                days_61_90 += invoice.amount_due
            else:
                over_90 += invoice.amount_due
        
        total_outstanding = current + days_1_30 + days_31_60 + days_61_90 + over_90
        
        # Get available credits
        available_credits = await self.credit_note_repo.get_available_credits(
            wholesale_customer_id,
            retail_customer_id
        )
        
        return CustomerAgingSummary(
            wholesale_customer_id=wholesale_customer_id,
            retail_customer_id=retail_customer_id,
            total_outstanding=total_outstanding,
            current=current,
            days_1_30=days_1_30,
            days_31_60=days_31_60,
            days_61_90=days_61_90,
            over_90_days=over_90,
            available_credit=sum(c.amount_remaining for c in available_credits)
        )
    
    # ========== Maintenance Tasks ==========
    
    async def update_overdue_invoices(self) -> int:
        """Update overdue flags for all invoices"""
        return await self.invoice_repo.update_overdue_flags()
    
    async def update_expired_credits(self) -> int:
        """Mark expired credit notes"""
        return await self.credit_note_repo.update_expired_credits()
