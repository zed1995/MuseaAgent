import logging

from pydantic import ValidationError

from backend.services.retrieval.contracts import RetrievalFilters
from backend.services.retrieval_preparation.contracts import PreparedRetrievalRequest
from backend.services.retrieval_preparation.fallback import (
    build_rewrite_fallback,
)

logger = logging.getLogger(__name__)


class RetrievalPreparationError(RuntimeError):
    """Raised when retrieval preparation cannot produce a usable request."""


class RetrievalPreparationService:
    def __init__(self, understanding_service, rewrite_service) -> None:
        self._understanding_service = understanding_service
        self._rewrite_service = rewrite_service

    def prepare(
        self,
        query: str,
        mode: str,
        explicit_filters: RetrievalFilters | None = None,
    ) -> PreparedRetrievalRequest:
        try:
            understanding = self._understanding_service.understand(
                query,
                mode,
                explicit_filters,
            )
        except Exception as exc:
            logger.error(
                "[prepare] understanding failed for query=%r mode=%s: %s: %s",
                query,
                mode,
                type(exc).__name__,
                exc,
            )
            raise RetrievalPreparationError(
                "retrieval understanding failed and did not return valid structured JSON"
            ) from exc

        try:
            rewrite = self._rewrite_service.rewrite(understanding)
            if self._has_empty_rewrite(rewrite):
                logger.warning(
                    "[prepare] empty rewrite generated for query=%r mode=%s: embedding=%r fts=%r notes=%s; using rewrite fallback",
                    query,
                    mode,
                    rewrite.rewrite_for_embedding,
                    rewrite.rewrite_for_fts,
                    rewrite.rewrite_notes,
                )
                rewrite = build_rewrite_fallback(understanding)
        except Exception as exc:
            if self._is_blank_rewrite_validation_error(exc):
                logger.warning(
                    "[prepare] empty rewrite generated for query=%r mode=%s; using rewrite fallback",
                    query,
                    mode,
                )
            else:
                logger.warning(
                    "[prepare] rewrite failed for query=%r mode=%s: %s: %s; using rewrite fallback",
                    query,
                    mode,
                    type(exc).__name__,
                    exc,
                )
            try:
                rewrite = build_rewrite_fallback(understanding)
            except Exception as fallback_exc:
                logger.error(
                    "[prepare] rewrite fallback failed for query=%r mode=%s: %s: %s",
                    query,
                    mode,
                    type(fallback_exc).__name__,
                    fallback_exc,
                )
                raise RetrievalPreparationError(
                    "retrieval rewrite failed and fallback could not produce a valid rewrite"
                ) from fallback_exc

        return PreparedRetrievalRequest(
            understanding=understanding,
            rewrite=rewrite,
        )

    def _has_empty_rewrite(self, rewrite) -> bool:
        return (
            not rewrite.rewrite_for_embedding.strip()
            or not rewrite.rewrite_for_fts.strip()
        )

    def _is_blank_rewrite_validation_error(self, exc: Exception) -> bool:
        if not isinstance(exc, ValidationError):
            return False
        return "rewrite must not be blank" in str(exc) or "at least 1 character" in str(exc)
