import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.embedding_provider import LexicalEmbeddingProvider
from app.services.matching_service import MatchingService


def main():
    manifest = json.load(open('data/eval/manifest.json'))
    posts = json.load(open('data/eval/posts.json'))
    ground_truth = json.load(open('data/eval/ground_truth.json'))

    relevant = set((g['image_id'], g['post_id']) for g in ground_truth)
    service = MatchingService(embedding_provider=LexicalEmbeddingProvider(), threshold=0.35)

    total_queries = len(manifest)
    correct_at_1 = 0
    reciprocal_ranks = []

    print('Provider: lexical baseline (text-derived from metadata)')
    print(f'Images: {len(manifest)}, Posts: {len(posts)}, Ground truth pairs: {len(relevant)}')
    print('-' * 60)

    for img in manifest:
        image = SimpleNamespace(id=img['id'], filename=img['filename'], file_path=img['path'], subject=img['subject'], category=img['category'], attributes={}, caption=img['subject'] + ' - ' + img['category'], confidence=0.96)
        blog_posts = []
        for p in posts:
            blog_posts.append(SimpleNamespace(id=p['id'], title=p['title'], content=p['content'], url='https://example.com/' + p['id']))
        result = service.match(image, blog_posts)
        ranked = result.get('matches', [])
        rr = 0.0
        for i, m in enumerate(ranked, start=1):
            if (image.id, m['blog_post_id']) in relevant:
                rr = 1.0 / i
                if i == 1:
                    correct_at_1 += 1
                break
        reciprocal_ranks.append(rr)

    precision_at_1 = correct_at_1 / total_queries if total_queries else 0.0
    mrr = sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0

    print(f'Precision@1: {correct_at_1}/{total_queries} = {precision_at_1:.3f}')
    print(f'MRR: {mrr:.3f}')
    print('-' * 60)
    print('Dataset: Real images from Lorem Picsum with recorded sources/licenses/attribution')
    print('NOTE: Using lexical baseline (text-derived). Not evaluating Gemini embeddings/API/full pipeline.')


if __name__ == '__main__':
    main()
