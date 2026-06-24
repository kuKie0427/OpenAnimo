"""bridge legacy storyboard/review/export revision

Revision ID: 0013_storyboard_elements_reviews_exports
Revises: 0019_create_universe_tables

This compatibility revision preserves the historical revision id that may
already be stamped in existing development databases. It is placed after the
current concrete migration chain so databases stamped with this legacy id are
accepted as current without replaying duplicate schema changes.
"""

revision = "0013_storyboard_elements_reviews_exports"
down_revision = "0019_create_universe_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
