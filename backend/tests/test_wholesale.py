"""
Wholesale Module Tests - Quick Validation

Basic tests to verify wholesale module functionality.
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wholesale import (
    WholesaleCustomer,
    ContractPricing,
    CustomerType,
    CustomerStatus,
    PaymentTerms,
    CreditStatus
)
from app.models.product import Product, ProductVariant
from app.models.category import Category
from app.models.user import User
from app.repositories.wholesale import WholesaleCustomerRepository, ContractPricingRepository
from app.services.wholesale import WholesaleService

pytestmark = pytest.mark.asyncio


class TestWholesaleBasics:
    """Basic wholesale functionality tests"""
    
    async def test_create_wholesale_customer(self, db_session: AsyncSession):
        """Test creating a wholesale customer"""
        repo = WholesaleCustomerRepository(db_session)
        
        customer_data = {
            "company_name": "Test Retailer LLC",
            "customer_type": CustomerType.RETAILER,
            "primary_contact_name": "Contact Person",
            "primary_email": f"test_{uuid4()}@retailer.com",
            "primary_phone": "9876543210",
            "billing_address_line1": "456 Oak Ave",
            "billing_city": "Delhi",
            "billing_state": "Delhi",
            "billing_postal_code": "110001",
            "billing_country": "India",
            "credit_limit": Decimal("100000.00"),
            "payment_terms": PaymentTerms.NET_60
        }
        
        customer = await repo.create(customer_data)
        
        assert customer.id is not None
        assert customer.company_name == "Test Retailer LLC"
        assert customer.status == CustomerStatus.PENDING_APPROVAL
        assert customer.credit_limit == Decimal("100000.00")
    
    async def test_credit_calculation(self, db_session: AsyncSession):
        """Test credit available calculation"""
        customer = WholesaleCustomer(
            company_name="Credit Test",
            customer_type=CustomerType.RETAILER,
            primary_contact_name="Test",
            primary_email=f"credit_{uuid4()}@test.com",
            primary_phone="1234567890",
            billing_address_line1="123 St",
            billing_city="City",
            billing_state="State",
            billing_postal_code="12345",
            billing_country="India",
            credit_limit=Decimal("10000.00"),
            credit_used=Decimal("7000.00")
        )
        
        customer.update_credit_available()
        
        assert customer.credit_available == Decimal("3000.00")
        assert customer.credit_status == CreditStatus.GOOD


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
