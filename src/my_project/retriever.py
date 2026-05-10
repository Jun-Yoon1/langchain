from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.tools import tool
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_upstage import UpstageEmbeddings

from .api_limits import create_query_limiter

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHROMA_DIR = str(PROJECT_ROOT / "data" / "chroma_db")
COLLECTION_NAME = "lecture_materials"

_api_limiter = create_query_limiter()
_api_cache: dict[tuple[str, str], str] = {}


def split_documents(documents: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
    return splitter.split_documents(documents)


def build_retriever(
    documents: list[Document],
    persist_directory: str = CHROMA_DIR,
    collection_name: str = COLLECTION_NAME,
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


def _build_lecture_retriever() -> VectorStoreRetriever:
    query_embeddings = UpstageEmbeddings(model="solar-embedding-1-large")
    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        persist_directory=CHROMA_DIR,
        embedding_function=query_embeddings,
    )
    return vectorstore.as_retriever(search_kwargs={"k": 3})


def get_lecture_tool(api_limiter=None, api_cache=None):
    """Return the lecture search tool bound to the given limiter/cache."""
    limiter = api_limiter or _api_limiter
    cache = api_cache if api_cache is not None else _api_cache
    lecture_retriever = None

    @tool
    def search_lecture_materials(query: str) -> str:
        """Search lecture PDFs for LangChain pipeline patterns such as RAG, Agent, tools, LangGraph, and multi-agent design."""
        nonlocal lecture_retriever
        cache_key = ("lecture", query)
        if cache_key in cache:
            return cache[cache_key]
        try:
            if lecture_retriever is None:
                lecture_retriever = _build_lecture_retriever()
            docs = limiter.run("upstage_embedding", lambda: lecture_retriever.invoke(query))
            if not docs:
                return "No relevant lecture material found."

            formatted = []
            for doc in docs:
                source = Path(doc.metadata.get("source", "unknown")).name
                page = doc.metadata.get("page", "?")
                formatted.append(f"[{source} p.{page}]\n{doc.page_content[:500]}")
            result = "\n\n".join(formatted)
            cache[cache_key] = result
            return result
        except Exception as exc:
            return f"Lecture search failed: {exc}"

    return search_lecture_materials
