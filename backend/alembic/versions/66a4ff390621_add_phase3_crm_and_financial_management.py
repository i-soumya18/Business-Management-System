"""Add Phase 3: CRM and Financial Management

Comprehensive migration for Phase 3 including:
- B2B CRM (Leads, Sales Opportunities, Customer Communications, Segmentation)
- B2C CRM (Retail Customers, Loyalty Program, Preferences)
- Financial Management (Invoices, Payments, Bills, Credit Notes)

Revision ID: 66a4ff390621
Revises: h23456789def
Create Date: 2025-12-15 08:27:15.111227

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '66a4ff390621'
down_revision = 'h23456789def'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enums for CRM
    op.execute("""
        CREATE TYPE leadstatus AS ENUM (
            'new', 'contacted', 'qualified', 'proposal_sent', 
            'negotiation', 'converted', 'lost', 'disqualified'
        );
        CREATE TYPE leadsource AS ENUM (
            'website', 'referral', 'trade_show', 'cold_call', 
            'email_campaign', 'social_media', 'partner', 'walk_in', 'other'
        );
        CREATE TYPE leadpriority AS ENUM ('low', 'medium', 'high', 'urgent');
        CREATE TYPE opportunitystage AS ENUM (
            'prospecting', 'qualification', 'needs_analysis', 
            'proposal', 'negotiation', 'closed_won', 'closed_lost'
        );
        CREATE TYPE communicationtype AS ENUM (
            'email', 'phone', 'meeting', 'video_call', 'sms', 
            'whatsapp', 'visit', 'note', 'other'
        );
        CREATE TYPE communicationdirection AS ENUM ('inbound', 'outbound');
        CREATE TYPE customertierlevel AS ENUM ('bronze', 'silver', 'gold', 'platinum');
        CREATE TYPE customerpreferencetype AS ENUM (
            'communication', 'shopping', 'payment', 'delivery', 'marketing'
        );
    """)
    
    # Create enums for Finance
    op.execute("""
        CREATE TYPE invoicestatus AS ENUM (
            'draft', 'sent', 'viewed', 'partially_paid', 
            'paid', 'overdue', 'cancelled', 'refunded'
        );
        CREATE TYPE paymentgateway AS ENUM (
            'razorpay', 'stripe', 'paypal', 'bank_transfer', 'cash', 
            'check', 'upi', 'credit_card', 'debit_card', 'net_banking', 
            'wallet', 'other'
        );
        CREATE TYPE paymentrecordstatus AS ENUM (
            'pending', 'processing', 'completed', 'failed', 
            'refunded', 'partially_refunded', 'cancelled'
        );
        CREATE TYPE billstatus AS ENUM (
            'draft', 'pending', 'approved', 'partially_paid', 
            'paid', 'overdue', 'cancelled'
        );
        CREATE TYPE expensecategory AS ENUM (
            'inventory', 'rent', 'utilities', 'salaries', 'marketing', 
            'shipping', 'office_supplies', 'equipment', 'maintenance', 
            'insurance', 'taxes', 'professional_fees', 'travel', 'other'
        );
    """)
    
    # ===== B2B CRM Tables =====
    
    # 1. Leads Table
    op.create_table(
        'leads',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('lead_number', sa.String(50), nullable=False, unique=True),
        sa.Column('company_name', sa.String(255), nullable=False),
        sa.Column('industry', sa.String(100)),
        sa.Column('company_size', sa.String(50)),
        sa.Column('website', sa.String(255)),
        sa.Column('contact_person', sa.String(255), nullable=False),
        sa.Column('title_position', sa.String(100)),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(20), nullable=False),
        sa.Column('alternate_phone', sa.String(20)),
        sa.Column('address_line1', sa.String(255)),
        sa.Column('address_line2', sa.String(255)),
        sa.Column('city', sa.String(100)),
        sa.Column('state', sa.String(100)),
        sa.Column('postal_code', sa.String(20)),
        sa.Column('country', sa.String(100), nullable=False, server_default='India'),
        sa.Column('status', sa.Enum('leadstatus', name='leadstatus', create_type=False), nullable=False, server_default='new'),
        sa.Column('source', sa.Enum('leadsource', name='leadsource', create_type=False), nullable=False),
        sa.Column('priority', sa.Enum('leadpriority', name='leadpriority', create_type=False), nullable=False, server_default='medium'),
        sa.Column('is_qualified', sa.Boolean, default=False),
        sa.Column('qualification_score', sa.Integer),
        sa.Column('estimated_deal_value', sa.Numeric(15, 2)),
        sa.Column('estimated_close_date', sa.DateTime(timezone=True)),
        sa.Column('requirements', sa.Text),
        sa.Column('notes', sa.Text),
        sa.Column('tags', postgresql.JSON),
        sa.Column('assigned_to_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('converted_to_customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('wholesale_customers.id', ondelete='SET NULL')),
        sa.Column('converted_at', sa.DateTime(timezone=True)),
        sa.Column('next_follow_up_date', sa.DateTime(timezone=True)),
        sa.Column('last_contact_date', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'))
    )
    
    # 2. Sales Opportunities Table
    op.create_table(
        'sales_opportunities',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('opportunity_number', sa.String(50), nullable=False, unique=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('wholesale_customers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('lead_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('leads.id', ondelete='SET NULL')),
        sa.Column('stage', sa.Enum('opportunitystage', name='opportunitystage', create_type=False), nullable=False, server_default='prospecting'),
        sa.Column('estimated_value', sa.Numeric(15, 2), nullable=False, server_default='0.00'),
        sa.Column('probability', sa.Integer, nullable=False, server_default='50'),
        sa.Column('expected_revenue', sa.Numeric(15, 2), nullable=False, server_default='0.00'),
        sa.Column('expected_close_date', sa.DateTime(timezone=True)),
        sa.Column('actual_close_date', sa.DateTime(timezone=True)),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('competitors', sa.Text),
        sa.Column('risks', sa.Text),
        sa.Column('products_interested', postgresql.JSON),
        sa.Column('next_step', sa.Text),
        sa.Column('next_step_date', sa.DateTime(timezone=True)),
        sa.Column('loss_reason', sa.Text),
        sa.Column('tags', postgresql.JSON),
        sa.Column('custom_fields', postgresql.JSON),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint('probability >= 0 AND probability <= 100', name='check_probability_range')
    )
    
    # 3. Customer Communications Table
    op.create_table(
        'customer_communications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('wholesale_customers.id', ondelete='CASCADE')),
        sa.Column('lead_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('leads.id', ondelete='CASCADE')),
        sa.Column('opportunity_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sales_opportunities.id', ondelete='CASCADE')),
        sa.Column('type', sa.Enum('communicationtype', name='communicationtype', create_type=False), nullable=False),
        sa.Column('direction', sa.Enum('communicationdirection', name='communicationdirection', create_type=False), nullable=False),
        sa.Column('subject', sa.String(500), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('contact_person', sa.String(255)),
        sa.Column('our_representative_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('communication_date', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('duration_minutes', sa.Integer),
        sa.Column('requires_follow_up', sa.Boolean, default=False),
        sa.Column('follow_up_date', sa.DateTime(timezone=True)),
        sa.Column('follow_up_completed', sa.Boolean, default=False),
        sa.Column('attachments', postgresql.JSON),
        sa.Column('related_order_id', postgresql.UUID(as_uuid=True)),
        sa.Column('tags', postgresql.JSON),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint(
            "(customer_id IS NOT NULL) OR (lead_id IS NOT NULL) OR (opportunity_id IS NOT NULL)",
            name="check_related_entity_exists"
        )
    )
    
    # 4. Customer Segments Table
    op.create_table(
        'customer_segments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('description', sa.Text),
        sa.Column('code', sa.String(50), nullable=False, unique=True),
        sa.Column('criteria', postgresql.JSON),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('priority', sa.Integer, default=0),
        sa.Column('benefits', postgresql.JSON),
        sa.Column('customer_count', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()'))
    )
    
    # 5. Customer Segment Mapping Table
    op.create_table(
        'customer_segment_mapping',
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('wholesale_customers.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('segment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('customer_segments.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('assigned_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'))
    )
    
    # ===== B2C CRM Tables =====
    
    # 6. Retail Customers Table
    op.create_table(
        'retail_customers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('customer_number', sa.String(50), nullable=False, unique=True),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('phone', sa.String(20), nullable=False),
        sa.Column('alternate_phone', sa.String(20)),
        sa.Column('date_of_birth', sa.Date),
        sa.Column('gender', sa.String(20)),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('is_verified', sa.Boolean, default=False),
        sa.Column('is_email_verified', sa.Boolean, default=False),
        sa.Column('is_phone_verified', sa.Boolean, default=False),
        sa.Column('address_line1', sa.String(255)),
        sa.Column('address_line2', sa.String(255)),
        sa.Column('city', sa.String(100)),
        sa.Column('state', sa.String(100)),
        sa.Column('postal_code', sa.String(20)),
        sa.Column('country', sa.String(100), nullable=False, server_default='India'),
        sa.Column('loyalty_points', sa.Integer, nullable=False, server_default='0'),
        sa.Column('loyalty_points_lifetime', sa.Integer, nullable=False, server_default='0'),
        sa.Column('loyalty_tier', sa.Enum('customertierlevel', name='customertierlevel', create_type=False), nullable=False, server_default='bronze'),
        sa.Column('tier_start_date', sa.Date),
        sa.Column('tier_expiry_date', sa.Date),
        sa.Column('total_orders', sa.Integer, nullable=False, server_default='0'),
        sa.Column('total_spent', sa.Numeric(15, 2), nullable=False, server_default='0.00'),
        sa.Column('average_order_value', sa.Numeric(15, 2), nullable=False, server_default='0.00'),
        sa.Column('first_order_date', sa.DateTime(timezone=True)),
        sa.Column('last_order_date', sa.DateTime(timezone=True)),
        sa.Column('rfm_recency_score', sa.Integer),
        sa.Column('rfm_frequency_score', sa.Integer),
        sa.Column('rfm_monetary_score', sa.Integer),
        sa.Column('rfm_segment', sa.String(50)),
        sa.Column('rfm_last_calculated', sa.DateTime(timezone=True)),
        sa.Column('clv', sa.Numeric(15, 2), nullable=False, server_default='0.00'),
        sa.Column('clv_last_calculated', sa.DateTime(timezone=True)),
        sa.Column('email_open_rate', sa.Numeric(5, 2)),
        sa.Column('email_click_rate', sa.Numeric(5, 2)),
        sa.Column('last_email_sent', sa.DateTime(timezone=True)),
        sa.Column('last_email_opened', sa.DateTime(timezone=True)),
        sa.Column('email_marketing_consent', sa.Boolean, default=True),
        sa.Column('sms_marketing_consent', sa.Boolean, default=True),
        sa.Column('push_notification_consent', sa.Boolean, default=True),
        sa.Column('preferred_categories', postgresql.JSON),
        sa.Column('preferred_brands', postgresql.JSON),
        sa.Column('preferred_sizes', postgresql.JSON),
        sa.Column('preferred_colors', postgresql.JSON),
        sa.Column('preferred_payment_method', sa.String(50)),
        sa.Column('acquisition_source', sa.String(100)),
        sa.Column('acquisition_campaign', sa.String(100)),
        sa.Column('referrer_customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('retail_customers.id', ondelete='SET NULL')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), unique=True),
        sa.Column('notes', sa.Text),
        sa.Column('tags', postgresql.JSON),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('last_activity_at', sa.DateTime(timezone=True)),
        sa.CheckConstraint('loyalty_points >= 0', name='check_loyalty_points_positive'),
        sa.CheckConstraint(
            'rfm_recency_score IS NULL OR (rfm_recency_score >= 1 AND rfm_recency_score <= 5)',
            name='check_rfm_recency_range'
        ),
        sa.CheckConstraint(
            'rfm_frequency_score IS NULL OR (rfm_frequency_score >= 1 AND rfm_frequency_score <= 5)',
            name='check_rfm_frequency_range'
        ),
        sa.CheckConstraint(
            'rfm_monetary_score IS NULL OR (rfm_monetary_score >= 1 AND rfm_monetary_score <= 5)',
            name='check_rfm_monetary_range'
        )
    )
    
    # 7. Loyalty Transactions Table
    op.create_table(
        'loyalty_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('retail_customers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('transaction_type', sa.String(50), nullable=False),
        sa.Column('points', sa.Integer, nullable=False),
        sa.Column('description', sa.String(500), nullable=False),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orders.id', ondelete='SET NULL')),
        sa.Column('balance_before', sa.Integer, nullable=False),
        sa.Column('balance_after', sa.Integer, nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True)),
        sa.Column('metadata', postgresql.JSON),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()'))
    )
    
    # 8. Customer Preferences Table
    op.create_table(
        'customer_preferences',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('retail_customers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('preference_type', sa.Enum('customerpreferencetype', name='customerpreferencetype', create_type=False), nullable=False),
        sa.Column('preference_key', sa.String(100), nullable=False),
        sa.Column('preference_value', sa.Text, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()'))
    )
    
    # ===== Financial Management Tables =====
    
    # 9. Invoices Table
    op.create_table(
        'invoices',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('invoice_number', sa.String(50), nullable=False, unique=True),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orders.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('wholesale_customers.id', ondelete='RESTRICT')),
        sa.Column('customer_name', sa.String(255), nullable=False),
        sa.Column('customer_email', sa.String(255), nullable=False),
        sa.Column('customer_phone', sa.String(20)),
        sa.Column('billing_address', sa.Text, nullable=False),
        sa.Column('status', sa.Enum('invoicestatus', name='invoicestatus', create_type=False), nullable=False, server_default='draft'),
        sa.Column('subtotal', sa.Numeric(15, 2), nullable=False, server_default='0.00'),
        sa.Column('tax_amount', sa.Numeric(15, 2), nullable=False, server_default='0.00'),
        sa.Column('discount_amount', sa.Numeric(15, 2), nullable=False, server_default='0.00'),
        sa.Column('shipping_amount', sa.Numeric(15, 2), nullable=False, server_default='0.00'),
        sa.Column('total_amount', sa.Numeric(15, 2), nullable=False, server_default='0.00'),
        sa.Column('paid_amount', sa.Numeric(15, 2), nullable=False, server_default='0.00'),
        sa.Column('balance_due', sa.Numeric(15, 2), nullable=False, server_default='0.00'),
        sa.Column('tax_rate', sa.Numeric(5, 2)),
        sa.Column('tax_id_number', sa.String(100)),
        sa.Column('invoice_date', sa.Date, nullable=False, server_default=sa.text('CURRENT_DATE')),
        sa.Column('due_date', sa.Date, nullable=False),
        sa.Column('paid_date', sa.Date),
        sa.Column('payment_terms', sa.String(50), nullable=False, server_default='NET_30'),
        sa.Column('payment_terms_days', sa.Integer, nullable=False, server_default='30'),
        sa.Column('sent_at', sa.DateTime(timezone=True)),
        sa.Column('viewed_at', sa.DateTime(timezone=True)),
        sa.Column('last_reminder_sent', sa.DateTime(timezone=True)),
        sa.Column('reminder_count', sa.Integer, default=0),
        sa.Column('notes', sa.Text),
        sa.Column('terms_and_conditions', sa.Text),
        sa.Column('currency', sa.String(3), nullable=False, server_default='INR'),
        sa.Column('metadata', postgresql.JSON),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.CheckConstraint('subtotal >= 0', name='check_invoice_subtotal_positive'),
        sa.CheckConstraint('total_amount >= 0', name='check_invoice_total_positive'),
        sa.CheckConstraint('paid_amount >= 0', name='check_invoice_paid_positive')
    )
    
    # 10. Payment Records Table
    op.create_table(
        'payment_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('payment_number', sa.String(50), nullable=False, unique=True),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('invoices.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='INR'),
        sa.Column('payment_gateway', sa.Enum('paymentgateway', name='paymentgateway', create_type=False), nullable=False),
        sa.Column('status', sa.Enum('paymentrecordstatus', name='paymentrecordstatus', create_type=False), nullable=False, server_default='pending'),
        sa.Column('gateway_transaction_id', sa.String(255)),
        sa.Column('gateway_payment_id', sa.String(255)),
        sa.Column('gateway_order_id', sa.String(255)),
        sa.Column('gateway_response', postgresql.JSON),
        sa.Column('payment_method_type', sa.String(50)),
        sa.Column('payment_method_details', postgresql.JSON),
        sa.Column('is_reconciled', sa.Boolean, default=False),
        sa.Column('reconciled_at', sa.DateTime(timezone=True)),
        sa.Column('reconciled_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('refund_amount', sa.Numeric(15, 2), nullable=False, server_default='0.00'),
        sa.Column('refund_transaction_id', sa.String(255)),
        sa.Column('refunded_at', sa.DateTime(timezone=True)),
        sa.Column('refund_reason', sa.Text),
        sa.Column('gateway_fee', sa.Numeric(15, 2), nullable=False, server_default='0.00'),
        sa.Column('notes', sa.Text),
        sa.Column('internal_notes', sa.Text),
        sa.Column('payment_date', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint('amount > 0', name='check_payment_amount_positive')
    )
    
    # 11. Credit Notes Table
    op.create_table(
        'credit_notes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('credit_note_number', sa.String(50), nullable=False, unique=True),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('invoices.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('reason', sa.Text, nullable=False),
        sa.Column('reason_type', sa.String(50), nullable=False),
        sa.Column('is_applied', sa.Boolean, default=False),
        sa.Column('applied_at', sa.DateTime(timezone=True)),
        sa.Column('issue_date', sa.Date, nullable=False, server_default=sa.text('CURRENT_DATE')),
        sa.Column('notes', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.CheckConstraint('amount > 0', name='check_credit_note_amount_positive')
    )
    
    # 12. Bills Table (Accounts Payable)
    op.create_table(
        'bills',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('bill_number', sa.String(50), nullable=False, unique=True),
        sa.Column('supplier_bill_number', sa.String(100)),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('suppliers.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('category', sa.Enum('expensecategory', name='expensecategory', create_type=False), nullable=False),
        sa.Column('status', sa.Enum('billstatus', name='billstatus', create_type=False), nullable=False, server_default='draft'),
        sa.Column('subtotal', sa.Numeric(15, 2), nullable=False, server_default='0.00'),
        sa.Column('tax_amount', sa.Numeric(15, 2), nullable=False, server_default='0.00'),
        sa.Column('total_amount', sa.Numeric(15, 2), nullable=False, server_default='0.00'),
        sa.Column('paid_amount', sa.Numeric(15, 2), nullable=False, server_default='0.00'),
        sa.Column('balance_due', sa.Numeric(15, 2), nullable=False, server_default='0.00'),
        sa.Column('bill_date', sa.Date, nullable=False, server_default=sa.text('CURRENT_DATE')),
        sa.Column('due_date', sa.Date, nullable=False),
        sa.Column('paid_date', sa.Date),
        sa.Column('payment_terms', sa.String(50), nullable=False, server_default='NET_30'),
        sa.Column('approved_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('approved_at', sa.DateTime(timezone=True)),
        sa.Column('attachments', postgresql.JSON),
        sa.Column('notes', sa.Text),
        sa.Column('currency', sa.String(3), nullable=False, server_default='INR'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.CheckConstraint('subtotal >= 0', name='check_bill_subtotal_positive'),
        sa.CheckConstraint('total_amount >= 0', name='check_bill_total_positive')
    )
    
    # 13. Vendor Payments Table
    op.create_table(
        'vendor_payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('payment_number', sa.String(50), nullable=False, unique=True),
        sa.Column('bill_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('bills.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('payment_method', sa.String(50), nullable=False),
        sa.Column('transaction_reference', sa.String(255)),
        sa.Column('bank_account', sa.String(100)),
        sa.Column('check_number', sa.String(50)),
        sa.Column('status', sa.Enum('paymentrecordstatus', name='paymentrecordstatus', create_type=False), nullable=False, server_default='pending'),
        sa.Column('payment_date', sa.Date, nullable=False, server_default=sa.text('CURRENT_DATE')),
        sa.Column('notes', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.CheckConstraint('amount > 0', name='check_vendor_payment_amount_positive')
    )
    
    # Create all indexes
    create_indexes()


def create_indexes():
    """Create all indexes for Phase 3 tables"""
    
    # Leads indexes
    op.create_index('idx_lead_lead_number', 'leads', ['lead_number'])
    op.create_index('idx_lead_company_name', 'leads', ['company_name'])
    op.create_index('idx_lead_email', 'leads', ['email'])
    op.create_index('idx_lead_city', 'leads', ['city'])
    op.create_index('idx_lead_status', 'leads', ['status'])
    op.create_index('idx_lead_status_priority', 'leads', ['status', 'priority'])
    op.create_index('idx_lead_assigned_status', 'leads', ['assigned_to_id', 'status'])
    op.create_index('idx_lead_created_at', 'leads', ['created_at'])
    
    # Sales Opportunities indexes
    op.create_index('idx_opportunity_number', 'sales_opportunities', ['opportunity_number'])
    op.create_index('idx_opportunity_customer_id', 'sales_opportunities', ['customer_id'])
    op.create_index('idx_opportunity_stage', 'sales_opportunities', ['stage'])
    op.create_index('idx_opportunity_customer_stage', 'sales_opportunities', ['customer_id', 'stage'])
    op.create_index('idx_opportunity_owner_stage', 'sales_opportunities', ['owner_id', 'stage'])
    op.create_index('idx_opportunity_expected_close', 'sales_opportunities', ['expected_close_date'])
    op.create_index('idx_opportunity_created_at', 'sales_opportunities', ['created_at'])
    
    # Customer Communications indexes
    op.create_index('idx_comm_customer_id', 'customer_communications', ['customer_id'])
    op.create_index('idx_comm_lead_id', 'customer_communications', ['lead_id'])
    op.create_index('idx_comm_opportunity_id', 'customer_communications', ['opportunity_id'])
    op.create_index('idx_comm_type', 'customer_communications', ['type'])
    op.create_index('idx_comm_customer_date', 'customer_communications', ['customer_id', 'communication_date'])
    op.create_index('idx_comm_lead_date', 'customer_communications', ['lead_id', 'communication_date'])
    op.create_index('idx_comm_opportunity_date', 'customer_communications', ['opportunity_id', 'communication_date'])
    op.create_index('idx_comm_rep_date', 'customer_communications', ['our_representative_id', 'communication_date'])
    op.create_index('idx_comm_follow_up', 'customer_communications', ['requires_follow_up', 'follow_up_date'])
    
    # Customer Segments indexes
    op.create_index('idx_segment_mapping_customer', 'customer_segment_mapping', ['customer_id'])
    op.create_index('idx_segment_mapping_segment', 'customer_segment_mapping', ['segment_id'])
    
    # Retail Customers indexes
    op.create_index('idx_retail_customer_number', 'retail_customers', ['customer_number'])
    op.create_index('idx_retail_customer_email', 'retail_customers', ['email'])
    op.create_index('idx_retail_customer_phone', 'retail_customers', ['phone'])
    op.create_index('idx_retail_customer_city', 'retail_customers', ['city'])
    op.create_index('idx_retail_customer_is_active', 'retail_customers', ['is_active'])
    op.create_index('idx_retail_customer_tier', 'retail_customers', ['loyalty_tier'])
    op.create_index('idx_retail_customer_rfm_segment', 'retail_customers', ['rfm_segment'])
    op.create_index('idx_retail_customer_last_order', 'retail_customers', ['last_order_date'])
    op.create_index('idx_retail_customer_created_at', 'retail_customers', ['created_at'])
    
    # Loyalty Transactions indexes
    op.create_index('idx_loyalty_txn_customer_id', 'loyalty_transactions', ['customer_id'])
    op.create_index('idx_loyalty_txn_customer_date', 'loyalty_transactions', ['customer_id', 'created_at'])
    op.create_index('idx_loyalty_txn_type', 'loyalty_transactions', ['transaction_type'])
    
    # Customer Preferences indexes
    op.create_index('idx_customer_pref_customer_id', 'customer_preferences', ['customer_id'])
    op.create_index('idx_customer_pref_customer_type', 'customer_preferences', ['customer_id', 'preference_type'])
    op.create_index('idx_customer_pref_key', 'customer_preferences', ['preference_key'])
    
    # Invoices indexes
    op.create_index('idx_invoice_number', 'invoices', ['invoice_number'])
    op.create_index('idx_invoice_order_id', 'invoices', ['order_id'])
    op.create_index('idx_invoice_customer_id', 'invoices', ['customer_id'])
    op.create_index('idx_invoice_status', 'invoices', ['status'])
    op.create_index('idx_invoice_total_amount', 'invoices', ['total_amount'])
    op.create_index('idx_invoice_customer_status', 'invoices', ['customer_id', 'status'])
    op.create_index('idx_invoice_due_date_status', 'invoices', ['due_date', 'status'])
    op.create_index('idx_invoice_created_at', 'invoices', ['created_at'])
    op.create_index('idx_invoice_invoice_date', 'invoices', ['invoice_date'])
    
    # Payment Records indexes
    op.create_index('idx_payment_number', 'payment_records', ['payment_number'])
    op.create_index('idx_payment_invoice_id', 'payment_records', ['invoice_id'])
    op.create_index('idx_payment_gateway', 'payment_records', ['payment_gateway'])
    op.create_index('idx_payment_status', 'payment_records', ['status'])
    op.create_index('idx_payment_invoice_status', 'payment_records', ['invoice_id', 'status'])
    op.create_index('idx_payment_gateway_txn', 'payment_records', ['gateway_transaction_id'])
    op.create_index('idx_payment_date', 'payment_records', ['payment_date'])
    op.create_index('idx_payment_reconciled', 'payment_records', ['is_reconciled'])
    
    # Credit Notes indexes
    op.create_index('idx_credit_note_number', 'credit_notes', ['credit_note_number'])
    op.create_index('idx_credit_note_invoice', 'credit_notes', ['invoice_id'])
    op.create_index('idx_credit_note_date', 'credit_notes', ['issue_date'])
    
    # Bills indexes
    op.create_index('idx_bill_number', 'bills', ['bill_number'])
    op.create_index('idx_bill_supplier_id', 'bills', ['supplier_id'])
    op.create_index('idx_bill_status', 'bills', ['status'])
    op.create_index('idx_bill_category', 'bills', ['category'])
    op.create_index('idx_bill_supplier_status', 'bills', ['supplier_id', 'status'])
    op.create_index('idx_bill_due_date_status', 'bills', ['due_date', 'status'])
    op.create_index('idx_bill_bill_date', 'bills', ['bill_date'])
    
    # Vendor Payments indexes
    op.create_index('idx_vendor_payment_number', 'vendor_payments', ['payment_number'])
    op.create_index('idx_vendor_payment_bill', 'vendor_payments', ['bill_id'])
    op.create_index('idx_vendor_payment_date', 'vendor_payments', ['payment_date'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('vendor_payments')
    op.drop_table('bills')
    op.drop_table('credit_notes')
    op.drop_table('payment_records')
    op.drop_table('invoices')
    op.drop_table('customer_preferences')
    op.drop_table('loyalty_transactions')
    op.drop_table('retail_customers')
    op.drop_table('customer_segment_mapping')
    op.drop_table('customer_segments')
    op.drop_table('customer_communications')
    op.drop_table('sales_opportunities')
    op.drop_table('leads')
    
    # Drop enums
    op.execute("""
        DROP TYPE IF EXISTS expensecategory;
        DROP TYPE IF EXISTS billstatus;
        DROP TYPE IF EXISTS paymentrecordstatus;
        DROP TYPE IF EXISTS paymentgateway;
        DROP TYPE IF EXISTS invoicestatus;
        DROP TYPE IF EXISTS customerpreferencetype;
        DROP TYPE IF EXISTS customertierlevel;
        DROP TYPE IF EXISTS communicationdirection;
        DROP TYPE IF EXISTS communicationtype;
        DROP TYPE IF EXISTS opportunitystage;
        DROP TYPE IF EXISTS leadpriority;
        DROP TYPE IF EXISTS leadsource;
        DROP TYPE IF EXISTS leadstatus;
    """)
