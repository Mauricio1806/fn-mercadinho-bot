"""initial schema

Revision ID: 000_initial_schema
Revises: 
Create Date: 2026-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '000_initial_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    op.create_table('customers',
        sa.Column('id', UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('phone', sa.String(20), nullable=False),
        sa.Column('name', sa.String(200), nullable=True),
        sa.Column('building_block', sa.String(10), nullable=True),
        sa.Column('apartment', sa.String(10), nullable=True),
        sa.Column('is_blocked', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('total_orders', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('phone')
    )
    op.create_table('product_categories',
        sa.Column('id', UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('products',
        sa.Column('id', UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('category_id', UUID(as_uuid=True), nullable=False),
        sa.Column('stock_quantity', sa.Integer(), nullable=True),
        sa.Column('is_available', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('in_stock', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['category_id'], ['product_categories.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('conversations',
        sa.Column('id', UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('customer_id', UUID(as_uuid=True), nullable=False),
        sa.Column('customer_phone', sa.String(20), nullable=True),
        sa.Column('customer_name', sa.String(200), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default=sa.text("'active'")),
        sa.Column('state', sa.String(50), nullable=False, server_default=sa.text("'greeting'")),
        sa.Column('message_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('last_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('orders',
        sa.Column('id', UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('customer_id', UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default=sa.text("'pending'")),
        sa.Column('total_amount', sa.Float(), nullable=False, server_default=sa.text('0')),
        sa.Column('delivery_building_block', sa.String(10), nullable=True),
        sa.Column('delivery_apartment', sa.String(10), nullable=True),
        sa.Column('delivery_fee', sa.Float(), nullable=False, server_default=sa.text('0')),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('pix_confirmed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('commission_amount', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('order_items',
        sa.Column('id', UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('order_id', UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', UUID(as_uuid=True), nullable=False),
        sa.Column('product_name', sa.String(200), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('unit_price', sa.Float(), nullable=False),
        sa.Column('subtotal', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('messages',
        sa.Column('id', UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('conversation_id', UUID(as_uuid=True), nullable=False),
        sa.Column('direction', sa.String(10), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_ai_generated', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('admins',
        sa.Column('id', UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('email', sa.String(200), nullable=False),
        sa.Column('hashed_password', sa.String(200), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_table('admin_users',
        sa.Column('id', UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('email', sa.String(200), nullable=False),
        sa.Column('hashed_password', sa.String(200), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_table('pix_receipt_logs',
        sa.Column('id', UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('order_id', UUID(as_uuid=True), nullable=True),
        sa.Column('raw_payload', sa.Text(), nullable=True),
        sa.Column('processed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('pix_receipt_logs')
    op.drop_table('admin_users')
    op.drop_table('messages')
    op.drop_table('order_items')
    op.drop_table('orders')
    op.drop_table('conversations')
    op.drop_table('products')
    op.drop_table('product_categories')
    op.drop_table('customers')
    op.drop_table('admins')
