
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.services.embedding_provider import LexicalEmbeddingProvider
from app.services.matching_service import MatchingService


CASES = [
    {
        "subject": "Red fox",
        "category": "wildlife",
        "caption": "A red fox standing in a forest.",
        "attributes": {"animal": "fox", "color": "red"},
        "relevant_title": "Red Foxes in Forest Habitats",
        "relevant_content": "Red foxes are wild mammals that live in forests and grasslands.",
        "distractor_title": "Preparing Healthy Vegetable Soup",
        "distractor_content": "A simple recipe using carrots, potatoes, and onions.",
    },
    {
        "subject": "Gray wolf",
        "category": "wildlife",
        "caption": "A gray wolf walking through a forest.",
        "attributes": {"animal": "wolf", "color": "gray"},
        "relevant_title": "Gray Wolves and Their Natural Habitats",
        "relevant_content": "Gray wolves are wild animals that hunt and live in forests.",
        "distractor_title": "Training Pet Dogs at Home",
        "distractor_content": "Dog training teaches pets basic commands and good behavior.",
    },
    {
        "subject": "Domestic cat",
        "category": "wildlife",
        "caption": "A domestic cat sitting on grass.",
        "attributes": {"animal": "cat"},
        "relevant_title": "Domestic Cats and Their Behavior",
        "relevant_content": "Domestic cats are familiar animals known for their behavior.",
        "distractor_title": "Elephants in African Wildlife",
        "distractor_content": "Elephants are large wild mammals that live in Africa.",
    },
    {
        "subject": "Lion",
        "category": "wildlife",
        "caption": "A lion resting in grassland.",
        "attributes": {"animal": "lion"},
        "relevant_title": "Lions in African Grasslands",
        "relevant_content": "Lions are wild cats that inhabit African grasslands.",
        "distractor_title": "How to Care for a Pet Cat",
        "distractor_content": "Pet cats need food, water, and regular care.",
    },
    {
        "subject": "Elephant",
        "category": "wildlife",
        "caption": "An elephant walking in its natural habitat.",
        "attributes": {"animal": "elephant"},
        "relevant_title": "Elephants and Wildlife Conservation",
        "relevant_content": "Elephants are large wild mammals important to conservation.",
        "distractor_title": "A Guide to Domestic Dogs",
        "distractor_content": "Dogs are popular pets and companions for families.",
    },
    {
        "subject": "Bird",
        "category": "wildlife",
        "caption": "A bird perched on a tree branch.",
        "attributes": {"animal": "bird"},
        "relevant_title": "Birds Living in Forest Ecosystems",
        "relevant_content": "Birds perch in trees and inhabit many forest ecosystems.",
        "distractor_title": "Growing Vegetables in a Garden",
        "distractor_content": "Gardeners grow vegetables in soil with water and sunlight.",
    },
    {
        "subject": "Laptop computer",
        "category": "technology",
        "caption": "A laptop computer on a desk.",
        "attributes": {"device": "laptop"},
        "relevant_title": "Choosing a Laptop Computer",
        "relevant_content": "Laptop computers are portable devices used for work and study.",
        "distractor_title": "Planning a Forest Hiking Trip",
        "distractor_content": "Hiking trips explore forests and outdoor destinations.",
    },
    {
        "subject": "Smartphone",
        "category": "technology",
        "caption": "A smartphone displaying a mobile application.",
        "attributes": {"device": "smartphone"},
        "relevant_title": "Smartphone Applications and Mobile Technology",
        "relevant_content": "Smartphones run mobile applications and digital services.",
        "distractor_title": "Wildlife Photography in Forests",
        "distractor_content": "Photographers capture wild animals in forest habitats.",
    },
    {
        "subject": "Travel backpack",
        "category": "travel",
        "caption": "A backpack prepared for a hiking trip.",
        "attributes": {"item": "backpack"},
        "relevant_title": "Packing a Backpack for Travel",
        "relevant_content": "A travel backpack carries essentials for hiking and trips.",
        "distractor_title": "Programming Software for Beginners",
        "distractor_content": "Software development involves writing and testing computer code.",
    },
    {
        "subject": "Vegetable soup",
        "category": "food",
        "caption": "A bowl of homemade vegetable soup.",
        "attributes": {"dish": "soup", "food": "vegetables"},
        "relevant_title": "Homemade Vegetable Soup Recipe",
        "relevant_content": "Prepare vegetable soup with carrots, potatoes, and fresh ingredients.",
        "distractor_title": "Laptop Hardware and Computer Software",
        "distractor_content": "Computer hardware and software support digital work.",
    },
]


def make_post(post_id, title, content):
    return SimpleNamespace(
        id=post_id,
        title=title,
        content=content,
        url=f"https://example.com/evaluation/{post_id}",
    )


def main():
    service = MatchingService(
        embedding_provider=LexicalEmbeddingProvider(),
        threshold=settings.matching_threshold,
    )

    correct_top1 = 0
    accepted = 0
    accepted_correct = 0

    print(f"Provider: lexical baseline")
    print(f"Threshold: {settings.matching_threshold:.2f}")
    print(f"Evaluation cases: {len(CASES)}")
    print("-" * 60)

    for index, case in enumerate(CASES, start=1):
        image = SimpleNamespace(
            id=index,
            filename=f"evaluation_{index}.jpg",
            file_path=f"data/evaluation_{index}.jpg",
            subject=case["subject"],
            category=case["category"],
            attributes=case["attributes"],
            caption=case["caption"],
            confidence=0.96,
        )

        relevant_post = make_post(
            index * 2,
            case["relevant_title"],
            case["relevant_content"],
        )
        distractor_post = make_post(
            index * 2 + 1,
            case["distractor_title"],
            case["distractor_content"],
        )

        result = service.match(image, [relevant_post, distractor_post])
        ranked = result["matches"]

        top1_id = ranked[0]["blog_post_id"] if ranked else None
        is_correct = top1_id == relevant_post.id
        is_accepted = result["status"] == "matched"

        correct_top1 += int(is_correct)
        accepted += int(is_accepted)
        accepted_correct += int(is_accepted and is_correct)

        print(
            f"{index:02d}. {case['subject']}: "
            f"top-1={'correct' if is_correct else 'incorrect'}, "
            f"status={result['status']}"
        )

    total = len(CASES)
    precision = correct_top1 / total
    acceptance_rate = accepted / total
    accepted_precision = (
        accepted_correct / accepted if accepted else 0.0
    )

    print("-" * 60)
    print(f"Top-1 precision: {correct_top1}/{total} = {precision:.1%}")
    print(f"Accepted matches: {accepted}/{total} = {acceptance_rate:.1%}")
    print(
        "Precision among accepted matches: "
        f"{accepted_correct}/{accepted} = {accepted_precision:.1%}"
        if accepted
        else "Precision among accepted matches: N/A (no accepted matches)"
    )
    print("Dataset: 10 manually labeled, synthetic evaluation cases.")
    print("These results do not establish real-world or neural-model accuracy.")


if __name__ == "__main__":
    main()
