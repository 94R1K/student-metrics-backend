"""add metric results

Revision ID: 67206af655e3
Revises: ab7ddd444281
Create Date: 2025-12-15 04:47:28.013070

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '67206af655e3'
down_revision: Union[str, None] = 'ab7ddd444281'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "metric_results",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "metric_name",
            sa.Enum(
                "retention",
                "engagement_score",
                "completion_rate",
                "time_on_task",
                "activity_index",
                "focus_ratio",
                name="metric_names",
            ),
            nullable=False,
        ),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("course_id", sa.String(), nullable=False),
        sa.Column("module_id", sa.String(), nullable=True),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("period_start", sa.DateTime(), nullable=False),
        sa.Column("period_end", sa.DateTime(), nullable=False),
        sa.Column("calculated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "metric_name",
            "user_id",
            "course_id",
            "module_id",
            "period_start",
            "period_end",
            name="uq_metric_scope",
        ),
    )
    op.create_index("ix_metric_results_user_id", "metric_results", ["user_id"])
    op.create_index("ix_metric_results_course_id", "metric_results", ["course_id"])
    op.create_index("ix_metric_results_module_id", "metric_results", ["module_id"])


def downgrade() -> None:
    op.drop_index("ix_metric_results_module_id", table_name="metric_results")
    op.drop_index("ix_metric_results_course_id", table_name="metric_results")
    op.drop_index("ix_metric_results_user_id", table_name="metric_results")
    op.drop_table("metric_results")
