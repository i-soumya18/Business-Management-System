"""add order management models

Revision ID: 8408ea989a51
Revises: d9d7f43815fe
Create Date: 2025-12-14 10:27:24.297338

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON


# revision identifiers, used by Alembic.
revision = '8408ea989a51'
down_revision = 'd9d7f43815fe'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enums will be created automatically by SQLAlchemy when creating the tables
    
    # Create order_history table
    op.create_table(
        'order_history',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('order_id', UUID(as_uuid=True), nullable=False),
        sa.Column('action', sa.Enum('created', 'confirmed', 'payment_received', 'processing_started',
                                     'packed', 'shipped', 'delivered', 'cancelled', 'refunded',
                                     'status_changed', 'note_added', 'payment_failed', 'return_requested',
                                     'returned', 'edited', 'assigned', 'inventory_reserved', 'inventory_released',
                                     name='orderhistoryaction'), nullable=False),
        sa.Column('old_status', sa.String(50), nullable=True),
        sa.Column('new_status', sa.String(50), nullable=True),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('performed_by_id', UUID(as_uuid=True), nullable=True),
        sa.Column('additional_data', JSON, nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['performed_by_id'], ['users.id'], ondelete='SET NULL'),
    )
    
    # Create indexes for order_history
    op.create_index('idx_order_history_order_date', 'order_history', ['order_id', 'created_at'])
    op.create_index('idx_order_history_action', 'order_history', ['action'])
    op.create_index('ix_order_history_id', 'order_history', ['id'])
    op.create_index('ix_order_history_order_id', 'order_history', ['order_id'])
    op.create_index('ix_order_history_performed_by_id', 'order_history', ['performed_by_id'])
    op.create_index('ix_order_history_created_at', 'order_history', ['created_at'])
    
    # Create order_notes table
    op.create_table(
        'order_notes',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('order_id', UUID(as_uuid=True), nullable=False),
        sa.Column('note', sa.Text, nullable=False),
        sa.Column('is_internal', sa.Boolean, default=True, nullable=False),
        sa.Column('notify_customer', sa.Boolean, default=False, nullable=False),
        sa.Column('notified_at', sa.DateTime, nullable=True),
        sa.Column('created_by_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
    )
    
    # Create indexes for order_notes
    op.create_index('idx_order_note_order_date', 'order_notes', ['order_id', 'created_at'])
    op.create_index('ix_order_notes_id', 'order_notes', ['id'])
    op.create_index('ix_order_notes_order_id', 'order_notes', ['order_id'])
    op.create_index('ix_order_notes_created_by_id', 'order_notes', ['created_by_id'])
    op.create_index('ix_order_notes_created_at', 'order_notes', ['created_at'])
    
    # Create order_fulfillments table
    op.create_table(
        'order_fulfillments',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('order_id', UUID(as_uuid=True), nullable=False),
        sa.Column('fulfillment_number', sa.String(50), nullable=False, unique=True),
        sa.Column('status', sa.Enum('pending', 'picking', 'packing', 'ready_to_ship', 'shipped',
                                     'partially_fulfilled', 'fulfilled', 'cancelled',
                                     name='fulfillmentstatus'), default='pending', nullable=False),
        sa.Column('warehouse_location', sa.String(100), nullable=True),
        sa.Column('assigned_to_id', UUID(as_uuid=True), nullable=True),
        sa.Column('items', JSON, nullable=False),
        sa.Column('box_size', sa.String(50), nullable=True),
        sa.Column('weight', sa.String(20), nullable=True),
        sa.Column('packing_materials', JSON, nullable=True),
        sa.Column('picking_notes', sa.Text, nullable=True),
        sa.Column('packing_notes', sa.Text, nullable=True),
        sa.Column('assigned_at', sa.DateTime, nullable=True),
        sa.Column('picking_started_at', sa.DateTime, nullable=True),
        sa.Column('picking_completed_at', sa.DateTime, nullable=True),
        sa.Column('packing_started_at', sa.DateTime, nullable=True),
        sa.Column('packing_completed_at', sa.DateTime, nullable=True),
        sa.Column('shipped_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_to_id'], ['users.id'], ondelete='SET NULL'),
    )
    
    # Create indexes for order_fulfillments
    op.create_index('idx_fulfillment_order', 'order_fulfillments', ['order_id'])
    op.create_index('idx_fulfillment_status', 'order_fulfillments', ['status'])
    op.create_index('idx_fulfillment_assigned', 'order_fulfillments', ['assigned_to_id'])
    op.create_index('ix_order_fulfillments_id', 'order_fulfillments', ['id'])
    op.create_index('ix_order_fulfillments_fulfillment_number', 'order_fulfillments', ['fulfillment_number'])
    
    # Create inventory_reservations table
    op.create_table(
        'inventory_reservations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('order_id', UUID(as_uuid=True), nullable=False),
        sa.Column('order_item_id', UUID(as_uuid=True), nullable=False),
        sa.Column('product_variant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('stock_location_id', UUID(as_uuid=True), nullable=True),
        sa.Column('quantity_reserved', sa.String(20), nullable=False),
        sa.Column('quantity_fulfilled', sa.String(20), default='0', nullable=False),
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        sa.Column('expires_at', sa.DateTime, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('reserved_at', sa.DateTime, nullable=False),
        sa.Column('released_at', sa.DateTime, nullable=True),
        sa.Column('fulfilled_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['order_item_id'], ['order_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_variant_id'], ['product_variants.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['stock_location_id'], ['stock_locations.id'], ondelete='SET NULL'),
    )
    
    # Create indexes for inventory_reservations
    op.create_index('idx_reservation_order', 'inventory_reservations', ['order_id'])
    op.create_index('idx_reservation_variant', 'inventory_reservations', ['product_variant_id'])
    op.create_index('idx_reservation_active', 'inventory_reservations', ['is_active', 'expires_at'])
    op.create_index('ix_inventory_reservations_id', 'inventory_reservations', ['id'])
    op.create_index('ix_inventory_reservations_order_id', 'inventory_reservations', ['order_id'])
    op.create_index('ix_inventory_reservations_order_item_id', 'inventory_reservations', ['order_item_id'])
    op.create_index('ix_inventory_reservations_product_variant_id', 'inventory_reservations', ['product_variant_id'])
    op.create_index('ix_inventory_reservations_stock_location_id', 'inventory_reservations', ['stock_location_id'])
    op.create_index('ix_inventory_reservations_is_active', 'inventory_reservations', ['is_active'])
    op.create_index('ix_inventory_reservations_expires_at', 'inventory_reservations', ['expires_at'])
    op.create_index('ix_inventory_reservations_reserved_at', 'inventory_reservations', ['reserved_at'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('inventory_reservations')
    op.drop_table('order_fulfillments')
    op.drop_table('order_notes')
    op.drop_table('order_history')
    
    # Drop enums
    sa.Enum(name='fulfillmentstatus').drop(op.get_bind())
    sa.Enum(name='orderhistoryaction').drop(op.get_bind())
