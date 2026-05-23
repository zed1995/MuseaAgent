from alembic import context
from sqlalchemy import engine_from_config, pool

from backend.models.base import Base

target_metadata = Base.metadata
