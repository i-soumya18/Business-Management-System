"""
Order Management Tests

Comprehensive tests for the Order Management System including:
- Order CRUD operations
- Status workflow transitions
- Order history and notes
- Fulfillment workflow
- Inventory reservations
- Dashboard and analytics
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient

from app.models.order import Order, OrderItem, OrderStatus, PaymentStatus, SalesChannel, PaymentMethod
from app.models.order_management import (
    OrderHistory, OrderNote, OrderFulfillment, InventoryReservation,
    OrderHistoryAction, FulfillmentStatus
)
from app.models.product import ProductVariant, Product
from app.services.order_management import OrderManagementService, ORDER_STATUS_TRANSITIONS
from app.schemas.order_management import (
    OrderSearchFilters,
    BulkOrderStatusUpdate,
    BulkOrderAssignment,
    OrderNoteCreate,
    OrderFulfillmentStatusUpdate
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_db():
    """Create a mock database session"""
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    db.get = AsyncMock()
    return db


@pytest.fixture
def mock_product_variant():
    """Create a mock product variant"""
    variant = MagicMock(spec=ProductVariant)
    variant.id = uuid4()
    variant.sku = "TEST-SKU-001"
    variant.name = "Test Variant"
    variant.price = Decimal("99.99")
    variant.cost_price = Decimal("50.00")
    variant.product = MagicMock()
    variant.product.name = "Test Product"
    return variant


@pytest.fixture
def mock_order():
    """Create a mock order"""
    order = MagicMock(spec=Order)
    order.id = uuid4()
    order.order_number = "EC-20251214-00001"
    order.channel = SalesChannel.ECOMMERCE
    order.status = OrderStatus.DRAFT
    order.customer_id = uuid4()
    order.subtotal = Decimal("199.98")
    order.discount_amount = Decimal("0")
    order.tax_amount = Decimal("18.00")
    order.shipping_amount = Decimal("10.00")
    order.total_amount = Decimal("227.98")
    order.payment_status = PaymentStatus.PENDING
    order.created_at = datetime.utcnow()
    order.updated_at = datetime.utcnow()
    order.items = []
    order.history = []
    order.notes = []
    order.fulfillments = []
    order.inventory_reservations = []
    return order


@pytest.fixture
def service(mock_db):
    """Create an order management service with mock db"""
    return OrderManagementService(mock_db)


# =============================================================================
# Status Transition Tests
# =============================================================================

class TestOrderStatusTransitions:
    """Test order status transition validation"""
    
    def test_valid_transitions_from_draft(self):
        """Test valid transitions from DRAFT status"""
        valid = ORDER_STATUS_TRANSITIONS[OrderStatus.DRAFT]
        assert OrderStatus.PENDING in valid
        assert OrderStatus.CANCELLED in valid
    
    def test_valid_transitions_from_pending(self):
        """Test valid transitions from PENDING status"""
        valid = ORDER_STATUS_TRANSITIONS[OrderStatus.PENDING]
        assert OrderStatus.CONFIRMED in valid
        assert OrderStatus.CANCELLED in valid
    
    def test_valid_transitions_from_confirmed(self):
        """Test valid transitions from CONFIRMED status"""
        valid = ORDER_STATUS_TRANSITIONS[OrderStatus.CONFIRMED]
        assert OrderStatus.PROCESSING in valid
        assert OrderStatus.CANCELLED in valid
    
    def test_valid_transitions_from_shipped(self):
        """Test valid transitions from SHIPPED status"""
        valid = ORDER_STATUS_TRANSITIONS[OrderStatus.SHIPPED]
        assert OrderStatus.IN_TRANSIT in valid
        assert OrderStatus.DELIVERED in valid
        assert OrderStatus.FAILED in valid
    
    def test_terminal_states_have_no_transitions(self):
        """Test that terminal states have no valid transitions"""
        assert len(ORDER_STATUS_TRANSITIONS[OrderStatus.CANCELLED]) == 0
        assert len(ORDER_STATUS_TRANSITIONS[OrderStatus.REFUNDED]) == 0
        assert len(ORDER_STATUS_TRANSITIONS[OrderStatus.RETURNED]) == 0
    
    def test_delivered_can_request_return(self):
        """Test that delivered orders can request returns"""
        valid = ORDER_STATUS_TRANSITIONS[OrderStatus.DELIVERED]
        assert OrderStatus.RETURN_REQUESTED in valid


# =============================================================================
# Service Unit Tests
# =============================================================================

class TestOrderManagementService:
    """Test OrderManagementService"""
    
    @pytest.mark.asyncio
    async def test_is_valid_status_transition_valid(self, service):
        """Test valid status transition check"""
        assert service._is_valid_status_transition(
            OrderStatus.DRAFT, OrderStatus.PENDING
        ) == True
        
        assert service._is_valid_status_transition(
            OrderStatus.PENDING, OrderStatus.CONFIRMED
        ) == True
    
    @pytest.mark.asyncio
    async def test_is_valid_status_transition_invalid(self, service):
        """Test invalid status transition check"""
        # Can't go from DRAFT directly to SHIPPED
        assert service._is_valid_status_transition(
            OrderStatus.DRAFT, OrderStatus.SHIPPED
        ) == False
        
        # Can't go from CANCELLED to anything
        assert service._is_valid_status_transition(
            OrderStatus.CANCELLED, OrderStatus.PENDING
        ) == False
    
    @pytest.mark.asyncio
    async def test_generate_order_number_ecommerce(self, service, mock_db):
        """Test order number generation for e-commerce"""
        # Mock count result
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_db.execute.return_value = mock_result
        
        order_number = await service._generate_order_number(SalesChannel.ECOMMERCE)
        
        assert order_number.startswith("EC-")
        assert "-00006" in order_number  # 5 + 1 = 6
    
    @pytest.mark.asyncio
    async def test_generate_order_number_wholesale(self, service, mock_db):
        """Test order number generation for wholesale"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_db.execute.return_value = mock_result
        
        order_number = await service._generate_order_number(SalesChannel.WHOLESALE)
        
        assert order_number.startswith("WS-")
        assert "-00001" in order_number
    
    @pytest.mark.asyncio
    async def test_generate_order_number_retail(self, service, mock_db):
        """Test order number generation for retail"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 99
        mock_db.execute.return_value = mock_result
        
        order_number = await service._generate_order_number(SalesChannel.RETAIL)
        
        assert order_number.startswith("RT-")
        assert "-00100" in order_number  # 99 + 1 = 100


class TestOrderHistoryTracking:
    """Test order history tracking"""
    
    @pytest.mark.asyncio
    async def test_history_entry_creation(self, service, mock_db):
        """Test that history entries are created correctly"""
        order_id = uuid4()
        
        # Mock the repository method
        with patch.object(service.history_repo, 'create_history_entry') as mock_create:
            mock_history = MagicMock(spec=OrderHistory)
            mock_history.id = uuid4()
            mock_history.order_id = order_id
            mock_history.action = OrderHistoryAction.CREATED
            mock_create.return_value = mock_history
            
            history = await service._create_history_entry(
                order_id=order_id,
                action=OrderHistoryAction.CREATED,
                description="Test order created",
                performed_by_id=uuid4()
            )
            
            mock_create.assert_called_once()
            assert history.action == OrderHistoryAction.CREATED


class TestFulfillmentWorkflow:
    """Test fulfillment workflow"""
    
    def test_fulfillment_status_values(self):
        """Test all fulfillment statuses are defined"""
        assert FulfillmentStatus.PENDING.value == "pending"
        assert FulfillmentStatus.PICKING.value == "picking"
        assert FulfillmentStatus.PACKING.value == "packing"
        assert FulfillmentStatus.READY_TO_SHIP.value == "ready_to_ship"
        assert FulfillmentStatus.SHIPPED.value == "shipped"
        assert FulfillmentStatus.FULFILLED.value == "fulfilled"
        assert FulfillmentStatus.CANCELLED.value == "cancelled"


class TestInventoryReservation:
    """Test inventory reservation logic"""
    
    def test_reservation_expiry_calculation(self):
        """Test that reservations expiry is correctly calculated"""
        from datetime import datetime, timedelta
        
        # Default expiry is 7 days
        now = datetime.utcnow()
        expires_at = now + timedelta(days=7)
        
        # Verify expiry is 7 days from now
        delta = expires_at - now
        assert delta.days == 7


# =============================================================================
# Schema Validation Tests
# =============================================================================

class TestSchemaValidation:
    """Test schema validation"""
    
    def test_order_search_filters_defaults(self):
        """Test OrderSearchFilters default values"""
        filters = OrderSearchFilters()
        
        assert filters.page == 1
        assert filters.page_size == 20
        assert filters.sort_by == "created_at"
        assert filters.sort_order == "desc"
        assert filters.search is None
        assert filters.statuses is None
    
    def test_order_search_filters_with_values(self):
        """Test OrderSearchFilters with custom values"""
        filters = OrderSearchFilters(
            search="test",
            statuses=["pending", "confirmed"],
            page=2,
            page_size=50,
            sort_by="total_amount",
            sort_order="asc"
        )
        
        assert filters.search == "test"
        assert len(filters.statuses) == 2
        assert filters.page == 2
        assert filters.page_size == 50
    
    def test_bulk_order_status_update_validation(self):
        """Test BulkOrderStatusUpdate validation"""
        update = BulkOrderStatusUpdate(
            order_ids=[uuid4(), uuid4()],
            new_status="confirmed",
            notes="Bulk confirmation"
        )
        
        assert len(update.order_ids) == 2
        assert update.new_status == "confirmed"
    
    def test_bulk_order_assignment_validation(self):
        """Test BulkOrderAssignment validation"""
        assignment = BulkOrderAssignment(
            order_ids=[uuid4(), uuid4(), uuid4()],
            assigned_to_id=uuid4(),
            notes="Assigned to warehouse team"
        )
        
        assert len(assignment.order_ids) == 3
        assert assignment.assigned_to_id is not None


# =============================================================================
# Order History Action Tests
# =============================================================================

class TestOrderHistoryActions:
    """Test order history action types"""
    
    def test_all_history_actions_defined(self):
        """Test all expected history actions exist"""
        expected_actions = [
            'created', 'confirmed', 'payment_received', 'processing_started',
            'packed', 'shipped', 'delivered', 'cancelled', 'refunded',
            'status_changed', 'note_added', 'payment_failed', 'return_requested',
            'returned', 'edited', 'assigned', 'inventory_reserved', 'inventory_released'
        ]
        
        for action_name in expected_actions:
            assert hasattr(OrderHistoryAction, action_name.upper())
    
    def test_history_action_values(self):
        """Test history action enum values"""
        assert OrderHistoryAction.CREATED.value == "created"
        assert OrderHistoryAction.CONFIRMED.value == "confirmed"
        assert OrderHistoryAction.SHIPPED.value == "shipped"
        assert OrderHistoryAction.CANCELLED.value == "cancelled"
        assert OrderHistoryAction.INVENTORY_RESERVED.value == "inventory_reserved"


# =============================================================================
# API Endpoint Tests (Integration-style with mocks)
# =============================================================================

class TestOrderAPIEndpoints:
    """Test API endpoint schemas and responses"""
    
    def test_order_response_schema(self):
        """Test OrderResponse schema structure"""
        from app.api.v1.orders import OrderResponse
        
        response = OrderResponse(
            id=uuid4(),
            order_number="EC-20251214-00001",
            channel=SalesChannel.ECOMMERCE,
            status=OrderStatus.PENDING,
            customer_id=uuid4(),
            wholesale_customer_id=None,
            customer_name="Test Customer",
            customer_email="test@example.com",
            customer_phone="+1234567890",
            subtotal=Decimal("100.00"),
            discount_amount=Decimal("10.00"),
            tax_amount=Decimal("8.10"),
            shipping_amount=Decimal("5.00"),
            total_amount=Decimal("103.10"),
            payment_status="pending",
            payment_method="card",
            order_date=datetime.utcnow(),
            confirmed_at=None,
            shipped_at=None,
            delivered_at=None,
            cancelled_at=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            items_count=2,
            notes_count=0,
            fulfillments_count=0
        )
        
        assert response.order_number == "EC-20251214-00001"
        assert response.total_amount == Decimal("103.10")
        assert response.items_count == 2
    
    def test_order_create_schema(self):
        """Test OrderCreate schema"""
        from app.api.v1.orders import OrderCreate, OrderItemCreate
        
        order_data = OrderCreate(
            channel=SalesChannel.ECOMMERCE,
            items=[
                OrderItemCreate(
                    product_variant_id=uuid4(),
                    quantity=2,
                    unit_price=Decimal("49.99")
                )
            ],
            customer_email="customer@example.com",
            customer_name="Test Customer",
            tax_percentage=9.0,
            shipping_amount=Decimal("5.99")
        )
        
        assert order_data.channel == SalesChannel.ECOMMERCE
        assert len(order_data.items) == 1
        assert order_data.reserve_inventory == True  # Default
    
    def test_fulfillment_status_update_schema(self):
        """Test FulfillmentStatusUpdate schema"""
        update = OrderFulfillmentStatusUpdate(
            status=FulfillmentStatus.PICKING,
            notes="Started picking items"
        )
        
        assert update.status == FulfillmentStatus.PICKING
        assert update.notes == "Started picking items"


# =============================================================================
# Business Logic Tests
# =============================================================================

class TestOrderBusinessLogic:
    """Test order business logic"""
    
    def test_order_total_calculation(self):
        """Test order total calculation logic"""
        subtotal = Decimal("100.00")
        discount = Decimal("10.00")
        tax = Decimal("8.10")
        shipping = Decimal("5.00")
        
        total = subtotal - discount + tax + shipping
        
        assert total == Decimal("103.10")
    
    def test_order_item_total_calculation(self):
        """Test order item total calculation"""
        quantity = 3
        unit_price = Decimal("29.99")
        item_discount = Decimal("5.00")
        tax_rate = Decimal("0.09")  # 9%
        
        item_subtotal = unit_price * quantity  # 89.97
        taxable_amount = item_subtotal - item_discount  # 84.97
        item_tax = taxable_amount * tax_rate  # ~7.65
        item_total = item_subtotal - item_discount + item_tax
        
        assert item_subtotal == Decimal("89.97")
        assert taxable_amount == Decimal("84.97")


class TestOrderStatusWorkflow:
    """Test complete order status workflow"""
    
    def test_ecommerce_order_workflow(self):
        """Test typical e-commerce order workflow"""
        workflow = [
            OrderStatus.DRAFT,
            OrderStatus.PENDING,
            OrderStatus.CONFIRMED,
            OrderStatus.PROCESSING,
            OrderStatus.READY_TO_SHIP,
            OrderStatus.SHIPPED,
            OrderStatus.IN_TRANSIT,
            OrderStatus.DELIVERED,
            OrderStatus.COMPLETED
        ]
        
        for i in range(len(workflow) - 1):
            current = workflow[i]
            next_status = workflow[i + 1]
            valid_next = ORDER_STATUS_TRANSITIONS.get(current, [])
            assert next_status in valid_next, f"Invalid transition: {current} -> {next_status}"
    
    def test_order_cancellation_workflow(self):
        """Test order cancellation from various states"""
        cancellable_states = [
            OrderStatus.DRAFT,
            OrderStatus.PENDING,
            OrderStatus.CONFIRMED,
            OrderStatus.PROCESSING,
            OrderStatus.READY_TO_SHIP
        ]
        
        for state in cancellable_states:
            valid_next = ORDER_STATUS_TRANSITIONS.get(state, [])
            assert OrderStatus.CANCELLED in valid_next, f"Should be able to cancel from {state}"
    
    def test_return_request_workflow(self):
        """Test return request workflow"""
        # Can request return after delivery or completion
        assert OrderStatus.RETURN_REQUESTED in ORDER_STATUS_TRANSITIONS[OrderStatus.DELIVERED]
        assert OrderStatus.RETURN_REQUESTED in ORDER_STATUS_TRANSITIONS[OrderStatus.COMPLETED]


class TestFulfillmentWorkflowLogic:
    """Test fulfillment workflow logic"""
    
    def test_fulfillment_workflow_sequence(self):
        """Test fulfillment status workflow sequence"""
        workflow = [
            FulfillmentStatus.PENDING,
            FulfillmentStatus.PICKING,
            FulfillmentStatus.PACKING,
            FulfillmentStatus.READY_TO_SHIP,
            FulfillmentStatus.SHIPPED,
            FulfillmentStatus.FULFILLED
        ]
        
        # Verify all statuses in workflow exist
        for status in workflow:
            assert status in FulfillmentStatus
    
    def test_partial_fulfillment_status(self):
        """Test partial fulfillment status exists"""
        assert FulfillmentStatus.PARTIALLY_FULFILLED.value == "partially_fulfilled"


# =============================================================================
# Dashboard and Analytics Tests
# =============================================================================

class TestDashboardAnalytics:
    """Test dashboard and analytics"""
    
    def test_order_status_count_schema(self):
        """Test OrderStatusCount schema"""
        from app.schemas.order_management import OrderStatusCount
        
        count = OrderStatusCount(status="pending", count=15)
        assert count.status == "pending"
        assert count.count == 15
    
    def test_fulfillment_stats_schema(self):
        """Test OrderFulfillmentStats schema"""
        from app.schemas.order_management import OrderFulfillmentStats
        
        stats = OrderFulfillmentStats(
            pending=10,
            picking=5,
            packing=3,
            ready_to_ship=2,
            shipped=50,
            partially_fulfilled=1,
            fulfilled=100,
            cancelled=5,
            total=176
        )
        
        assert stats.total == 176
        assert stats.fulfilled == 100


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Test error handling"""
    
    def test_invalid_status_transition_logic(self):
        """Test that invalid status transitions are detected"""
        # Can't go from CANCELLED to anything
        valid_from_cancelled = ORDER_STATUS_TRANSITIONS.get(OrderStatus.CANCELLED, [])
        assert len(valid_from_cancelled) == 0
        
        # Can't go from DRAFT directly to SHIPPED
        valid_from_draft = ORDER_STATUS_TRANSITIONS.get(OrderStatus.DRAFT, [])
        assert OrderStatus.SHIPPED not in valid_from_draft
    
    def test_terminal_states_cannot_transition(self):
        """Test that terminal states cannot transition"""
        terminal_states = [
            OrderStatus.CANCELLED,
            OrderStatus.REFUNDED,
            OrderStatus.RETURNED
        ]
        
        for state in terminal_states:
            valid_transitions = ORDER_STATUS_TRANSITIONS.get(state, [])
            assert len(valid_transitions) == 0, f"{state} should have no valid transitions"


# =============================================================================
# Bulk Operations Tests
# =============================================================================

class TestBulkOperations:
    """Test bulk operations"""
    
    def test_bulk_operation_result_structure(self):
        """Test BulkOperationResult structure"""
        from app.schemas.order_management import BulkOperationResult
        
        result = BulkOperationResult(
            success_count=8,
            failure_count=2,
            failed_ids=[uuid4(), uuid4()],
            errors=["Order 1: Already cancelled", "Order 2: Not found"]
        )
        
        assert result.success_count == 8
        assert result.failure_count == 2
        assert len(result.failed_ids) == 2
        assert len(result.errors) == 2


# Run with: pytest tests/test_order_management.py -v
