"""
Test configuration and fixtures
"""
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from httpx import AsyncClient
import asyncio

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings


# Create test database engine
test_engine = create_async_engine(
    settings.TEST_DATABASE_URL or settings.DATABASE_URL.replace("bms_db", "bms_test"),
    echo=False,
    pool_pre_ping=True,
)

# Create test session factory
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop():
    """
    Create an instance of the default event loop for each test case.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a fresh database session for each test
    """
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async with TestSessionLocal() as session:
        yield session
    
    # Drop tables after test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """
    Create a test client with database override
    """
    def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    return AsyncClient(app=app, base_url="http://test")


@pytest.fixture
def mock_user_data():
    """
    Mock user data for testing
    """
    return {
        "email": "test@example.com",
        "password": "SecurePass123",
        "first_name": "Test",
        "last_name": "User",
        "phone": "+1234567890"
    }


@pytest.fixture
def mock_login_data():
    """
    Mock login data for testing
    """
    return {
        "email": "test@example.com",
        "password": "SecurePass123"
    }


# ===== CRM Test Fixtures =====

@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    """Create a test user"""
    from app.models.user import User
    from app.core.security import hash_password

    user = User(
        email="crm.user@test.com",
        hashed_password=hash_password("TestPass123"),
        first_name="CRM",
        last_name="User",
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_headers(test_user, client: AsyncClient):
    """Create authentication headers"""
    from app.core.security import create_access_token

    access_token = create_access_token(data={"sub": test_user.email, "user_id": str(test_user.id)})
    return {"Authorization": f"Bearer {access_token}"}


@pytest_asyncio.fixture
async def test_wholesale_customer(db_session: AsyncSession):
    """Create a test wholesale customer"""
    from app.models.wholesale import WholesaleCustomer, PaymentTerms
    from decimal import Decimal

    customer = WholesaleCustomer(
        company_name="Test Wholesale Co",
        contact_person="Jane Manager",
        email="wholesale@test.com",
        phone="+911234567890",
        address="123 Test Street",
        city="Mumbai",
        state="Maharashtra",
        country="India",
        postal_code="400001",
        payment_terms=PaymentTerms.NET_30,
        credit_limit=Decimal("100000.00"),
        credit_used=Decimal("0.00")
    )
    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)
    return customer


@pytest_asyncio.fixture
async def test_lead(db_session: AsyncSession, test_user):
    """Create a test lead"""
    from app.models.crm import Lead, LeadStatus, LeadSource, LeadPriority
    from decimal import Decimal

    lead = Lead(
        lead_number="LEAD-TEST-0001",
        company_name="Test Lead Company",
        industry="Retail",
        contact_person="John Prospect",
        email="lead@test.com",
        phone="+919876543210",
        address_line1="456 Lead Ave",
        city="Delhi",
        state="Delhi",
        country="India",
        postal_code="110001",
        source=LeadSource.WEBSITE,
        status=LeadStatus.NEW,
        priority=LeadPriority.MEDIUM,
        estimated_deal_value=Decimal("50000.00"),
        created_by_id=test_user.id
    )
    db_session.add(lead)
    await db_session.commit()
    await db_session.refresh(lead)
    return lead


@pytest_asyncio.fixture
async def test_opportunity(db_session: AsyncSession, test_wholesale_customer, test_user):
    """Create a test sales opportunity"""
    from app.models.crm import SalesOpportunity, OpportunityStage
    from decimal import Decimal

    opportunity = SalesOpportunity(
        opportunity_number="OPP-TEST-0001",
        name="Test Opportunity - Q4 Order",
        description="Winter collection bulk order",
        customer_id=test_wholesale_customer.id,
        owner_id=test_user.id,
        stage=OpportunityStage.PROSPECTING,
        estimated_value=Decimal("100000.00"),
        probability=50,
        expected_revenue=Decimal("50000.00")
    )
    db_session.add(opportunity)
    await db_session.commit()
    await db_session.refresh(opportunity)
    return opportunity


@pytest_asyncio.fixture
async def test_communication(db_session: AsyncSession, test_wholesale_customer, test_user):
    """Create a test customer communication"""
    from app.models.crm import CustomerCommunication, CommunicationType, CommunicationDirection

    communication = CustomerCommunication(
        customer_id=test_wholesale_customer.id,
        our_representative_id=test_user.id,
        type=CommunicationType.PHONE,
        direction=CommunicationDirection.OUTBOUND,
        subject="Follow-up call",
        content="Discussed order requirements",
        duration_minutes=10,
        requires_follow_up=True
    )
    db_session.add(communication)
    await db_session.commit()
    await db_session.refresh(communication)
    return communication


@pytest_asyncio.fixture
async def test_segment(db_session: AsyncSession):
    """Create a test customer segment"""
    from app.models.crm import CustomerSegment

    segment = CustomerSegment(
        name="Test Premium Segment",
        description="Test segment for premium customers",
        code="TEST-PREM",
        criteria={"min_spend": 100000},
        is_active=True,
        priority=1,
        customer_count=0
    )
    db_session.add(segment)
    await db_session.commit()
    await db_session.refresh(segment)
    return segment


# ===== Retail Customer (B2C CRM) Test Fixtures =====

@pytest_asyncio.fixture
async def test_retail_customer(db_session: AsyncSession):
    """Create a test retail customer"""
    from app.models.retail_customer import RetailCustomer, CustomerTierLevel
    from decimal import Decimal

    customer = RetailCustomer(
        customer_number="CUST-TEST-0001",
        first_name="John",
        last_name="Customer",
        email="john.customer@test.com",
        phone="+919123456789",
        address_line1="789 Customer St",
        city="Bangalore",
        state="Karnataka",
        country="India",
        postal_code="560001",
        loyalty_tier=CustomerTierLevel.BRONZE,
        loyalty_points=100,
        loyalty_points_lifetime=100,
        total_orders=0,
        total_spent=Decimal("0.00"),
        average_order_value=Decimal("0.00"),
        email_marketing_consent=True,
        sms_marketing_consent=True,
        is_active=True
    )
    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)
    return customer


@pytest_asyncio.fixture
async def test_loyalty_transaction(db_session: AsyncSession, test_retail_customer):
    """Create a test loyalty transaction"""
    from app.models.retail_customer import LoyaltyTransaction
    from datetime import datetime, timedelta

    transaction = LoyaltyTransaction(
        customer_id=test_retail_customer.id,
        transaction_type="EARNED",
        points=100,
        description="Welcome bonus",
        balance_before=0,
        balance_after=100,
        expires_at=datetime.utcnow() + timedelta(days=365)
    )
    db_session.add(transaction)
    await db_session.commit()
    await db_session.refresh(transaction)
    return transaction


@pytest_asyncio.fixture
async def test_customer_preference(db_session: AsyncSession, test_retail_customer):
    """Create a test customer preference"""
    from app.models.retail_customer import CustomerPreference, CustomerPreferenceType

    preference = CustomerPreference(
        customer_id=test_retail_customer.id,
        preference_type=CustomerPreferenceType.COMMUNICATION,
        preference_key="email_frequency",
        preference_value="weekly"
    )
    db_session.add(preference)
    await db_session.commit()
    await db_session.refresh(preference)
    return preference


# ===== Accounts Payable Test Fixtures =====

@pytest_asyncio.fixture
async def test_supplier(db_session: AsyncSession):
    """Create a test supplier"""
    from app.models.supplier import Supplier
    from uuid import uuid4

    supplier = Supplier(
        id=uuid4(),
        name="Test Fabric Supplier Ltd",
        code="SUP-001",
        contact_person="John Smith",
        email="john@supplier.com",
        phone="+1234567890",
        address_line1="123 Business St",
        city="Mumbai",
        state="Maharashtra",
        postal_code="400001",
        country="India",
        tax_id="GST123456789",
        payment_terms="Net 30",
        credit_limit=100000.00,
        is_active=True
    )
    db_session.add(supplier)
    await db_session.commit()
    await db_session.refresh(supplier)
    return supplier


@pytest_asyncio.fixture
async def test_bill(db_session: AsyncSession, test_supplier, test_user):
    """Create a test bill in DRAFT status"""
    from app.models.finance import Bill, BillStatus, ExpenseCategory
    from datetime import date, timedelta
    from decimal import Decimal
    from uuid import uuid4

    bill = Bill(
        id=uuid4(),
        bill_number="BILL-2025-000001",
        supplier_id=test_supplier.id,
        supplier_bill_number="SUP-INV-2025-001",
        description="Fabric purchase for winter collection",
        category=ExpenseCategory.INVENTORY,
        status=BillStatus.DRAFT,
        subtotal=Decimal("10000.00"),
        tax_amount=Decimal("1800.00"),
        total_amount=Decimal("11800.00"),
        paid_amount=Decimal("0.00"),
        balance_due=Decimal("11800.00"),
        bill_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        payment_terms="NET_30",
        created_by_id=test_user.id
    )
    db_session.add(bill)
    await db_session.commit()
    await db_session.refresh(bill)
    return bill


@pytest_asyncio.fixture
async def test_pending_bill(db_session: AsyncSession, test_supplier, test_user):
    """Create a test bill in PENDING status"""
    from app.models.finance import Bill, BillStatus, ExpenseCategory
    from datetime import date, timedelta
    from decimal import Decimal
    from uuid import uuid4

    bill = Bill(
        id=uuid4(),
        bill_number="BILL-2025-000002",
        supplier_id=test_supplier.id,
        description="Office supplies purchase",
        category=ExpenseCategory.OFFICE_SUPPLIES,
        status=BillStatus.PENDING,
        subtotal=Decimal("5000.00"),
        tax_amount=Decimal("900.00"),
        total_amount=Decimal("5900.00"),
        paid_amount=Decimal("0.00"),
        balance_due=Decimal("5900.00"),
        bill_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        payment_terms="NET_30",
        created_by_id=test_user.id
    )
    db_session.add(bill)
    await db_session.commit()
    await db_session.refresh(bill)
    return bill


@pytest_asyncio.fixture
async def test_approved_bill(db_session: AsyncSession, test_supplier, test_user):
    """Create a test bill in APPROVED status"""
    from app.models.finance import Bill, BillStatus, ExpenseCategory
    from datetime import date, datetime, timedelta
    from decimal import Decimal
    from uuid import uuid4

    bill = Bill(
        id=uuid4(),
        bill_number="BILL-2025-000003",
        supplier_id=test_supplier.id,
        description="Approved bill for testing payments",
        category=ExpenseCategory.INVENTORY,
        status=BillStatus.APPROVED,
        subtotal=Decimal("15000.00"),
        tax_amount=Decimal("2700.00"),
        total_amount=Decimal("17700.00"),
        paid_amount=Decimal("0.00"),
        balance_due=Decimal("17700.00"),
        bill_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        payment_terms="NET_30",
        approved_by_id=test_user.id,
        approved_at=datetime.utcnow(),
        created_by_id=test_user.id
    )
    db_session.add(bill)
    await db_session.commit()
    await db_session.refresh(bill)
    return bill


@pytest_asyncio.fixture
async def test_vendor_payment(db_session: AsyncSession, test_approved_bill, test_user):
    """Create a test vendor payment"""
    from app.models.finance import VendorPayment, PaymentRecordStatus
    from datetime import date
    from decimal import Decimal
    from uuid import uuid4

    payment = VendorPayment(
        id=uuid4(),
        payment_number="VPAY-2025-000001",
        bill_id=test_approved_bill.id,
        amount=Decimal("8000.00"),
        payment_method="BANK_TRANSFER",
        payment_date=date.today(),
        transaction_reference="TXN-TEST-001",
        status=PaymentRecordStatus.COMPLETED,
        created_by_id=test_user.id
    )
    db_session.add(payment)
    
    # Update bill
    test_approved_bill.paid_amount += payment.amount
    test_approved_bill.balance_due = test_approved_bill.total_amount - test_approved_bill.paid_amount
    test_approved_bill.status = BillStatus.PARTIALLY_PAID
    
    await db_session.commit()
    await db_session.refresh(payment)
    return payment


@pytest_asyncio.fixture
async def test_pending_bills(db_session: AsyncSession, test_supplier, test_user):
    """Create multiple test bills in PENDING status"""
    from app.models.finance import Bill, BillStatus, ExpenseCategory
    from datetime import date, timedelta
    from decimal import Decimal
    from uuid import uuid4

    bills = []
    for i in range(5):
        bill = Bill(
            id=uuid4(),
            bill_number=f"BILL-2025-{100+i:06d}",
            supplier_id=test_supplier.id,
            description=f"Test bill {i+1}",
            category=ExpenseCategory.INVENTORY,
            status=BillStatus.PENDING,
            subtotal=Decimal("1000.00") * (i + 1),
            tax_amount=Decimal("180.00") * (i + 1),
            total_amount=Decimal("1180.00") * (i + 1),
            paid_amount=Decimal("0.00"),
            balance_due=Decimal("1180.00") * (i + 1),
            bill_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            payment_terms="NET_30",
            created_by_id=test_user.id
        )
        db_session.add(bill)
        bills.append(bill)
    
    await db_session.commit()
    for bill in bills:
        await db_session.refresh(bill)
    return bills


@pytest_asyncio.fixture
async def test_bills(db_session: AsyncSession, test_supplier, test_user):
    """Create multiple test bills in various statuses"""
    from app.models.finance import Bill, BillStatus, ExpenseCategory
    from datetime import date, timedelta
    from decimal import Decimal
    from uuid import uuid4

    bills = []
    statuses = [BillStatus.DRAFT, BillStatus.PENDING, BillStatus.APPROVED]
    
    for i, status in enumerate(statuses):
        bill = Bill(
            id=uuid4(),
            bill_number=f"BILL-2025-{200+i:06d}",
            supplier_id=test_supplier.id,
            description=f"Bill with {status.value} status",
            category=ExpenseCategory.INVENTORY,
            status=status,
            subtotal=Decimal("2000.00"),
            tax_amount=Decimal("360.00"),
            total_amount=Decimal("2360.00"),
            paid_amount=Decimal("0.00"),
            balance_due=Decimal("2360.00"),
            bill_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            payment_terms="NET_30",
            created_by_id=test_user.id
        )
        db_session.add(bill)
        bills.append(bill)
    
    await db_session.commit()
    for bill in bills:
        await db_session.refresh(bill)
    return bills
