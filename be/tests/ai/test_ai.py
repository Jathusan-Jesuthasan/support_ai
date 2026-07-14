import pytest
from app.ai.service import AIService


@pytest.mark.asyncio
async def test_ai_service_test_mode():
    ai = AIService()
    assert ai.is_test_mode is True

    # Test embeddings
    texts = ["hello world", "test sequence"]
    embeddings = await ai.generate_embeddings(texts)
    assert len(embeddings) == 2
    assert len(embeddings[0]) == 768

    # Test completion
    answer = await ai.generate_completion("sys prompt", "user query")
    assert "mock" in answer.lower()

    # Test stream
    streamed = []
    async for tok in ai.generate_completion_stream("sys prompt", "user query"):
        streamed.append(tok)
    assert len(streamed) > 0
    assert "mock" in "".join(streamed).lower()

    # Test summary
    summary = await ai.generate_document_summary("some document text contents")
    assert len(summary) > 0

    # Test tags
    tags = await ai.extract_tags("some document text contents")
    assert len(tags) > 0

    # Test validation grounding
    score = await ai.validate_grounding(["context 1", "context 2"], "mock answer")
    assert score == 1.0
