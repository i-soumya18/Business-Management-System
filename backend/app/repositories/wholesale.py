"""
Wholesale Customer Repository

Data access layer for wholesale customer management, credit tracking,
and contract pricing operations.
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from decimal import Decimal
from datetime import datetime, date

from sqlalchemy import select, func, and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.wholesale import (
    WholesaleCustomer,
    ContractPricing,
    CustomerStatus,
    CustomerType,
    CreditStatus,
    PaymentTerms
)
from app.repositories.base import BaseRepository


class WholesaleCustomerRepository(BaseRepository[WholesaleCustomer]):
    """Repository for WholesaleCustomer operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(WholesaleCustomer, db)
    
    async def get_by_id_with_relationships(self, customer_id: UUID) -> Optional[WholesaleCustomer]:
        """Get customer by ID with all relationships loaded"""
        query = (
            select(WholesaleCustomer)
            .where(WholesaleCustomer.id == customer_id)
            .options(
                selectinload(WholesaleCustomer.sales_rep),
                selectinload(WholesaleCustomer.contract_prices),
                selectinload(WholesaleCustomer.approved_by)
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_company_name(self, company_name: str) -> Optional[WholesaleCustomer]:
        """Get customer by company name"""
        query = select(WholesaleCustomer).where(
            WholesaleCustomer.company_name == company_name
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_tax_id(self, tax_id: str) -> Optional[WholesaleCustomer]:
        """Get customer by tax ID (GST/VAT number)"""
        query = select(WholesaleCustomer).where(
            WholesaleCustomer.tax_id == tax_id
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_business_registration(
        self, registration_number: str
    ) -> Optional[WholesaleCustomer]:
        """Get customer by business registration number"""
        query = select(WholesaleCustomer).where(
            WholesaleCustomer.business_registration_number == registration_number
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[WholesaleCustomer]:
        """Get customer by primary email"""
        query = select(WholesaleCustomer).where(
            WholesaleCustomer.primary_email == email
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_sales_rep(
        self,
        sales_rep_id: UUID,
        skip: int = 0,
        limit: int = 100,
        status: Optional[CustomerStatus] = None
    ) -> tuple[List[WholesaleCustomer], int]:
        """Get all customers assigned to a sales representative"""
        query = select(WholesaleCustomer).where(
            WholesaleCustomer.sales_rep_id == sales_rep_id
        )
        
        if status:
            query = query.where(WholesaleCustomer.status == status)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()
        
        # Get paginated results
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        customers = result.scalars().all()
        
        return list(customers), total
    
    async def get_by_status(
        self,
        status: CustomerStatus,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[WholesaleCustomer], int]:
        """Get customers by status"""
        query = select(WholesaleCustomer).where(
            WholesaleCustomer.status == status
        )
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()
        
        # Get paginated results
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        customers = result.scalars().all()
        
        return list(customers), total
    
    async def get_pending_approvals(
        self, skip: int = 0, limit: int = 100
    ) -> tuple[List[WholesaleCustomer], int]:
        """Get customers pending approval"""
        return await self.get_by_status(CustomerStatus.PENDING_APPROVAL, skip, limit)
    
    async def get_active_customers(
        self, skip: int = 0, limit: int = 100
    ) -> tuple[List[WholesaleCustomer], int]:
        """Get active customers"""
        return await self.get_by_status(CustomerStatus.ACTIVE, skip, limit)
    
    async def search_customers(
        self,
        search_term: str,
        customer_type: Optional[CustomerType] = None,
        status: Optional[CustomerStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[WholesaleCustomer], int]:
        """Search customers by company name, email, or phone"""
        query = select(WholesaleCustomer).where(
            or_(
                WholesaleCustomer.company_name.ilike(f"%{search_term}%"),
                WholesaleCustomer.primary_email.ilike(f"%{search_term}%"),
                WholesaleCustomer.primary_phone.ilike(f"%{search_term}%"),
                WholesaleCustomer.tax_id.ilike(f"%{search_term}%")
            )
        )
        
        if customer_type:
            query = query.where(WholesaleCustomer.customer_type == customer_type)
        
        if status:
            query = query.where(WholesaleCustomer.status == status)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()
        
        # Get paginated results
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        customers = result.scalars().all()
        
        return list(customers), total
    
    async def update_credit_used(
        self, customer_id: UUID, amount: Decimal, operation: str = "increase"
    ) -> Optional[WholesaleCustomer]:
        """Update customer's credit used amount"""
        customer = await self.get_by_id(customer_id)
        if not customer:
            return None
        
        if operation == "increase":
            customer.credit_used += amount
        elif operation == "decrease":
            customer.credit_used = max(Decimal("0.00"), customer.credit_used - amount)
        
        customer.update_credit_available()
        await self.db.commit()
        await self.db.refresh(customer)
        return customer
    
    async def update_credit_limit(
        self, customer_id: UUID, new_limit: Decimal
    ) -> Optional[WholesaleCustomer]:
        """Update customer's credit limit"""
        customer = await self.get_by_id(customer_id)
        if not customer:
            return None
        
        customer.credit_limit = new_limit
        customer.update_credit_available()
        await self.db.commit()
        await self.db.refresh(customer)
        return customer
    
    async def approve_customer(
        self, customer_id: UUID, approved_by_id: UUID
    ) -> Optional[WholesaleCustomer]:
        """Approve a pending customer"""
        customer = await self.get_by_id(customer_id)
        if not customer:
            return None
        
        customer.status = CustomerStatus.ACTIVE
        customer.approved_at = datetime.utcnow()
        customer.approved_by_id = approved_by_id
        
        await self.db.commit()
        await self.db.refresh(customer)
        return customer
    
    async def reject_customer(self, customer_id: UUID) -> Optional[WholesaleCustomer]:
        """Reject a pending customer"""
        customer = await self.get_by_id(customer_id)
        if not customer:
            return None
        
        customer.status = CustomerStatus.REJECTED
        await self.db.commit()
        await self.db.refresh(customer)
        return customer
    
    async def suspend_customer(self, customer_id: UUID) -> Optional[WholesaleCustomer]:
        """Suspend a customer account"""
        customer = await self.get_by_id(customer_id)
        if not customer:
            return None
        
        customer.status = CustomerStatus.SUSPENDED
        customer.credit_status = CreditStatus.SUSPENDED
        await self.db.commit()
        await self.db.refresh(customer)
        return customer
    
    async def reactivate_customer(self, customer_id: UUID) -> Optional[WholesaleCustomer]:
        """Reactivate a suspended/inactive customer"""
        customer = await self.get_by_id(customer_id)
        if not customer:
            return None
        
        customer.status = CustomerStatus.ACTIVE
        customer.update_credit_available()  # Recalculate credit status
        await self.db.commit()
        await self.db.refresh(customer)
        return customer
    
    async def update_performance_metrics(
        self,
        customer_id: UUID,
        total_orders: int,
        total_spent: Decimal,
        average_order_value: Decimal,
        last_order_date: datetime
    ) -> Optional[WholesaleCustomer]:
        """Update customer performance metrics"""
        customer = await self.get_by_id(customer_id)
        if not customer:
            return None
        
        customer.total_orders = total_orders
        customer.total_spent = total_spent
        customer.average_order_value = average_order_value
        customer.last_order_date = last_order_date
        
        await self.db.commit()
        await self.db.refresh(customer)
        return customer
    
    async def get_customers_exceeding_credit(self) -> List[WholesaleCustomer]:
        """Get all customers who have exceeded their credit limit"""
        query = select(WholesaleCustomer).where(
            WholesaleCustomer.credit_used > WholesaleCustomer.credit_limit
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_customers_near_credit_limit(
        self, threshold: float = 0.9
    ) -> List[WholesaleCustomer]:
        """Get customers approaching their credit limit"""
        query = select(WholesaleCustomer).where(
            and_(
                WholesaleCustomer.credit_used >= WholesaleCustomer.credit_limit * threshold,
                WholesaleCustomer.credit_used < WholesaleCustomer.credit_limit
            )
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())


class ContractPricingRepository(BaseRepository[ContractPricing]):
    """Repository for ContractPricing operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(ContractPricing, db)
    
    async def get_by_customer(
        self,
        customer_id: UUID,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[ContractPricing], int]:
        """Get all contract prices for a customer"""
        query = select(ContractPricing).where(
            ContractPricing.customer_id == customer_id
        )
        
        if active_only:
            query = query.where(ContractPricing.is_active == True)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()
        
        # Get paginated results
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        prices = result.scalars().all()
        
        return list(prices), total
    
    async def get_by_product_variant(
        self, customer_id: UUID, product_variant_id: UUID
    ) -> Optional[ContractPricing]:
        """Get contract price for a specific product variant"""
        query = select(ContractPricing).where(
            and_(
                ContractPricing.customer_id == customer_id,
                ContractPricing.product_variant_id == product_variant_id,
                ContractPricing.is_active == True
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_category(
        self, customer_id: UUID, category_id: UUID
    ) -> Optional[ContractPricing]:
        """Get contract price for a category"""
        query = select(ContractPricing).where(
            and_(
                ContractPricing.customer_id == customer_id,
                ContractPricing.category_id == category_id,
                ContractPricing.is_active == True
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_valid_prices_for_customer(
        self,
        customer_id: UUID,
        check_date: Optional[date] = None
    ) -> List[ContractPricing]:
        """Get all valid contract prices for a customer on a specific date"""
        check_date = check_date or date.today()
        
        query = select(ContractPricing).where(
            and_(
                ContractPricing.customer_id == customer_id,
                ContractPricing.is_active == True,
                ContractPricing.valid_from <= check_date,
                ContractPricing.valid_until >= check_date
            )
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_applicable_price(
        self,
        customer_id: UUID,
        product_variant_id: Optional[UUID] = None,
        category_id: Optional[UUID] = None,
        quantity: int = 1,
        check_date: Optional[date] = None
    ) -> Optional[ContractPricing]:
        """
        Get the most applicable contract price for a customer
        Priority: Product variant > Category
        """
        check_date = check_date or date.today()
        
        # First try product-specific pricing
        if product_variant_id:
            query = select(ContractPricing).where(
                and_(
                    ContractPricing.customer_id == customer_id,
                    ContractPricing.product_variant_id == product_variant_id,
                    ContractPricing.is_active == True,
                    ContractPricing.valid_from <= check_date,
                    ContractPricing.valid_until >= check_date,
                    ContractPricing.minimum_quantity <= quantity,
                    or_(
                        ContractPricing.maximum_quantity.is_(None),
                        ContractPricing.maximum_quantity >= quantity
                    )
                )
            )
            result = await self.db.execute(query)
            price = result.scalar_one_or_none()
            if price:
                return price
        
        # Fall back to category pricing
        if category_id:
            query = select(ContractPricing).where(
                and_(
                    ContractPricing.customer_id == customer_id,
                    ContractPricing.category_id == category_id,
                    ContractPricing.is_active == True,
                    ContractPricing.valid_from <= check_date,
                    ContractPricing.valid_until >= check_date,
                    ContractPricing.minimum_quantity <= quantity,
                    or_(
                        ContractPricing.maximum_quantity.is_(None),
                        ContractPricing.maximum_quantity >= quantity
                    )
                )
            )
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        
        return None
    
    async def deactivate_expired_prices(self) -> int:
        """Deactivate all expired contract prices"""
        today = date.today()
        
        query = (
            update(ContractPricing)
            .where(
                and_(
                    ContractPricing.is_active == True,
                    ContractPricing.valid_until < today
                )
            )
            .values(is_active=False)
        )
        
        result = await self.db.execute(query)
        await self.db.commit()
        return result.rowcount
    
    async def bulk_deactivate_for_customer(
        self, customer_id: UUID
    ) -> int:
        """Deactivate all contract prices for a customer"""
        query = (
            update(ContractPricing)
            .where(
                and_(
                    ContractPricing.customer_id == customer_id,
                    ContractPricing.is_active == True
                )
            )
            .values(is_active=False)
        )
        
        result = await self.db.execute(query)
        await self.db.commit()
        return result.rowcount
