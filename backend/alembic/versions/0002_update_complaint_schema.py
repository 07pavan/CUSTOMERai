"""Update complaint schema — rename existing columns and add new audit/traceability fields.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Update PostgreSQL Native ENUM types if running under PostgreSQL
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.execute("ALTER TYPE sourcetype ADD VALUE IF NOT EXISTS 'pharmacy';")
        op.execute("ALTER TYPE status ADD VALUE IF NOT EXISTS 'ready_to_commit';")

    # 2. Alter complaints table using batch_alter_table for SQLite & Postgres compatibility
    with op.batch_alter_table('complaints', schema=None) as batch_op:
        # Rename existing columns
        batch_op.alter_column('source_type', new_column_name='complaint_source')
        batch_op.alter_column('complainant_name', new_column_name='customer_name')
        batch_op.alter_column('category', new_column_name='complaint_category')
        batch_op.alter_column('description', new_column_name='complaint_description')

        # Add new columns
        batch_op.add_column(sa.Column('product_strength', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('affected_quantity', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('manufacturing_date', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('expiry_date', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('originating_site_block', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('impacted_npm', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('suggested_next_action', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('initial_risk_assessment', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('complaints', schema=None) as batch_op:
        # Drop added columns
        batch_op.drop_column('initial_risk_assessment')
        batch_op.drop_column('suggested_next_action')
        batch_op.drop_column('impacted_npm')
        batch_op.drop_column('originating_site_block')
        batch_op.drop_column('expiry_date')
        batch_op.drop_column('manufacturing_date')
        batch_op.drop_column('affected_quantity')
        batch_op.drop_column('product_strength')

        # Rename columns back
        batch_op.alter_column('complaint_source', new_column_name='source_type')
        batch_op.alter_column('customer_name', new_column_name='complainant_name')
        batch_op.alter_column('complaint_category', new_column_name='category')
        batch_op.alter_column('complaint_description', new_column_name='description')
