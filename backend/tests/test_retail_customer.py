"""
Tests for Retail Customer (B2C CRM) Module

Comprehensive tests covering:
- Customer registration and management
- Loyalty program operations
- Customer preferences
- RFM analysis
- CLV calculation
- Bulk operations
"""

import pytest
from datetime import datetime, timedelta, date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.retail_customer import (
    RetailCustomer,
    LoyaltyTransaction,
    CustomerPreference,
    CustomerTierLevel,
    CustomerPreferenceType
)
from app.repositories.retail_customer import (
    RetailCustomerRepository,
    LoyaltyTransactionRepository,
    CustomerPreferenceRepository
)
from app.services.retail_customer import RetailCustomerService


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
async def retail_customer_repo(db_session: AsyncSession):
    """Retail customer repository fixture"""
    return RetailCustomerRepository(db_session)


@pytest.fixture
async def loyalty_repo(db_session: AsyncSession):
    """Loyalty transaction repository fixture"""
    return LoyaltyTransactionRepository(db_session)


@pytest.fixture
async def preference_repo(db_session: AsyncSession):
    """Customer preference repository fixture"""
    return CustomerPreferenceRepository(db_session)


@pytest.fixture
async def retail_service(db_session: AsyncSession):
    """Retail customer service fixture"""
    return RetailCustomerService(db_session)


@pytest.fixture
async def sample_retail_customer(retail_customer_repo: RetailCustomerRepository):
    """Create a sample retail customer"""
    customer_data = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "phone": "+1234567890",
        "city": "Mumbai",
        "state": "Maharashtra",
        "country": "India",
        "email_marketing_consent": True,
        "sms_marketing_consent": True
    }
    
    customer = await retail_customer_repo.create_customer(customer_data)
    return customer


# ============================================================================
# Customer Repository Tests
# ============================================================================

@pytest.mark.asyncio
async def test_create_retail_customer(retail_customer_repo: RetailCustomerRepository):
    """Test creating a retail customer"""
    customer_data = {
        "first_name": "Jane",
        "last_name": "Smith",
        "email": "jane.smith@example.com",
        "phone": "+1987654321",
        "city": "Delhi",
        "country": "India"
    }
    
    customer = await retail_customer_repo.create_customer(customer_data)
    
    assert customer.id is not None
    assert customer.customer_number.startswith("CUST-")
    assert customer.first_name == "Jane"
    assert customer.last_name == "Smith"
    assert customer.email == "jane.smith@example.com"
    assert customer.loyalty_tier == CustomerTierLevel.BRONZE
    assert customer.loyalty_points == 0
    assert customer.total_orders == 0
    assert customer.is_active is True


@pytest.mark.asyncio
async def test_get_customer_by_email(
    retail_customer_repo: RetailCustomerRepository,
    sample_retail_customer: RetailCustomer
):
    """Test getting customer by email"""
    customer = await retail_customer_repo.get_by_email(sample_retail_customer.email)
    
    assert customer is not None
    assert customer.id == sample_retail_customer.id
    assert customer.email == sample_retail_customer.email


@pytest.mark.asyncio
async def test_get_customer_by_phone(
    retail_customer_repo: RetailCustomerRepository,
    sample_retail_customer: RetailCustomer
):
    """Test getting customer by phone"""
    customer = await retail_customer_repo.get_by_phone(sample_retail_customer.phone)
    
    assert customer is not None
    assert customer.id == sample_retail_customer.id
    assert customer.phone == sample_retail_customer.phone


@pytest.mark.asyncio
async def test_search_customers(retail_customer_repo: RetailCustomerRepository):
    """Test customer search with filters"""
    # Create multiple customers
    for i in range(5):
        await retail_customer_repo.create_customer({
            "first_name": f"Customer{i}",
            "last_name": f"Test{i}",
            "email": f"customer{i}@test.com",
            "phone": f"+12345678{i:02d}",
            "city": "Mumbai" if i % 2 == 0 else "Delhi"
        })
    
    # Search by city
    mumbai_customers = await retail_customer_repo.search_customers(city="Mumbai")
    assert len(mumbai_customers) == 3
    
    # Search by name
    search_results = await retail_customer_repo.search_customers(search="Customer1")
    assert len(search_results) == 1
    assert search_results[0].first_name == "Customer1"


@pytest.mark.asyncio
async def test_update_loyalty_points(
    retail_customer_repo: RetailCustomerRepository,
    sample_retail_customer: RetailCustomer
):
    """Test updating loyalty points"""
    customer = await retail_customer_repo.update_loyalty_points(
        sample_retail_customer.id,
        100
    )
    
    assert customer.loyalty_points == 100
    assert customer.loyalty_points_lifetime == 100
    
    # Add more points
    customer = await retail_customer_repo.update_loyalty_points(
        sample_retail_customer.id,
        50
    )
    
    assert customer.loyalty_points == 150
    assert customer.loyalty_points_lifetime == 150


@pytest.mark.asyncio
async def test_update_purchase_metrics(
    retail_customer_repo: RetailCustomerRepository,
    sample_retail_customer: RetailCustomer
):
    """Test updating purchase metrics"""
    order_total = Decimal("1500.00")
    order_date = datetime.utcnow()
    
    customer = await retail_customer_repo.update_purchase_metrics(
        sample_retail_customer.id,
        order_total,
        order_date
    )
    
    assert customer.total_orders == 1
    assert customer.total_spent == order_total
    assert customer.average_order_value == order_total
    assert customer.first_order_date == order_date
    assert customer.last_order_date == order_date


@pytest.mark.asyncio
async def test_update_rfm_scores(
    retail_customer_repo: RetailCustomerRepository,
    sample_retail_customer: RetailCustomer
):
    """Test updating RFM scores"""
    customer = await retail_customer_repo.update_rfm_scores(
        sample_retail_customer.id,
        recency_score=5,
        frequency_score=4,
        monetary_score=4,
        segment="Loyal"
    )
    
    assert customer.rfm_recency_score == 5
    assert customer.rfm_frequency_score == 4
    assert customer.rfm_monetary_score == 4
    assert customer.rfm_segment == "Loyal"
    assert customer.rfm_last_calculated is not None


@pytest.mark.asyncio
async def test_bulk_update_status(retail_customer_repo: RetailCustomerRepository):
    """Test bulk status update"""
    # Create multiple customers
    customer_ids = []
    for i in range(3):
        customer = await retail_customer_repo.create_customer({
            "first_name": f"Bulk{i}",
            "last_name": "Test",
            "email": f"bulk{i}@test.com",
            "phone": f"+13456789{i:02d}"
        })
        customer_ids.append(customer.id)
    
    # Bulk deactivate
    count = await retail_customer_repo.bulk_update_status(customer_ids, False)
    
    assert count == 3
    
    # Verify status
    for cid in customer_ids:
        customer = await retail_customer_repo.get(cid)
        assert customer.is_active is False


# ============================================================================
# Loyalty Transaction Tests
# ============================================================================

@pytest.mark.asyncio
async def test_create_loyalty_transaction(
    loyalty_repo: LoyaltyTransactionRepository,
    sample_retail_customer: RetailCustomer
):
    """Test creating loyalty transaction"""
    transaction = await loyalty_repo.create_transaction(
        customer_id=sample_retail_customer.id,
        transaction_type="EARNED",
        points=100,
        description="Welcome bonus",
        balance_before=0,
        balance_after=100,
        expires_at=datetime.utcnow() + timedelta(days=365)
    )
    
    assert transaction.id is not None
    assert transaction.customer_id == sample_retail_customer.id
    assert transaction.transaction_type == "EARNED"
    assert transaction.points == 100
    assert transaction.balance_after == 100


@pytest.mark.asyncio
async def test_get_customer_transactions(
    loyalty_repo: LoyaltyTransactionRepository,
    sample_retail_customer: RetailCustomer
):
    """Test getting customer transactions"""
    # Create multiple transactions
    for i in range(5):
        await loyalty_repo.create_transaction(
            customer_id=sample_retail_customer.id,
            transaction_type="EARNED" if i % 2 == 0 else "REDEEMED",
            points=50,
            description=f"Transaction {i}",
            balance_before=i * 50,
            balance_after=(i + 1) * 50
        )
    
    # Get all transactions
    transactions = await loyalty_repo.get_customer_transactions(
        sample_retail_customer.id
    )
    
    assert len(transactions) == 5
    
    # Filter by type
    earned = await loyalty_repo.get_customer_transactions(
        sample_retail_customer.id,
        transaction_type="EARNED"
    )
    
    assert len(earned) == 3


@pytest.mark.asyncio
async def test_get_points_expiring_soon(
    loyalty_repo: LoyaltyTransactionRepository,
    sample_retail_customer: RetailCustomer
):
    """Test getting points expiring soon"""
    # Create transaction expiring in 20 days
    expires_soon = datetime.utcnow() + timedelta(days=20)
    await loyalty_repo.create_transaction(
        customer_id=sample_retail_customer.id,
        transaction_type="EARNED",
        points=100,
        description="Expiring soon",
        balance_before=0,
        balance_after=100,
        expires_at=expires_soon
    )
    
    # Create transaction expiring in 60 days
    expires_later = datetime.utcnow() + timedelta(days=60)
    await loyalty_repo.create_transaction(
        customer_id=sample_retail_customer.id,
        transaction_type="EARNED",
        points=200,
        description="Expiring later",
        balance_before=100,
        balance_after=300,
        expires_at=expires_later
    )
    
    # Get expiring within 30 days
    expiring = await loyalty_repo.get_points_expiring_soon(
        sample_retail_customer.id,
        days=30
    )
    
    assert len(expiring) == 1
    assert expiring[0].points == 100


# ============================================================================
# Customer Preference Tests
# ============================================================================

@pytest.mark.asyncio
async def test_upsert_preference(
    preference_repo: CustomerPreferenceRepository,
    sample_retail_customer: RetailCustomer
):
    """Test creating/updating preference"""
    # Create new preference
    pref = await preference_repo.upsert_preference(
        customer_id=sample_retail_customer.id,
        preference_type=CustomerPreferenceType.COMMUNICATION,
        preference_key="email_frequency",
        preference_value="weekly"
    )
    
    assert pref.id is not None
    assert pref.preference_value == "weekly"
    
    # Update existing preference
    pref = await preference_repo.upsert_preference(
        customer_id=sample_retail_customer.id,
        preference_type=CustomerPreferenceType.COMMUNICATION,
        preference_key="email_frequency",
        preference_value="daily"
    )
    
    assert pref.preference_value == "daily"


@pytest.mark.asyncio
async def test_get_customer_preferences(
    preference_repo: CustomerPreferenceRepository,
    sample_retail_customer: RetailCustomer
):
    """Test getting customer preferences"""
    # Create multiple preferences
    await preference_repo.upsert_preference(
        sample_retail_customer.id,
        CustomerPreferenceType.COMMUNICATION,
        "email_frequency",
        "weekly"
    )
    
    await preference_repo.upsert_preference(
        sample_retail_customer.id,
        CustomerPreferenceType.SHOPPING,
        "favorite_category",
        "shirts"
    )
    
    # Get all preferences
    prefs = await preference_repo.get_customer_preferences(
        sample_retail_customer.id
    )
    
    assert len(prefs) == 2
    
    # Get by type
    comm_prefs = await preference_repo.get_customer_preferences(
        sample_retail_customer.id,
        CustomerPreferenceType.COMMUNICATION
    )
    
    assert len(comm_prefs) == 1
    assert comm_prefs[0].preference_key == "email_frequency"


# ============================================================================
# Service Layer Tests
# ============================================================================

@pytest.mark.asyncio
async def test_register_customer(retail_service: RetailCustomerService):
    """Test customer registration with welcome bonus"""
    customer_data = {
        "first_name": "Alice",
        "last_name": "Johnson",
        "email": "alice.johnson@example.com",
        "phone": "+1555123456",
        "city": "Bangalore"
    }
    
    customer, loyalty_txn = await retail_service.register_customer(
        customer_data,
        welcome_bonus=150
    )
    
    assert customer.id is not None
    assert customer.loyalty_points == 150
    assert loyalty_txn is not None
    assert loyalty_txn.points == 150
    assert loyalty_txn.transaction_type == "EARNED"


@pytest.mark.asyncio
async def test_earn_loyalty_points(
    retail_service: RetailCustomerService,
    sample_retail_customer: RetailCustomer
):
    """Test earning loyalty points"""
    transaction = await retail_service.earn_loyalty_points(
        customer_id=sample_retail_customer.id,
        points=200,
        description="Purchase reward",
        expiry_days=365
    )
    
    assert transaction.points == 200
    assert transaction.balance_after == 200
    assert transaction.expires_at is not None


@pytest.mark.asyncio
async def test_redeem_loyalty_points(
    retail_service: RetailCustomerService,
    retail_customer_repo: RetailCustomerRepository,
    sample_retail_customer: RetailCustomer
):
    """Test redeeming loyalty points"""
    # First earn some points
    await retail_service.earn_loyalty_points(
        customer_id=sample_retail_customer.id,
        points=500,
        description="Earned points"
    )
    
    # Redeem points
    transaction = await retail_service.redeem_loyalty_points(
        customer_id=sample_retail_customer.id,
        points=200,
        description="Discount redemption"
    )
    
    assert transaction.points == 200
    assert transaction.balance_after == 300
    
    # Verify customer balance
    customer = await retail_customer_repo.get(sample_retail_customer.id)
    assert customer.loyalty_points == 300


@pytest.mark.asyncio
async def test_redeem_insufficient_points(
    retail_service: RetailCustomerService,
    sample_retail_customer: RetailCustomer
):
    """Test redeeming with insufficient points"""
    with pytest.raises(ValueError, match="Insufficient points"):
        await retail_service.redeem_loyalty_points(
            customer_id=sample_retail_customer.id,
            points=100,
            description="Should fail"
        )


@pytest.mark.asyncio
async def test_update_loyalty_tier_auto(
    retail_service: RetailCustomerService,
    retail_customer_repo: RetailCustomerRepository,
    sample_retail_customer: RetailCustomer
):
    """Test auto-calculating loyalty tier"""
    # Earn enough points for Silver tier (10,000 lifetime)
    await retail_customer_repo.update_loyalty_points(sample_retail_customer.id, 10000)
    
    customer = await retail_service.update_loyalty_tier(
        sample_retail_customer.id,
        auto_calculate=True
    )
    
    assert customer.loyalty_tier == CustomerTierLevel.SILVER
    assert customer.tier_start_date is not None


@pytest.mark.asyncio
async def test_calculate_rfm_scores(
    retail_service: RetailCustomerService,
    retail_customer_repo: RetailCustomerRepository
):
    """Test RFM score calculation"""
    # Create customers with purchase history
    customers = []
    for i in range(10):
        customer = await retail_customer_repo.create_customer({
            "first_name": f"RFM{i}",
            "last_name": "Test",
            "email": f"rfm{i}@test.com",
            "phone": f"+16789012{i:02d}"
        })
        
        # Simulate purchase history
        await retail_customer_repo.update_purchase_metrics(
            customer.id,
            Decimal(str(1000 * (i + 1))),
            datetime.utcnow() - timedelta(days=i * 10)
        )
        
        customers.append(customer)
    
    # Calculate RFM scores
    updated = await retail_service.calculate_rfm_scores()
    
    assert len(updated) >= len(customers)
    
    # Verify scores are calculated
    for customer in updated:
        assert customer.rfm_recency_score is not None
        assert 1 <= customer.rfm_recency_score <= 5
        assert customer.rfm_frequency_score is not None
        assert customer.rfm_monetary_score is not None
        assert customer.rfm_segment is not None


@pytest.mark.asyncio
async def test_get_rfm_segment_distribution(
    retail_service: RetailCustomerService,
    retail_customer_repo: RetailCustomerRepository
):
    """Test RFM segment distribution"""
    # Create customers and calculate RFM
    for i in range(5):
        customer = await retail_customer_repo.create_customer({
            "first_name": f"Segment{i}",
            "last_name": "Test",
            "email": f"segment{i}@test.com",
            "phone": f"+17890123{i:02d}"
        })
        
        await retail_customer_repo.update_purchase_metrics(
            customer.id,
            Decimal("2000"),
            datetime.utcnow() - timedelta(days=5)
        )
    
    # Calculate RFM
    await retail_service.calculate_rfm_scores()
    
    # Get distribution
    distribution = await retail_service.get_rfm_segment_distribution()
    
    assert distribution["total_customers_analyzed"] >= 5
    assert len(distribution["segment_distribution"]) > 0


@pytest.mark.asyncio
async def test_calculate_clv(
    retail_service: RetailCustomerService,
    retail_customer_repo: RetailCustomerRepository
):
    """Test CLV calculation"""
    # Create customer with purchase history
    customer = await retail_customer_repo.create_customer({
        "first_name": "CLV",
        "last_name": "Test",
        "email": "clv@test.com",
        "phone": "+18901234567"
    })
    
    # Add purchase history
    for i in range(5):
        await retail_customer_repo.update_purchase_metrics(
            customer.id,
            Decimal("1500.00"),
            datetime.utcnow() - timedelta(days=i * 30)
        )
    
    # Calculate RFM first (required for CLV)
    await retail_service.calculate_rfm_scores([customer.id])
    
    # Calculate CLV
    updated = await retail_service.calculate_clv([customer.id], prediction_months=12)
    
    assert len(updated) == 1
    assert updated[0].clv > Decimal("0")
    assert updated[0].clv_last_calculated is not None


@pytest.mark.asyncio
async def test_get_clv_analysis(
    retail_service: RetailCustomerService,
    retail_customer_repo: RetailCustomerRepository
):
    """Test CLV analysis"""
    # Create customers
    for i in range(3):
        customer = await retail_customer_repo.create_customer({
            "first_name": f"CLVAnalysis{i}",
            "last_name": "Test",
            "email": f"clvanalysis{i}@test.com",
            "phone": f"+19012345{i:02d}"
        })
        
        # Add purchase history
        await retail_customer_repo.update_purchase_metrics(
            customer.id,
            Decimal(str((i + 1) * 2000)),
            datetime.utcnow() - timedelta(days=10)
        )
        
        # Calculate RFM and CLV
        await retail_service.calculate_rfm_scores([customer.id])
        await retail_service.calculate_clv([customer.id])
    
    # Get analysis
    analysis = await retail_service.get_clv_analysis(limit=10)
    
    assert analysis["total_customers_analyzed"] >= 3
    assert analysis["total_clv"] > Decimal("0")
    assert analysis["average_clv"] > Decimal("0")
    assert len(analysis["distribution"]) > 0


@pytest.mark.asyncio
async def test_expire_loyalty_points(
    retail_service: RetailCustomerService,
    loyalty_repo: LoyaltyTransactionRepository,
    retail_customer_repo: RetailCustomerRepository,
    sample_retail_customer: RetailCustomer
):
    """Test expiring loyalty points"""
    # Earn points with past expiry
    expired_date = datetime.utcnow() - timedelta(days=1)
    await loyalty_repo.create_transaction(
        customer_id=sample_retail_customer.id,
        transaction_type="EARNED",
        points=100,
        description="Expired points",
        balance_before=0,
        balance_after=100,
        expires_at=expired_date
    )
    
    # Update customer balance
    await retail_customer_repo.update_loyalty_points(sample_retail_customer.id, 100)
    
    # Expire points
    expired = await retail_service.expire_loyalty_points(sample_retail_customer.id)
    
    assert expired == 100
    
    # Verify balance
    customer = await retail_customer_repo.get(sample_retail_customer.id)
    assert customer.loyalty_points == 0


@pytest.mark.asyncio
async def test_get_loyalty_balance(
    retail_service: RetailCustomerService,
    loyalty_repo: LoyaltyTransactionRepository,
    retail_customer_repo: RetailCustomerRepository,
    sample_retail_customer: RetailCustomer
):
    """Test getting loyalty balance with expiry info"""
    # Earn points
    await retail_service.earn_loyalty_points(
        customer_id=sample_retail_customer.id,
        points=500,
        description="Test points",
        expiry_days=15  # Expires in 15 days
    )
    
    balance = await retail_service.get_loyalty_balance(sample_retail_customer.id)
    
    assert balance["current_balance"] == 500
    assert balance["lifetime_points"] == 500
    assert balance["points_expiring_soon"] == 500  # Within 30 days
    assert balance["points_expiring_date"] is not None


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_customer_lifecycle(retail_service: RetailCustomerService):
    """Test complete customer lifecycle"""
    # 1. Register customer
    customer, welcome_txn = await retail_service.register_customer(
        {
            "first_name": "Lifecycle",
            "last_name": "Test",
            "email": "lifecycle@test.com",
            "phone": "+10123456789",
            "city": "Chennai"
        },
        welcome_bonus=100
    )
    
    assert customer.loyalty_points == 100
    assert customer.loyalty_tier == CustomerTierLevel.BRONZE
    
    # 2. Verify email
    customer = await retail_service.verify_email(customer.id)
    assert customer.is_email_verified is True
    
    # 3. Make purchases and earn points
    for i in range(5):
        await retail_service.earn_loyalty_points(
            customer.id,
            points=200,
            description=f"Purchase {i+1}"
        )
    
    # 4. Redeem points
    await retail_service.redeem_loyalty_points(
        customer.id,
        points=300,
        description="Discount redemption"
    )
    
    # 5. Update tier
    customer = await retail_service.update_loyalty_tier(
        customer.id,
        auto_calculate=True
    )
    
    # 6. Calculate RFM
    await retail_service.calculate_rfm_scores([customer.id])
    
    # 7. Calculate CLV
    await retail_service.calculate_clv([customer.id])
    
    # 8. Get balance
    balance = await retail_service.get_loyalty_balance(customer.id)
    
    assert balance["current_balance"] == 800  # 100 + (5*200) - 300
    assert customer.loyalty_points_lifetime == 1100  # 100 + (5*200)
