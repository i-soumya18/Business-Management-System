"""Add garment-specific models

Revision ID: g12345678abc
Revises: dbd86207331b
Create Date: 2024-01-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'g12345678abc'
down_revision: Union[str, None] = 'dbd86207331b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE sizecategory AS ENUM ('tops', 'bottoms', 'dresses', 'outerwear', 'underwear', 'accessories')")
    op.execute("CREATE TYPE region AS ENUM ('us', 'eu', 'uk', 'asia', 'international')")
    op.execute("CREATE TYPE season AS ENUM ('spring', 'summer', 'fall', 'winter', 'all_season')")
    
    # Create size_charts table
    op.create_table(
        'size_charts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('category', postgresql.ENUM('tops', 'bottoms', 'dresses', 'outerwear', 'underwear', 'accessories', name='sizecategory'), nullable=False),
        sa.Column('region', postgresql.ENUM('us', 'eu', 'uk', 'asia', 'international', name='region'), nullable=False),
        sa.Column('sizes', postgresql.JSONB(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_size_charts_category'), 'size_charts', ['category'], unique=False)
    op.create_index(op.f('ix_size_charts_name'), 'size_charts', ['name'], unique=False)
    op.create_index(op.f('ix_size_charts_region'), 'size_charts', ['region'], unique=False)

    # Create colors table
    op.create_table(
        'colors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('hex_code', sa.String(length=7), nullable=False),
        sa.Column('pantone_code', sa.String(length=20), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
        sa.UniqueConstraint('hex_code')
    )
    op.create_index(op.f('ix_colors_code'), 'colors', ['code'], unique=False)
    op.create_index(op.f('ix_colors_name'), 'colors', ['name'], unique=False)

    # Create fabrics table
    op.create_table(
        'fabrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('composition', sa.String(length=200), nullable=False),
        sa.Column('weight_gsm', sa.Integer(), nullable=True),
        sa.Column('properties', postgresql.JSONB(), nullable=True),
        sa.Column('care_instructions', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index(op.f('ix_fabrics_code'), 'fabrics', ['code'], unique=False)
    op.create_index(op.f('ix_fabrics_name'), 'fabrics', ['name'], unique=False)

    # Create styles table
    op.create_table(
        'styles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index(op.f('ix_styles_code'), 'styles', ['code'], unique=False)
    op.create_index(op.f('ix_styles_name'), 'styles', ['name'], unique=False)

    # Create collections table
    op.create_table(
        'collections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('season', postgresql.ENUM('spring', 'summer', 'fall', 'winter', 'all_season', name='season'), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index(op.f('ix_collections_code'), 'collections', ['code'], unique=False)
    op.create_index(op.f('ix_collections_name'), 'collections', ['name'], unique=False)
    op.create_index(op.f('ix_collections_season'), 'collections', ['season'], unique=False)
    op.create_index(op.f('ix_collections_year'), 'collections', ['year'], unique=False)

    # Create measurement_specs table
    op.create_table(
        'measurement_specs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('size', sa.String(length=20), nullable=False),
        sa.Column('chest', sa.Float(), nullable=True),
        sa.Column('waist', sa.Float(), nullable=True),
        sa.Column('hips', sa.Float(), nullable=True),
        sa.Column('length', sa.Float(), nullable=True),
        sa.Column('sleeve_length', sa.Float(), nullable=True),
        sa.Column('shoulder_width', sa.Float(), nullable=True),
        sa.Column('additional_measurements', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_measurement_specs_product_id'), 'measurement_specs', ['product_id'], unique=False)
    op.create_index(op.f('ix_measurement_specs_size'), 'measurement_specs', ['size'], unique=False)

    # Create garment_images table
    op.create_table(
        'garment_images',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('color_id', sa.Integer(), nullable=True),
        sa.Column('image_url', sa.String(length=500), nullable=False),
        sa.Column('alt_text', sa.String(length=200), nullable=True),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['color_id'], ['colors.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_garment_images_color_id'), 'garment_images', ['color_id'], unique=False)
    op.create_index(op.f('ix_garment_images_product_id'), 'garment_images', ['product_id'], unique=False)

    # Create product_fabrics junction table
    op.create_table(
        'product_fabrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('fabric_id', sa.Integer(), nullable=False),
        sa.Column('percentage', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['fabric_id'], ['fabrics.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_product_fabrics_fabric_id'), 'product_fabrics', ['fabric_id'], unique=False)
    op.create_index(op.f('ix_product_fabrics_product_id'), 'product_fabrics', ['product_id'], unique=False)


def downgrade() -> None:
    # Drop tables
    op.drop_table('product_fabrics')
    op.drop_table('garment_images')
    op.drop_table('measurement_specs')
    op.drop_table('collections')
    op.drop_table('styles')
    op.drop_table('fabrics')
    op.drop_table('colors')
    op.drop_table('size_charts')
    
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS season")
    op.execute("DROP TYPE IF EXISTS region")
    op.execute("DROP TYPE IF EXISTS sizecategory")
