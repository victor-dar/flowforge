import re
from io import BytesIO

from pypdf import PdfReader


class DocumentProcessingError(ValueError):
    status_code = 422


class UnsupportedDocumentType(DocumentProcessingError):
    status_code = 415


class DocumentUploadTooLarge(DocumentProcessingError):
    status_code = 413


class DocumentTextTooLarge(DocumentProcessingError):
    status_code = 413


class EmptyDocumentContent(DocumentProcessingError):
    status_code = 422


class DocumentExtractionFailed(DocumentProcessingError):
    status_code = 422


def extract_document_text(
    filename: str,
    content_type: str | None,
    data: bytes,
    max_upload_bytes: int,
    max_text_characters: int,
) -> str:
    if len(data) > max_upload_bytes:
        raise DocumentUploadTooLarge("O arquivo excede o limite configurado de upload.")

    is_pdf = filename.lower().endswith(".pdf") or content_type == "application/pdf"
    is_text = filename.lower().endswith((".txt", ".md", ".csv"))
    if not is_pdf and not is_text:
        raise UnsupportedDocumentType(
            "Formato não suportado. Envie PDF, TXT, MD ou CSV."
        )

    if is_pdf:
        try:
            reader = PdfReader(BytesIO(data))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:
            raise DocumentExtractionFailed("Não foi possível extrair texto do PDF.") from exc
    else:
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise DocumentExtractionFailed(
                "O arquivo de texto não está codificado em UTF-8."
            ) from exc

    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        raise EmptyDocumentContent("O arquivo não contém texto extraível.")
    if len(normalized) > max_text_characters:
        raise DocumentTextTooLarge(
            f"O texto extraído excede o limite de {max_text_characters} caracteres."
        )

    return normalized
