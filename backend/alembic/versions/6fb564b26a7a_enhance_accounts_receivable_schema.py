"""enhance accounts receivable schema

Revision ID: 6fb564b26a7a
Revises: 66a4ff390621
Create Date: 2025-12-17 23:23:40.601302

Enhances Accounts Receivable functionality with:
- Added InvoiceItem table for line items
- Added PaymentReminder table for payment reminders
- Enhanced Invoice model with retail customer support
- Enhanced PaymentRecord with customer references
- Enhanced CreditNote with improved tracking
- Added new enums: ReminderType, CreditNoteReason
- Updated indexes and constraints
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '6fb564b26a7a'
down_revision = '66a4ff390621'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create new enum types
    reminder_type = postgresql.ENUM('FRIENDLY', 'FIRST', 'SECOND', 'FINAL', 'LEGAL', name='remindertype', create_type=False)
    reminder_type.create(op.get_bind(), checkfirst=True)
    
    credit_note_reason = postgresql.ENUM(
        'PRODUCT_RETURN', 'DAMAGED_GOODS', 'PRICING_ERROR', 'DISCOUNT_ADJUSTMENT',
        'SERVICE_ISSUE', 'CANCELLATION', 'GOODWILL', 'OTHER',
        name='creditnotereason', create_type=False
    )
    credit_note_reason.create(op.get_bind(), checkfirst=True)
    
    # Update InvoiceStatus enum to include new statuses
    op.execute("ALTER TYPE invoicestatus ADD VALUE IF NOT EXISTS 'PENDING'")
    op.execute("ALTER TYPE invoicestatus ADD VALUE IF NOT EXISTS 'VOID'")
    
    # ==================== Enhance Invoices Table ====================
    
    # Add retail_customer_id column
    op.add_column('invoices', sa.Column('retail_customer_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_invoices_retail_customer',
        'invoices', 'retail_customers',
        ['retail_customer_id'], ['id'],
        ondelete='RESTRICT'
    )
    op.create_index('ix_invoices_customer_retail', 'invoices', ['retail_customer_id', 'status'])
    
    # Rename customer_id to wholesale_customer_id
    op.alter_column('invoices', 'customer_id', new_column_name='wholesale_customer_id')
    
    # Add new columns to invoices
    op.add_column('invoices', sa.Column('customer_tax_id', sa.String(100), nullable=True))
    op.add_column('invoices', sa.Column('billing_address_line1', sa.String(255), nullable=True))
    op.add_column('invoices', sa.Column('billing_address_line2', sa.String(255), nullable=True))
    op.add_column('invoices', sa.Column('billing_city', sa.String(100), nullable=True))
    op.add_column('invoices', sa.Column('billing_state', sa.String(100), nullable=True))
    op.add_column('invoices', sa.Column('billing_postal_code', sa.String(20), nullable=True))
    op.add_column('invoices', sa.Column('billing_country', sa.String(100), nullable=True, server_default='India'))
    op.add_column('invoices', sa.Column('credit_applied', sa.Numeric(15, 2), nullable=False, server_default='0.00'))
    op.add_column('invoices', sa.Column('is_sent', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('invoices', sa.Column('last_reminder_sent_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('invoices', sa.Column('reminders_sent', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('invoices', sa.Column('is_overdue_flag', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('invoices', sa.Column('internal_notes', sa.Text(), nullable=True))
    op.add_column('invoices', sa.Column('reference_number', sa.String(100), nullable=True))
    op.add_column('invoices', sa.Column('additional_data', sa.JSON(), nullable=True))
    
    # Rename metadata to additional_data if it exists
    # op.alter_column('invoices', 'metadata', new_column_name='additional_data')
    
    # Drop old billing_address column and recreate as structured fields
    # Migrate data from old billing_address to new fields
    op.execute("""
        UPDATE invoices 
        SET billing_address_line1 = COALESCE(billing_address, 'N/A'),
            billing_city = 'N/A',
            billing_state = 'N/A',
            billing_postal_code = '000000'
        WHERE billing_address_line1 IS NULL
    """)
    
    # Now make them NOT NULL
    op.alter_column('invoices', 'billing_address_line1', nullable=False)
    op.alter_column('invoices', 'billing_city', nullable=False)
    op.alter_column('invoices', 'billing_state', nullable=False)
    op.alter_column('invoices', 'billing_postal_code', nullable=False)
    
    # Drop old billing_address column if it exists
    try:
        op.drop_column('invoices', 'billing_address')
    except:
        pass
    
    # Rename columns
    try:
        op.alter_column('invoices', 'paid_amount', new_column_name='amount_paid')
    except:
        pass
    
    try:
        op.alter_column('invoices', 'balance_due', new_column_name='amount_due')
    except:
        pass
    
    try:
        op.alter_column('invoices', 'reminder_count', new_column_name='reminders_sent')
    except:
        pass
    
    try:
        op.alter_column('invoices', 'last_reminder_sent', new_column_name='last_reminder_sent_at')
    except:
        pass
    
    # Drop old indexes
    try:
        op.drop_index('idx_invoice_customer_status', 'invoices')
    except:
        pass
    
    # Create new indexes
    op.create_index('ix_invoices_customer_wholesale', 'invoices', ['wholesale_customer_id', 'status'])
    op.create_index('ix_invoices_dates', 'invoices', ['invoice_date', 'due_date'])
    op.create_index('ix_invoices_overdue', 'invoices', ['is_overdue_flag', 'status'])
    
    # Add check constraint
    op.execute("""
        ALTER TABLE invoices 
        ADD CONSTRAINT check_invoice_has_customer 
        CHECK (wholesale_customer_id IS NOT NULL OR retail_customer_id IS NOT NULL)
    """)
    
    # ==================== Create InvoiceItems Table ====================
    
    op.create_table(
        'invoice_items',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('invoice_id', sa.UUID(), nullable=False),
        sa.Column('item_description', sa.String(500), nullable=False),
        sa.Column('sku', sa.String(100), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('unit_price', sa.Numeric(15, 2), nullable=False),
        sa.Column('discount_percentage', sa.Numeric(5, 2), nullable=False, server_default='0.00'),
        sa.Column('discount_amount', sa.Numeric(15, 2), nullable=False, server_default='0.00'),
        sa.Column('tax_rate', sa.Numeric(5, 2), nullable=False, server_default='0.00'),
        sa.Column('tax_amount', sa.Numeric(15, 2), nullable=False, server_default='0.00'),
        sa.Column('line_total', sa.Numeric(15, 2), nullable=False, server_default='0.00'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='CASCADE'),
        sa.CheckConstraint('quantity > 0', name='check_invoice_item_quantity_positive'),
        sa.CheckConstraint('unit_price >= 0', name='check_invoice_item_price_positive')
    )
    
    op.create_index('ix_invoice_items_id', 'invoice_items', ['id'])
    op.create_index('ix_invoice_items_invoice', 'invoice_items', ['invoice_id'])
    
    # ==================== Enhance PaymentRecords Table ====================
    
    # Add customer reference columns
    op.add_column('payment_records', sa.Column('wholesale_customer_id', sa.UUID(), nullable=True))
    op.add_column('payment_records', sa.Column('retail_customer_id', sa.UUID(), nullable=True))
    op.add_column('payment_records', sa.Column('payment_date', sa.Date(), nullable=True, server_default=sa.func.current_date()))
    op.add_column('payment_records', sa.Column('transaction_reference', sa.String(255), nullable=True))
    op.add_column('payment_records', sa.Column('bank_name', sa.String(200), nullable=True))
    op.add_column('payment_records', sa.Column('bank_account_last4', sa.String(4), nullable=True))
    op.add_column('payment_records', sa.Column('cheque_number', sa.String(50), nullable=True))
    op.add_column('payment_records', sa.Column('reference_number', sa.String(100), nullable=True))
    op.add_column('payment_records', sa.Column('additional_data', sa.JSON(), nullable=True))
    op.add_column('payment_records', sa.Column('created_by_id', sa.UUID(), nullable=True))
    
    # Create foreign keys
    op.create_foreign_key(
        'fk_payments_wholesale_customer',
        'payment_records', 'wholesale_customers',
        ['wholesale_customer_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_payments_retail_customer',
        'payment_records', 'retail_customers',
        ['retail_customer_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_payments_created_by',
        'payment_records', 'users',
        ['created_by_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Update payment_date to NOT NULL after setting default
    op.execute("UPDATE payment_records SET payment_date = CURRENT_DATE WHERE payment_date IS NULL")
    op.alter_column('payment_records', 'payment_date', nullable=False)
    
    # Create new indexes
    op.create_index('ix_payments_customer_wholesale', 'payment_records', ['wholesale_customer_id', 'status'])
    op.create_index('ix_payments_customer_retail', 'payment_records', ['retail_customer_id', 'status'])
    op.create_index('ix_payments_reconciliation', 'payment_records', ['is_reconciled', 'payment_date'])
    
    # ==================== Enhance CreditNotes Table ====================
    
    # Add customer reference columns
    op.add_column('credit_notes', sa.Column('wholesale_customer_id', sa.UUID(), nullable=True))
    op.add_column('credit_notes', sa.Column('retail_customer_id', sa.UUID(), nullable=True))
    
    # Rename and add new columns
    try:
        op.alter_column('credit_notes', 'amount', new_column_name='total_amount')
    except:
        pass
    
    op.add_column('credit_notes', sa.Column('amount_used', sa.Numeric(15, 2), nullable=False, server_default='0.00'))
    op.add_column('credit_notes', sa.Column('amount_remaining', sa.Numeric(15, 2), nullable=False, server_default='0.00'))
    op.add_column('credit_notes', sa.Column('is_expired', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('credit_notes', sa.Column('expiry_date', sa.Date(), nullable=True))
    op.add_column('credit_notes', sa.Column('internal_notes', sa.Text(), nullable=True))
    op.add_column('credit_notes', sa.Column('approved_by_id', sa.UUID(), nullable=True))
    op.add_column('credit_notes', sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('credit_notes', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    
    # Change reason_type to use enum
    op.execute("ALTER TABLE credit_notes ALTER COLUMN reason_type TYPE varchar(50)")
    op.execute("ALTER TABLE credit_notes RENAME COLUMN reason_type TO reason")
    op.execute("ALTER TABLE credit_notes ALTER COLUMN reason TYPE creditnotereason USING reason::creditnotereason")
    
    # Update amount_remaining to match total_amount for existing records
    op.execute("UPDATE credit_notes SET amount_remaining = total_amount WHERE amount_remaining = 0")
    
    # Create foreign keys
    op.create_foreign_key(
        'fk_credit_notes_wholesale_customer',
        'credit_notes', 'wholesale_customers',
        ['wholesale_customer_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_credit_notes_retail_customer',
        'credit_notes', 'retail_customers',
        ['retail_customer_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_credit_notes_approved_by',
        'credit_notes', 'users',
        ['approved_by_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Create new indexes
    op.create_index('ix_credit_notes_customer_wholesale', 'credit_notes', ['wholesale_customer_id', 'is_applied'])
    op.create_index('ix_credit_notes_customer_retail', 'credit_notes', ['retail_customer_id', 'is_applied'])
    op.create_index('ix_credit_notes_status', 'credit_notes', ['is_applied', 'is_expired'])
    
    # ==================== Create PaymentReminders Table ====================
    
    op.create_table(
        'payment_reminders',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('invoice_id', sa.UUID(), nullable=False),
        sa.Column('reminder_type', sa.Enum('FRIENDLY', 'FIRST', 'SECOND', 'FINAL', 'LEGAL', name='remindertype'), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('days_overdue', sa.Integer(), nullable=False),
        sa.Column('sent_to_email', sa.String(255), nullable=True),
        sa.Column('sent_to_phone', sa.String(20), nullable=True),
        sa.Column('email_sent', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('sms_sent', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('subject', sa.String(500), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('is_acknowledged', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('customer_response', sa.Text(), nullable=True),
        sa.Column('created_by_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL')
    )
    
    op.create_index('ix_payment_reminders_id', 'payment_reminders', ['id'])
    op.create_index('ix_payment_reminders_invoice_type', 'payment_reminders', ['invoice_id', 'reminder_type'])
    op.create_index('ix_payment_reminders_sent', 'payment_reminders', ['sent_at', 'reminder_type'])


def downgrade() -> None:
    # Drop payment_reminders table
    op.drop_table('payment_reminders')
    
    # Drop invoice_items table
    op.drop_table('invoice_items')
    
    # Revert credit_notes changes
    op.drop_constraint('fk_credit_notes_wholesale_customer', 'credit_notes', type_='foreignkey')
    op.drop_constraint('fk_credit_notes_retail_customer', 'credit_notes', type_='foreignkey')
    op.drop_constraint('fk_credit_notes_approved_by', 'credit_notes', type_='foreignkey')
    op.drop_index('ix_credit_notes_customer_wholesale', 'credit_notes')
    op.drop_index('ix_credit_notes_customer_retail', 'credit_notes')
    op.drop_index('ix_credit_notes_status', 'credit_notes')
    op.drop_column('credit_notes', 'approved_at')
    op.drop_column('credit_notes', 'approved_by_id')
    op.drop_column('credit_notes', 'internal_notes')
    op.drop_column('credit_notes', 'expiry_date')
    op.drop_column('credit_notes', 'is_expired')
    op.drop_column('credit_notes', 'amount_remaining')
    op.drop_column('credit_notes', 'amount_used')
    op.drop_column('credit_notes', 'retail_customer_id')
    op.drop_column('credit_notes', 'wholesale_customer_id')
    
    # Revert payment_records changes
    op.drop_constraint('fk_payments_wholesale_customer', 'payment_records', type_='foreignkey')
    op.drop_constraint('fk_payments_retail_customer', 'payment_records', type_='foreignkey')
    op.drop_constraint('fk_payments_created_by', 'payment_records', type_='foreignkey')
    op.drop_index('ix_payments_customer_wholesale', 'payment_records')
    op.drop_index('ix_payments_customer_retail', 'payment_records')
    op.drop_index('ix_payments_reconciliation', 'payment_records')
    op.drop_column('payment_records', 'created_by_id')
    op.drop_column('payment_records', 'additional_data')
    op.drop_column('payment_records', 'reference_number')
    op.drop_column('payment_records', 'cheque_number')
    op.drop_column('payment_records', 'bank_account_last4')
    op.drop_column('payment_records', 'bank_name')
    op.drop_column('payment_records', 'transaction_reference')
    op.drop_column('payment_records', 'payment_date')
    op.drop_column('payment_records', 'retail_customer_id')
    op.drop_column('payment_records', 'wholesale_customer_id')
    
    # Revert invoices changes
    op.drop_constraint('check_invoice_has_customer', 'invoices')
    op.drop_index('ix_invoices_overdue', 'invoices')
    op.drop_index('ix_invoices_dates', 'invoices')
    op.drop_index('ix_invoices_customer_wholesale', 'invoices')
    op.drop_index('ix_invoices_customer_retail', 'invoices')
    op.drop_constraint('fk_invoices_retail_customer', 'invoices', type_='foreignkey')
    op.drop_column('invoices', 'additional_data')
    op.drop_column('invoices', 'reference_number')
    op.drop_column('invoices', 'internal_notes')
    op.drop_column('invoices', 'is_overdue_flag')
    op.drop_column('invoices', 'reminders_sent')
    op.drop_column('invoices', 'last_reminder_sent_at')
    op.drop_column('invoices', 'is_sent')
    op.drop_column('invoices', 'credit_applied')
    op.drop_column('invoices', 'billing_country')
    op.drop_column('invoices', 'billing_postal_code')
    op.drop_column('invoices', 'billing_state')
    op.drop_column('invoices', 'billing_city')
    op.drop_column('invoices', 'billing_address_line2')
    op.drop_column('invoices', 'billing_address_line1')
    op.drop_column('invoices', 'customer_tax_id')
    op.drop_column('invoices', 'retail_customer_id')
    
    # Drop enums
    op.execute("DROP TYPE IF EXISTS creditnotereason")
    op.execute("DROP TYPE IF EXISTS remindertype")
