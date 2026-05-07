from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document


def load_documents(paths: list[str]) -> list[Document]:
    documents: list[Document] = []

    for raw_path in paths:
        path = Path(raw_path)
        if path.is_dir():
            documents.extend(load_documents([str(item) for item in path.rglob("*") if item.is_file()]))
            continue

        suffix = path.suffix.lower()
        if suffix == ".pdf":
            documents.extend(PyPDFLoader(str(path)).load())
        elif suffix in {".txt", ".md"}:
            documents.extend(TextLoader(str(path), encoding="utf-8").load())
        else:
            raise ValueError(f"Unsupported file type: {path}")

    return documents
