"""
Comprehensive Tests for Accounts Receivable Module

Tests for invoices, payments, credit notes, reminders, and AR analytics.
"""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

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
from app.repositories.accounts_receivable import (
    InvoiceRepository,
    InvoiceItemRepository,
    PaymentRecordRepository,
    CreditNoteRepository,
    PaymentReminderRepository
)
from app.services.accounts_receivable import AccountsReceivableService
from app.schemas.accounts_receivable import (
    InvoiceCreate,
    InvoiceItemCreate,
    PaymentRecordCreate,
    CreditNoteCreate,
    ApplyCreditNote
)


# ========== Invoice Repository Tests ==========

@pytest.mark.asyncio
class TestInvoiceRepository:
    """Test InvoiceRepository"""
    
    async def test_create_invoice(self, db: AsyncSession, test_user):
        """Test creating invoice"""
        repo = InvoiceRepository(db)
        
        invoice = Invoice(
            invoice_number="INV-TEST-001",
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status=InvoiceStatus.DRAFT,
            subtotal=Decimal("1000.00"),
            tax_rate=Decimal("10.0"),
            tax_amount=Decimal("100.00"),
            total_amount=Decimal("1100.00"),
            amount_paid=Decimal("0.00"),
            amount_due=Decimal("1100.00"),
            customer_name="Test Customer",
            customer_email="test@example.com",
            billing_address_line1="123 Test St",
            billing_city="Test City",
            billing_state="TS",
            billing_postal_code="12345",
            billing_country="Test Country",
            payment_terms="Net 30",
            created_by_id=test_user.id
        )
        
        created = await repo.create(invoice)
        await db.commit()
        
        assert created.id is not None
        assert created.invoice_number == "INV-TEST-001"
        assert created.total_amount == Decimal("1100.00")
        assert created.status == InvoiceStatus.DRAFT
    
    async def test_get_by_invoice_number(self, db: AsyncSession, test_invoice):
        """Test getting invoice by number"""
        repo = InvoiceRepository(db)
        
        invoice = await repo.get_by_invoice_number(test_invoice.invoice_number)
        
        assert invoice is not None
        assert invoice.id == test_invoice.id
    
    async def test_generate_invoice_number(self, db: AsyncSession):
        """Test invoice number generation"""
        repo = InvoiceRepository(db)
        
        number1 = await repo.generate_invoice_number()
        number2 = await repo.generate_invoice_number()
        
        assert number1.startswith("INV-")
        assert number2.startswith("INV-")
        assert number1 != number2
    
    async def test_search_invoices(self, db: AsyncSession, test_invoice):
        """Test searching invoices with filters"""
        repo = InvoiceRepository(db)
        
        invoices, total = await repo.search_invoices(
            status=InvoiceStatus.DRAFT,
            skip=0,
            limit=10
        )
        
        assert total > 0
        assert len(invoices) > 0
        assert all(i.status == InvoiceStatus.DRAFT for i in invoices)
    
    async def test_get_overdue_invoices(self, db: AsyncSession):
        """Test getting overdue invoices"""
        repo = InvoiceRepository(db)
        
        # Create overdue invoice
        invoice = Invoice(
            invoice_number="INV-OVERDUE-001",
            invoice_date=date.today() - timedelta(days=60),
            due_date=date.today() - timedelta(days=30),
            status=InvoiceStatus.OVERDUE,
            is_overdue_flag=True,
            total_amount=Decimal("500.00"),
            amount_due=Decimal("500.00"),
            customer_name="Overdue Customer"
        )
        await repo.create(invoice)
        await db.commit()
        
        overdue = await repo.get_overdue_invoices()
        
        assert len(overdue) > 0
        assert all(i.is_overdue_flag for i in overdue)


# ========== Payment Repository Tests ==========

@pytest.mark.asyncio
class TestPaymentRecordRepository:
    """Test PaymentRecordRepository"""
    
    async def test_create_payment(self, db: AsyncSession, test_invoice, test_user):
        """Test creating payment record"""
        repo = PaymentRecordRepository(db)
        
        payment = PaymentRecord(
            payment_number="PAY-TEST-001",
            invoice_id=test_invoice.id,
            amount=Decimal("500.00"),
            payment_date=date.today(),
            payment_gateway=PaymentGateway.BANK_TRANSFER,
            payment_method="Bank Transfer",
            status=PaymentRecordStatus.COMPLETED,
            created_by_id=test_user.id
        )
        
        created = await repo.create(payment)
        await db.commit()
        
        assert created.id is not None
        assert created.amount == Decimal("500.00")
        assert created.status == PaymentRecordStatus.COMPLETED
    
    async def test_get_by_invoice(self, db: AsyncSession, test_invoice, test_payment):
        """Test getting payments by invoice"""
        repo = PaymentRecordRepository(db)
        
        payments = await repo.get_by_invoice(test_invoice.id)
        
        assert len(payments) > 0
        assert all(p.invoice_id == test_invoice.id for p in payments)
    
    async def test_generate_payment_number(self, db: AsyncSession):
        """Test payment number generation"""
        repo = PaymentRecordRepository(db)
        
        number1 = await repo.generate_payment_number()
        number2 = await repo.generate_payment_number()
        
        assert number1.startswith("PAY-")
        assert number2.startswith("PAY-")
        assert number1 != number2
    
    async def test_get_unreconciled_payments(self, db: AsyncSession, test_payment):
        """Test getting unreconciled payments"""
        repo = PaymentRecordRepository(db)
        
        unreconciled = await repo.get_unreconciled_payments()
        
        assert len(unreconciled) >= 0
        assert all(not p.is_reconciled for p in unreconciled)


# ========== Credit Note Repository Tests ==========

@pytest.mark.asyncio
class TestCreditNoteRepository:
    """Test CreditNoteRepository"""
    
    async def test_create_credit_note(self, db: AsyncSession, test_invoice, test_user):
        """Test creating credit note"""
        repo = CreditNoteRepository(db)
        
        credit_note = CreditNote(
            credit_note_number="CN-TEST-001",
            invoice_id=test_invoice.id,
            amount=Decimal("100.00"),
            amount_remaining=Decimal("100.00"),
            reason=CreditNoteReason.RETURN,
            description="Product return",
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=365),
            is_approved=True,
            created_by_id=test_user.id
        )
        
        created = await repo.create(credit_note)
        await db.commit()
        
        assert created.id is not None
        assert created.amount == Decimal("100.00")
        assert created.reason == CreditNoteReason.RETURN
    
    async def test_get_available_credits(self, db: AsyncSession, test_credit_note):
        """Test getting available credits"""
        repo = CreditNoteRepository(db)
        
        credits = await repo.get_available_credits(
            wholesale_customer_id=test_credit_note.wholesale_customer_id
        )
        
        assert len(credits) >= 0
        assert all(c.amount_remaining > 0 for c in credits)
        assert all(not c.is_expired for c in credits)
    
    async def test_generate_credit_note_number(self, db: AsyncSession):
        """Test credit note number generation"""
        repo = CreditNoteRepository(db)
        
        number1 = await repo.generate_credit_note_number()
        number2 = await repo.generate_credit_note_number()
        
        assert number1.startswith("CN-")
        assert number2.startswith("CN-")
        assert number1 != number2


# ========== Service Tests ==========

@pytest.mark.asyncio
class TestAccountsReceivableService:
    """Test AccountsReceivableService"""
    
    async def test_create_invoice_with_items(self, db: AsyncSession, test_user):
        """Test creating invoice with items through service"""
        service = AccountsReceivableService(db)
        
        data = InvoiceCreate(
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            customer_name="Test Customer",
            customer_email="test@example.com",
            billing_address_line1="123 Test St",
            billing_city="Test City",
            billing_state="TS",
            billing_postal_code="12345",
            billing_country="Test Country",
            payment_terms="Net 30",
            tax_rate=Decimal("10.0"),
            items=[
                InvoiceItemCreate(
                    description="Test Product 1",
                    quantity=Decimal("2"),
                    unit_price=Decimal("100.00"),
                    line_total=Decimal("200.00"),
                    tax_rate=Decimal("10.0")
                ),
                InvoiceItemCreate(
                    description="Test Product 2",
                    quantity=Decimal("1"),
                    unit_price=Decimal("150.00"),
                    line_total=Decimal("150.00"),
                    tax_rate=Decimal("10.0")
                )
            ]
        )
        
        invoice = await service.create_invoice(data, test_user.id)
        
        assert invoice.id is not None
        assert invoice.subtotal == Decimal("350.00")
        assert invoice.tax_amount == Decimal("35.00")
        assert invoice.total_amount == Decimal("385.00")
        assert len(invoice.items) == 2
    
    async def test_send_invoice(self, db: AsyncSession, test_invoice):
        """Test sending invoice"""
        service = AccountsReceivableService(db)
        
        invoice = await service.send_invoice(test_invoice.id)
        
        assert invoice.status == InvoiceStatus.SENT
        assert invoice.is_sent is True
        assert invoice.sent_at is not None
    
    async def test_record_payment(self, db: AsyncSession, test_invoice, test_user):
        """Test recording payment"""
        service = AccountsReceivableService(db)
        
        data = PaymentRecordCreate(
            invoice_id=test_invoice.id,
            amount=Decimal("500.00"),
            payment_date=date.today(),
            payment_gateway=PaymentGateway.BANK_TRANSFER,
            payment_method="Bank Transfer"
        )
        
        payment, updated_invoice = await service.record_payment(data, test_user.id)
        
        assert payment.id is not None
        assert payment.amount == Decimal("500.00")
        assert updated_invoice.amount_paid >= Decimal("500.00")
        assert updated_invoice.amount_due == updated_invoice.total_amount - updated_invoice.amount_paid
    
    async def test_record_full_payment(self, db: AsyncSession, test_invoice, test_user):
        """Test recording full payment"""
        service = AccountsReceivableService(db)
        
        data = PaymentRecordCreate(
            invoice_id=test_invoice.id,
            amount=test_invoice.amount_due,
            payment_date=date.today(),
            payment_gateway=PaymentGateway.BANK_TRANSFER,
            payment_method="Bank Transfer"
        )
        
        payment, updated_invoice = await service.record_payment(data, test_user.id)
        
        assert updated_invoice.status == InvoiceStatus.PAID
        assert updated_invoice.amount_due == Decimal("0.00")
        assert updated_invoice.paid_at is not None
    
    async def test_create_credit_note(self, db: AsyncSession, test_invoice, test_user):
        """Test creating credit note"""
        service = AccountsReceivableService(db)
        
        data = CreditNoteCreate(
            invoice_id=test_invoice.id,
            amount=Decimal("100.00"),
            reason=CreditNoteReason.RETURN,
            description="Product return"
        )
        
        credit_note = await service.create_credit_note(data, test_user.id)
        
        assert credit_note.id is not None
        assert credit_note.amount == Decimal("100.00")
        assert credit_note.amount_remaining == Decimal("100.00")
        assert credit_note.is_approved is True
    
    async def test_apply_credit_note(self, db: AsyncSession, test_invoice, test_credit_note, test_user):
        """Test applying credit note to invoice"""
        service = AccountsReceivableService(db)
        
        original_due = test_invoice.amount_due
        
        data = ApplyCreditNote(
            credit_note_id=test_credit_note.id,
            invoice_id=test_invoice.id,
            amount_to_apply=Decimal("50.00")
        )
        
        credit_note, invoice = await service.apply_credit_note(data, test_user.id)
        
        assert credit_note.amount_used == Decimal("50.00")
        assert credit_note.amount_remaining == credit_note.amount - Decimal("50.00")
        assert invoice.amount_due == original_due - Decimal("50.00")
        assert invoice.credit_applied == Decimal("50.00")
    
    async def test_send_payment_reminder(self, db: AsyncSession, test_invoice, test_user):
        """Test sending payment reminder"""
        service = AccountsReceivableService(db)
        
        # Update invoice to overdue
        await service.invoice_repo.update(
            test_invoice.id,
            {
                "status": InvoiceStatus.OVERDUE,
                "is_overdue_flag": True,
                "due_date": date.today() - timedelta(days=10)
            }
        )
        await db.commit()
        
        reminder = await service.send_payment_reminder(
            test_invoice.id,
            ReminderType.FIRST,
            test_user.id
        )
        
        assert reminder.id is not None
        assert reminder.reminder_type == ReminderType.FIRST
        assert reminder.sent_at is not None
    
    async def test_reconcile_payment(self, db: AsyncSession, test_payment, test_user):
        """Test reconciling payment"""
        service = AccountsReceivableService(db)
        
        payment = await service.reconcile_payment(
            test_payment.id,
            test_user.id,
            "Matched with bank statement"
        )
        
        assert payment.is_reconciled is True
        assert payment.reconciled_at is not None
        assert payment.reconciled_by_id == test_user.id
    
    async def test_void_invoice(self, db: AsyncSession, test_invoice):
        """Test voiding invoice"""
        service = AccountsReceivableService(db)
        
        invoice = await service.void_invoice(test_invoice.id, "Customer cancelled")
        
        assert invoice.status == InvoiceStatus.VOID
        assert "Voided" in invoice.notes
    
    async def test_get_aging_report(self, db: AsyncSession):
        """Test generating aging report"""
        service = AccountsReceivableService(db)
        
        report = await service.get_aging_report()
        
        assert report.report_date == date.today()
        assert report.total_outstanding >= Decimal("0.00")
        assert report.current.amount >= Decimal("0.00")
    
    async def test_get_invoice_summary(self, db: AsyncSession):
        """Test getting invoice summary"""
        service = AccountsReceivableService(db)
        
        summary = await service.get_invoice_summary()
        
        assert summary.total_invoices >= 0
        assert summary.total_invoiced >= Decimal("0.00")
        assert summary.total_paid >= Decimal("0.00")
    
    async def test_get_ar_dashboard(self, db: AsyncSession):
        """Test getting AR dashboard"""
        service = AccountsReceivableService(db)
        
        dashboard = await service.get_ar_dashboard()
        
        assert dashboard.report_date == date.today()
        assert dashboard.invoice_summary is not None
        assert dashboard.payment_summary is not None
        assert dashboard.aging_report is not None


# ========== API Tests ==========

@pytest.mark.asyncio
class TestAccountsReceivableAPI:
    """Test AR API endpoints"""
    
    async def test_create_invoice_api(self, client, auth_headers):
        """Test POST /api/ar/invoices"""
        data = {
            "invoice_date": date.today().isoformat(),
            "due_date": (date.today() + timedelta(days=30)).isoformat(),
            "customer_name": "API Test Customer",
            "customer_email": "apitest@example.com",
            "billing_address_line1": "123 API St",
            "billing_city": "API City",
            "billing_state": "AS",
            "billing_postal_code": "12345",
            "billing_country": "API Country",
            "payment_terms": "Net 30",
            "tax_rate": "10.0",
            "items": [
                {
                    "description": "Test Item",
                    "quantity": "1",
                    "unit_price": "100.00",
                    "line_total": "100.00",
                    "tax_rate": "10.0"
                }
            ]
        }
        
        response = await client.post(
            "/api/ar/invoices",
            json=data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        result = response.json()
        assert result["customer_name"] == "API Test Customer"
        assert result["total_amount"] == "110.00"
    
    async def test_get_invoice_api(self, client, auth_headers, test_invoice):
        """Test GET /api/ar/invoices/{id}"""
        response = await client.get(
            f"/api/ar/invoices/{test_invoice.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["id"] == str(test_invoice.id)
    
    async def test_list_invoices_api(self, client, auth_headers):
        """Test GET /api/ar/invoices"""
        response = await client.get(
            "/api/ar/invoices?limit=10",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        result = response.json()
        assert "items" in result
        assert "total" in result
    
    async def test_record_payment_api(self, client, auth_headers, test_invoice):
        """Test POST /api/ar/payments"""
        data = {
            "invoice_id": str(test_invoice.id),
            "amount": "250.00",
            "payment_date": date.today().isoformat(),
            "payment_gateway": "bank_transfer",
            "payment_method": "Bank Transfer"
        }
        
        response = await client.post(
            "/api/ar/payments",
            json=data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        result = response.json()
        assert result["amount"] == "250.00"
    
    async def test_get_aging_report_api(self, client, auth_headers):
        """Test GET /api/ar/analytics/aging-report"""
        response = await client.get(
            "/api/ar/analytics/aging-report",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        result = response.json()
        assert "report_date" in result
        assert "total_outstanding" in result
    
    async def test_get_ar_dashboard_api(self, client, auth_headers):
        """Test GET /api/ar/analytics/dashboard"""
        response = await client.get(
            "/api/ar/analytics/dashboard",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        result = response.json()
        assert "invoice_summary" in result
        assert "payment_summary" in result
        assert "aging_report" in result


# ========== Fixtures ==========

@pytest.fixture
async def test_invoice(db: AsyncSession, test_user):
    """Create test invoice"""
    repo = InvoiceRepository(db)
    
    invoice = Invoice(
        invoice_number=f"INV-TEST-{uuid4().hex[:8]}",
        invoice_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        status=InvoiceStatus.DRAFT,
        subtotal=Decimal("1000.00"),
        tax_rate=Decimal("10.0"),
        tax_amount=Decimal("100.00"),
        total_amount=Decimal("1100.00"),
        amount_paid=Decimal("0.00"),
        amount_due=Decimal("1100.00"),
        customer_name="Test Customer",
        customer_email="test@example.com",
        billing_address_line1="123 Test St",
        billing_city="Test City",
        billing_state="TS",
        billing_postal_code="12345",
        billing_country="Test Country",
        payment_terms="Net 30",
        created_by_id=test_user.id
    )
    
    created = await repo.create(invoice)
    await db.commit()
    
    return created


@pytest.fixture
async def test_payment(db: AsyncSession, test_invoice, test_user):
    """Create test payment"""
    repo = PaymentRecordRepository(db)
    
    payment = PaymentRecord(
        payment_number=f"PAY-TEST-{uuid4().hex[:8]}",
        invoice_id=test_invoice.id,
        amount=Decimal("500.00"),
        payment_date=date.today(),
        payment_gateway=PaymentGateway.BANK_TRANSFER,
        payment_method="Bank Transfer",
        status=PaymentRecordStatus.COMPLETED,
        is_reconciled=False,
        created_by_id=test_user.id
    )
    
    created = await repo.create(payment)
    await db.commit()
    
    return created


@pytest.fixture
async def test_credit_note(db: AsyncSession, test_invoice, test_user):
    """Create test credit note"""
    repo = CreditNoteRepository(db)
    
    credit_note = CreditNote(
        credit_note_number=f"CN-TEST-{uuid4().hex[:8]}",
        invoice_id=test_invoice.id,
        amount=Decimal("100.00"),
        amount_used=Decimal("0.00"),
        amount_remaining=Decimal("100.00"),
        reason=CreditNoteReason.RETURN,
        description="Test credit note",
        issue_date=date.today(),
        expiry_date=date.today() + timedelta(days=365),
        is_approved=True,
        created_by_id=test_user.id
    )
    
    created = await repo.create(credit_note)
    await db.commit()
    
    return created
