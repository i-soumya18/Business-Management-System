"""
Retail Customer Service - B2C CRM

Service layer for retail customer operations including:
- Customer lifecycle management
- Loyalty program operations
- RFM (Recency, Frequency, Monetary) analysis
- CLV (Customer Lifetime Value) calculation
- Customer segmentation
"""

from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
import statistics

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


class RetailCustomerService:
    """Service for retail customer operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.customer_repo = RetailCustomerRepository(db)
        self.loyalty_repo = LoyaltyTransactionRepository(db)
        self.preference_repo = CustomerPreferenceRepository(db)
    
    # ========================================================================
    # Customer Management
    # ========================================================================
    
    async def register_customer(
        self,
        customer_data: Dict[str, Any],
        welcome_bonus: int = 100
    ) -> Tuple[RetailCustomer, Optional[LoyaltyTransaction]]:
        """
        Register a new customer and award welcome bonus
        
        Args:
            customer_data: Customer data
            welcome_bonus: Welcome bonus points
            
        Returns:
            Tuple of (customer, loyalty_transaction)
        """
        # Create customer
        customer = await self.customer_repo.create_customer(customer_data)
        
        # Award welcome bonus
        loyalty_txn = None
        if welcome_bonus > 0:
            loyalty_txn = await self.earn_loyalty_points(
                customer_id=customer.id,
                points=welcome_bonus,
                description="Welcome bonus",
                expiry_days=365
            )
        
        return customer, loyalty_txn
    
    async def verify_email(
        self,
        customer_id: UUID
    ) -> RetailCustomer:
        """Verify customer email"""
        customer = await self.customer_repo.get(customer_id)
        if not customer:
            raise ValueError("Customer not found")
        
        customer.is_email_verified = True
        customer.is_verified = (
            customer.is_email_verified and customer.is_phone_verified
        )
        
        await self.db.commit()
        await self.db.refresh(customer)
        return customer
    
    async def verify_phone(
        self,
        customer_id: UUID
    ) -> RetailCustomer:
        """Verify customer phone"""
        customer = await self.customer_repo.get(customer_id)
        if not customer:
            raise ValueError("Customer not found")
        
        customer.is_phone_verified = True
        customer.is_verified = (
            customer.is_email_verified and customer.is_phone_verified
        )
        
        await self.db.commit()
        await self.db.refresh(customer)
        return customer
    
    async def deactivate_customer(
        self,
        customer_id: UUID,
        reason: str
    ) -> RetailCustomer:
        """Deactivate a customer"""
        customer = await self.customer_repo.get(customer_id)
        if not customer:
            raise ValueError("Customer not found")
        
        customer.is_active = False
        customer.updated_at = datetime.utcnow()
        
        if customer.notes:
            customer.notes += f"\n[{datetime.utcnow()}] Deactivated: {reason}"
        else:
            customer.notes = f"[{datetime.utcnow()}] Deactivated: {reason}"
        
        await self.db.commit()
        await self.db.refresh(customer)
        return customer
    
    async def reactivate_customer(
        self,
        customer_id: UUID
    ) -> RetailCustomer:
        """Reactivate a customer"""
        customer = await self.customer_repo.get(customer_id)
        if not customer:
            raise ValueError("Customer not found")
        
        customer.is_active = True
        customer.updated_at = datetime.utcnow()
        
        if customer.notes:
            customer.notes += f"\n[{datetime.utcnow()}] Reactivated"
        else:
            customer.notes = f"[{datetime.utcnow()}] Reactivated"
        
        await self.db.commit()
        await self.db.refresh(customer)
        return customer
    
    # ========================================================================
    # Loyalty Program
    # ========================================================================
    
    async def earn_loyalty_points(
        self,
        customer_id: UUID,
        points: int,
        description: str,
        order_id: Optional[UUID] = None,
        expiry_days: int = 365
    ) -> LoyaltyTransaction:
        """
        Award loyalty points to customer
        
        Args:
            customer_id: Customer ID
            points: Points to award
            description: Transaction description
            order_id: Related order ID
            expiry_days: Days until points expire
            
        Returns:
            Loyalty transaction record
        """
        if points <= 0:
            raise ValueError("Points must be positive")
        
        customer = await self.customer_repo.get(customer_id)
        if not customer:
            raise ValueError("Customer not found")
        
        balance_before = customer.loyalty_points
        balance_after = balance_before + points
        
        # Calculate expiry date
        expires_at = datetime.utcnow() + timedelta(days=expiry_days)
        
        # Create transaction
        transaction = await self.loyalty_repo.create_transaction(
            customer_id=customer_id,
            transaction_type="EARNED",
            points=points,
            description=description,
            balance_before=balance_before,
            balance_after=balance_after,
            order_id=order_id,
            expires_at=expires_at
        )
        
        # Update customer points
        await self.customer_repo.update_loyalty_points(customer_id, points)
        
        return transaction
    
    async def redeem_loyalty_points(
        self,
        customer_id: UUID,
        points: int,
        description: str,
        order_id: Optional[UUID] = None
    ) -> LoyaltyTransaction:
        """
        Redeem loyalty points
        
        Args:
            customer_id: Customer ID
            points: Points to redeem
            description: Transaction description
            order_id: Related order ID
            
        Returns:
            Loyalty transaction record
        """
        if points <= 0:
            raise ValueError("Points must be positive")
        
        customer = await self.customer_repo.get(customer_id)
        if not customer:
            raise ValueError("Customer not found")
        
        if customer.loyalty_points < points:
            raise ValueError(
                f"Insufficient points. Available: {customer.loyalty_points}, "
                f"Required: {points}"
            )
        
        balance_before = customer.loyalty_points
        balance_after = balance_before - points
        
        # Create transaction
        transaction = await self.loyalty_repo.create_transaction(
            customer_id=customer_id,
            transaction_type="REDEEMED",
            points=points,
            description=description,
            balance_before=balance_before,
            balance_after=balance_after,
            order_id=order_id
        )
        
        # Update customer points
        await self.customer_repo.update_loyalty_points(customer_id, -points)
        
        return transaction
    
    async def adjust_loyalty_points(
        self,
        customer_id: UUID,
        points: int,
        reason: str
    ) -> LoyaltyTransaction:
        """
        Adjust loyalty points (admin operation)
        
        Args:
            customer_id: Customer ID
            points: Points to add (positive) or subtract (negative)
            reason: Adjustment reason
            
        Returns:
            Loyalty transaction record
        """
        customer = await self.customer_repo.get(customer_id)
        if not customer:
            raise ValueError("Customer not found")
        
        balance_before = customer.loyalty_points
        balance_after = balance_before + points
        
        if balance_after < 0:
            raise ValueError("Adjustment would result in negative balance")
        
        transaction_type = "ADJUSTED_ADD" if points > 0 else "ADJUSTED_SUB"
        
        # Create transaction
        transaction = await self.loyalty_repo.create_transaction(
            customer_id=customer_id,
            transaction_type=transaction_type,
            points=abs(points),
            description=f"Manual adjustment: {reason}",
            balance_before=balance_before,
            balance_after=balance_after
        )
        
        # Update customer points
        await self.customer_repo.update_loyalty_points(customer_id, points)
        
        return transaction
    
    async def expire_loyalty_points(
        self,
        customer_id: Optional[UUID] = None
    ) -> int:
        """
        Expire loyalty points that have passed expiry date
        
        Args:
            customer_id: Specific customer or None for all customers
            
        Returns:
            Number of points expired
        """
        expired_transactions = await self.loyalty_repo.get_expired_points(
            customer_id
        )
        
        total_expired = 0
        
        for txn in expired_transactions:
            customer = await self.customer_repo.get(txn.customer_id)
            if not customer:
                continue
            
            # Only expire if customer still has points
            if customer.loyalty_points >= txn.points:
                balance_before = customer.loyalty_points
                balance_after = balance_before - txn.points
                
                # Create expiry transaction
                await self.loyalty_repo.create_transaction(
                    customer_id=customer.id,
                    transaction_type="EXPIRED",
                    points=txn.points,
                    description=f"Points expired from transaction {txn.id}",
                    balance_before=balance_before,
                    balance_after=balance_after,
                    metadata={"original_transaction_id": str(txn.id)}
                )
                
                # Update customer points
                await self.customer_repo.update_loyalty_points(
                    customer.id,
                    -txn.points
                )
                
                total_expired += txn.points
        
        return total_expired
    
    async def get_loyalty_balance(
        self,
        customer_id: UUID
    ) -> Dict[str, Any]:
        """Get customer loyalty balance with expiry info"""
        customer = await self.customer_repo.get(customer_id)
        if not customer:
            raise ValueError("Customer not found")
        
        # Get points expiring soon (next 30 days)
        expiring_txns = await self.loyalty_repo.get_points_expiring_soon(
            customer_id,
            days=30
        )
        
        points_expiring = sum(txn.points for txn in expiring_txns)
        next_expiry = expiring_txns[0].expires_at if expiring_txns else None
        
        return {
            "customer_id": customer.id,
            "current_balance": customer.loyalty_points,
            "lifetime_points": customer.loyalty_points_lifetime,
            "points_expiring_soon": points_expiring,
            "points_expiring_date": next_expiry,
            "tier": customer.loyalty_tier
        }
    
    async def update_loyalty_tier(
        self,
        customer_id: UUID,
        auto_calculate: bool = True
    ) -> RetailCustomer:
        """
        Update customer loyalty tier based on rules or manual assignment
        
        Tier Rules:
        - Bronze: < 10,000 lifetime points
        - Silver: 10,000 - 49,999 lifetime points
        - Gold: 50,000 - 99,999 lifetime points
        - Platinum: >= 100,000 lifetime points
        
        Args:
            customer_id: Customer ID
            auto_calculate: Auto-calculate tier based on rules
            
        Returns:
            Updated customer
        """
        customer = await self.customer_repo.get(customer_id)
        if not customer:
            raise ValueError("Customer not found")
        
        if auto_calculate:
            lifetime_points = customer.loyalty_points_lifetime
            
            if lifetime_points >= 100000:
                new_tier = CustomerTierLevel.PLATINUM
            elif lifetime_points >= 50000:
                new_tier = CustomerTierLevel.GOLD
            elif lifetime_points >= 10000:
                new_tier = CustomerTierLevel.SILVER
            else:
                new_tier = CustomerTierLevel.BRONZE
            
            if new_tier != customer.loyalty_tier:
                # Tier upgrade - set expiry to 1 year
                tier_expiry = (
                    datetime.utcnow() + timedelta(days=365)
                ).date()
                
                await self.customer_repo.update_loyalty_tier(
                    customer_id,
                    new_tier,
                    tier_expiry
                )
        
        return await self.customer_repo.get(customer_id)
    
    # ========================================================================
    # RFM Analysis
    # ========================================================================
    
    async def calculate_rfm_scores(
        self,
        customer_ids: Optional[List[UUID]] = None
    ) -> List[RetailCustomer]:
        """
        Calculate RFM scores for customers
        
        RFM Analysis:
        - Recency: Days since last purchase (lower is better)
        - Frequency: Number of purchases (higher is better)
        - Monetary: Total amount spent (higher is better)
        
        Each metric scored 1-5, then segmented into customer types
        
        Args:
            customer_ids: Specific customers or None for all
            
        Returns:
            List of updated customers
        """
        # Get customers to analyze
        if customer_ids:
            customers = []
            for cid in customer_ids:
                customer = await self.customer_repo.get(cid)
                if customer and customer.total_orders > 0:
                    customers.append(customer)
        else:
            customers = await self.customer_repo.get_customers_needing_rfm_update()
        
        if not customers:
            return []
        
        # Calculate recency (days since last order)
        now = datetime.utcnow()
        recency_values = []
        frequency_values = []
        monetary_values = []
        
        for customer in customers:
            if customer.last_order_date:
                recency = (now - customer.last_order_date).days
                recency_values.append(recency)
            frequency_values.append(customer.total_orders)
            monetary_values.append(float(customer.total_spent))
        
        # Calculate quintiles for scoring
        recency_quintiles = self._calculate_quintiles(recency_values, reverse=True)
        frequency_quintiles = self._calculate_quintiles(frequency_values)
        monetary_quintiles = self._calculate_quintiles(monetary_values)
        
        # Score each customer
        updated_customers = []
        
        for customer in customers:
            if not customer.last_order_date:
                continue
            
            recency = (now - customer.last_order_date).days
            frequency = customer.total_orders
            monetary = float(customer.total_spent)
            
            # Calculate scores (1-5)
            r_score = self._get_quintile_score(recency, recency_quintiles, reverse=True)
            f_score = self._get_quintile_score(frequency, frequency_quintiles)
            m_score = self._get_quintile_score(monetary, monetary_quintiles)
            
            # Determine segment
            segment = self._determine_rfm_segment(r_score, f_score, m_score)
            
            # Update customer
            updated = await self.customer_repo.update_rfm_scores(
                customer.id,
                r_score,
                f_score,
                m_score,
                segment
            )
            updated_customers.append(updated)
        
        return updated_customers
    
    def _calculate_quintiles(
        self,
        values: List[float],
        reverse: bool = False
    ) -> List[float]:
        """Calculate quintile thresholds"""
        if not values:
            return [0, 0, 0, 0, 0]
        
        sorted_values = sorted(values, reverse=reverse)
        n = len(sorted_values)
        
        return [
            sorted_values[int(n * 0.2)],
            sorted_values[int(n * 0.4)],
            sorted_values[int(n * 0.6)],
            sorted_values[int(n * 0.8)],
            sorted_values[-1]
        ]
    
    def _get_quintile_score(
        self,
        value: float,
        quintiles: List[float],
        reverse: bool = False
    ) -> int:
        """Get score (1-5) based on quintile position"""
        for i, threshold in enumerate(quintiles):
            if value <= threshold:
                score = i + 1
                break
        else:
            score = 5
        
        if reverse:
            score = 6 - score  # Invert for recency
        
        return score
    
    def _determine_rfm_segment(
        self,
        r_score: int,
        f_score: int,
        m_score: int
    ) -> str:
        """
        Determine customer segment based on RFM scores
        
        Segments:
        - Champions: R=5, F=5, M=5 (best customers)
        - Loyal: R=4-5, F=4-5, M=3-5
        - Potential Loyalist: R=4-5, F=3, M=3-4
        - New Customers: R=5, F=1-2, M=1-2
        - Promising: R=4-5, F=2-3, M=2-3
        - Need Attention: R=3, F=3-4, M=3-4
        - About to Sleep: R=2-3, F=2-3, M=2-3
        - At Risk: R=1-2, F=3-4, M=3-5
        - Can't Lose Them: R=1-2, F=5, M=5
        - Hibernating: R=1-2, F=2-3, M=1-2
        - Lost: R=1, F=1, M=1-2
        """
        if r_score == 5 and f_score == 5 and m_score == 5:
            return "Champion"
        elif r_score >= 4 and f_score >= 4 and m_score >= 3:
            return "Loyal"
        elif r_score >= 4 and f_score == 3 and m_score >= 3:
            return "Potential Loyalist"
        elif r_score == 5 and f_score <= 2 and m_score <= 2:
            return "New Customer"
        elif r_score >= 4 and f_score >= 2 and m_score >= 2:
            return "Promising"
        elif r_score == 3 and f_score >= 3 and m_score >= 3:
            return "Need Attention"
        elif r_score >= 2 and f_score >= 2 and m_score >= 2:
            return "About to Sleep"
        elif r_score <= 2 and f_score >= 3 and m_score >= 3:
            return "At Risk"
        elif r_score <= 2 and f_score == 5 and m_score == 5:
            return "Can't Lose Them"
        elif r_score <= 2 and f_score >= 2 and m_score <= 2:
            return "Hibernating"
        else:
            return "Lost"
    
    async def get_rfm_segment_distribution(self) -> Dict[str, Any]:
        """Get RFM segment distribution and metrics"""
        distribution = await self.customer_repo.get_rfm_segment_distribution()
        
        total_customers = sum(d["count"] for d in distribution)
        total_revenue = sum(d["total_revenue"] for d in distribution)
        
        # Calculate percentages
        for segment_data in distribution:
            segment_data["percentage"] = (
                Decimal(segment_data["count"]) / Decimal(total_customers) * 100
                if total_customers > 0 else Decimal("0")
            )
        
        # Count by segment type
        segment_counts = {d["segment"]: d["count"] for d in distribution}
        
        return {
            "total_customers_analyzed": total_customers,
            "total_revenue": total_revenue,
            "segment_distribution": distribution,
            "champion_count": segment_counts.get("Champion", 0),
            "loyal_count": segment_counts.get("Loyal", 0),
            "potential_loyalist_count": segment_counts.get("Potential Loyalist", 0),
            "new_customers_count": segment_counts.get("New Customer", 0),
            "promising_count": segment_counts.get("Promising", 0),
            "need_attention_count": segment_counts.get("Need Attention", 0),
            "about_to_sleep_count": segment_counts.get("About to Sleep", 0),
            "at_risk_count": segment_counts.get("At Risk", 0),
            "cannot_lose_count": segment_counts.get("Can't Lose Them", 0),
            "hibernating_count": segment_counts.get("Hibernating", 0),
            "lost_count": segment_counts.get("Lost", 0)
        }
    
    # ========================================================================
    # CLV (Customer Lifetime Value) Calculation
    # ========================================================================
    
    async def calculate_clv(
        self,
        customer_ids: Optional[List[UUID]] = None,
        prediction_months: int = 12
    ) -> List[RetailCustomer]:
        """
        Calculate Customer Lifetime Value (CLV)
        
        CLV Formula:
        CLV = (Average Order Value) × (Purchase Frequency) × (Customer Lifespan)
        
        Where:
        - Average Order Value = total_spent / total_orders
        - Purchase Frequency = total_orders / customer_age_months
        - Customer Lifespan = predicted based on historical data
        
        Args:
            customer_ids: Specific customers or None for all
            prediction_months: Months to predict into future
            
        Returns:
            List of updated customers
        """
        # Get customers to analyze
        if customer_ids:
            customers = []
            for cid in customer_ids:
                customer = await self.customer_repo.get(cid)
                if customer and customer.total_orders > 0:
                    customers.append(customer)
        else:
            customers = await self.customer_repo.get_customers_needing_clv_update()
        
        if not customers:
            return []
        
        updated_customers = []
        
        for customer in customers:
            clv = await self._calculate_customer_clv(
                customer,
                prediction_months
            )
            
            updated = await self.customer_repo.update_clv(customer.id, clv)
            updated_customers.append(updated)
        
        return updated_customers
    
    async def _calculate_customer_clv(
        self,
        customer: RetailCustomer,
        prediction_months: int
    ) -> Decimal:
        """Calculate CLV for a single customer"""
        if customer.total_orders == 0:
            return Decimal("0")
        
        # Calculate customer age in months
        age_days = (datetime.utcnow() - customer.created_at).days
        age_months = max(age_days / 30, 1)  # At least 1 month
        
        # Average order value
        aov = customer.average_order_value
        
        # Purchase frequency (orders per month)
        purchase_frequency = Decimal(customer.total_orders) / Decimal(age_months)
        
        # Estimate customer lifespan
        # Use RFM segment to adjust lifespan prediction
        lifespan_months = self._estimate_lifespan(
            customer.rfm_segment,
            prediction_months
        )
        
        # CLV = AOV × Purchase Frequency × Lifespan
        clv = aov * purchase_frequency * Decimal(lifespan_months)
        
        # Apply discount factor for future value (optional)
        # discount_rate = 0.1  # 10% annual discount
        # monthly_discount = (1 + discount_rate) ** (1/12)
        # clv = clv / Decimal(monthly_discount ** prediction_months)
        
        return clv.quantize(Decimal("0.01"))
    
    def _estimate_lifespan(
        self,
        rfm_segment: Optional[str],
        default_months: int
    ) -> int:
        """
        Estimate customer lifespan based on RFM segment
        
        Args:
            rfm_segment: RFM segment name
            default_months: Default lifespan if no segment
            
        Returns:
            Estimated lifespan in months
        """
        # Segment-based lifespan multipliers
        lifespan_multipliers = {
            "Champion": 2.0,
            "Loyal": 1.8,
            "Potential Loyalist": 1.5,
            "New Customer": 1.2,
            "Promising": 1.3,
            "Need Attention": 1.0,
            "About to Sleep": 0.8,
            "At Risk": 0.6,
            "Can't Lose Them": 1.5,
            "Hibernating": 0.5,
            "Lost": 0.3
        }
        
        multiplier = lifespan_multipliers.get(rfm_segment, 1.0)
        return int(default_months * multiplier)
    
    async def get_clv_analysis(
        self,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Get CLV analysis and distribution"""
        # Get top customers by CLV
        top_customers = await self.customer_repo.get_top_customers_by_clv(limit)
        
        if not top_customers:
            return {
                "total_customers_analyzed": 0,
                "total_clv": Decimal("0"),
                "average_clv": Decimal("0"),
                "median_clv": Decimal("0"),
                "distribution": [],
                "top_customers": []
            }
        
        # Calculate statistics
        clv_values = [float(c.clv) for c in top_customers]
        total_clv = sum(clv_values)
        average_clv = total_clv / len(clv_values)
        median_clv = statistics.median(clv_values)
        
        # Create distribution buckets
        distribution = self._create_clv_distribution(top_customers)
        
        return {
            "total_customers_analyzed": len(top_customers),
            "total_clv": Decimal(str(total_clv)),
            "average_clv": Decimal(str(average_clv)),
            "median_clv": Decimal(str(median_clv)),
            "distribution": distribution,
            "top_customers": top_customers[:10]  # Top 10
        }
    
    def _create_clv_distribution(
        self,
        customers: List[RetailCustomer]
    ) -> List[Dict[str, Any]]:
        """Create CLV distribution buckets"""
        buckets = [
            {"label": "0-1000", "min": 0, "max": 1000},
            {"label": "1000-5000", "min": 1000, "max": 5000},
            {"label": "5000-10000", "min": 5000, "max": 10000},
            {"label": "10000-25000", "min": 10000, "max": 25000},
            {"label": "25000-50000", "min": 25000, "max": 50000},
            {"label": "50000+", "min": 50000, "max": float('inf')}
        ]
        
        # Count customers in each bucket
        for bucket in buckets:
            bucket["count"] = 0
            bucket["total_clv"] = Decimal("0")
        
        total_customers = len(customers)
        
        for customer in customers:
            clv = float(customer.clv)
            for bucket in buckets:
                if bucket["min"] <= clv < bucket["max"]:
                    bucket["count"] += 1
                    bucket["total_clv"] += customer.clv
                    break
        
        # Calculate percentages
        for bucket in buckets:
            bucket["percentage"] = (
                Decimal(bucket["count"]) / Decimal(total_customers) * 100
                if total_customers > 0 else Decimal("0")
            )
            bucket["min_value"] = Decimal(str(bucket["min"]))
            bucket["max_value"] = (
                Decimal(str(bucket["max"]))
                if bucket["max"] != float('inf')
                else Decimal("999999")
            )
            del bucket["min"]
            del bucket["max"]
        
        return buckets
    
    # ========================================================================
    # Customer Preferences
    # ========================================================================
    
    async def update_customer_preferences(
        self,
        customer_id: UUID,
        preferences: List[Dict[str, Any]]
    ) -> List[CustomerPreference]:
        """Bulk update customer preferences"""
        return await self.preference_repo.bulk_upsert_preferences(
            customer_id,
            preferences
        )
    
    async def get_customer_preferences(
        self,
        customer_id: UUID,
        preference_type: Optional[CustomerPreferenceType] = None
    ) -> List[CustomerPreference]:
        """Get customer preferences"""
        return await self.preference_repo.get_customer_preferences(
            customer_id,
            preference_type
        )
