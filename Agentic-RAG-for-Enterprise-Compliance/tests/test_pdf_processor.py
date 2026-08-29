from src.database.pdf_processor import _split_by_clause_boundaries


def test_clause_headers_produce_one_chunk_per_clause():
    text = (
        "Clause 1.1: General Scope of Compute Services.\n"
        "Vendor Alpha will provide scalable data compute architectures.\n"
        "Clause 2.2: European Union Zone Data Retention Constraints.\n"
        "All data will be retained for ninety (90) days.\n"
        "SECTION 3: Signature Block.\n"
        "IN WITNESS WHEREOF, the parties have executed this agreement."
    )

    chunks = _split_by_clause_boundaries(text, chunk_size=500, overlap=100)

    assert len(chunks) == 3
    assert chunks[0].startswith("Clause 1.1:")
    assert chunks[1].startswith("Clause 2.2:")
    assert chunks[2].startswith("SECTION 3:")
    # Each clause stays intact — no clause header ends up split across chunks.
    assert "Clause 2.2" not in chunks[0]
    assert "SECTION 3" not in chunks[1]


def test_no_clause_headers_falls_back_to_windowing():
    text = "This page has no numbered clause structure at all, just plain narrative text. " * 10

    chunks = _split_by_clause_boundaries(text, chunk_size=200, overlap=50)

    assert len(chunks) > 1  # plain windowing still splits long unstructured text


def test_oversized_clause_still_gets_windowed():
    long_body = "Filler contract language repeated many times. " * 40
    text = f"Clause 9.1: Indemnification.\n{long_body}"

    chunks = _split_by_clause_boundaries(text, chunk_size=200, overlap=50)

    # A single oversized clause should still be broken into multiple windows,
    # rather than shipped as one enormous unsplit chunk.
    assert len(chunks) > 1
    assert all(len(c) <= 220 for c in chunks)
