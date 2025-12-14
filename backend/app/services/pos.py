"""
Point of Sale (POS) Service

Business logic for POS operations including cashier shifts, transactions,
returns, exchanges, and cash drawer management.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pos import (
    CashierShift,
    CashDrawer,
    POSTransaction,
    ReturnExchange,
    ShiftStatus,
    CashDrawerStatus,
    POSTransactionType,
    ReturnReason
)
from app.models.order import Order, OrderItem, OrderStatus, PaymentStatus
from app.repositories.pos import (
    CashierShiftRepository,
    CashDrawerRepository,
    POSTransactionRepository,
    ReturnExchangeRepository
)
from app.repositories.product import ProductVariantRepository
from app.repositories.inventory import InventoryLevelRepository
from app.schemas.pos import (
    CashierShiftCreate,
    CashierShiftClose,
    POSSaleCreate,
    POSSaleResponse,
    ReturnExchangeCreate,
    CashMovement
)


class POSService:
    """Service for POS operations"""
    
    def __init__(
        self,
        db: AsyncSession,
        shift_repo: CashierShiftRepository,
        drawer_repo: CashDrawerRepository,
        transaction_repo: POSTransactionRepository,
        return_repo: ReturnExchangeRepository,
        variant_repo: ProductVariantRepository,
        inventory_repo: InventoryLevelRepository
    ):
        self.db = db
        self.shift_repo = shift_repo
        self.drawer_repo = drawer_repo
        self.transaction_repo = transaction_repo
        self.return_repo = return_repo
        self.variant_repo = variant_repo
        self.inventory_repo = inventory_repo
    
    # ==================== Shift Management ====================
    
    async def start_shift(
        self,
        cashier_id: UUID,
        shift_data: CashierShiftCreate
    ) -> CashierShift:
        """Start a new cashier shift"""
        # Check if cashier already has an active shift
        existing_shift = await self.shift_repo.get_active_shift_for_cashier(cashier_id)
        if existing_shift:
            raise ValueError(
                f"Cashier already has an active shift (#{existing_shift.shift_number}). "
                "Please close the existing shift first."
            )
        
        # Generate shift number
        shift_number = await self.shift_repo.generate_shift_number()
        
        # Create shift
        shift = CashierShift(
            shift_number=shift_number,
            cashier_id=cashier_id,
            register_number=shift_data.register_number,
            opening_cash=shift_data.opening_cash,
            opening_notes=shift_data.opening_notes,
            status=ShiftStatus.ACTIVE,
            started_at=datetime.utcnow()
        )
        
        shift = await self.shift_repo.create(shift)
        
        # Create associated cash drawer
        drawer = CashDrawer(
            shift_id=shift.id,
            status=CashDrawerStatus.OPEN,
            current_balance=shift_data.opening_cash
        )
        
        await self.drawer_repo.create(drawer)
        
        return shift
    
    async def close_shift(
        self,
        shift_id: UUID,
        close_data: CashierShiftClose
    ) -> CashierShift:
        """Close a cashier shift"""
        shift = await self.shift_repo.get(shift_id)
        if not shift:
            raise ValueError(f"Shift {shift_id} not found")
        
        if shift.status != ShiftStatus.ACTIVE:
            raise ValueError(f"Shift is not active (current status: {shift.status})")
        
        # Close the shift
        shift.close_shift(close_data.closing_cash)
        shift.closing_notes = close_data.closing_notes
        
        # Close the cash drawer
        drawer = await self.drawer_repo.get_by_shift(shift_id)
        if drawer:
            await self.drawer_repo.close_drawer(
                drawer.id,
                close_data.closing_cash,
                shift.expected_cash
            )
            
            # Update denomination breakdown if provided
            if close_data.denomination_breakdown:
                drawer.denomination_breakdown = close_data.denomination_breakdown
                await self.db.commit()
        
        await self.db.commit()
        await self.db.refresh(shift)
        
        return shift
    
    async def reconcile_shift(
        self,
        shift_id: UUID,
        reconciliation_notes: Optional[str] = None
    ) -> CashierShift:
        """Reconcile a closed shift"""
        shift = await self.shift_repo.get(shift_id)
        if not shift:
            raise ValueError(f"Shift {shift_id} not found")
        
        if shift.status != ShiftStatus.CLOSED:
            raise ValueError(f"Shift must be closed before reconciliation (current status: {shift.status})")
        
        shift.status = ShiftStatus.RECONCILED
        shift.reconciliation_notes = reconciliation_notes
        
        await self.db.commit()
        await self.db.refresh(shift)
        
        return shift
    
    async def get_active_shift_for_cashier(
        self,
        cashier_id: UUID
    ) -> Optional[CashierShift]:
        """Get the active shift for a cashier"""
        return await self.shift_repo.get_active_shift_for_cashier(cashier_id)
    
    # ==================== Cash Drawer Management ====================
    
    async def add_cash_to_drawer(
        self,
        shift_id: UUID,
        cash_movement: CashMovement
    ) -> Dict[str, Any]:
        """Add cash to drawer (cash in)"""
        shift = await self.shift_repo.get(shift_id)
        if not shift:
            raise ValueError(f"Shift {shift_id} not found")
        
        if shift.status != ShiftStatus.ACTIVE:
            raise ValueError("Cannot add cash to inactive shift")
        
        drawer = await self.drawer_repo.get_by_shift(shift_id)
        if not drawer:
            raise ValueError(f"Cash drawer not found for shift {shift_id}")
        
        # Update drawer balance
        drawer = await self.drawer_repo.update_balance(
            drawer.id,
            cash_movement.amount,
            is_addition=True
        )
        
        # Create transaction record
        transaction_number = await self.transaction_repo.generate_transaction_number()
        transaction = POSTransaction(
            transaction_number=transaction_number,
            transaction_type=POSTransactionType.CASH_IN,
            shift_id=shift_id,
            amount=cash_movement.amount,
            payment_method="cash",
            notes=f"{cash_movement.reason}\n{cash_movement.notes or ''}".strip()
        )
        
        await self.transaction_repo.create(transaction)
        
        return {
            "transaction_id": transaction.id,
            "transaction_number": transaction_number,
            "new_balance": drawer.current_balance
        }
    
    async def remove_cash_from_drawer(
        self,
        shift_id: UUID,
        cash_movement: CashMovement
    ) -> Dict[str, Any]:
        """Remove cash from drawer (cash out/payout)"""
        shift = await self.shift_repo.get(shift_id)
        if not shift:
            raise ValueError(f"Shift {shift_id} not found")
        
        if shift.status != ShiftStatus.ACTIVE:
            raise ValueError("Cannot remove cash from inactive shift")
        
        drawer = await self.drawer_repo.get_by_shift(shift_id)
        if not drawer:
            raise ValueError(f"Cash drawer not found for shift {shift_id}")
        
        # Check if sufficient cash available
        if drawer.current_balance < cash_movement.amount:
            raise ValueError(
                f"Insufficient cash in drawer. Available: {drawer.current_balance}, "
                f"Requested: {cash_movement.amount}"
            )
        
        # Update drawer balance
        drawer = await self.drawer_repo.update_balance(
            drawer.id,
            cash_movement.amount,
            is_addition=False
        )
        
        # Create transaction record
        transaction_number = await self.transaction_repo.generate_transaction_number()
        transaction = POSTransaction(
            transaction_number=transaction_number,
            transaction_type=POSTransactionType.CASH_OUT,
            shift_id=shift_id,
            amount=cash_movement.amount,
            payment_method="cash",
            notes=f"{cash_movement.reason}\n{cash_movement.notes or ''}".strip()
        )
        
        await self.transaction_repo.create(transaction)
        
        return {
            "transaction_id": transaction.id,
            "transaction_number": transaction_number,
            "new_balance": drawer.current_balance
        }
    
    async def get_drawer_status(self, shift_id: UUID) -> Optional[CashDrawer]:
        """Get current cash drawer status"""
        return await self.drawer_repo.get_by_shift(shift_id)
    
    # ==================== POS Sales ====================
    
    async def process_sale(
        self,
        cashier_id: UUID,
        sale_data: POSSaleCreate
    ) -> POSSaleResponse:
        """Process a POS sale"""
        # Get active shift
        shift = await self.get_active_shift_for_cashier(cashier_id)
        if not shift:
            raise ValueError("No active shift found. Please start a shift first.")
        
        # Validate items and calculate totals
        subtotal = Decimal("0.00")
        total_tax = Decimal("0.00")
        items_data = []
        
        for item in sale_data.items:
            # Get product variant
            variant = await self.variant_repo.get(item.product_variant_id)
            if not variant:
                raise ValueError(f"Product variant {item.product_variant_id} not found")
            
            # Check stock availability
            # TODO: Implement stock check across locations
            
            # Calculate item total
            item_subtotal = item.unit_price * item.quantity
            item_total = item_subtotal - item.discount_amount + item.tax_amount
            
            subtotal += item_subtotal
            total_tax += item.tax_amount
            
            items_data.append({
                "variant_id": item.product_variant_id,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "discount": item.discount_amount,
                "tax": item.tax_amount,
                "total": item_total
            })
        
        # Apply subtotal discount
        total_discount = sale_data.subtotal_discount + sum(
            item.discount_amount for item in sale_data.items
        )
        total_amount = subtotal - sale_data.subtotal_discount + total_tax
        
        # Calculate change if cash payment
        change_due = None
        if sale_data.payment_method.lower() == "cash" and sale_data.amount_tendered:
            if sale_data.amount_tendered < total_amount:
                raise ValueError(
                    f"Insufficient payment. Total: {total_amount}, "
                    f"Tendered: {sale_data.amount_tendered}"
                )
            change_due = sale_data.amount_tendered - total_amount
        
        # Create order
        from app.models.order import SalesChannel
        order = Order(
            customer_id=cashier_id,  # Use cashier as customer for now
            channel=SalesChannel.POS,
            status=OrderStatus.COMPLETED,  # POS sales are completed immediately
            payment_status=PaymentStatus.PAID,
            subtotal=subtotal,
            discount=total_discount,
            tax=total_tax,
            total=total_amount,
            notes=sale_data.notes
        )
        
        # Add order items
        for item_data in items_data:
            order_item = OrderItem(
                product_variant_id=item_data["variant_id"],
                quantity=item_data["quantity"],
                unit_price=item_data["unit_price"],
                discount=item_data["discount"],
                tax=item_data["tax"],
                subtotal=item_data["total"]
            )
            order.items.append(order_item)
        
        self.db.add(order)
        await self.db.flush()
        
        # Generate transaction and receipt numbers
        transaction_number = await self.transaction_repo.generate_transaction_number()
        receipt_number = await self.transaction_repo.generate_receipt_number()
        
        # Create POS transaction
        transaction = POSTransaction(
            transaction_number=transaction_number,
            transaction_type=POSTransactionType.SALE,
            shift_id=shift.id,
            order_id=order.id,
            amount=total_amount,
            payment_method=sale_data.payment_method,
            customer_name=sale_data.customer_name,
            customer_phone=sale_data.customer_phone,
            customer_email=sale_data.customer_email,
            receipt_number=receipt_number,
            receipt_generated=True,
            notes=sale_data.notes
        )
        
        await self.transaction_repo.create(transaction)
        
        # Update shift totals
        await self.shift_repo.update_shift_totals(
            shift.id,
            total_amount,
            POSTransactionType.SALE,
            sale_data.payment_method
        )
        
        # Update cash drawer for cash payments
        if sale_data.payment_method.lower() == "cash":
            drawer = await self.drawer_repo.get_by_shift(shift.id)
            if drawer:
                await self.drawer_repo.update_balance(
                    drawer.id,
                    total_amount,
                    is_addition=True
                )
        
        # TODO: Update inventory levels
        
        await self.db.commit()
        
        return POSSaleResponse(
            order_id=order.id,
            transaction_id=transaction.id,
            transaction_number=transaction_number,
            receipt_number=receipt_number,
            subtotal=subtotal,
            total_discount=total_discount,
            total_tax=total_tax,
            total_amount=total_amount,
            payment_method=sale_data.payment_method,
            amount_tendered=sale_data.amount_tendered,
            change_due=change_due,
            transaction_at=transaction.transaction_at
        )
    
    # ==================== Returns and Exchanges ====================
    
    async def process_return(
        self,
        cashier_id: UUID,
        return_data: ReturnExchangeCreate
    ) -> ReturnExchange:
        """Process a product return"""
        # Get active shift
        shift = await self.get_active_shift_for_cashier(cashier_id)
        if not shift:
            raise ValueError("No active shift found. Please start a shift first.")
        
        # Get original order
        from app.repositories.base import BaseRepository
        order_repo = BaseRepository(Order, self.db)
        original_order = await order_repo.get(return_data.original_order_id)
        if not original_order:
            raise ValueError(f"Original order {return_data.original_order_id} not found")
        
        # Validate return items exist in original order
        original_items = {str(item.product_variant_id): item for item in original_order.items}
        
        # Calculate refund amount
        refund_amount = Decimal("0.00")
        returned_items_dict = {}
        
        for return_item in return_data.returned_items:
            variant_id_str = str(return_item.product_variant_id)
            
            if variant_id_str not in original_items:
                raise ValueError(
                    f"Product variant {return_item.product_variant_id} "
                    f"not found in original order"
                )
            
            original_item = original_items[variant_id_str]
            
            # Validate quantity
            if return_item.quantity > original_item.quantity:
                raise ValueError(
                    f"Return quantity ({return_item.quantity}) exceeds "
                    f"original quantity ({original_item.quantity})"
                )
            
            # Calculate refund for this item (proportional)
            item_refund = (original_item.subtotal / original_item.quantity) * return_item.quantity
            refund_amount += item_refund
            
            returned_items_dict[variant_id_str] = {
                "product_variant_id": variant_id_str,
                "quantity": return_item.quantity,
                "reason": return_item.reason.value,
                "condition": return_item.condition,
                "restock": return_item.restock,
                "refund_amount": float(item_refund)
            }
        
        # Apply restocking fee
        refund_amount -= return_data.restocking_fee
        if refund_amount < Decimal("0.00"):
            refund_amount = Decimal("0.00")
        
        # Generate return number
        return_number = await self.return_repo.generate_return_number()
        
        # Create return record
        return_exchange = ReturnExchange(
            return_number=return_number,
            is_exchange=return_data.is_exchange,
            original_order_id=return_data.original_order_id,
            new_order_id=return_data.new_order_id,
            reason=return_data.reason,
            reason_description=return_data.reason_description,
            refund_amount=refund_amount,
            restocking_fee=return_data.restocking_fee,
            processed_by_id=cashier_id,
            restocked=False,
            returned_items=returned_items_dict,
            notes=return_data.notes
        )
        
        return_exchange = await self.return_repo.create(return_exchange)
        
        # Create POS transaction for return
        transaction_number = await self.transaction_repo.generate_transaction_number()
        transaction = POSTransaction(
            transaction_number=transaction_number,
            transaction_type=(
                POSTransactionType.EXCHANGE if return_data.is_exchange
                else POSTransactionType.RETURN
            ),
            shift_id=shift.id,
            original_order_id=return_data.original_order_id,
            amount=refund_amount,
            payment_method="cash",  # Assume cash refund
            notes=f"Return: {return_data.reason.value}\n{return_data.notes or ''}".strip()
        )
        
        transaction = await self.transaction_repo.create(transaction)
        
        # Link transaction to return
        return_exchange.pos_transaction_id = transaction.id
        
        # Update shift totals
        await self.shift_repo.update_shift_totals(
            shift.id,
            refund_amount,
            POSTransactionType.EXCHANGE if return_data.is_exchange else POSTransactionType.RETURN,
            "cash"
        )
        
        # Update cash drawer (remove cash for refund)
        if not return_data.is_exchange and refund_amount > Decimal("0.00"):
            drawer = await self.drawer_repo.get_by_shift(shift.id)
            if drawer:
                await self.drawer_repo.update_balance(
                    drawer.id,
                    refund_amount,
                    is_addition=False
                )
        
        # TODO: Restock items if applicable
        
        await self.db.commit()
        await self.db.refresh(return_exchange)
        
        return return_exchange
    
    async def restock_return_items(
        self,
        return_id: UUID,
        location_id: UUID
    ) -> ReturnExchange:
        """Restock items from a return"""
        return_exchange = await self.return_repo.get(return_id)
        if not return_exchange:
            raise ValueError(f"Return {return_id} not found")
        
        if return_exchange.restocked:
            raise ValueError("Items have already been restocked")
        
        # TODO: Implement inventory restocking logic
        # For each item in returned_items where restock=True:
        #   - Create InventoryMovement with type RETURN
        #   - Update InventoryLevel
        
        return_exchange.restocked = True
        await self.db.commit()
        await self.db.refresh(return_exchange)
        
        return return_exchange
    
    # ==================== Analytics ====================
    
    async def get_shift_analytics(self, shift_id: UUID) -> Dict[str, Any]:
        """Get detailed analytics for a shift"""
        shift = await self.shift_repo.get(shift_id)
        if not shift:
            raise ValueError(f"Shift {shift_id} not found")
        
        # Get transaction summary
        summary = await self.transaction_repo.get_shift_summary(shift_id)
        
        # Get transaction counts by type
        transactions = await self.transaction_repo.get_by_shift(shift_id)
        
        sales_count = sum(1 for t in transactions if t.transaction_type == POSTransactionType.SALE)
        returns_count = sum(1 for t in transactions if t.transaction_type == POSTransactionType.RETURN)
        exchanges_count = sum(1 for t in transactions if t.transaction_type == POSTransactionType.EXCHANGE)
        
        # Calculate averages
        average_transaction_value = (
            shift.total_sales / shift.total_transactions
            if shift.total_transactions > 0
            else Decimal("0.00")
        )
        
        return {
            "shift_id": shift.id,
            "shift_number": shift.shift_number,
            "duration_minutes": shift.duration_minutes,
            "total_transactions": shift.total_transactions,
            "sales_count": sales_count,
            "returns_count": returns_count,
            "exchanges_count": exchanges_count,
            "gross_sales": shift.total_sales,
            "net_sales": shift.total_sales - shift.total_returns,
            "total_returns": shift.total_returns,
            "total_exchanges": shift.total_exchanges,
            "cash_amount": shift.cash_sales,
            "card_amount": shift.card_sales,
            "upi_amount": shift.upi_sales,
            "other_amount": shift.other_sales,
            "average_transaction_value": average_transaction_value,
            "opening_cash": shift.opening_cash,
            "expected_cash": shift.expected_cash,
            "closing_cash": shift.closing_cash,
            "cash_variance": shift.cash_variance
        }
