import json
from io import BytesIO
from pathlib import Path

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.documents import (
    DocumentExtractionFailed,
    DocumentTextTooLarge,
    DocumentUploadTooLarge,
    EmptyDocumentContent,
    UnsupportedDocumentType,
    extract_document_text,
)
from app.ai import chunk_text, cosine_similarity, relevant_context


FIXTURES = Path(__file__).parent / "fixtures" / "rag_eval"


def make_pdf(text: str | None) -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)

    if text is not None:
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
                NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
            }
        )
        page[NameObject("/Resources")] = DictionaryObject(
            {
                NameObject("/Font"): DictionaryObject(
                    {NameObject("/F1"): writer._add_object(font)}
                )
            }
        )
        content = DecodedStreamObject()
        content.set_data(
            f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("ascii")
        )
        page[NameObject("/Contents")] = writer._add_object(content)

    output = BytesIO()
    writer.write(output)
    return output.getvalue()


@pytest.mark.parametrize(
    ("filename", "content_type", "data", "expected"),
    [
        ("guia.txt", "text/plain", "Olá, você está em São Paulo.".encode(), "Olá, você está em São Paulo."),
        ("guia.txt", "text/plain", b"\xef\xbb\xbfOl\xc3\xa1, a\xc3\xa7\xc3\xa3o.", "Olá, ação."),
        (
            "guia.md",
            "text/markdown",
            "# Informações\n\nAtendimento cordial.".encode(),
            "# Informações Atendimento cordial.",
        ),
        ("dados.csv", "text/csv", "item,preço\ncafé, R$ 5,00".encode(), "item,preço café, R$ 5,00"),
    ],
)
def test_extracts_supported_utf8_text_formats(
    filename, content_type, data, expected
):
    assert extract_document_text(filename, content_type, data, 1024, 1024) == expected


def test_extracts_selectable_pdf_text():
    pdf = make_pdf("Selectable PDF text.")

    assert (
        extract_document_text("manual.pdf", "application/pdf", pdf, 1024 * 1024, 1024)
        == "Selectable PDF text."
    )


def test_pdf_without_extractable_text_is_rejected():
    with pytest.raises(EmptyDocumentContent, match="não contém texto extraível"):
        extract_document_text("blank.pdf", "application/pdf", make_pdf(None), 1024, 1024)


@pytest.mark.parametrize(
    ("filename", "content_type", "data", "error", "message"),
    [
        ("empty.txt", "text/plain", b"", EmptyDocumentContent, "não contém texto"),
        ("broken.pdf", "application/pdf", b"not a pdf", DocumentExtractionFailed, "PDF"),
        ("bad.txt", "text/plain", b"\xff\xfe", DocumentExtractionFailed, "UTF-8"),
        ("file.exe", "application/octet-stream", b"data", UnsupportedDocumentType, "Formato"),
    ],
)
def test_rejects_empty_or_invalid_document_content(
    filename, content_type, data, error, message
):
    with pytest.raises(error, match=message):
        extract_document_text(filename, content_type, data, 1024, 1024)


def test_rejects_extracted_text_above_character_limit_instead_of_truncating():
    with pytest.raises(DocumentTextTooLarge, match="limite de 5 caracteres"):
        extract_document_text("large.txt", "text/plain", b"seis!!", 1024, 5)


def test_rejects_upload_above_byte_limit():
    with pytest.raises(DocumentUploadTooLarge, match="limite configurado"):
        extract_document_text("file.txt", "text/plain", b"12345", 4, 100)


def test_hybrid_lexical_context_ranks_relevant_paraphrase():
    documents = [
        "O suporte envia a primeira resposta em até um dia útil.",
        "Pedidos podem ser cancelados sem custo até 24 horas.",
    ]

    context = relevant_context(
        "Em quanto tempo alguém costuma me responder?",
        documents,
    )

    assert "primeira resposta" in context


def test_cosine_similarity_handles_valid_vectors_and_edge_cases():
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    assert cosine_similarity([], []) == 0.0
    assert cosine_similarity([1.0], [1.0, 2.0]) == 0.0


def test_chunk_text_splits_large_document_with_overlap():
    text = "A" * 1200
    chunks = chunk_text(text, chunk_size=500, overlap=50)

    assert len(chunks) == 3
    assert chunks[0][-50:] == chunks[1][:50]


def test_evaluation_corpus_has_unique_questions_and_valid_source_excerpts():
    corpus = json.loads((FIXTURES / "questions.json").read_text(encoding="utf-8"))
    questions = corpus["questions"]
    question_ids = [question["id"] for question in questions]
    categories = {question["category"] for question in questions}
    all_documents = {
        document
        for documents in corpus["chatbots"].values()
        for document in documents
    }

    assert len(question_ids) == len(set(question_ids))
    assert len(questions) == 11
    assert {
        "direct_answer",
        "paraphrase",
        "no_answer",
        "multi_document",
        "chatbot_isolation",
    } <= categories

    for question in questions:
        assert question["id"]
        assert question["question"]
        assert question["category"]
        assert question["chatbot_id"] in corpus["chatbots"]
        allowed_documents = set(corpus["chatbots"][question["chatbot_id"]])
        expected_documents = set(question["expected_documents"])
        assert expected_documents <= all_documents
        assert expected_documents <= allowed_documents
        assert {item["document"] for item in question["reference_excerpts"]} == expected_documents
        for excerpt in question["reference_excerpts"]:
            document = (FIXTURES / excerpt["document"]).read_text(encoding="utf-8")
            assert excerpt["text"] in document
        if question["category"] == "chatbot_isolation":
            forbidden_documents = set(question["must_not_use_documents"])
            assert forbidden_documents <= all_documents
            assert forbidden_documents.isdisjoint(allowed_documents)
        if question["category"] in {"no_answer", "chatbot_isolation"}:
            assert not expected_documents
            assert question["expected_behavior"] == "abstain"


def test_upload_endpoint_rejects_empty_malformed_pdf_and_truncated_text(
    client, monkeypatch
):
    from app.config import settings

    response = client.post(
        "/api/auth/register",
        json={"email": "documents@example.com", "password": "senha-segura-123"},
    )
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    bot = client.post(
        "/api/bots",
        headers=headers,
        json={"name": "Processamento"},
    ).json()
    url = f"/api/bots/{bot['id']}/documents"

    empty = client.post(
        url,
        headers=headers,
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    malformed_pdf = client.post(
        url,
        headers=headers,
        files={"file": ("broken.pdf", b"invalid pdf", "application/pdf")},
    )
    assert empty.status_code == 422
    assert "não contém texto extraível" in empty.json()["detail"]
    assert malformed_pdf.status_code == 422
    assert "PDF" in malformed_pdf.json()["detail"]

    monkeypatch.setattr(settings, "max_document_characters", 5)
    too_many_characters = client.post(
        url,
        headers=headers,
        files={"file": ("large.txt", b"seis!!", "text/plain")},
    )
    assert too_many_characters.status_code == 413
    assert "limite de 5 caracteres" in too_many_characters.json()["detail"]
    assert client.get(url, headers=headers).json() == []
