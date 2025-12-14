"""
Wholesale Service

Business logic for wholesale operations including MOQ validation,
credit limit management, bulk pricing, and order approval workflows.
"""

from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from decimal import Decimal
from datetime import datetime, date

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wholesale import (
    WholesaleCustomer,
    ContractPricing,
    CustomerStatus,
    CreditStatus,
    PaymentTerms
)
from app.models.order import Order, OrderItem, OrderStatus, SalesChannel
from app.models.product import ProductVariant
from app.repositories.wholesale import WholesaleCustomerRepository, ContractPricingRepository
from app.repositories.product import ProductVariantRepository
from app.schemas.wholesale import (
    WholesaleOrderValidation,
    BulkPricingResponse
)


class WholesaleService:
    """Service layer for wholesale business logic"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.customer_repo = WholesaleCustomerRepository(db)
        self.contract_repo = ContractPricingRepository(db)
        self.product_repo = ProductVariantRepository(db)
    
    # ==================== Order Validation ====================
    
    async def validate_wholesale_order(
        self,
        customer_id: UUID,
        items: List[Dict[str, Any]],
        apply_credit_check: bool = True
    ) -> WholesaleOrderValidation:
        """
        Comprehensive validation for wholesale orders
        
        Validates:
        - Customer status and eligibility
        - Minimum Order Quantity (MOQ)
        - Minimum Order Value (MOV)
        - Credit limit availability
        - Product availability
        - Contract pricing applicability
        
        Args:
            customer_id: UUID of the wholesale customer
            items: List of order items [{"product_variant_id": UUID, "quantity": int}]
            apply_credit_check: Whether to check credit limits
        
        Returns:
            WholesaleOrderValidation with validation results and details
        """
        validation = WholesaleOrderValidation(
            is_valid=True,
            errors=[],
            warnings=[]
        )
        
        # Get customer
        customer = await self.customer_repo.get_by_id(customer_id)
        if not customer:
            validation.is_valid = False
            validation.errors.append("Customer not found")
            return validation
        
        # Check customer status
        if customer.status != CustomerStatus.ACTIVE:
            validation.is_valid = False
            validation.errors.append(f"Customer account is {customer.status.value}")
            return validation
        
        # Calculate order totals
        total_quantity = 0
        order_value = Decimal("0.00")
        
        for item in items:
            product_variant_id = item.get("product_variant_id")
            quantity = item.get("quantity", 0)
            
            # Validate product exists
            product_variant = await self.product_repo.get_by_id(product_variant_id)
            if not product_variant:
                validation.errors.append(f"Product variant {product_variant_id} not found")
                validation.is_valid = False
                continue
            
            # Get applicable price (contract or regular)
            contract_price = await self.contract_repo.get_applicable_price(
                customer_id=customer_id,
                product_variant_id=product_variant_id,
                category_id=product_variant.product.category_id if product_variant.product else None,
                quantity=quantity
            )
            
            if contract_price:
                unit_price = contract_price.contract_price
                validation.pricing_applied = True
            else:
                # Use product's price
                unit_price = product_variant.price
            
            # Apply customer discount if no contract pricing
            if not contract_price and customer.default_discount_percentage > 0:
                discount_multiplier = Decimal("1") - (customer.default_discount_percentage / Decimal("100"))
                unit_price = unit_price * discount_multiplier
            
            total_quantity += quantity
            order_value += unit_price * quantity
        
        validation.total_quantity = total_quantity
        validation.order_value = order_value
        
        # MOQ Validation
        if customer.minimum_order_quantity > 0:
            if total_quantity < customer.minimum_order_quantity:
                validation.is_valid = False
                validation.moq_passed = False
                validation.errors.append(
                    f"Minimum order quantity is {customer.minimum_order_quantity} units. "
                    f"Current order has {total_quantity} units."
                )
        
        # MOV Validation
        if customer.minimum_order_value > 0:
            if order_value < customer.minimum_order_value:
                validation.is_valid = False
                validation.mov_passed = False
                validation.errors.append(
                    f"Minimum order value is {customer.minimum_order_value}. "
                    f"Current order value is {order_value}."
                )
        
        # Credit Check
        if apply_credit_check and customer.payment_terms != PaymentTerms.IMMEDIATE:
            validation.credit_required = order_value
            validation.credit_available = customer.credit_available
            
            if not customer.has_sufficient_credit(order_value):
                validation.is_valid = False
                validation.credit_check_passed = False
                validation.errors.append(
                    f"Insufficient credit. Required: {order_value}, "
                    f"Available: {customer.credit_available}"
                )
            elif customer.credit_status == CreditStatus.WARNING:
                validation.warnings.append(
                    "Customer is approaching credit limit. "
                    f"Available credit: {customer.credit_available}"
                )
        
        return validation
    
    # ==================== Bulk Pricing ====================
    
    async def calculate_bulk_pricing(
        self,
        customer_id: UUID,
        items: List[Dict[str, Any]]
    ) -> BulkPricingResponse:
        """
        Calculate bulk pricing for wholesale orders
        
        Applies:
        - Contract pricing (if available)
        - Volume discounts
        - Customer default discounts
        - Pricing tier rules
        
        Args:
            customer_id: UUID of the wholesale customer
            items: List of items [{"product_variant_id": UUID, "quantity": int}]
        
        Returns:
            BulkPricingResponse with detailed pricing breakdown
        """
        customer = await self.customer_repo.get_by_id(customer_id)
        if not customer:
            raise ValueError("Customer not found")
        
        priced_items = []
        subtotal = Decimal("0.00")
        total_discount = Decimal("0.00")
        pricing_tiers_applied = []
        
        for item in items:
            product_variant_id = item.get("product_variant_id")
            quantity = item.get("quantity", 0)
            
            # Get product
            product_variant = await self.product_repo.get_by_id(product_variant_id)
            if not product_variant:
                continue
            
            base_price = product_variant.price
            unit_price = base_price
            discount = Decimal("0.00")
            pricing_source = "regular"
            
            # Check for contract pricing
            contract_price = await self.contract_repo.get_applicable_price(
                customer_id=customer_id,
                product_variant_id=product_variant_id,
                category_id=product_variant.product.category_id if product_variant.product else None,
                quantity=quantity
            )
            
            if contract_price:
                unit_price = contract_price.contract_price
                discount = (base_price - unit_price) * quantity
                pricing_source = "contract"
                pricing_tiers_applied.append(f"Contract pricing for {product_variant.sku}")
            else:
                # Apply customer default discount
                if customer.default_discount_percentage > 0:
                    discount_amount = base_price * (customer.default_discount_percentage / Decimal("100"))
                    unit_price = base_price - discount_amount
                    discount = discount_amount * quantity
                    pricing_source = "customer_discount"
            
            item_total = unit_price * quantity
            
            priced_items.append({
                "product_variant_id": str(product_variant_id),
                "sku": product_variant.sku,
                "name": product_variant.product.name if product_variant.product else "Unknown",
                "quantity": quantity,
                "base_price": float(base_price),
                "unit_price": float(unit_price),
                "discount_per_unit": float((base_price - unit_price)),
                "discount": float(discount),
                "total": float(item_total),
                "pricing_source": pricing_source
            })
            
            subtotal += item_total
            total_discount += discount
        
        return BulkPricingResponse(
            items=priced_items,
            subtotal=subtotal,
            total_discount=total_discount,
            total=subtotal,
            pricing_tiers_applied=pricing_tiers_applied
        )
    
    # ==================== Credit Management ====================
    
    async def reserve_credit(
        self,
        customer_id: UUID,
        amount: Decimal,
        reference: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Reserve credit for an order
        
        Args:
            customer_id: Customer UUID
            amount: Amount to reserve
            reference: Order reference
        
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        customer = await self.customer_repo.get_by_id(customer_id)
        if not customer:
            return False, "Customer not found"
        
        if customer.status != CustomerStatus.ACTIVE:
            return False, f"Customer account is {customer.status.value}"
        
        if not customer.has_sufficient_credit(amount):
            return False, (
                f"Insufficient credit. Required: {amount}, "
                f"Available: {customer.credit_available}"
            )
        
        # Reserve credit by increasing credit_used
        await self.customer_repo.update_credit_used(
            customer_id=customer_id,
            amount=amount,
            operation="increase"
        )
        
        return True, None
    
    async def release_credit(
        self,
        customer_id: UUID,
        amount: Decimal,
        reference: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Release reserved credit (e.g., when order is cancelled)
        
        Args:
            customer_id: Customer UUID
            amount: Amount to release
            reference: Order reference
        
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        customer = await self.customer_repo.get_by_id(customer_id)
        if not customer:
            return False, "Customer not found"
        
        # Release credit by decreasing credit_used
        await self.customer_repo.update_credit_used(
            customer_id=customer_id,
            amount=amount,
            operation="decrease"
        )
        
        return True, None
    
    async def check_credit_status(
        self, customer_id: UUID
    ) -> Dict[str, Any]:
        """Get comprehensive credit status for a customer"""
        customer = await self.customer_repo.get_by_id(customer_id)
        if not customer:
            raise ValueError("Customer not found")
        
        utilization_percentage = 0
        if customer.credit_limit > 0:
            utilization_percentage = (
                customer.credit_used / customer.credit_limit * 100
            )
        
        return {
            "credit_limit": float(customer.credit_limit),
            "credit_used": float(customer.credit_used),
            "credit_available": float(customer.credit_available),
            "credit_status": customer.credit_status.value,
            "utilization_percentage": float(utilization_percentage),
            "payment_terms": customer.payment_terms.value,
            "payment_terms_days": customer.payment_terms_days
        }
    
    # ==================== Order Approval ====================
    
    async def requires_order_approval(
        self, customer_id: UUID, order_value: Decimal
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if an order requires approval
        
        Approval required if:
        - Customer has requires_approval flag
        - Order value exceeds credit limit
        - Customer credit status is WARNING or EXCEEDED
        - Customer is new (fewer than X orders)
        
        Returns:
            Tuple of (requires_approval: bool, reason: Optional[str])
        """
        customer = await self.customer_repo.get_by_id(customer_id)
        if not customer:
            return False, None
        
        # Auto-approve if enabled
        if customer.auto_approve_orders:
            return False, None
        
        # Check explicit approval flag
        if customer.requires_approval:
            return True, "Customer requires manual approval for all orders"
        
        # Check credit status
        if customer.credit_status in [CreditStatus.WARNING, CreditStatus.EXCEEDED]:
            return True, f"Customer credit status is {customer.credit_status.value}"
        
        # Check if order would exceed credit limit
        if not customer.has_sufficient_credit(order_value):
            return True, "Order value exceeds available credit"
        
        # Check if new customer (fewer than 3 orders)
        if customer.total_orders < 3:
            return True, "New customer with limited order history"
        
        return False, None
    
    # ==================== Performance Metrics ====================
    
    async def update_customer_performance(
        self, customer_id: UUID
    ) -> Optional[WholesaleCustomer]:
        """
        Recalculate and update customer performance metrics
        
        Calculates:
        - Total orders
        - Total spent
        - Average order value
        - Last order date
        """
        from sqlalchemy import select, func
        
        # Calculate metrics from orders
        query = select(
            func.count(Order.id).label("total_orders"),
            func.sum(Order.total).label("total_spent"),
            func.avg(Order.total).label("average_order_value"),
            func.max(Order.order_date).label("last_order_date")
        ).where(
            Order.wholesale_customer_id == customer_id,
            Order.status.in_([
                OrderStatus.COMPLETED,
                OrderStatus.DELIVERED
            ])
        )
        
        result = await self.db.execute(query)
        metrics = result.one()
        
        # Update customer
        return await self.customer_repo.update_performance_metrics(
            customer_id=customer_id,
            total_orders=metrics.total_orders or 0,
            total_spent=metrics.total_spent or Decimal("0.00"),
            average_order_value=metrics.average_order_value or Decimal("0.00"),
            last_order_date=metrics.last_order_date
        )
    
    # ==================== Contract Pricing Management ====================
    
    async def get_effective_price(
        self,
        customer_id: UUID,
        product_variant_id: UUID,
        quantity: int = 1
    ) -> Tuple[Decimal, str]:
        """
        Get the effective price for a product for a customer
        
        Returns:
            Tuple of (price: Decimal, pricing_source: str)
        """
        # Get product
        product_variant = await self.product_repo.get_by_id(product_variant_id)
        if not product_variant:
            raise ValueError("Product variant not found")
        
        customer = await self.customer_repo.get_by_id(customer_id)
        if not customer:
            raise ValueError("Customer not found")
        
        base_price = product_variant.price
        
        # Check for contract pricing
        contract_price = await self.contract_repo.get_applicable_price(
            customer_id=customer_id,
            product_variant_id=product_variant_id,
            category_id=product_variant.product.category_id if product_variant.product else None,
            quantity=quantity
        )
        
        if contract_price:
            return contract_price.contract_price, "contract"
        
        # Apply customer default discount
        if customer.default_discount_percentage > 0:
            discount_multiplier = Decimal("1") - (customer.default_discount_percentage / Decimal("100"))
            discounted_price = base_price * discount_multiplier
            return discounted_price, "customer_discount"
        
        return base_price, "regular"
    
    async def cleanup_expired_contracts(self) -> int:
        """Deactivate expired contract prices"""
        return await self.contract_repo.deactivate_expired_prices()
    
    # ==================== Customer Analytics ====================
    
    async def get_customer_summary(
        self, customer_id: UUID
    ) -> Dict[str, Any]:
        """Get comprehensive customer summary"""
        customer = await self.customer_repo.get_by_id_with_relationships(customer_id)
        if not customer:
            raise ValueError("Customer not found")
        
        credit_status = await self.check_credit_status(customer_id)
        
        return {
            "id": str(customer.id),
            "company_name": customer.company_name,
            "customer_type": customer.customer_type.value,
            "status": customer.status.value,
            "contact": {
                "primary_contact": customer.primary_contact_name,
                "primary_email": customer.primary_email,
                "primary_phone": customer.primary_phone
            },
            "credit": credit_status,
            "performance": {
                "total_orders": customer.total_orders,
                "total_spent": float(customer.total_spent),
                "average_order_value": float(customer.average_order_value),
                "last_order_date": customer.last_order_date.isoformat() if customer.last_order_date else None
            },
            "settings": {
                "payment_terms": customer.payment_terms.value,
                "minimum_order_quantity": customer.minimum_order_quantity,
                "minimum_order_value": float(customer.minimum_order_value),
                "default_discount": float(customer.default_discount_percentage),
                "has_contract_pricing": customer.has_contract_pricing,
                "requires_approval": customer.requires_approval
            },
            "sales_rep": {
                "id": str(customer.sales_rep.id) if customer.sales_rep else None,
                "name": customer.sales_rep.full_name if customer.sales_rep else None
            } if customer.sales_rep else None
        }
