import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from my_project.chain import build_chat_chain, build_rag_chain
from my_project.loader import load_documents
from my_project.retriever import build_retriever


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LangChain personal LLM app")
    parser.add_argument("--query", required=True, help="Question to ask")
    parser.add_argument("--data-path", nargs="*", default=[], help="PDF, TXT, MD file or directory paths for RAG")
    parser.add_argument("--persist-dir", default="chroma_db", help="Chroma persistence directory")
    parser.add_argument("--model", default="solar-pro", help="Upstage chat model name")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()

    if not os.getenv("UPSTAGE_API_KEY"):
        raise RuntimeError("UPSTAGE_API_KEY is missing. Create .env from .env.example and add your key.")

    if args.data_path:
        documents = load_documents(args.data_path)
        retriever = build_retriever(documents, persist_directory=args.persist_dir)
        chain = build_rag_chain(retriever, model=args.model)
        answer = chain.invoke(args.query)
    else:
        chain = build_chat_chain(model=args.model)
        answer = chain.invoke({"question": args.query})

    print(answer)


if __name__ == "__main__":
    main()
