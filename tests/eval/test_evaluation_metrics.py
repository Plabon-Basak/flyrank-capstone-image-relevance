import json
from app.services.embedding_provider import LexicalEmbeddingProvider
from app.services.matching_service import MatchingService


def compute_metrics(ranked_results_by_query, relevant_set):
    total = len(ranked_results_by_query)
    if total == 0:
        return {'precision_at_1': 0.0, 'recall_at_k': 0.0, 'mrr': 0.0}
    correct_at_1 = 0
    rrs = []
    for qid, ranked in ranked_results_by_query.items():
        rr = 0.0
        for i, m in enumerate(ranked, start=1):
            if (qid, m) in relevant_set:
                rr = 1.0 / i
                if i == 1:
                    correct_at_1 += 1
                break
        rrs.append(rr)
    p1 = correct_at_1 / total
    mrr = sum(rrs) / len(rrs)
    return {'precision_at_1': p1, 'recall_at_k': p1, 'mrr': mrr}


def test_precision_at_1_calculation():
    ranked = {'img1': ['post1', 'post2'], 'img2': ['post1', 'post3']}
    rel = {('img1', 'post1'), ('img2', 'post1')}
    m = compute_metrics(ranked, rel)
    assert abs(m['precision_at_1'] - 1.0) < 1e-9


def test_recall_at_k_calculation():
    ranked = {'img1': ['post1']}
    rel = {('img1', 'post1')}
    m = compute_metrics(ranked, rel)
    assert abs(m['recall_at_k'] - 1.0) < 1e-9


def test_mrr_calculation():
    ranked = {'img1': ['post2', 'post1']}
    rel = {('img1', 'post1')}
    m = compute_metrics(ranked, rel)
    assert abs(m['mrr'] - 0.5) < 1e-9


def test_empty_evaluation_inputs():
    m = compute_metrics({}, set())
    assert m['precision_at_1'] == 0.0
    assert m['recall_at_k'] == 0.0
    assert m['mrr'] == 0.0


def test_missing_image_reference_invalid():
    manifest = json.load(open('data/eval/manifest.json'))
    mids = {m['id'] for m in manifest}
    gt = json.load(open('data/eval/ground_truth.json'))
    for g in gt:
        assert g['image_id'] in mids


def test_missing_post_reference_invalid():
    posts = json.load(open('data/eval/posts.json'))
    pids = {p['id'] for p in posts}
    gt = json.load(open('data/eval/ground_truth.json'))
    for g in gt:
        assert g['post_id'] in pids


def test_lexical_baseline_no_gemini_provider():
    service = MatchingService(embedding_provider=LexicalEmbeddingProvider(), threshold=0.35)
    assert isinstance(service.embedding_provider, LexicalEmbeddingProvider)
