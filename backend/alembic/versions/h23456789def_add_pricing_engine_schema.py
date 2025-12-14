"""Add pricing engine schema

Revision ID: h23456789def
Revises: 8408ea989a51
Create Date: 2025-12-14 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'h23456789def'
down_revision = '8408ea989a51'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create pricing_rules table
    op.create_table(
        'pricing_rules',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('rule_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('discount_type', sa.String(50), nullable=False),
        sa.Column('discount_value', sa.Numeric(15, 4), nullable=False),
        sa.Column('max_discount_amount', sa.Numeric(15, 2), nullable=True),
        sa.Column('min_price', sa.Numeric(15, 2), nullable=True),
        sa.Column('applicable_channels', sa.JSON(), nullable=True),
        sa.Column('applicable_customer_tiers', sa.JSON(), nullable=True),
        sa.Column('start_date', sa.DateTime(), nullable=True),
        sa.Column('end_date', sa.DateTime(), nullable=True),
        sa.Column('start_time', sa.String(10), nullable=True),
        sa.Column('end_time', sa.String(10), nullable=True),
        sa.Column('applicable_days', sa.JSON(), nullable=True),
        sa.Column('min_quantity', sa.Integer(), nullable=True),
        sa.Column('max_quantity', sa.Integer(), nullable=True),
        sa.Column('min_order_value', sa.Numeric(15, 2), nullable=True),
        sa.Column('max_order_value', sa.Numeric(15, 2), nullable=True),
        sa.Column('buy_quantity', sa.Integer(), nullable=True),
        sa.Column('get_quantity', sa.Integer(), nullable=True),
        sa.Column('get_discount_percentage', sa.Numeric(5, 2), nullable=True),
        sa.Column('max_uses', sa.Integer(), nullable=True),
        sa.Column('current_uses', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_uses_per_customer', sa.Integer(), nullable=True),
        sa.Column('is_stackable', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_exclusive', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('conditions', sa.JSON(), nullable=True),
        sa.Column('created_by_id', sa.UUID(), nullable=True),
        sa.Column('updated_by_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_pricing_rules_id', 'pricing_rules', ['id'])
    op.create_index('ix_pricing_rules_code', 'pricing_rules', ['code'], unique=True)
    op.create_index('ix_pricing_rules_rule_type', 'pricing_rules', ['rule_type'])
    op.create_index('ix_pricing_rules_status', 'pricing_rules', ['status'])
    op.create_index('ix_pricing_rules_priority', 'pricing_rules', ['priority'])
    op.create_index('ix_pricing_rules_start_date', 'pricing_rules', ['start_date'])
    op.create_index('ix_pricing_rules_end_date', 'pricing_rules', ['end_date'])
    op.create_index('ix_pricing_rules_type_status', 'pricing_rules', ['rule_type', 'status'])
    op.create_index('ix_pricing_rules_priority_status', 'pricing_rules', ['priority', 'status'])
    op.create_index('ix_pricing_rules_dates', 'pricing_rules', ['start_date', 'end_date'])
    
    # Create pricing_rule_products table
    op.create_table(
        'pricing_rule_products',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('pricing_rule_id', sa.UUID(), nullable=False),
        sa.Column('product_id', sa.UUID(), nullable=True),
        sa.Column('product_variant_id', sa.UUID(), nullable=True),
        sa.Column('is_excluded', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('override_discount_value', sa.Numeric(15, 4), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['pricing_rule_id'], ['pricing_rules.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_variant_id'], ['product_variants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('(product_id IS NOT NULL) OR (product_variant_id IS NOT NULL)', name='check_product_or_variant')
    )
    op.create_index('ix_pricing_rule_products_pricing_rule_id', 'pricing_rule_products', ['pricing_rule_id'])
    op.create_index('ix_pricing_rule_products_product_id', 'pricing_rule_products', ['product_id'])
    op.create_index('ix_pricing_rule_products_product_variant_id', 'pricing_rule_products', ['product_variant_id'])
    op.create_index('ix_pricing_rule_products_rule_product', 'pricing_rule_products', ['pricing_rule_id', 'product_id'])
    op.create_index('ix_pricing_rule_products_rule_variant', 'pricing_rule_products', ['pricing_rule_id', 'product_variant_id'])
    
    # Create pricing_rule_categories table
    op.create_table(
        'pricing_rule_categories',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('pricing_rule_id', sa.UUID(), nullable=False),
        sa.Column('category_id', sa.UUID(), nullable=False),
        sa.Column('include_subcategories', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_excluded', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['pricing_rule_id'], ['pricing_rules.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_pricing_rule_categories_pricing_rule_id', 'pricing_rule_categories', ['pricing_rule_id'])
    op.create_index('ix_pricing_rule_categories_category_id', 'pricing_rule_categories', ['category_id'])
    op.create_index('ix_pricing_rule_categories_rule_cat', 'pricing_rule_categories', ['pricing_rule_id', 'category_id'])
    
    # Create pricing_rule_customers table
    op.create_table(
        'pricing_rule_customers',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('pricing_rule_id', sa.UUID(), nullable=False),
        sa.Column('wholesale_customer_id', sa.UUID(), nullable=True),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('override_discount_value', sa.Numeric(15, 4), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['pricing_rule_id'], ['pricing_rules.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['wholesale_customer_id'], ['wholesale_customers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_pricing_rule_customers_pricing_rule_id', 'pricing_rule_customers', ['pricing_rule_id'])
    op.create_index('ix_pricing_rule_customers_wholesale_customer_id', 'pricing_rule_customers', ['wholesale_customer_id'])
    op.create_index('ix_pricing_rule_customers_user_id', 'pricing_rule_customers', ['user_id'])
    op.create_index('ix_pricing_rule_customers_rule_wholesale', 'pricing_rule_customers', ['pricing_rule_id', 'wholesale_customer_id'])
    op.create_index('ix_pricing_rule_customers_rule_user', 'pricing_rule_customers', ['pricing_rule_id', 'user_id'])
    
    # Create channel_prices table
    op.create_table(
        'channel_prices',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('product_id', sa.UUID(), nullable=True),
        sa.Column('product_variant_id', sa.UUID(), nullable=True),
        sa.Column('channel', sa.String(50), nullable=False),
        sa.Column('base_price', sa.Numeric(15, 2), nullable=False),
        sa.Column('compare_at_price', sa.Numeric(15, 2), nullable=True),
        sa.Column('cost_price', sa.Numeric(15, 2), nullable=True),
        sa.Column('currency', sa.String(3), nullable=False, server_default='INR'),
        sa.Column('min_price', sa.Numeric(15, 2), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('effective_from', sa.DateTime(), nullable=True),
        sa.Column('effective_until', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_variant_id'], ['product_variants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('(product_id IS NOT NULL) OR (product_variant_id IS NOT NULL)', name='check_channel_price_product_or_variant')
    )
    op.create_index('ix_channel_prices_product_id', 'channel_prices', ['product_id'])
    op.create_index('ix_channel_prices_product_variant_id', 'channel_prices', ['product_variant_id'])
    op.create_index('ix_channel_prices_channel', 'channel_prices', ['channel'])
    op.create_index('ix_channel_prices_product_channel', 'channel_prices', ['product_id', 'channel'])
    op.create_index('ix_channel_prices_variant_channel', 'channel_prices', ['product_variant_id', 'channel'])
    op.create_index('ix_channel_prices_channel_active', 'channel_prices', ['channel', 'is_active'])
    
    # Create volume_discounts table
    op.create_table(
        'volume_discounts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('product_id', sa.UUID(), nullable=True),
        sa.Column('product_variant_id', sa.UUID(), nullable=True),
        sa.Column('category_id', sa.UUID(), nullable=True),
        sa.Column('is_global', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('min_quantity', sa.Integer(), nullable=False),
        sa.Column('max_quantity', sa.Integer(), nullable=True),
        sa.Column('discount_type', sa.String(50), nullable=False),
        sa.Column('discount_value', sa.Numeric(15, 4), nullable=False),
        sa.Column('channel', sa.String(50), nullable=True),
        sa.Column('customer_tier', sa.String(50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('start_date', sa.DateTime(), nullable=True),
        sa.Column('end_date', sa.DateTime(), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_variant_id'], ['product_variants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_volume_discounts_product_id', 'volume_discounts', ['product_id'])
    op.create_index('ix_volume_discounts_product_variant_id', 'volume_discounts', ['product_variant_id'])
    op.create_index('ix_volume_discounts_category_id', 'volume_discounts', ['category_id'])
    op.create_index('ix_volume_discounts_product_qty', 'volume_discounts', ['product_id', 'min_quantity'])
    op.create_index('ix_volume_discounts_category_qty', 'volume_discounts', ['category_id', 'min_quantity'])
    op.create_index('ix_volume_discounts_active', 'volume_discounts', ['is_active', 'priority'])
    
    # Create promotions table
    op.create_table(
        'promotions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('discount_type', sa.String(50), nullable=False),
        sa.Column('discount_value', sa.Numeric(15, 4), nullable=False),
        sa.Column('max_discount_amount', sa.Numeric(15, 2), nullable=True),
        sa.Column('min_order_value', sa.Numeric(15, 2), nullable=True),
        sa.Column('min_quantity', sa.Integer(), nullable=True),
        sa.Column('buy_quantity', sa.Integer(), nullable=True),
        sa.Column('get_quantity', sa.Integer(), nullable=True),
        sa.Column('get_discount_percentage', sa.Numeric(5, 2), nullable=True),
        sa.Column('applicable_channels', sa.JSON(), nullable=True),
        sa.Column('applicable_customer_tiers', sa.JSON(), nullable=True),
        sa.Column('first_order_only', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('applicable_product_ids', sa.JSON(), nullable=True),
        sa.Column('applicable_category_ids', sa.JSON(), nullable=True),
        sa.Column('excluded_product_ids', sa.JSON(), nullable=True),
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('end_date', sa.DateTime(), nullable=False),
        sa.Column('max_uses', sa.Integer(), nullable=True),
        sa.Column('current_uses', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_uses_per_customer', sa.Integer(), nullable=True),
        sa.Column('is_stackable', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('auto_apply', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('display_name', sa.String(200), nullable=True),
        sa.Column('terms_conditions', sa.Text(), nullable=True),
        sa.Column('banner_image_url', sa.String(500), nullable=True),
        sa.Column('created_by_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_promotions_id', 'promotions', ['id'])
    op.create_index('ix_promotions_code', 'promotions', ['code'], unique=True)
    op.create_index('ix_promotions_status', 'promotions', ['status'])
    op.create_index('ix_promotions_start_date', 'promotions', ['start_date'])
    op.create_index('ix_promotions_end_date', 'promotions', ['end_date'])
    op.create_index('ix_promotions_dates_status', 'promotions', ['start_date', 'end_date', 'status'])
    op.create_index('ix_promotions_auto_apply', 'promotions', ['auto_apply', 'status'])
    
    # Create promotion_usages table
    op.create_table(
        'promotion_usages',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('promotion_id', sa.UUID(), nullable=False),
        sa.Column('order_id', sa.UUID(), nullable=True),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('wholesale_customer_id', sa.UUID(), nullable=True),
        sa.Column('discount_amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('order_total_before_discount', sa.Numeric(15, 2), nullable=False),
        sa.Column('order_total_after_discount', sa.Numeric(15, 2), nullable=False),
        sa.Column('used_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['promotion_id'], ['promotions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['wholesale_customer_id'], ['wholesale_customers.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_promotion_usages_promotion_id', 'promotion_usages', ['promotion_id'])
    op.create_index('ix_promotion_usages_order_id', 'promotion_usages', ['order_id'])
    op.create_index('ix_promotion_usages_user_id', 'promotion_usages', ['user_id'])
    op.create_index('ix_promotion_usages_wholesale_customer_id', 'promotion_usages', ['wholesale_customer_id'])
    op.create_index('ix_promotion_usages_promo_user', 'promotion_usages', ['promotion_id', 'user_id'])
    op.create_index('ix_promotion_usages_promo_wholesale', 'promotion_usages', ['promotion_id', 'wholesale_customer_id'])
    
    # Create price_history table
    op.create_table(
        'price_history',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('product_id', sa.UUID(), nullable=True),
        sa.Column('product_variant_id', sa.UUID(), nullable=True),
        sa.Column('channel', sa.String(50), nullable=True),
        sa.Column('old_price', sa.Numeric(15, 2), nullable=True),
        sa.Column('new_price', sa.Numeric(15, 2), nullable=False),
        sa.Column('old_cost', sa.Numeric(15, 2), nullable=True),
        sa.Column('new_cost', sa.Numeric(15, 2), nullable=True),
        sa.Column('currency', sa.String(3), nullable=False, server_default='INR'),
        sa.Column('change_reason', sa.String(50), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('changed_by_id', sa.UUID(), nullable=True),
        sa.Column('pricing_rule_id', sa.UUID(), nullable=True),
        sa.Column('effective_date', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('extra_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_variant_id'], ['product_variants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['changed_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['pricing_rule_id'], ['pricing_rules.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('(product_id IS NOT NULL) OR (product_variant_id IS NOT NULL)', name='check_price_history_product_or_variant')
    )
    op.create_index('ix_price_history_product_id', 'price_history', ['product_id'])
    op.create_index('ix_price_history_product_variant_id', 'price_history', ['product_variant_id'])
    op.create_index('ix_price_history_channel', 'price_history', ['channel'])
    op.create_index('ix_price_history_product_date', 'price_history', ['product_id', 'effective_date'])
    op.create_index('ix_price_history_variant_date', 'price_history', ['product_variant_id', 'effective_date'])
    op.create_index('ix_price_history_channel_date', 'price_history', ['channel', 'effective_date'])
    op.create_index('ix_price_history_reason', 'price_history', ['change_reason', 'effective_date'])
    
    # Create competitor_prices table
    op.create_table(
        'competitor_prices',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('product_id', sa.UUID(), nullable=True),
        sa.Column('product_variant_id', sa.UUID(), nullable=True),
        sa.Column('competitor_name', sa.String(200), nullable=False),
        sa.Column('competitor_url', sa.String(500), nullable=True),
        sa.Column('competitor_product_name', sa.String(500), nullable=True),
        sa.Column('competitor_sku', sa.String(100), nullable=True),
        sa.Column('price', sa.Numeric(15, 2), nullable=False),
        sa.Column('sale_price', sa.Numeric(15, 2), nullable=True),
        sa.Column('currency', sa.String(3), nullable=False, server_default='INR'),
        sa.Column('in_stock', sa.Boolean(), nullable=True),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('match_confidence', sa.Numeric(5, 2), nullable=True),
        sa.Column('observed_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('is_latest', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('extra_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_variant_id'], ['product_variants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_competitor_prices_product_id', 'competitor_prices', ['product_id'])
    op.create_index('ix_competitor_prices_product_variant_id', 'competitor_prices', ['product_variant_id'])
    op.create_index('ix_competitor_prices_competitor_name', 'competitor_prices', ['competitor_name'])
    op.create_index('ix_competitor_prices_product_competitor', 'competitor_prices', ['product_id', 'competitor_name'])
    op.create_index('ix_competitor_prices_variant_competitor', 'competitor_prices', ['product_variant_id', 'competitor_name'])
    op.create_index('ix_competitor_prices_observed', 'competitor_prices', ['observed_at'])
    op.create_index('ix_competitor_prices_latest', 'competitor_prices', ['is_latest', 'competitor_name'])
    
    # Create customer_pricing_tiers table
    op.create_table(
        'customer_pricing_tiers',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('wholesale_customer_id', sa.UUID(), nullable=True),
        sa.Column('tier', sa.String(50), nullable=False, server_default='standard'),
        sa.Column('discount_percentage', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('assignment_reason', sa.String(200), nullable=True),
        sa.Column('effective_from', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('effective_until', sa.DateTime(), nullable=True),
        sa.Column('is_automatic', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['wholesale_customer_id'], ['wholesale_customers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('(user_id IS NOT NULL) OR (wholesale_customer_id IS NOT NULL)', name='check_customer_tier_user_or_wholesale')
    )
    op.create_index('ix_customer_pricing_tiers_user_id', 'customer_pricing_tiers', ['user_id'])
    op.create_index('ix_customer_pricing_tiers_wholesale_customer_id', 'customer_pricing_tiers', ['wholesale_customer_id'])
    op.create_index('ix_customer_pricing_tiers_user', 'customer_pricing_tiers', ['user_id', 'tier'])
    op.create_index('ix_customer_pricing_tiers_wholesale', 'customer_pricing_tiers', ['wholesale_customer_id', 'tier'])


def downgrade() -> None:
    # Drop tables in reverse order of creation
    op.drop_table('customer_pricing_tiers')
    op.drop_table('competitor_prices')
    op.drop_table('price_history')
    op.drop_table('promotion_usages')
    op.drop_table('promotions')
    op.drop_table('volume_discounts')
    op.drop_table('channel_prices')
    op.drop_table('pricing_rule_customers')
    op.drop_table('pricing_rule_categories')
    op.drop_table('pricing_rule_products')
    op.drop_table('pricing_rules')
