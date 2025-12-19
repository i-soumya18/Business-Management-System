"""
Accounts Payable Module Tests

Comprehensive tests for bills, vendor payments, and expense management.
Tests include:
- Bill CRUD operations
- Bill approval workflow
- Vendor payment processing
- Aging reports
- Expense reports
- Vendor performance metrics
- Bulk operations
"""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance import Bill, VendorPayment, BillStatus, ExpenseCategory, PaymentRecordStatus
from app.models.supplier import Supplier
from app.models.user import User


class TestBillManagement:
    """Test bill CRUD operations and lifecycle"""
    
    @pytest.mark.asyncio
    async def test_create_bill(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_supplier: Supplier
    ):
        """Test creating a new bill"""
        bill_data = {
            "supplier_id": str(test_supplier.id),
            "supplier_bill_number": "SUP-INV-2025-001",
            "description": "Fabric purchase for winter collection",
            "category": "inventory",
            "subtotal": 10000.00,
            "tax_amount": 1800.00,
            "total_amount": 11800.00,
            "bill_date": str(date.today()),
            "due_date": str(date.today() + timedelta(days=30)),
            "payment_terms": "NET_30",
            "notes": "Payment via bank transfer",
            "currency": "INR"
        }
        
        response = await client.post(
            "/api/v1/accounts-payable/bills",
            json=bill_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["supplier_id"] == bill_data["supplier_id"]
        assert data["status"] == "draft"
        assert "bill_number" in data
        assert data["bill_number"].startswith("BILL-")
        assert float(data["total_amount"]) == bill_data["total_amount"]
        assert float(data["balance_due"]) == bill_data["total_amount"]
        assert float(data["paid_amount"]) == 0.0
    
    @pytest.mark.asyncio
    async def test_create_bill_invalid_supplier(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """Test creating bill with invalid supplier"""
        bill_data = {
            "supplier_id": str(uuid4()),
            "description": "Test bill",
            "category": "inventory",
            "subtotal": 1000.00,
            "tax_amount": 180.00,
            "total_amount": 1180.00,
            "bill_date": str(date.today()),
            "due_date": str(date.today() + timedelta(days=30))
        }
        
        response = await client.post(
            "/api/v1/accounts-payable/bills",
            json=bill_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_create_bill_invalid_amounts(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_supplier: Supplier
    ):
        """Test creating bill with mismatched amounts"""
        bill_data = {
            "supplier_id": str(test_supplier.id),
            "description": "Test bill",
            "category": "inventory",
            "subtotal": 1000.00,
            "tax_amount": 180.00,
            "total_amount": 1500.00,  # Doesn't match subtotal + tax
            "bill_date": str(date.today()),
            "due_date": str(date.today() + timedelta(days=30))
        }
        
        response = await client.post(
            "/api/v1/accounts-payable/bills",
            json=bill_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_get_bill_by_id(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_bill: Bill
    ):
        """Test getting bill by ID"""
        response = await client.get(
            f"/api/v1/accounts-payable/bills/{test_bill.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_bill.id)
        assert data["bill_number"] == test_bill.bill_number
        assert "supplier_name" in data
    
    @pytest.mark.asyncio
    async def test_get_bill_by_number(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_bill: Bill
    ):
        """Test getting bill by bill number"""
        response = await client.get(
            f"/api/v1/accounts-payable/bills/by-number/{test_bill.bill_number}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["bill_number"] == test_bill.bill_number
    
    @pytest.mark.asyncio
    async def test_update_bill(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_bill: Bill
    ):
        """Test updating a bill"""
        update_data = {
            "description": "Updated fabric purchase description",
            "notes": "Updated payment instructions"
        }
        
        response = await client.put(
            f"/api/v1/accounts-payable/bills/{test_bill.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == update_data["description"]
        assert update_data["notes"] in data["notes"]
    
    @pytest.mark.asyncio
    async def test_delete_draft_bill(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_bill: Bill
    ):
        """Test deleting a draft bill"""
        response = await client.delete(
            f"/api/v1/accounts-payable/bills/{test_bill.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 204
    
    @pytest.mark.asyncio
    async def test_search_bills(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_supplier: Supplier
    ):
        """Test searching bills with filters"""
        response = await client.get(
            "/api/v1/accounts-payable/bills",
            params={
                "supplier_id": str(test_supplier.id),
                "category": "inventory",
                "skip": 0,
                "limit": 100
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)


class TestBillWorkflow:
    """Test bill approval workflow"""
    
    @pytest.mark.asyncio
    async def test_submit_for_approval(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_bill: Bill
    ):
        """Test submitting bill for approval"""
        response = await client.post(
            f"/api/v1/accounts-payable/bills/{test_bill.id}/submit-for-approval",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
    
    @pytest.mark.asyncio
    async def test_approve_bill(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_pending_bill: Bill
    ):
        """Test approving a pending bill"""
        response = await client.post(
            f"/api/v1/accounts-payable/bills/{test_pending_bill.id}/approve",
            json={"notes": "Approved for payment"},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert data["approved_by_id"] is not None
        assert data["approved_at"] is not None
    
    @pytest.mark.asyncio
    async def test_approve_non_pending_bill(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_bill: Bill
    ):
        """Test approving a non-pending bill fails"""
        response = await client.post(
            f"/api/v1/accounts-payable/bills/{test_bill.id}/approve",
            json={"notes": "Should fail"},
            headers=auth_headers
        )
        
        assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_cancel_bill(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_bill: Bill
    ):
        """Test cancelling a bill"""
        response = await client.post(
            f"/api/v1/accounts-payable/bills/{test_bill.id}/cancel",
            params={"reason": "Supplier invoice cancelled"},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
    
    @pytest.mark.asyncio
    async def test_get_pending_approval_bills(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """Test getting bills pending approval"""
        response = await client.get(
            "/api/v1/accounts-payable/bills/pending-approval",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestVendorPayments:
    """Test vendor payment processing"""
    
    @pytest.mark.asyncio
    async def test_create_payment(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_approved_bill: Bill
    ):
        """Test creating a vendor payment"""
        payment_data = {
            "bill_id": str(test_approved_bill.id),
            "amount": 5000.00,
            "payment_method": "BANK_TRANSFER",
            "payment_date": str(date.today()),
            "transaction_reference": "TXN-2025-001",
            "bank_account": "ACCT-123456",
            "notes": "Partial payment via bank transfer"
        }
        
        response = await client.post(
            "/api/v1/accounts-payable/payments",
            json=payment_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "payment_number" in data
        assert data["payment_number"].startswith("VPAY-")
        assert float(data["amount"]) == payment_data["amount"]
        assert data["status"] == "completed"
        assert data["bill_id"] == payment_data["bill_id"]
    
    @pytest.mark.asyncio
    async def test_create_payment_exceeds_balance(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_approved_bill: Bill
    ):
        """Test creating payment exceeding balance fails"""
        payment_data = {
            "bill_id": str(test_approved_bill.id),
            "amount": float(test_approved_bill.balance_due) + 1000.00,
            "payment_method": "BANK_TRANSFER",
            "payment_date": str(date.today())
        }
        
        response = await client.post(
            "/api/v1/accounts-payable/payments",
            json=payment_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "exceeds balance" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_full_payment_updates_bill_status(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_approved_bill: Bill
    ):
        """Test full payment updates bill to PAID status"""
        payment_data = {
            "bill_id": str(test_approved_bill.id),
            "amount": float(test_approved_bill.balance_due),
            "payment_method": "BANK_TRANSFER",
            "payment_date": str(date.today())
        }
        
        # Create payment
        response = await client.post(
            "/api/v1/accounts-payable/payments",
            json=payment_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        
        # Check bill status
        bill_response = await client.get(
            f"/api/v1/accounts-payable/bills/{test_approved_bill.id}",
            headers=auth_headers
        )
        
        assert bill_response.status_code == 200
        bill_data = bill_response.json()
        assert bill_data["status"] == "paid"
        assert bill_data["paid_date"] is not None
        assert float(bill_data["balance_due"]) < 1.0  # Allow small rounding
    
    @pytest.mark.asyncio
    async def test_partial_payment_updates_bill_status(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_approved_bill: Bill
    ):
        """Test partial payment updates bill to PARTIALLY_PAID status"""
        payment_data = {
            "bill_id": str(test_approved_bill.id),
            "amount": float(test_approved_bill.balance_due) / 2,
            "payment_method": "BANK_TRANSFER",
            "payment_date": str(date.today())
        }
        
        # Create payment
        response = await client.post(
            "/api/v1/accounts-payable/payments",
            json=payment_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        
        # Check bill status
        bill_response = await client.get(
            f"/api/v1/accounts-payable/bills/{test_approved_bill.id}",
            headers=auth_headers
        )
        
        assert bill_response.status_code == 200
        bill_data = bill_response.json()
        assert bill_data["status"] == "partially_paid"
        assert float(bill_data["paid_amount"]) == payment_data["amount"]
    
    @pytest.mark.asyncio
    async def test_get_payment_by_id(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_vendor_payment: VendorPayment
    ):
        """Test getting payment by ID"""
        response = await client.get(
            f"/api/v1/accounts-payable/payments/{test_vendor_payment.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_vendor_payment.id)
        assert "bill_number" in data
        assert "supplier_name" in data
    
    @pytest.mark.asyncio
    async def test_cancel_payment(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_vendor_payment: VendorPayment
    ):
        """Test cancelling a vendor payment"""
        response = await client.post(
            f"/api/v1/accounts-payable/payments/{test_vendor_payment.id}/cancel",
            params={"reason": "Payment reversed by bank"},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
    
    @pytest.mark.asyncio
    async def test_search_payments(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_approved_bill: Bill
    ):
        """Test searching payments"""
        response = await client.get(
            "/api/v1/accounts-payable/payments",
            params={"bill_id": str(test_approved_bill.id)},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
    
    @pytest.mark.asyncio
    async def test_get_payments_by_bill(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_approved_bill: Bill
    ):
        """Test getting payments for a bill"""
        response = await client.get(
            f"/api/v1/accounts-payable/payments/bill/{test_approved_bill.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestReportsAndAnalytics:
    """Test reporting and analytics endpoints"""
    
    @pytest.mark.asyncio
    async def test_aging_report(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """Test aging report generation"""
        response = await client.get(
            "/api/v1/accounts-payable/reports/aging",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "as_of_date" in data
        assert "total_outstanding" in data
        assert "total_overdue" in data
        assert "aging_buckets" in data
        assert "by_supplier" in data
        assert isinstance(data["aging_buckets"], list)
        assert isinstance(data["by_supplier"], list)
    
    @pytest.mark.asyncio
    async def test_expense_report(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """Test expense report generation"""
        response = await client.get(
            "/api/v1/accounts-payable/reports/expenses",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "date_from" in data
        assert "date_to" in data
        assert "total_expenses" in data
        assert "total_paid" in data
        assert "total_outstanding" in data
        assert "by_category" in data
        assert "top_suppliers" in data
        assert isinstance(data["by_category"], list)
        assert isinstance(data["top_suppliers"], list)
    
    @pytest.mark.asyncio
    async def test_vendor_performance(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_supplier: Supplier
    ):
        """Test vendor performance metrics"""
        response = await client.get(
            f"/api/v1/accounts-payable/reports/vendor-performance/{test_supplier.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["supplier_id"] == str(test_supplier.id)
        assert data["supplier_name"] == test_supplier.name
        assert "total_bills" in data
        assert "total_amount" in data
        assert "paid_amount" in data
        assert "outstanding_amount" in data
        assert "draft_count" in data
        assert "pending_count" in data
        assert "approved_count" in data
        assert "paid_count" in data
        assert "overdue_count" in data
    
    @pytest.mark.asyncio
    async def test_dashboard(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """Test dashboard data retrieval"""
        response = await client.get(
            "/api/v1/accounts-payable/dashboard",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total_outstanding" in data
        assert "total_overdue" in data
        assert "bills_due_this_week" in data
        assert "bills_due_this_month" in data
        assert "by_status" in data
        assert "by_category" in data
        assert "aging_summary" in data
        assert "recent_bills_count" in data
        assert "recent_payments_count" in data


class TestBulkOperations:
    """Test bulk operations"""
    
    @pytest.mark.asyncio
    async def test_bulk_approve_bills(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_pending_bills: list
    ):
        """Test bulk bill approval"""
        bill_ids = [str(bill.id) for bill in test_pending_bills[:3]]
        
        response = await client.post(
            "/api/v1/accounts-payable/bills/bulk-approve",
            json={
                "bill_ids": bill_ids,
                "notes": "Bulk approval"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == len(bill_ids)
        assert data["failed_count"] == 0
    
    @pytest.mark.asyncio
    async def test_bulk_update_status(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_bills: list
    ):
        """Test bulk status update"""
        bill_ids = [str(bill.id) for bill in test_bills[:2]]
        
        response = await client.post(
            "/api/v1/accounts-payable/bills/bulk-update-status",
            json={
                "bill_ids": bill_ids,
                "status": "cancelled",
                "notes": "Bulk cancellation"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] >= 0
        assert isinstance(data["failed_ids"], list)


class TestOverdueAndDueSoon:
    """Test overdue and due soon queries"""
    
    @pytest.mark.asyncio
    async def test_get_overdue_bills(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """Test getting overdue bills"""
        response = await client.get(
            "/api/v1/accounts-payable/bills/overdue",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_get_bills_due_soon(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """Test getting bills due soon"""
        response = await client.get(
            "/api/v1/accounts-payable/bills/due-soon",
            params={"days": 7},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_get_bills_by_supplier(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_supplier: Supplier
    ):
        """Test getting bills by supplier"""
        response = await client.get(
            f"/api/v1/accounts-payable/bills/supplier/{test_supplier.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
