"""
Retail Customer Repositories - B2C CRM

Repository layer for retail customer operations including:
- Customer CRUD operations
- Loyalty transaction management
- Customer preference management
- Advanced search and filtering
"""

from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy import select, func, and_, or_, desc, case, extract
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.retail_customer import (
    RetailCustomer,
    LoyaltyTransaction,
    CustomerPreference,
    CustomerTierLevel,
    CustomerPreferenceType
)
from app.repositories.base import BaseRepository


class RetailCustomerRepository(BaseRepository[RetailCustomer]):
    """Repository for RetailCustomer operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(RetailCustomer, db)
    
    async def create_customer(
        self,
        customer_data: Dict[str, Any],
        generate_number: bool = True
    ) -> RetailCustomer:
        """
        Create a new retail customer with auto-generated customer number
        
        Args:
            customer_data: Customer data dictionary
            generate_number: Whether to auto-generate customer number
            
        Returns:
            Created RetailCustomer instance
        """
        if generate_number:
            customer_data["customer_number"] = await self._generate_customer_number()
        
        return await self.create(customer_data)
    
    async def _generate_customer_number(self) -> str:
        """
        Generate unique customer number: CUST-YYYYMMDD-XXXX
        
        Returns:
            Generated customer number
        """
        today = datetime.utcnow().strftime("%Y%m%d")
        prefix = f"CUST-{today}"
        
        # Get the latest customer number for today
        result = await self.db.execute(
            select(RetailCustomer.customer_number)
            .where(RetailCustomer.customer_number.like(f"{prefix}-%"))
            .order_by(desc(RetailCustomer.customer_number))
            .limit(1)
        )
        last_number = result.scalar_one_or_none()
        
        if last_number:
            # Extract sequence and increment
            sequence = int(last_number.split("-")[-1])
            new_sequence = sequence + 1
        else:
            new_sequence = 1
        
        return f"{prefix}-{new_sequence:04d}"
    
    async def get_by_email(self, email: str) -> Optional[RetailCustomer]:
        """Get customer by email"""
        result = await self.db.execute(
            select(RetailCustomer).where(RetailCustomer.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_by_phone(self, phone: str) -> Optional[RetailCustomer]:
        """Get customer by phone"""
        result = await self.db.execute(
            select(RetailCustomer).where(RetailCustomer.phone == phone)
        )
        return result.scalar_one_or_none()
    
    async def get_by_customer_number(
        self,
        customer_number: str
    ) -> Optional[RetailCustomer]:
        """Get customer by customer number"""
        result = await self.db.execute(
            select(RetailCustomer)
            .where(RetailCustomer.customer_number == customer_number)
        )
        return result.scalar_one_or_none()
    
    async def get_by_user_id(self, user_id: UUID) -> Optional[RetailCustomer]:
        """Get customer by linked user ID"""
        result = await self.db.execute(
            select(RetailCustomer).where(RetailCustomer.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def search_customers(
        self,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        loyalty_tier: Optional[CustomerTierLevel] = None,
        rfm_segment: Optional[str] = None,
        city: Optional[str] = None,
        min_total_spent: Optional[Decimal] = None,
        max_total_spent: Optional[Decimal] = None,
        min_orders: Optional[int] = None,
        max_orders: Optional[int] = None,
        registered_after: Optional[datetime] = None,
        registered_before: Optional[datetime] = None,
        last_order_after: Optional[datetime] = None,
        last_order_before: Optional[datetime] = None,
        has_email_consent: Optional[bool] = None,
        has_sms_consent: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[RetailCustomer]:
        """
        Advanced customer search with multiple filters
        
        Args:
            search: Search term for name, email, phone, customer number
            is_active: Filter by active status
            loyalty_tier: Filter by loyalty tier
            rfm_segment: Filter by RFM segment
            city: Filter by city
            min_total_spent: Minimum total spent
            max_total_spent: Maximum total spent
            min_orders: Minimum number of orders
            max_orders: Maximum number of orders
            registered_after: Registered after date
            registered_before: Registered before date
            last_order_after: Last order after date
            last_order_before: Last order before date
            has_email_consent: Filter by email consent
            has_sms_consent: Filter by SMS consent
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of matching customers
        """
        query = select(RetailCustomer)
        conditions = []
        
        # Search term
        if search:
            search_pattern = f"%{search}%"
            conditions.append(
                or_(
                    RetailCustomer.first_name.ilike(search_pattern),
                    RetailCustomer.last_name.ilike(search_pattern),
                    RetailCustomer.email.ilike(search_pattern),
                    RetailCustomer.phone.ilike(search_pattern),
                    RetailCustomer.customer_number.ilike(search_pattern)
                )
            )
        
        # Status filters
        if is_active is not None:
            conditions.append(RetailCustomer.is_active == is_active)
        
        if loyalty_tier is not None:
            conditions.append(RetailCustomer.loyalty_tier == loyalty_tier)
        
        if rfm_segment is not None:
            conditions.append(RetailCustomer.rfm_segment == rfm_segment)
        
        if city is not None:
            conditions.append(RetailCustomer.city == city)
        
        # Spending filters
        if min_total_spent is not None:
            conditions.append(RetailCustomer.total_spent >= min_total_spent)
        
        if max_total_spent is not None:
            conditions.append(RetailCustomer.total_spent <= max_total_spent)
        
        # Order count filters
        if min_orders is not None:
            conditions.append(RetailCustomer.total_orders >= min_orders)
        
        if max_orders is not None:
            conditions.append(RetailCustomer.total_orders <= max_orders)
        
        # Date filters
        if registered_after is not None:
            conditions.append(RetailCustomer.created_at >= registered_after)
        
        if registered_before is not None:
            conditions.append(RetailCustomer.created_at <= registered_before)
        
        if last_order_after is not None:
            conditions.append(RetailCustomer.last_order_date >= last_order_after)
        
        if last_order_before is not None:
            conditions.append(RetailCustomer.last_order_date <= last_order_before)
        
        # Marketing consent filters
        if has_email_consent is not None:
            conditions.append(
                RetailCustomer.email_marketing_consent == has_email_consent
            )
        
        if has_sms_consent is not None:
            conditions.append(
                RetailCustomer.sms_marketing_consent == has_sms_consent
            )
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(desc(RetailCustomer.created_at))
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def count_customers(
        self,
        is_active: Optional[bool] = None,
        loyalty_tier: Optional[CustomerTierLevel] = None
    ) -> int:
        """Count customers with optional filters"""
        query = select(func.count(RetailCustomer.id))
        
        conditions = []
        if is_active is not None:
            conditions.append(RetailCustomer.is_active == is_active)
        
        if loyalty_tier is not None:
            conditions.append(RetailCustomer.loyalty_tier == loyalty_tier)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await self.db.execute(query)
        return result.scalar_one()
    
    async def update_loyalty_points(
        self,
        customer_id: UUID,
        points_change: int
    ) -> RetailCustomer:
        """
        Update customer loyalty points
        
        Args:
            customer_id: Customer ID
            points_change: Points to add (positive) or subtract (negative)
            
        Returns:
            Updated customer
        """
        customer = await self.get(customer_id)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")
        
        new_points = customer.loyalty_points + points_change
        if new_points < 0:
            raise ValueError("Insufficient loyalty points")
        
        customer.loyalty_points = new_points
        if points_change > 0:
            customer.loyalty_points_lifetime += points_change
        
        await self.db.commit()
        await self.db.refresh(customer)
        return customer
    
    async def update_purchase_metrics(
        self,
        customer_id: UUID,
        order_total: Decimal,
        order_date: datetime
    ) -> RetailCustomer:
        """
        Update customer purchase metrics after order
        
        Args:
            customer_id: Customer ID
            order_total: Order total amount
            order_date: Order date
            
        Returns:
            Updated customer
        """
        customer = await self.get(customer_id)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")
        
        customer.total_orders += 1
        customer.total_spent += order_total
        customer.average_order_value = customer.total_spent / customer.total_orders
        
        if not customer.first_order_date:
            customer.first_order_date = order_date
        
        customer.last_order_date = order_date
        customer.last_activity_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(customer)
        return customer
    
    async def update_rfm_scores(
        self,
        customer_id: UUID,
        recency_score: int,
        frequency_score: int,
        monetary_score: int,
        segment: str
    ) -> RetailCustomer:
        """Update customer RFM scores"""
        customer = await self.get(customer_id)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")
        
        customer.rfm_recency_score = recency_score
        customer.rfm_frequency_score = frequency_score
        customer.rfm_monetary_score = monetary_score
        customer.rfm_segment = segment
        customer.rfm_last_calculated = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(customer)
        return customer
    
    async def update_clv(
        self,
        customer_id: UUID,
        clv: Decimal
    ) -> RetailCustomer:
        """Update customer lifetime value"""
        customer = await self.get(customer_id)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")
        
        customer.clv = clv
        customer.clv_last_calculated = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(customer)
        return customer
    
    async def update_loyalty_tier(
        self,
        customer_id: UUID,
        tier: CustomerTierLevel,
        tier_expiry_date: Optional[date] = None
    ) -> RetailCustomer:
        """Update customer loyalty tier"""
        customer = await self.get(customer_id)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")
        
        customer.loyalty_tier = tier
        customer.tier_start_date = datetime.utcnow().date()
        customer.tier_expiry_date = tier_expiry_date
        
        await self.db.commit()
        await self.db.refresh(customer)
        return customer
    
    async def bulk_update_status(
        self,
        customer_ids: List[UUID],
        is_active: bool
    ) -> int:
        """Bulk update customer status"""
        from sqlalchemy import update
        
        stmt = (
            update(RetailCustomer)
            .where(RetailCustomer.id.in_(customer_ids))
            .values(is_active=is_active, updated_at=datetime.utcnow())
        )
        
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount
    
    async def bulk_update_tier(
        self,
        customer_ids: List[UUID],
        tier: CustomerTierLevel,
        tier_expiry_date: Optional[date] = None
    ) -> int:
        """Bulk update loyalty tier"""
        from sqlalchemy import update
        
        stmt = (
            update(RetailCustomer)
            .where(RetailCustomer.id.in_(customer_ids))
            .values(
                loyalty_tier=tier,
                tier_start_date=datetime.utcnow().date(),
                tier_expiry_date=tier_expiry_date,
                updated_at=datetime.utcnow()
            )
        )
        
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount
    
    async def get_customers_needing_rfm_update(
        self,
        days_since_last_calc: int = 7
    ) -> List[RetailCustomer]:
        """Get customers needing RFM recalculation"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_since_last_calc)
        
        result = await self.db.execute(
            select(RetailCustomer)
            .where(
                and_(
                    RetailCustomer.is_active == True,
                    RetailCustomer.total_orders > 0,
                    or_(
                        RetailCustomer.rfm_last_calculated.is_(None),
                        RetailCustomer.rfm_last_calculated < cutoff_date
                    )
                )
            )
        )
        return list(result.scalars().all())
    
    async def get_customers_needing_clv_update(
        self,
        days_since_last_calc: int = 30
    ) -> List[RetailCustomer]:
        """Get customers needing CLV recalculation"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_since_last_calc)
        
        result = await self.db.execute(
            select(RetailCustomer)
            .where(
                and_(
                    RetailCustomer.is_active == True,
                    RetailCustomer.total_orders > 0,
                    or_(
                        RetailCustomer.clv_last_calculated.is_(None),
                        RetailCustomer.clv_last_calculated < cutoff_date
                    )
                )
            )
        )
        return list(result.scalars().all())
    
    async def get_rfm_segment_distribution(self) -> List[Dict[str, Any]]:
        """Get RFM segment distribution"""
        result = await self.db.execute(
            select(
                RetailCustomer.rfm_segment,
                func.count(RetailCustomer.id).label("count"),
                func.sum(RetailCustomer.total_spent).label("total_revenue"),
                func.avg(RetailCustomer.average_order_value).label("avg_order_value")
            )
            .where(
                and_(
                    RetailCustomer.is_active == True,
                    RetailCustomer.rfm_segment.isnot(None)
                )
            )
            .group_by(RetailCustomer.rfm_segment)
        )
        
        return [
            {
                "segment": row.rfm_segment,
                "count": row.count,
                "total_revenue": row.total_revenue or Decimal("0"),
                "avg_order_value": row.avg_order_value or Decimal("0")
            }
            for row in result.all()
        ]
    
    async def get_top_customers_by_clv(
        self,
        limit: int = 100
    ) -> List[RetailCustomer]:
        """Get top customers by CLV"""
        result = await self.db.execute(
            select(RetailCustomer)
            .where(RetailCustomer.is_active == True)
            .order_by(desc(RetailCustomer.clv))
            .limit(limit)
        )
        return list(result.scalars().all())


class LoyaltyTransactionRepository(BaseRepository[LoyaltyTransaction]):
    """Repository for LoyaltyTransaction operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(LoyaltyTransaction, db)
    
    async def create_transaction(
        self,
        customer_id: UUID,
        transaction_type: str,
        points: int,
        description: str,
        balance_before: int,
        balance_after: int,
        order_id: Optional[UUID] = None,
        expires_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> LoyaltyTransaction:
        """Create a new loyalty transaction"""
        transaction = LoyaltyTransaction(
            customer_id=customer_id,
            transaction_type=transaction_type,
            points=points,
            description=description,
            balance_before=balance_before,
            balance_after=balance_after,
            order_id=order_id,
            expires_at=expires_at,
            metadata=metadata
        )
        
        self.db.add(transaction)
        await self.db.commit()
        await self.db.refresh(transaction)
        return transaction
    
    async def get_customer_transactions(
        self,
        customer_id: UUID,
        transaction_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[LoyaltyTransaction]:
        """Get transactions for a customer"""
        query = (
            select(LoyaltyTransaction)
            .where(LoyaltyTransaction.customer_id == customer_id)
        )
        
        if transaction_type:
            query = query.where(
                LoyaltyTransaction.transaction_type == transaction_type
            )
        
        query = query.order_by(desc(LoyaltyTransaction.created_at))
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_points_expiring_soon(
        self,
        customer_id: UUID,
        days: int = 30
    ) -> List[LoyaltyTransaction]:
        """Get points expiring within specified days"""
        cutoff_date = datetime.utcnow() + timedelta(days=days)
        
        result = await self.db.execute(
            select(LoyaltyTransaction)
            .where(
                and_(
                    LoyaltyTransaction.customer_id == customer_id,
                    LoyaltyTransaction.transaction_type == "EARNED",
                    LoyaltyTransaction.expires_at.isnot(None),
                    LoyaltyTransaction.expires_at <= cutoff_date,
                    LoyaltyTransaction.expires_at > datetime.utcnow()
                )
            )
            .order_by(LoyaltyTransaction.expires_at)
        )
        return list(result.scalars().all())
    
    async def get_expired_points(
        self,
        customer_id: Optional[UUID] = None
    ) -> List[LoyaltyTransaction]:
        """Get expired earned points not yet marked as expired"""
        query = (
            select(LoyaltyTransaction)
            .where(
                and_(
                    LoyaltyTransaction.transaction_type == "EARNED",
                    LoyaltyTransaction.expires_at.isnot(None),
                    LoyaltyTransaction.expires_at <= datetime.utcnow()
                )
            )
        )
        
        if customer_id:
            query = query.where(LoyaltyTransaction.customer_id == customer_id)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_total_points_by_type(
        self,
        customer_id: UUID
    ) -> Dict[str, int]:
        """Get total points by transaction type"""
        result = await self.db.execute(
            select(
                LoyaltyTransaction.transaction_type,
                func.sum(LoyaltyTransaction.points).label("total")
            )
            .where(LoyaltyTransaction.customer_id == customer_id)
            .group_by(LoyaltyTransaction.transaction_type)
        )
        
        return {
            row.transaction_type: row.total or 0
            for row in result.all()
        }


class CustomerPreferenceRepository(BaseRepository[CustomerPreference]):
    """Repository for CustomerPreference operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(CustomerPreference, db)
    
    async def get_customer_preferences(
        self,
        customer_id: UUID,
        preference_type: Optional[CustomerPreferenceType] = None
    ) -> List[CustomerPreference]:
        """Get all preferences for a customer"""
        query = (
            select(CustomerPreference)
            .where(CustomerPreference.customer_id == customer_id)
        )
        
        if preference_type:
            query = query.where(
                CustomerPreference.preference_type == preference_type
            )
        
        query = query.order_by(CustomerPreference.preference_type)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_preference(
        self,
        customer_id: UUID,
        preference_type: CustomerPreferenceType,
        preference_key: str
    ) -> Optional[CustomerPreference]:
        """Get a specific preference"""
        result = await self.db.execute(
            select(CustomerPreference)
            .where(
                and_(
                    CustomerPreference.customer_id == customer_id,
                    CustomerPreference.preference_type == preference_type,
                    CustomerPreference.preference_key == preference_key
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def upsert_preference(
        self,
        customer_id: UUID,
        preference_type: CustomerPreferenceType,
        preference_key: str,
        preference_value: str
    ) -> CustomerPreference:
        """Create or update a preference"""
        preference = await self.get_preference(
            customer_id,
            preference_type,
            preference_key
        )
        
        if preference:
            preference.preference_value = preference_value
            preference.updated_at = datetime.utcnow()
        else:
            preference = CustomerPreference(
                customer_id=customer_id,
                preference_type=preference_type,
                preference_key=preference_key,
                preference_value=preference_value
            )
            self.db.add(preference)
        
        await self.db.commit()
        await self.db.refresh(preference)
        return preference
    
    async def bulk_upsert_preferences(
        self,
        customer_id: UUID,
        preferences: List[Dict[str, Any]]
    ) -> List[CustomerPreference]:
        """Bulk create or update preferences"""
        results = []
        
        for pref_data in preferences:
            preference = await self.upsert_preference(
                customer_id=customer_id,
                preference_type=pref_data["preference_type"],
                preference_key=pref_data["preference_key"],
                preference_value=pref_data["preference_value"]
            )
            results.append(preference)
        
        return results
    
    async def delete_preference(
        self,
        customer_id: UUID,
        preference_type: CustomerPreferenceType,
        preference_key: str
    ) -> bool:
        """Delete a specific preference"""
        preference = await self.get_preference(
            customer_id,
            preference_type,
            preference_key
        )
        
        if preference:
            await self.db.delete(preference)
            await self.db.commit()
            return True
        
        return False
    
    async def delete_all_customer_preferences(
        self,
        customer_id: UUID,
        preference_type: Optional[CustomerPreferenceType] = None
    ) -> int:
        """Delete all preferences for a customer"""
        from sqlalchemy import delete
        
        stmt = delete(CustomerPreference).where(
            CustomerPreference.customer_id == customer_id
        )
        
        if preference_type:
            stmt = stmt.where(
                CustomerPreference.preference_type == preference_type
            )
        
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount
