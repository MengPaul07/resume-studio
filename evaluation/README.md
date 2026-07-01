# RAG Evaluation

Isolated from the main app. Evaluates JD retrieval quality **only** — does not touch agent logic.

## Structure

```
evaluation/
├── README.md
├── generate_data.py      # Generate synthetic JDs + labeled queries via LLM
├── run_eval.py           # Run retrieval eval, compute Recall@k / MRR / NDCG
├── fixtures/
│   └── jds/              # Generated JDs (seed into FAISS)
├── eval_queries.json     # Generated: labeled queries
└── results/
    └── report.md         # Latest run metrics
```

## Quick Start

```bash
# 1. Generate test data (needs API key)
python evaluation/generate_data.py

# 2. Run evaluation
python evaluation/run_eval.py

# 3. View results
cat evaluation/results/report.md
```

## Metrics

| Metric | Target | Why |
|--------|--------|-----|
| Recall@5 | ≥ 0.70 | Top 5 must capture 70% of relevant JDs |
| Recall@10 | ≥ 0.85 | Wider window as safety net |
| MRR | ≥ 0.50 | First relevant result shouldn't be buried |
| Hit Rate | ≥ 0.85 | Most queries should find at least one match |

## Experiments

Each run compares:
- **FAISS only** (distance-sorted top-k)
- **FAISS + reranker** (cross-encoder re-scored top-k)

The delta between them quantifies reranker contribution.
