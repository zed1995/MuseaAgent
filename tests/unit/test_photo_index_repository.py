from sqlalchemy.dialects import postgresql

from backend.models.photo_index import PhotoIndexOrmModel
from backend.repositories.photo_index_repository import _build_weighted_tsvector


def test_weighted_tsvector_uses_sql_literals_for_weights() -> None:
    expression = _build_weighted_tsvector(PhotoIndexOrmModel)
    compiled = str(expression.compile(dialect=postgresql.dialect()))

    assert "setweight" in compiled
    assert "::VARCHAR" not in compiled
    assert "'A'" in compiled
    assert "'B'" in compiled
    assert "'C'" in compiled
