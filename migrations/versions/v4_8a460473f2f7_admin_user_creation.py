"""admin user creation

Revision ID: 8a460473f2f7
Revises: 2fab8985131c
Create Date: 2024-10-21 21:44:25.922252

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pwdlib import PasswordHash

from main_app.auth.models import User
from main_app.config import settings

# revision identifiers, used by Alembic.
revision: str = "8a460473f2f7"
down_revision: Union[str, None] = "dd8a90fe9020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    with sa.orm.Session(bind=conn) as session:
        password_hash = PasswordHash.recommended()
        admin_user = User(
            first_name=settings.APP_ADMIN_USER_FIRST_NAME,
            last_name=settings.APP_ADMIN_USER_LAST_NAME,
            email=settings.APP_ADMIN_USER_EMAIL,
            hashed_password=password_hash.hash(settings.APP_ADMIN_USER_PASSWORD),
            is_superuser=True
        )
        session.add(admin_user)
        session.commit()


def downgrade() -> None:
    conn = op.get_bind()
    with sa.orm.Session(bind=conn) as session:
        session.execute(
            sa.delete(User)
            .where(User.email == settings.APP_ADMIN_USER_EMAIL)
        )
        session.commit()
