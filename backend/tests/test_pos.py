"""
Tests for POS (Point of Sale) Module

Basic tests for cashier shifts, transactions, and return/exchange functionality.
"""

import pytest
from decimal import Decimal
from uuid import uuid4

from app.models.pos import (
    CashierShift,
    CashDrawer,
    POSTransaction,
    ReturnExchange,
    ShiftStatus,
    CashDrawerStatus,
    POSTransactionType
)


class TestPOSBasics:
    """Basic POS model tests"""
    
    def test_create_cashier_shift(self):
        """Test creating a cashier shift"""
        shift = CashierShift(
            shift_number="SH-20231214-0001",
            cashier_id=uuid4(),
            register_number="POS-01",
            opening_cash=Decimal("500.00"),
            status=ShiftStatus.ACTIVE
        )
        
        assert shift.shift_number == "SH-20231214-0001"
        assert shift.register_number == "POS-01"
        assert shift.opening_cash == Decimal("500.00")
        assert shift.status == ShiftStatus.ACTIVE
        assert shift.total_transactions == 0
        assert shift.total_sales == Decimal("0.00")
    
    def test_shift_cash_calculation(self):
        """Test shift cash calculations"""
        shift = CashierShift(
            shift_number="SH-20231214-0002",
            cashier_id=uuid4(),
            register_number="POS-02",
            opening_cash=Decimal("300.00"),
            status=ShiftStatus.ACTIVE
        )
        
        # Add some sales
        shift.cash_sales = Decimal("1200.00")
        shift.total_returns = Decimal("50.00")
        
        # Calculate expected cash
        expected = shift.calculate_expected_cash()
        
        assert expected == Decimal("1450.00")  # 300 + 1200 - 50
    
    def test_close_shift(self):
        """Test closing a shift"""
        shift = CashierShift(
            shift_number="SH-20231214-0003",
            cashier_id=uuid4(),
            register_number="POS-03",
            opening_cash=Decimal("400.00"),
            status=ShiftStatus.ACTIVE,
            cash_sales=Decimal("800.00"),
            total_returns=Decimal("20.00")
        )
        
        # Close shift with actual cash count
        shift.close_shift(Decimal("1185.00"))
        
        assert shift.status == ShiftStatus.CLOSED
        assert shift.ended_at is not None
        assert shift.closing_cash == Decimal("1185.00")
        assert shift.expected_cash == Decimal("1180.00")  # 400 + 800 - 20
        assert shift.cash_variance == Decimal("5.00")  # 1185 - 1180
    
    def test_cash_drawer_creation(self):
        """Test creating a cash drawer"""
        drawer = CashDrawer(
            shift_id=uuid4(),
            status=CashDrawerStatus.OPEN,
            current_balance=Decimal("500.00")
        )
        
        assert drawer.status == CashDrawerStatus.OPEN
        assert drawer.current_balance == Decimal("500.00")
    
    def test_pos_transaction_creation(self):
        """Test creating a POS transaction"""
        transaction = POSTransaction(
            transaction_number="TXN-20231214-000001",
            transaction_type=POSTransactionType.SALE,
            shift_id=uuid4(),
            amount=Decimal("125.50"),
            payment_method="cash"
        )
        
        assert transaction.transaction_number == "TXN-20231214-000001"
        assert transaction.transaction_type == POSTransactionType.SALE
        assert transaction.amount == Decimal("125.50")
        assert transaction.payment_method == "cash"
        assert transaction.receipt_generated is False
    
    def test_return_exchange_creation(self):
        """Test creating a return/exchange"""
        return_exchange = ReturnExchange(
            return_number="RTN-20231214-00001",
            is_exchange=False,
            original_order_id=uuid4(),
            processed_by_id=uuid4(),
            reason="DEFECTIVE",
            refund_amount=Decimal("75.00"),
            restocking_fee=Decimal("5.00"),
            returned_items={"item1": {"quantity": 1}},
            restocked=False
        )
        
        assert return_exchange.return_number == "RTN-20231214-00001"
        assert return_exchange.is_exchange is False
        assert return_exchange.refund_amount == Decimal("75.00")
        assert return_exchange.restocking_fee == Decimal("5.00")
        assert return_exchange.restocked is False


class TestShiftWorkflow:
    """Test complete shift workflow"""
    
    def test_shift_lifecycle(self):
        """Test full shift lifecycle: open -> sales -> close -> reconcile"""
        # Start shift
        shift = CashierShift(
            shift_number="SH-20231214-0100",
            cashier_id=uuid4(),
            register_number="POS-10",
            opening_cash=Decimal("500.00"),
            status=ShiftStatus.ACTIVE
        )
        
        assert shift.status == ShiftStatus.ACTIVE
        
        # Process transactions
        shift.total_transactions = 15
        shift.total_sales = Decimal("2500.00")
        shift.cash_sales = Decimal("1200.00")
        shift.card_sales = Decimal("800.00")
        shift.upi_sales = Decimal("500.00")
        shift.total_returns = Decimal("100.00")
        
        # Close shift
        shift.close_shift(Decimal("1605.00"))  # 500 + 1200 - 100 = 1600, +5 variance
        
        assert shift.status == ShiftStatus.CLOSED
        assert shift.closing_cash == Decimal("1605.00")
        assert shift.expected_cash == Decimal("1600.00")
        assert shift.cash_variance == Decimal("5.00")
        
        # Reconcile shift
        shift.status = ShiftStatus.RECONCILED
        shift.reconciliation_notes = "Shift reconciled, minor variance approved"
        
        assert shift.status == ShiftStatus.RECONCILED


class TestCashDrawerOperations:
    """Test cash drawer operations"""
    
    def test_cash_drawer_balance(self):
        """Test cash drawer balance updates"""
        drawer = CashDrawer(
            shift_id=uuid4(),
            status=CashDrawerStatus.OPEN,
            current_balance=Decimal("500.00")
        )
        
        # Add cash (sale)
        drawer.current_balance += Decimal("125.50")
        assert drawer.current_balance == Decimal("625.50")
        
        # Remove cash (refund)
        drawer.current_balance -= Decimal("25.00")
        assert drawer.current_balance == Decimal("600.50")
        
        # Close drawer
        drawer.status = CashDrawerStatus.BALANCED
        assert drawer.status == CashDrawerStatus.BALANCED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
