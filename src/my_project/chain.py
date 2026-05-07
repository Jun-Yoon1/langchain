from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnablePassthrough
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_upstage import ChatUpstage


def build_chat_chain(model: str = "solar-pro") -> Runnable:
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a helpful Korean assistant. Answer clearly and concisely.",
            ),
            ("human", "{question}"),
        ]
    )
    llm = ChatUpstage(model=model)
    return prompt | llm | StrOutputParser()


def build_rag_chain(
    retriever: VectorStoreRetriever,
    model: str = "solar-pro",
) -> Runnable:
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Answer the question using only the reference documents. "
                'If the answer is not in the documents, say "확인할 수 없습니다".\n\n'
                "Reference documents:\n{context}",
            ),
            ("human", "{question}"),
        ]
    )
    llm = ChatUpstage(model=model)

    return (
        {
            "context": retriever | _format_documents,
            "question": RunnablePassthrough(),
        }
        | prompt
        | llm
        | StrOutputParser()
    )


def _format_documents(documents: list[Document]) -> str:
    return "\n\n".join(document.page_content for document in documents)
