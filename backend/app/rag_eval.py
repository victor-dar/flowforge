import json
import unicodedata
from pathlib import Path
from typing import Iterable

from app.ai import relevant_context


FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "rag_eval"


def normalize_text(text: str) -> str:
    return "".join(
        char
        for char in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(char)
    ).lower()


def evaluate_corpus(corpus_path: Path | None = None) -> dict:
    corpus_path = corpus_path or FIXTURES / "questions.json"
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    results: list[dict] = []

    for question in corpus["questions"]:
        document_names = corpus["chatbots"][question["chatbot_id"]]
        documents = [
            (FIXTURES / name).read_text(encoding="utf-8")
            for name in document_names
        ]
        context = relevant_context(question["question"], documents, limit=4)
        normalized_context = normalize_text(context)
        expected = [
            normalize_text(excerpt["text"])
            for excerpt in question["reference_excerpts"]
        ]
        found_expected = sum(
            1
            for excerpt in expected
            if excerpt in normalized_context
        )
        forbidden_names = question.get("must_not_use_documents", [])
        forbidden = [
            normalize_text((FIXTURES / name).read_text(encoding="utf-8")[:300])
            for name in forbidden_names
        ]
        contains_forbidden = any(
            fragment and fragment in normalized_context
            for fragment in forbidden
        )

        if question["expected_behavior"] == "abstain":
            is_relevant = not context.strip() or not contains_forbidden
        else:
            is_relevant = found_expected == len(expected)

        reciprocal_rank = 0.0
        if expected:
            chunks = [
                normalize_text(chunk)
                for chunk in context.split("\n")
                if chunk.strip()
            ]
            for rank, chunk in enumerate(chunks, start=1):
                if any(excerpt in chunk for excerpt in expected):
                    reciprocal_rank = 1 / rank
                    break

        results.append(
            {
                "id": question["id"],
                "category": question["category"],
                "relevant": is_relevant,
                "expected_retrieval": found_expected,
                "expected_count": len(expected),
                "contains_forbidden": contains_forbidden,
                "reciprocal_rank": reciprocal_rank,
            }
        )

    relevant = [item for item in results if item["category"] != "chatbot_isolation"]
    source_answers = [
        item
        for item in relevant
        if item["expected_count"] > 0
    ]
    source_recall = (
        sum(item["expected_retrieval"] for item in source_answers)
        / sum(item["expected_count"] for item in source_answers)
        if source_answers
        else 1.0
    )
    answer_success = (
        sum(bool(item["relevant"]) for item in source_answers)
        / len(source_answers)
        if source_answers
        else 1.0
    )
    isolation_success = (
        sum(
            1
            for item in results
            if item["category"] == "chatbot_isolation" and not item["contains_forbidden"]
        )
        / sum(1 for item in results if item["category"] == "chatbot_isolation")
        if any(item["category"] == "chatbot_isolation" for item in results)
        else 1.0
    )
    mrr = (
        sum(item["reciprocal_rank"] for item in source_answers)
        / len(source_answers)
        if source_answers
        else 0.0
    )

    return {
        "question_count": len(results),
        "source_recall": round(source_recall, 4),
        "answer_success": round(answer_success, 4),
        "chatbot_isolation": round(isolation_success, 4),
        "mrr": round(mrr, 4),
        "results": results,
    }


def main() -> None:
    print(json.dumps(evaluate_corpus(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
