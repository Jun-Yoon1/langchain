from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_upstage import UpstageEmbeddings


def split_documents(documents: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
    return splitter.split_documents(documents)


def build_retriever(
    documents: list[Document],
    persist_directory: str = str(Path(__file__).resolve().parents[2] / "data" / "chroma_db"),
    collection_name: str = "project_docs",
    k: int = 4,
) -> VectorStoreRetriever:
    chunks = split_documents(documents)
    embeddings = UpstageEmbeddings(model="solar-embedding-1-large")
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=collection_name,
        persist_directory=persist_directory,
    )
    return vectorstore.as_retriever(search_kwargs={"k": k})
