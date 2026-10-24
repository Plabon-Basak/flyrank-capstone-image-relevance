import json
import os
from PIL import Image


def test_manifest_loads():
    manifest = json.load(open('data/eval/manifest.json'))
    assert isinstance(manifest, list)
    assert len(manifest) >= 40


def test_manifest_has_required_fields():
    manifest = json.load(open('data/eval/manifest.json'))
    required = {'id', 'filename', 'path', 'category', 'subject', 'source', 'license', 'attribution'}
    for entry in manifest:
        assert required.issubset(entry.keys()), entry


def test_all_images_readable():
    manifest = json.load(open('data/eval/manifest.json'))
    for entry in manifest:
        p = entry['path']
        assert os.path.exists(p), f'Missing image: {p}'
        img = Image.open(p)
        img.verify()


def test_categories_present():
    manifest = json.load(open('data/eval/manifest.json'))
    cats = set(m['category'] for m in manifest)
    assert len(cats) >= 4
    assert cats.issuperset({'wildlife', 'technology', 'food', 'travel'})


def test_posts_load():
    posts = json.load(open('data/eval/posts.json'))
    assert isinstance(posts, list)
    assert len(posts) >= 10
    for p in posts:
        assert p.get('id')
        assert p.get('title')
        assert p.get('content') and len(p['content']) > 10


def test_ground_truth_load():
    gt = json.load(open('data/eval/ground_truth.json'))
    assert isinstance(gt, list)
    assert len(gt) >= 20


def test_ground_truth_valid_references():
    manifest = json.load(open('data/eval/manifest.json'))
    posts = json.load(open('data/eval/posts.json'))
    gt = json.load(open('data/eval/ground_truth.json'))
    mids = {m['id'] for m in manifest}
    pids = {p['id'] for p in posts}
    for g in gt:
        assert g['image_id'] in mids, f'Invalid image ref: {g}'
        assert g['post_id'] in pids, f'Invalid post ref: {g}'
