"""
app/models/base.py
------------------
SQLAlchemy 2.0 DeclarativeBase with PostgreSQL-friendly naming conventions.

Naming conventions
------------------
SQLAlchemy can auto-name constraints (PK, FK, IX, UQ, CK) using a template.
Setting them here ensures Alembic generates consistent, short, deterministic
constraint names across all environments — critical for `alembic --autogenerate`
to produce clean diffs rather than detecting phantom constraint renames.

Convention tokens:
    %(constraint_name)s  — explicit name given in Column()/relationship()
    %(column_0_name)s    — first column in the constraint
    %(table_name)s       — table the constraint belongs to
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Convention-driven constraint naming to keep Alembic migrations deterministic.
NAMING_CONVENTION: dict = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """
    Project-wide SQLAlchemy declarative base.

    All ORM models must inherit from this class.
    The attached metadata carries the naming convention so that
    Alembic autogenerate produces consistent constraint names.
    """
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
