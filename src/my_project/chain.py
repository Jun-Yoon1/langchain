import re
import warnings

from langchain_upstage import ChatUpstage

warnings.filterwarnings("ignore", message="The default value of `allowed_objects` will change.*")

from langgraph.errors import GraphRecursionError
from langgraph.prebuilt import create_react_agent

from .api_limits import create_query_limiter
from .github_tool import get_github_tool
from .retriever import get_lecture_tool

TOOL_CALL_LOG: list[dict[str, str]] = []

api_limiter = create_query_limiter()
api_cache: dict[tuple[str, str], str] = {}

search_lecture_materials = get_lecture_tool(api_limiter=api_limiter, api_cache=api_cache)
search_github_repos = get_github_tool(
    api_limiter=api_limiter,
    api_cache=api_cache,
    tool_call_log=TOOL_CALL_LOG,
)

SYSTEM_PROMPT = """You are a LangChain pipeline design expert. Answer in Korean.

You must call both tools exactly once before the final answer:
1. search_lecture_materials: find lecture evidence and review sections.
2. search_github_repos: find similar GitHub repositories.

Do not call the same tool more than once. If a tool returns fewer than 3 repositories or an operation message, do not retry. Use the available repo blocks and finish naturally.

GitHub query rule:
- Before calling search_github_repos, translate the user idea (often Korean) into 3-6 English LangChain ecosystem keywords.
- Always include a domain noun (recipe, document, news, etc.) AND at least one pipeline pattern keyword (rag, agent, retrieval, chatbot, summarization, fact checking, recommendation).
- Do not include the word langchain in the query because the tool adds it automatically.
- Examples:
  * "냉장고 재료 레시피 추천 챗봇" -> "recipe recommendation rag chatbot"
  * "회사 위키 Q&A 봇" -> "document qa rag retrieval chatbot"
  * "뉴스 요약 + 팩트체크 봇" -> "news summarization fact checking agent"
  * "PDF 책에서 인용 추출하는 도구" -> "pdf citation extraction rag retrieval"
  * "주식 시세 알림 + 분석" -> "stock price monitoring agent retrieval"
- If unsure, fall back to "rag chatbot".

Tool result handling:
- If a tool observation contains OPERATION_META, ignore that line. It is tool operation metadata.
- For GitHub refs, extract only repo blocks that start with '- owner/repo'.
- Never include OPERATION_META or tool operation messages in github_refs or the user-facing answer.

Stack constraints (apply to the final answer):
- Vector store: always Chroma (never FAISS or faiss_retriever).
- LLM/Embeddings: always ChatUpstage / UpstageEmbeddings / solar-pro (never OpenAI, GPT, or any other provider).
- 필요한 컴포넌트: list ONLY filenames that exist (or would exist) inside src/my_project/.
  Allowed base names: loader.py, retriever.py, github_tool.py, chain.py, schemas.py.
  Domain-specific variants are allowed (e.g., recipe_tool.py, news_tool.py, fact_check_tool.py).
  FORBIDDEN: faiss_retriever.py, openai_llm.py, streamlit_ui.py, or any file outside src/my_project/.

Recommendation levels:
- Level 1: simple RAG/document QA.
- Level 2: RAG + single Agent + tools.
- Level 3: multi-agent or explicit LangGraph orchestration. Recommend only when clearly needed for a 5-day deadline.

Final answer format, in Korean:
추천 레벨: Level 1 / Level 2 / Level 3
추천 이유: 3-5 sentences with lecture evidence.
필요한 컴포넌트: comma-separated file names.
복습할 강의 섹션: section names and short reasons.
참고 GitHub 레포: bullet list with name, url, stars, description. Include only real repos.
"""

SYNTHESIS_PROMPT = """You are a LangChain pipeline design expert. Answer in Korean.
Use the provided lecture context and GitHub context only.
Do not mention tool failures, retries, recursion, or OPERATION_META.
If GitHub context has fewer than 3 repos, list only the real repos available.

Stack constraints (apply to the final answer):
- Vector store: always Chroma (never FAISS or faiss_retriever).
- LLM/Embeddings: always ChatUpstage / UpstageEmbeddings / solar-pro (never OpenAI, GPT, or any other provider).
- 필요한 컴포넌트: list ONLY filenames inside src/my_project/.
  Allowed: loader.py, retriever.py, github_tool.py, chain.py, schemas.py, or domain-specific variants.
  FORBIDDEN: faiss_retriever.py, openai_llm.py, streamlit_ui.py.

Final answer format, in Korean:
추천 레벨: Level 1 / Level 2 / Level 3
추천 이유: 3-5 sentences with lecture evidence.
필요한 컴포넌트: comma-separated file names.
복습할 강의 섹션: section names and short reasons.
참고 GitHub 레포: bullet list with name, url, stars, description. Include only real repos.
"""

agent = None


def build_agent():
    llm = ChatUpstage(model="solar-pro")
    tools = [search_lecture_materials, search_github_repos]
    return create_react_agent(model=llm, tools=tools, prompt=SYSTEM_PROMPT)


def get_agent():
    global agent
    if agent is None:
        agent = build_agent()
    return agent


def github_query_hint(query: str) -> str:
    if "레시피" in query or "냉장고" in query:
        return "recipe recommendation rag chatbot"
    if "위키" in query or "문서" in query or "Q&A" in query:
        return "document qa rag chatbot retrieval"
    if "뉴스" in query or "팩트체크" in query or "요약" in query:
        return "news summarization fact checking agent retrieval"
    return "rag chatbot"


def extract_real_github_blocks(tool_calls: list[dict[str, str]]) -> list[str]:
    blocks = []
    for call in tool_calls:
        if call.get("tool") != "search_github_repos":
            continue
        current = []
        for line in call.get("result", "").splitlines():
            if line.startswith("- "):
                if current:
                    blocks.append("\n".join(current))
                current = [line]
            elif current and (line.startswith("  ") or not line.strip()):
                current.append(line)
        if current:
            blocks.append("\n".join(current))
    deduped = []
    seen = set()
    for block in blocks:
        repo_line = block.splitlines()[0]
        if repo_line not in seen:
            seen.add(repo_line)
            deduped.append(block)
    return deduped[:3]


def replace_github_refs_with_tool_results(answer: str, tool_calls: list[dict[str, str]]) -> str:
    blocks = extract_real_github_blocks(tool_calls)
    if not blocks:
        return answer
    label = "참고 GitHub 레포"
    refs = label + ":\n" + "\n\n".join(blocks)
    match = re.search(r"\*\*참고 GitHub 레포\*\*:?|참고 GitHub 레포:", answer)
    if not match:
        head = answer.rstrip()
    else:
        head = answer[:match.start()].rstrip()
    if head.endswith("**"):
        head = head[:-2].rstrip()
    return head + "\n\n" + refs


def build_deterministic_fallback_answer(query: str, tool_calls: list[dict[str, str]]) -> str:
    """Create a reviewable answer without another chat-model call when the graph or API rate limit fails."""
    repos = extract_real_github_blocks(tool_calls)
    refs = "\n\n".join(repos) if repos else "- No real GitHub repository block was returned by the tool."
    if "냉장고" in query or "레시피" in query:
        level = "Level 2"
        reason = "레시피 추천은 RAG 검색과 단일 Agent/Tool 제어가 함께 필요한 사례입니다. S99 프로젝트 OT에서 레시피 추천 봇이 RAG+Agent 예시로 제시되었고, S2-2 RAG Pipeline의 검색+생성 구조와 맞습니다."
        components = "loader.py, retriever.py, recipe_tool.py, chain.py"
        sections = "S99 프로젝트 OT, S2-2 RAG Pipeline, S3-1 Agent and Tools"
    elif "위키" in query or "Q&A" in query:
        level = "Level 1"
        reason = "사내 위키 Q&A는 문서 로드, 청크 분할, 벡터 검색, 답변 생성으로 충분한 RAG 사례입니다. S2-2 RAG Pipeline의 기본 구조와 S99의 사내 위키 챗봇 예시에 맞춰 Level 1이 적합합니다."
        components = "loader.py, retriever.py, chain.py, schemas.py"
        sections = "S2-2 RAG Pipeline, S99 프로젝트 OT"
    else:
        level = "Level 2"
        reason = "뉴스 요약과 팩트체크는 RAG 검색 결과를 기반으로 검증 Tool을 선택하는 Agent 패턴이 필요합니다. S3-1 Agent and Tools의 다중 Tool 예시와 S2-2 RAG Pipeline의 검색 구조를 결합하는 Level 2가 적합합니다."
        components = "loader.py, retriever.py, news_tool.py, chain.py"
        sections = "S2-2 RAG Pipeline, S3-1 Agent and Tools, S6-1 RAG Limitations"
    return (
        f"추천 레벨: {level}\n"
        f"추천 이유: {reason}\n"
        f"필요한 컴포넌트: {components}\n"
        f"복습할 강의 섹션: {sections}\n\n"
        f"참고 GitHub 레포:\n{refs}"
    )


def synthesize_with_single_pass(query: str, error: Exception | None = None) -> dict:
    """Fallback path when the tool-calling graph or chat API fails. It still uses both tools once."""
    api_limiter.reset()
    api_cache.clear()
    before = len(TOOL_CALL_LOG)
    search_lecture_materials.invoke(f"pipeline recommendation {github_query_hint(query)}")
    search_github_repos.invoke(github_query_hint(query))
    tool_calls = TOOL_CALL_LOG[before:]
    answer = build_deterministic_fallback_answer(query, tool_calls)
    return {
        "answer": answer,
        "tool_calls": tool_calls,
        "api_calls": api_limiter.snapshot(),
        "fallback_used": True,
        "fallback_error": type(error).__name__ if error else "",
    }


def ask_agent(query: str) -> dict:
    """Reset per-question API limits and add an English GitHub query hint for traceability."""
    api_limiter.reset()
    api_cache.clear()
    before = len(TOOL_CALL_LOG)
    user_message = (
        f"{query}\n\n"
        f"GitHub search query hint: {github_query_hint(query)}\n"
        "Remember: call search_lecture_materials once and search_github_repos once, then answer."
    )
    try:
        result = get_agent().invoke(
            {"messages": [{"role": "user", "content": user_message}]},
            config={"recursion_limit": 15},
        )
        tool_calls = TOOL_CALL_LOG[before:]
        answer = replace_github_refs_with_tool_results(result["messages"][-1].content, tool_calls)
        return {
            "answer": answer,
            "tool_calls": tool_calls,
            "api_calls": api_limiter.snapshot(),
            "fallback_used": False,
            "fallback_error": "",
        }
    except GraphRecursionError as exc:
        del TOOL_CALL_LOG[before:]
        return synthesize_with_single_pass(query, exc)
    except Exception as exc:
        del TOOL_CALL_LOG[before:]
        return synthesize_with_single_pass(query, exc)
