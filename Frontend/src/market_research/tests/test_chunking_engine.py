import pytest

from ..services.chunking_engine import ChunkingAndEmbeddingEngine


@pytest.mark.asyncio
async def test_chunk_content_single_chunk_does_not_loop():
    engine = ChunkingAndEmbeddingEngine(db_adapter=object())
    short_text = "This is a short document." * 5

    chunks = await engine.chunk_content(short_text, chunk_size=1000, chunk_overlap=200)

    assert len(chunks) == 1
    assert short_text.strip() == chunks[0]["content"]


@pytest.mark.asyncio
async def test_chunk_content_progresses_with_overlap():
    engine = ChunkingAndEmbeddingEngine(db_adapter=object())
    content = " ".join([f"Sentence {i}." for i in range(50)])

    chunks = await engine.chunk_content(content, chunk_size=150, chunk_overlap=50, content_type="pdf")

    # Ensure we produced multiple chunks and the last chunk isn't repeated
    assert len(chunks) > 1

    contents = [chunk["content"] for chunk in chunks]
    assert contents[-1] != contents[-2]
    assert contents[-1].strip().endswith("Sentence 49.")
