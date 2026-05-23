from backend.services.indexing.contracts import NormalizedSourcePhoto, TextArtifacts


def assemble_text_artifacts(source: NormalizedSourcePhoto) -> TextArtifacts:
    fragments = [
        fragment.strip()
        for fragment in (source.raw_title, source.raw_description, source.raw_alt_description)
        if fragment and fragment.strip()
    ]
    source_text = "\n".join(fragments) if fragments else f"unsplash:{source.unsplash_photo_id}"
    return TextArtifacts(
        source_text=source_text,
        analysis_text=source_text,
    )
