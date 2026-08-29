from src.retrieval.hybrid_retriever import HybridRetriever, RetrieveItem


def _retriever() -> HybridRetriever:
    return HybridRetriever(client=None, embedder=None, reranker=None)


def _item(point_id: str, text: str, score: float) -> RetrieveItem:
    return RetrieveItem(
        point_id=point_id,
        text=text,
        document_name="msa.pdf",
        page_number=1,
        section_label="Operative Clause",
        chunk_hash="h",
        score=score,
        retrieval_method="dense_vector",
    )


def test_token_overlap_score_identical_strings_is_one():
    retriever = _retriever()
    score = retriever._token_overlap_score("data retention policy", "data retention policy")
    assert score == 1.0


def test_token_overlap_score_disjoint_strings_is_zero():
    retriever = _retriever()
    score = retriever._token_overlap_score("data retention policy", "completely different sentence")
    assert score == 0.0


def test_token_overlap_score_partial_overlap_between_zero_and_one():
    retriever = _retriever()
    score = retriever._token_overlap_score("data retention policy", "data transfer policy")
    assert 0.0 < score < 1.0


def test_bm25_score_rewards_term_presence():
    retriever = _retriever()
    present = retriever._bm25_lexical_score("retention", "the retention period is ninety days")
    absent = retriever._bm25_lexical_score("retention", "no matching terms here at all")
    assert present > 0.0
    assert absent == 0.0


def test_bm25_score_ignores_short_tokens():
    retriever = _retriever()
    # "is", "a", "of" are all <=2 chars and should be filtered out of query terms
    score = retriever._bm25_lexical_score("is a of", "is a of is a of")
    assert score == 0.0


def test_rrf_ranks_item_strong_in_both_signals_highest():
    retriever = _retriever()
    query = "data retention ninety days"
    items = [
        _item("weak", "irrelevant boilerplate about signatures", 0.1),
        _item("strong", "data retention ninety days clause", 0.9),
        _item("mixed", "data retention discussed generally", 0.5),
    ]

    fused = retriever._compute_rrf(items, query)

    assert fused[0].point_id == "strong"


def test_rrf_returns_empty_for_no_hits():
    retriever = _retriever()
    assert retriever._compute_rrf([], "any query") == []
