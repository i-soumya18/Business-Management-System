"""
Accounts Payable Service

Business logic for bills, vendor payments, and expense management.
Handles bill lifecycle, payment processing, approval workflows, and reporting.
"""

from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID, uuid4
from decimal import Decimal
from datetime import datetime, date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance import (
    Bill,
    VendorPayment,
    BillStatus,
    ExpenseCategory,
    PaymentRecordStatus
)
from app.models.supplier import Supplier
from app.repositories.accounts_payable import BillRepository, VendorPaymentRepository
from app.repositories.category_brand_supplier import SupplierRepository
from app.schemas.accounts_payable import (
    BillCreate,
    BillUpdate,
    VendorPaymentCreate,
    AgingReportResponse,
    SupplierAgingReport,
    AgingBucket,
    ExpenseSummary,
    ExpenseReportResponse,
    VendorPerformance,
    AccountsPayableDashboard
)


class AccountsPayableService:
    """Service for Accounts Payable operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.bill_repo = BillRepository(db)
        self.payment_repo = VendorPaymentRepository(db)
        self.supplier_repo = SupplierRepository(db)
    
    # ==================== Bill Management ====================
    
    async def create_bill(
        self,
        bill_data: BillCreate,
        created_by_id: Optional[UUID] = None
    ) -> Bill:
        """
        Create a new bill
        
        Args:
            bill_data: Bill creation data
            created_by_id: ID of user creating the bill
        
        Returns:
            Created bill
        """
        # Verify supplier exists
        supplier = await self.supplier_repo.get(bill_data.supplier_id)
        if not supplier:
            raise ValueError(f"Supplier with ID {bill_data.supplier_id} not found")
        
        if not supplier.is_active:
            raise ValueError(f"Supplier {supplier.name} is not active")
        
        # Generate bill number
        bill_number = await self._generate_bill_number()
        
        # Calculate balance due
        balance_due = bill_data.total_amount
        
        # Create bill
        bill = Bill(
            id=uuid4(),
            bill_number=bill_number,
            supplier_id=bill_data.supplier_id,
            supplier_bill_number=bill_data.supplier_bill_number,
            description=bill_data.description,
            category=bill_data.category,
            status=BillStatus.DRAFT,
            subtotal=bill_data.subtotal,
            tax_amount=bill_data.tax_amount,
            total_amount=bill_data.total_amount,
            paid_amount=Decimal("0.00"),
            balance_due=balance_due,
            bill_date=bill_data.bill_date,
            due_date=bill_data.due_date,
            payment_terms=bill_data.payment_terms,
            notes=bill_data.notes,
            attachments=bill_data.attachments,
            currency=bill_data.currency,
            created_by_id=created_by_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        bill = await self.bill_repo.create(bill)
        await self.db.commit()
        await self.db.refresh(bill)
        
        return bill
    
    async def update_bill(
        self,
        bill_id: UUID,
        bill_data: BillUpdate
    ) -> Bill:
        """
        Update an existing bill
        
        Args:
            bill_id: Bill ID
            bill_data: Bill update data
        
        Returns:
            Updated bill
        """
        bill = await self.bill_repo.get(bill_id)
        if not bill:
            raise ValueError(f"Bill with ID {bill_id} not found")
        
        # Only draft bills can be fully edited
        if bill.status not in [BillStatus.DRAFT, BillStatus.PENDING]:
            raise ValueError(f"Cannot edit bill in status: {bill.status.value}")
        
        # Update fields
        update_data = bill_data.model_dump(exclude_unset=True)
        
        # Recalculate balance if amounts change
        if any(k in update_data for k in ['subtotal', 'tax_amount', 'total_amount']):
            subtotal = update_data.get('subtotal', bill.subtotal)
            tax_amount = update_data.get('tax_amount', bill.tax_amount)
            total_amount = update_data.get('total_amount', bill.total_amount)
            
            # Verify total matches
            expected_total = subtotal + tax_amount
            if abs(total_amount - expected_total) > Decimal("0.01"):
                raise ValueError(f"Total amount {total_amount} does not match subtotal + tax ({expected_total})")
            
            # Recalculate balance due
            update_data['balance_due'] = total_amount - bill.paid_amount
        
        for key, value in update_data.items():
            setattr(bill, key, value)
        
        bill.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(bill)
        
        return bill
    
    async def approve_bill(
        self,
        bill_id: UUID,
        approved_by_id: UUID,
        notes: Optional[str] = None
    ) -> Bill:
        """
        Approve a bill for payment
        
        Args:
            bill_id: Bill ID
            approved_by_id: ID of user approving the bill
            notes: Approval notes
        
        Returns:
            Approved bill
        """
        bill = await self.bill_repo.get(bill_id)
        if not bill:
            raise ValueError(f"Bill with ID {bill_id} not found")
        
        if bill.status != BillStatus.PENDING:
            raise ValueError(f"Can only approve bills in PENDING status. Current status: {bill.status.value}")
        
        bill.status = BillStatus.APPROVED
        bill.approved_by_id = approved_by_id
        bill.approved_at = datetime.utcnow()
        
        if notes:
            bill.notes = f"{bill.notes or ''}\n[Approval] {notes}".strip()
        
        bill.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(bill)
        
        return bill
    
    async def submit_for_approval(
        self,
        bill_id: UUID
    ) -> Bill:
        """
        Submit a bill for approval
        
        Args:
            bill_id: Bill ID
        
        Returns:
            Updated bill
        """
        bill = await self.bill_repo.get(bill_id)
        if not bill:
            raise ValueError(f"Bill with ID {bill_id} not found")
        
        if bill.status != BillStatus.DRAFT:
            raise ValueError(f"Can only submit DRAFT bills for approval. Current status: {bill.status.value}")
        
        # Validate bill has all required information
        if bill.total_amount <= Decimal("0.00"):
            raise ValueError("Bill total amount must be greater than 0")
        
        bill.status = BillStatus.PENDING
        bill.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(bill)
        
        return bill
    
    async def cancel_bill(
        self,
        bill_id: UUID,
        reason: Optional[str] = None
    ) -> Bill:
        """
        Cancel a bill
        
        Args:
            bill_id: Bill ID
            reason: Cancellation reason
        
        Returns:
            Cancelled bill
        """
        bill = await self.bill_repo.get(bill_id)
        if not bill:
            raise ValueError(f"Bill with ID {bill_id} not found")
        
        if bill.status == BillStatus.PAID:
            raise ValueError("Cannot cancel a paid bill")
        
        if bill.paid_amount > Decimal("0.00"):
            raise ValueError("Cannot cancel a bill with payments. Refund payments first.")
        
        bill.status = BillStatus.CANCELLED
        
        if reason:
            bill.notes = f"{bill.notes or ''}\n[Cancelled] {reason}".strip()
        
        bill.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(bill)
        
        return bill
    
    async def _generate_bill_number(self) -> str:
        """Generate unique bill number"""
        # Format: BILL-YYYY-NNNNNN
        today = datetime.utcnow()
        prefix = f"BILL-{today.year}"
        
        # Get count of bills created this year
        query_result = await self.db.execute(
            f"SELECT COUNT(*) FROM bills WHERE bill_number LIKE '{prefix}%'"
        )
        count = query_result.scalar_one()
        
        sequence = count + 1
        return f"{prefix}-{sequence:06d}"
    
    # ==================== Payment Management ====================
    
    async def create_payment(
        self,
        payment_data: VendorPaymentCreate,
        created_by_id: Optional[UUID] = None
    ) -> VendorPayment:
        """
        Create a vendor payment
        
        Args:
            payment_data: Payment creation data
            created_by_id: ID of user creating the payment
        
        Returns:
            Created payment
        """
        # Get bill
        bill = await self.bill_repo.get(payment_data.bill_id)
        if not bill:
            raise ValueError(f"Bill with ID {payment_data.bill_id} not found")
        
        # Validate bill status
        if bill.status == BillStatus.CANCELLED:
            raise ValueError("Cannot make payment against cancelled bill")
        
        if bill.status == BillStatus.PAID:
            raise ValueError("Bill is already fully paid")
        
        # Validate payment amount
        if payment_data.amount > bill.balance_due:
            raise ValueError(
                f"Payment amount {payment_data.amount} exceeds balance due {bill.balance_due}"
            )
        
        if payment_data.amount <= Decimal("0.00"):
            raise ValueError("Payment amount must be greater than 0")
        
        # Generate payment number
        payment_number = await self._generate_payment_number()
        
        # Create payment
        payment = VendorPayment(
            id=uuid4(),
            payment_number=payment_number,
            bill_id=payment_data.bill_id,
            amount=payment_data.amount,
            payment_method=payment_data.payment_method,
            payment_date=payment_data.payment_date,
            transaction_reference=payment_data.transaction_reference,
            bank_account=payment_data.bank_account,
            check_number=payment_data.check_number,
            notes=payment_data.notes,
            status=PaymentRecordStatus.COMPLETED,
            created_by_id=created_by_id,
            created_at=datetime.utcnow()
        )
        
        payment = await self.payment_repo.create(payment)
        
        # Update bill payment status
        bill.paid_amount += payment_data.amount
        bill.balance_due = bill.total_amount - bill.paid_amount
        
        # Update bill status
        if bill.balance_due <= Decimal("0.01"):  # Allow small rounding errors
            bill.status = BillStatus.PAID
            bill.paid_date = payment_data.payment_date
        elif bill.status in [BillStatus.PENDING, BillStatus.APPROVED]:
            bill.status = BillStatus.PARTIALLY_PAID
        
        bill.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(payment)
        await self.db.refresh(bill)
        
        return payment
    
    async def cancel_payment(
        self,
        payment_id: UUID,
        reason: Optional[str] = None
    ) -> VendorPayment:
        """
        Cancel a vendor payment
        
        Args:
            payment_id: Payment ID
            reason: Cancellation reason
        
        Returns:
            Cancelled payment
        """
        payment = await self.payment_repo.get(payment_id)
        if not payment:
            raise ValueError(f"Payment with ID {payment_id} not found")
        
        if payment.status == PaymentRecordStatus.CANCELLED:
            raise ValueError("Payment is already cancelled")
        
        # Get associated bill
        bill = await self.bill_repo.get(payment.bill_id)
        if not bill:
            raise ValueError(f"Associated bill not found")
        
        # Reverse payment from bill
        bill.paid_amount -= payment.amount
        bill.balance_due = bill.total_amount - bill.paid_amount
        
        # Update bill status
        if bill.paid_amount <= Decimal("0.01"):
            if bill.status == BillStatus.PAID:
                bill.status = BillStatus.APPROVED
                bill.paid_date = None
        elif bill.status == BillStatus.PAID:
            bill.status = BillStatus.PARTIALLY_PAID
            bill.paid_date = None
        
        bill.updated_at = datetime.utcnow()
        
        # Cancel payment
        payment.status = PaymentRecordStatus.CANCELLED
        if reason:
            payment.notes = f"{payment.notes or ''}\n[Cancelled] {reason}".strip()
        
        await self.db.commit()
        await self.db.refresh(payment)
        await self.db.refresh(bill)
        
        return payment
    
    async def _generate_payment_number(self) -> str:
        """Generate unique payment number"""
        # Format: VPAY-YYYY-NNNNNN
        today = datetime.utcnow()
        prefix = f"VPAY-{today.year}"
        
        # Get count of payments created this year
        query_result = await self.db.execute(
            f"SELECT COUNT(*) FROM vendor_payments WHERE payment_number LIKE '{prefix}%'"
        )
        count = query_result.scalar_one()
        
        sequence = count + 1
        return f"{prefix}-{sequence:06d}"
    
    # ==================== Reporting & Analytics ====================
    
    async def get_aging_report(
        self,
        supplier_id: Optional[UUID] = None,
        category: Optional[ExpenseCategory] = None,
        as_of_date: Optional[date] = None
    ) -> AgingReportResponse:
        """
        Generate aging report for accounts payable
        
        Args:
            supplier_id: Filter by supplier
            category: Filter by expense category
            as_of_date: Report as of date (defaults to today)
        
        Returns:
            Aging report with buckets and supplier breakdown
        """
        reference_date = as_of_date or date.today()
        
        # Get aging buckets
        aging_data = await self.bill_repo.get_aging_report(
            supplier_id=supplier_id,
            category=category,
            as_of_date=reference_date
        )
        
        aging_buckets = [
            AgingBucket(
                bucket=bucket["bucket"],
                count=bucket["count"],
                total_amount=bucket["total_amount"]
            )
            for bucket in aging_data
        ]
        
        # Calculate totals
        total_outstanding = await self.bill_repo.calculate_total_outstanding(
            supplier_id=supplier_id,
            category=category
        )
        total_overdue = await self.bill_repo.calculate_total_overdue(supplier_id=supplier_id)
        
        # Get supplier breakdown
        supplier_aging = await self._get_supplier_aging(
            supplier_id=supplier_id,
            category=category,
            as_of_date=reference_date
        )
        
        return AgingReportResponse(
            as_of_date=reference_date,
            total_outstanding=total_outstanding,
            total_overdue=total_overdue,
            aging_buckets=aging_buckets,
            by_supplier=supplier_aging
        )
    
    async def _get_supplier_aging(
        self,
        supplier_id: Optional[UUID] = None,
        category: Optional[ExpenseCategory] = None,
        as_of_date: Optional[date] = None
    ) -> List[SupplierAgingReport]:
        """Get aging breakdown by supplier"""
        reference_date = as_of_date or date.today()
        
        # Get all suppliers with outstanding bills
        query = """
            SELECT 
                s.id as supplier_id,
                s.name as supplier_name,
                s.code as supplier_code,
                SUM(b.balance_due) as total_outstanding,
                COUNT(b.id) as total_bills,
                SUM(CASE WHEN b.due_date >= :ref_date THEN b.balance_due ELSE 0 END) as current,
                SUM(CASE WHEN b.due_date < :ref_date AND b.due_date >= :ref_date - INTERVAL '30 days' 
                    THEN b.balance_due ELSE 0 END) as days_1_30,
                SUM(CASE WHEN b.due_date < :ref_date - INTERVAL '30 days' AND b.due_date >= :ref_date - INTERVAL '60 days' 
                    THEN b.balance_due ELSE 0 END) as days_31_60,
                SUM(CASE WHEN b.due_date < :ref_date - INTERVAL '60 days' AND b.due_date >= :ref_date - INTERVAL '90 days' 
                    THEN b.balance_due ELSE 0 END) as days_61_90,
                SUM(CASE WHEN b.due_date < :ref_date - INTERVAL '90 days' 
                    THEN b.balance_due ELSE 0 END) as days_90_plus,
                COUNT(CASE WHEN b.due_date < :ref_date THEN 1 END) as overdue_bills
            FROM suppliers s
            INNER JOIN bills b ON b.supplier_id = s.id
            WHERE b.status IN ('pending', 'approved', 'partially_paid')
        """
        
        params = {"ref_date": reference_date}
        
        if supplier_id:
            query += " AND s.id = :supplier_id"
            params["supplier_id"] = str(supplier_id)
        
        if category:
            query += " AND b.category = :category"
            params["category"] = category.value
        
        query += " GROUP BY s.id, s.name, s.code ORDER BY total_outstanding DESC"
        
        result = await self.db.execute(query, params)
        rows = result.fetchall()
        
        return [
            SupplierAgingReport(
                supplier_id=row.supplier_id,
                supplier_name=row.supplier_name,
                supplier_code=row.supplier_code,
                total_outstanding=row.total_outstanding or Decimal("0.00"),
                total_overdue=sum([
                    row.days_1_30 or Decimal("0.00"),
                    row.days_31_60 or Decimal("0.00"),
                    row.days_61_90 or Decimal("0.00"),
                    row.days_90_plus or Decimal("0.00")
                ]),
                current=row.current or Decimal("0.00"),
                days_1_30=row.days_1_30 or Decimal("0.00"),
                days_31_60=row.days_31_60 or Decimal("0.00"),
                days_61_90=row.days_61_90 or Decimal("0.00"),
                days_90_plus=row.days_90_plus or Decimal("0.00"),
                total_bills=row.total_bills or 0,
                overdue_bills=row.overdue_bills or 0
            )
            for row in rows
        ]
    
    async def get_expense_report(
        self,
        category: Optional[ExpenseCategory] = None,
        supplier_id: Optional[UUID] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> ExpenseReportResponse:
        """
        Generate expense report
        
        Args:
            category: Filter by category
            supplier_id: Filter by supplier
            date_from: Start date
            date_to: End date
        
        Returns:
            Expense report with category breakdown
        """
        # Default date range to current month
        if not date_from:
            date_from = date.today().replace(day=1)
        if not date_to:
            date_to = date.today()
        
        # Get expense summary
        expense_data = await self.bill_repo.get_expense_summary(
            date_from=date_from,
            date_to=date_to,
            supplier_id=supplier_id
        )
        
        by_category = [
            ExpenseSummary(
                category=exp["category"],
                total_amount=exp["total_amount"],
                bill_count=exp["bill_count"],
                paid_amount=exp["paid_amount"],
                outstanding_amount=exp["outstanding_amount"]
            )
            for exp in expense_data
        ]
        
        # Calculate totals
        total_expenses = sum(exp.total_amount for exp in by_category)
        total_paid = sum(exp.paid_amount for exp in by_category)
        total_outstanding = sum(exp.outstanding_amount for exp in by_category)
        
        # Get top suppliers
        top_suppliers = await self._get_top_suppliers(
            date_from=date_from,
            date_to=date_to,
            limit=10
        )
        
        return ExpenseReportResponse(
            date_from=date_from,
            date_to=date_to,
            total_expenses=total_expenses,
            total_paid=total_paid,
            total_outstanding=total_outstanding,
            by_category=by_category,
            top_suppliers=top_suppliers
        )
    
    async def _get_top_suppliers(
        self,
        date_from: date,
        date_to: date,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get top suppliers by expense amount"""
        query = """
            SELECT 
                s.id,
                s.name,
                s.code,
                COUNT(b.id) as bill_count,
                SUM(b.total_amount) as total_amount,
                SUM(b.paid_amount) as paid_amount
            FROM suppliers s
            INNER JOIN bills b ON b.supplier_id = s.id
            WHERE b.bill_date >= :date_from AND b.bill_date <= :date_to
            GROUP BY s.id, s.name, s.code
            ORDER BY total_amount DESC
            LIMIT :limit
        """
        
        result = await self.db.execute(
            query,
            {"date_from": date_from, "date_to": date_to, "limit": limit}
        )
        
        return [
            {
                "supplier_id": str(row.id),
                "supplier_name": row.name,
                "supplier_code": row.code,
                "bill_count": row.bill_count,
                "total_amount": float(row.total_amount or 0),
                "paid_amount": float(row.paid_amount or 0)
            }
            for row in result.fetchall()
        ]
    
    async def get_vendor_performance(
        self,
        supplier_id: UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> VendorPerformance:
        """
        Get vendor payment performance metrics
        
        Args:
            supplier_id: Supplier ID
            date_from: Start date
            date_to: End date
        
        Returns:
            Vendor performance metrics
        """
        # Get supplier
        supplier = await self.supplier_repo.get(supplier_id)
        if not supplier:
            raise ValueError(f"Supplier with ID {supplier_id} not found")
        
        # Query bill statistics
        query = """
            SELECT 
                COUNT(*) as total_bills,
                SUM(total_amount) as total_amount,
                SUM(paid_amount) as paid_amount,
                SUM(balance_due) as outstanding_amount,
                COUNT(CASE WHEN status = 'draft' THEN 1 END) as draft_count,
                COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_count,
                COUNT(CASE WHEN status = 'approved' THEN 1 END) as approved_count,
                COUNT(CASE WHEN status = 'paid' THEN 1 END) as paid_count,
                COUNT(CASE WHEN status IN ('pending', 'approved', 'partially_paid') 
                    AND due_date < CURRENT_DATE THEN 1 END) as overdue_count,
                AVG(CASE WHEN paid_date IS NOT NULL 
                    THEN EXTRACT(DAY FROM paid_date - bill_date) END) as avg_days_to_pay
            FROM bills
            WHERE supplier_id = :supplier_id
        """
        
        params = {"supplier_id": str(supplier_id)}
        
        if date_from:
            query += " AND bill_date >= :date_from"
            params["date_from"] = date_from
        if date_to:
            query += " AND bill_date <= :date_to"
            params["date_to"] = date_to
        
        result = await self.db.execute(query, params)
        row = result.fetchone()
        
        # Calculate on-time payment rate
        on_time_rate = None
        if row.paid_count > 0:
            on_time_query = """
                SELECT COUNT(*) 
                FROM bills 
                WHERE supplier_id = :supplier_id 
                AND status = 'paid' 
                AND paid_date <= due_date
            """
            on_time_result = await self.db.execute(on_time_query, params)
            on_time_count = on_time_result.scalar_one()
            on_time_rate = (on_time_count / row.paid_count) * 100
        
        return VendorPerformance(
            supplier_id=supplier_id,
            supplier_name=supplier.name,
            total_bills=row.total_bills or 0,
            total_amount=row.total_amount or Decimal("0.00"),
            paid_amount=row.paid_amount or Decimal("0.00"),
            outstanding_amount=row.outstanding_amount or Decimal("0.00"),
            average_days_to_pay=row.avg_days_to_pay,
            on_time_payment_rate=on_time_rate,
            draft_count=row.draft_count or 0,
            pending_count=row.pending_count or 0,
            approved_count=row.approved_count or 0,
            paid_count=row.paid_count or 0,
            overdue_count=row.overdue_count or 0
        )
    
    async def get_dashboard_data(self) -> AccountsPayableDashboard:
        """
        Get comprehensive dashboard data
        
        Returns:
            Dashboard data with summary statistics
        """
        # Calculate summary metrics
        total_outstanding = await self.bill_repo.calculate_total_outstanding()
        total_overdue = await self.bill_repo.calculate_total_overdue()
        
        # Bills due this week
        bills_due_week = await self.bill_repo.get_due_soon(days=7)
        
        # Bills due this month
        bills_due_month = await self.bill_repo.get_due_soon(days=30)
        
        # Get status counts
        status_counts = await self.bill_repo.get_by_status_counts()
        
        # Get category summary (last 30 days)
        date_from = date.today() - timedelta(days=30)
        expense_data = await self.bill_repo.get_expense_summary(date_from=date_from)
        by_category = [
            ExpenseSummary(
                category=exp["category"],
                total_amount=exp["total_amount"],
                bill_count=exp["bill_count"],
                paid_amount=exp["paid_amount"],
                outstanding_amount=exp["outstanding_amount"]
            )
            for exp in expense_data
        ]
        
        # Get aging summary
        aging_data = await self.bill_repo.get_aging_report()
        aging_summary = [
            AgingBucket(
                bucket=bucket["bucket"],
                count=bucket["count"],
                total_amount=bucket["total_amount"]
            )
            for bucket in aging_data
        ]
        
        # Recent activity counts
        recent_bills = await self.bill_repo.search_bills(
            bill_date_from=date.today() - timedelta(days=7),
            limit=100
        )
        
        recent_payments = await self.payment_repo.get_recent_payments(days=7)
        
        return AccountsPayableDashboard(
            total_outstanding=total_outstanding,
            total_overdue=total_overdue,
            bills_due_this_week=len(bills_due_week),
            bills_due_this_month=len(bills_due_month),
            by_status=status_counts,
            by_category=by_category,
            aging_summary=aging_summary,
            recent_bills_count=len(recent_bills[0]),
            recent_payments_count=len(recent_payments)
        )
    
    # ==================== Bulk Operations ====================
    
    async def bulk_approve_bills(
        self,
        bill_ids: List[UUID],
        approved_by_id: UUID,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Approve multiple bills
        
        Args:
            bill_ids: List of bill IDs
            approved_by_id: ID of user approving
            notes: Approval notes
        
        Returns:
            Results summary
        """
        success_count = 0
        failed_count = 0
        failed_ids = []
        errors = []
        
        for bill_id in bill_ids:
            try:
                await self.approve_bill(bill_id, approved_by_id, notes)
                success_count += 1
            except Exception as e:
                failed_count += 1
                failed_ids.append(bill_id)
                errors.append(f"Bill {bill_id}: {str(e)}")
        
        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "failed_ids": failed_ids,
            "errors": errors
        }
    
    async def bulk_update_status(
        self,
        bill_ids: List[UUID],
        status: BillStatus,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update status for multiple bills
        
        Args:
            bill_ids: List of bill IDs
            status: New status
            notes: Status change notes
        
        Returns:
            Results summary
        """
        success_count = 0
        failed_count = 0
        failed_ids = []
        errors = []
        
        for bill_id in bill_ids:
            try:
                bill = await self.bill_repo.get(bill_id)
                if not bill:
                    raise ValueError(f"Bill not found")
                
                bill.status = status
                if notes:
                    bill.notes = f"{bill.notes or ''}\n[Status Update] {notes}".strip()
                bill.updated_at = datetime.utcnow()
                
                await self.db.commit()
                success_count += 1
            except Exception as e:
                failed_count += 1
                failed_ids.append(bill_id)
                errors.append(f"Bill {bill_id}: {str(e)}")
                await self.db.rollback()
        
        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "failed_ids": failed_ids,
            "errors": errors
        }
