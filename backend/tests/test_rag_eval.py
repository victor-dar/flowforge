import json
from pathlib import Path

from app.ai import relevant_context


FIXTURES = Path(__file__).parent / "fixtures" / "rag_eval"


def test_rag_corpus_retrieval_metrics():
    corpus = json.loads((FIXTURES / "questions.json").read_text(encoding="utf-8"))
    scored = {"answer_from_sources": [], "abstain": []}

    for question in corpus["questions"]:
        documents = [
            (FIXTURES / name).read_text(encoding="utf-8")
            for name in corpus["chatbots"][question["chatbot_id"]]
        ]
        context = relevant_context(question["question"], documents, limit=4)

        if question["expected_behavior"] == "abstain":
            forbidden = [
                (FIXTURES / name).read_text(encoding="utf-8")
                for name in question.get("must_not_use_documents", [])
            ]
            retrieved_forbidden = any(text[:300] in context for text in forbidden)
            scored["abstain"].append(not retrieved_forbidden)
            continue

        expected_text = [
            excerpt["text"]
            for excerpt in question["reference_excerpts"]
        ]
        scored["answer_from_sources"].append(
            all(text.lower() in context.lower() for text in expected_text)
        )

    source_recall = sum(scored["answer_from_sources"]) / len(scored["answer_from_sources"])
    abstain_rate = sum(scored["abstain"]) / len(scored["abstain"])

    assert source_recall >= 0.70
    assert abstain_rate >= 0.80
