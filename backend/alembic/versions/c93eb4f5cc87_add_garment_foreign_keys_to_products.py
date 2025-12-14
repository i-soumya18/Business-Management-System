"""Alembic version control for database migrations

Revision ID: c93eb4f5cc87
Revises: 170c17b750f6
Create Date: 2025-12-14 10:14:20.106192

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c93eb4f5cc87'
down_revision = '170c17b750f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add foreign keys to products table
    op.add_column('products', sa.Column('size_chart_id', sa.UUID(), nullable=True))
    op.add_column('products', sa.Column('style_id', sa.UUID(), nullable=True))
    op.add_column('products', sa.Column('collection_id', sa.UUID(), nullable=True))
    
    # Add foreign keys to product_variants table
    op.add_column('product_variants', sa.Column('color_id', sa.UUID(), nullable=True))
    
    # Create foreign key constraints
    op.create_foreign_key(
        'fk_products_size_chart_id',
        'products',
        'size_charts',
        ['size_chart_id'],
        ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_products_style_id',
        'products',
        'styles',
        ['style_id'],
        ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_products_collection_id',
        'products',
        'collections',
        ['collection_id'],
        ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_product_variants_color_id',
        'product_variants',
        'colors',
        ['color_id'],
        ['id'],
        ondelete='SET NULL'
    )
    
    # Create indexes
    op.create_index('ix_products_size_chart_id', 'products', ['size_chart_id'])
    op.create_index('ix_products_style_id', 'products', ['style_id'])
    op.create_index('ix_products_collection_id', 'products', ['collection_id'])
    op.create_index('ix_product_variants_color_id', 'product_variants', ['color_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_product_variants_color_id', 'product_variants')
    op.drop_index('ix_products_collection_id', 'products')
    op.drop_index('ix_products_style_id', 'products')
    op.drop_index('ix_products_size_chart_id', 'products')
    
    # Drop foreign key constraints
    op.drop_constraint('fk_product_variants_color_id', 'product_variants', type_='foreignkey')
    op.drop_constraint('fk_products_collection_id', 'products', type_='foreignkey')
    op.drop_constraint('fk_products_style_id', 'products', type_='foreignkey')
    op.drop_constraint('fk_products_size_chart_id', 'products', type_='foreignkey')
    
    # Drop columns
    op.drop_column('product_variants', 'color_id')
    op.drop_column('products', 'collection_id')
    op.drop_column('products', 'style_id')
    op.drop_column('products', 'size_chart_id')
