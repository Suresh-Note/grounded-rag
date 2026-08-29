import time
import json
from src.retrieval.hybrid_retriever import HybridRetriever

TEST_DATASET = [
    {
        "query": "What is the timeline for processing manual data deletion requests under GDPR?",
        "expected_keyword": "120-business-day",
        "category": "Data Retention & SLA"
    },
    {
        "query": "Are operational logs transferred outside the European Union with Standard Contractual Clauses?",
        "expected_keyword": "Standard Contractual Clauses",
        "category": "Data Sovereignty & GDPR"
    }
]

def run_retrieval_benchmark():
    print("=" * 65)
    print("🚀 RUNNING OFFLINE RAG EVALUATION BENCHMARK SUITE")
    print("=" * 65)
    
    retriever = HybridRetriever.create()
    total_tests = len(TEST_DATASET)
    hits_at_k = 0
    total_latency_ms = 0.0

    for idx, test in enumerate(TEST_DATASET, 1):
        category_name = test["category"]
        expected = test["expected_keyword"]
        
        start_time = time.time()
        results = retriever.retrieve(test["query"], jurisdiction="European Union")
        elapsed_ms = (time.time() - start_time) * 1000
        total_latency_ms += elapsed_ms

        found = any(expected.lower() in r.text.lower() for r in results)
        if found:
            hits_at_k += 1
            status = "✅ PASS"
        else:
            status = "❌ FAIL"

        top_score = results[0].score if results else 0.0
        method = results[0].retrieval_method if results else "none"

        print(f"[{idx}/{total_tests}] {category_name:<22} | {status} | Latency: {elapsed_ms:5.1f}ms | Method: {method:<20} | Score: {top_score:.4f}")

    recall_at_k = (hits_at_k / total_tests) * 100
    avg_latency = total_latency_ms / total_tests

    print("-" * 65)
    print("📊 SUMMARY METRICS:")
    print(f"   • RRF Retrieval Recall@K: {recall_at_k:.1f}%")
    print(f"   • Avg Retrieval Latency:  {avg_latency:.1f} ms")
    print("=" * 65)

if __name__ == "__main__":
    run_retrieval_benchmark()

