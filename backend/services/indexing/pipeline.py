from backend.services.indexing.contracts import EnrichmentContext
from backend.services.indexing.source_normalizer import normalize_unsplash_photo
from backend.services.indexing.text_assembly import assemble_text_artifacts
from backend.services.indexing.validation import build_completed_index_entry


class IndexingPipeline:
    def __init__(self, *, id_generator, translator, enricher, scorer, embedder, repository) -> None:
        self._id_generator = id_generator
        self._translator = translator
        self._enricher = enricher
        self._scorer = scorer
        self._embedder = embedder
        self._repository = repository

    def process_photo(self, payload: dict):
        source = normalize_unsplash_photo(payload)
        context = EnrichmentContext(source=source)

        context.text_artifacts = assemble_text_artifacts(source)
        context.text_artifacts.search_text = self._translator.to_search_text(
            analysis_text=context.text_artifacts.analysis_text or "",
        )
        context.semantic_artifacts = self._enricher.enrich(
            image_url=source.regular_url,
            analysis_text=context.text_artifacts.analysis_text or "",
            search_text=context.text_artifacts.search_text or "",
        )
        context.semantic_artifacts = self._scorer.score(
            semantic_artifacts=context.semantic_artifacts,
        )
        context.retrieval_artifacts.embedding = self._embedder.embed(
            search_text=context.text_artifacts.search_text or "",
            caption=context.semantic_artifacts.ai_caption or "",
            tags=(context.semantic_artifacts.scene_tags or [])
            + (context.semantic_artifacts.style_tags or []),
        )

        entry = build_completed_index_entry(
            context=context,
            entry_id=self._id_generator.next_id(),
        )
        self._repository.upsert_index_entry(entry)
        return entry

    @property
    def translator(self):
        return self._translator

    @property
    def enricher(self):
        return self._enricher

    @property
    def embedder(self):
        return self._embedder
