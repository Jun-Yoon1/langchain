import os
import re

import requests
from langchain_core.tools import tool

from .api_limits import create_query_limiter

GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"
ECOSYSTEM_KEYWORDS = {
    "rag": 2,
    "retrieval": 2,
    "agent": 2,
    "llm": 1,
    "chatbot": 1,
    "vector": 1,
    "embedding": 1,
    "multimodal": 1,
    "orchestration": 1,
    "document": 1,
    "qa": 1,
}
CORE_KEYWORDS = ("langchain", "langgraph")

_api_limiter = create_query_limiter()
_api_cache: dict[tuple[str, str], str] = {}


def github_headers() -> dict[str, str]:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def normalize_github_query(query: str) -> str:
    lower = query.lower()
    if any(token in lower for token in ["recipe", "recommendation", "recommender"]):
        base = "recipe recommendation rag chatbot"
    elif any(token in lower for token in ["wiki", "document", "documents", "qa", "q&a"]):
        base = "document qa rag chatbot retrieval"
    elif any(token in lower for token in ["news", "summary", "summarization", "fact", "factcheck", "fact-check"]):
        base = "news summarization fact checking agent retrieval"
    else:
        ascii_terms = [term.lower() for term in re.findall(r"[A-Za-z0-9]+", query) if len(term) >= 2]
        base = " ".join(ascii_terms) or "rag chatbot"

    terms = [term for term in base.split() if term not in {"langchain", "langgraph"}]
    return " ".join(dict.fromkeys(terms))


def github_search_request_unbudgeted(query: str, per_page: int = 10) -> requests.Response:
    """Direct GitHub call. The caller is responsible for budgeting."""
    params = {"q": f"langchain {query} in:name,description,readme", "sort": "stars", "per_page": per_page}
    return requests.get(
        GITHUB_SEARCH_URL,
        headers=github_headers(),
        params=params,
        timeout=10,
    )


def github_search_request(query: str, per_page: int = 10, api_limiter=None) -> requests.Response:
    limiter = api_limiter or _api_limiter
    return limiter.run(
        "github_search",
        lambda: github_search_request_unbudgeted(query, per_page),
    )


def repo_search_text(item: dict) -> str:
    return " ".join([
        item.get("full_name") or "",
        item.get("name") or "",
        item.get("description") or "",
        " ".join(item.get("topics") or []),
    ]).lower()


def extract_query_terms(query: str) -> list[str]:
    return [term.lower() for term in re.findall(r"[A-Za-z0-9]+", query) if len(term) >= 2]


def repo_relevance_score(item: dict, query: str) -> tuple[int, list[str]]:
    text = repo_search_text(item)
    core_matches = [keyword for keyword in CORE_KEYWORDS if keyword in text]
    if not core_matches:
        return 0, []

    matched = [f"core:{keyword}" for keyword in core_matches]
    score = 5

    for term in extract_query_terms(query):
        if term in text:
            score += 3
            matched.append(f"query:{term}")

    for keyword, weight in ECOSYSTEM_KEYWORDS.items():
        if keyword in text:
            score += weight
            matched.append(f"ecosystem:{keyword}")

    stars = int(item.get("stargazers_count") or 0)
    stars_bonus = min(stars // 1000, 5)
    score += stars_bonus
    if stars_bonus:
        matched.append(f"stars:+{stars_bonus}")
    return score, matched


def select_relevant_repos(
    items: list[dict],
    query: str,
    limit: int = 3,
    min_score: int = 6,
) -> tuple[list[tuple[dict, int, list[str]]], bool]:
    scored = []
    gate_candidates = []
    for item in items:
        score, matched = repo_relevance_score(item, query)
        if score <= 0:
            continue
        row = (item, score, matched)
        gate_candidates.append(row)
        if score >= min_score:
            scored.append(row)

    sort_key = lambda row: (row[1], int(row[0].get("stargazers_count") or 0))
    if scored:
        return sorted(scored, key=sort_key, reverse=True)[:limit], False

    fallback = sorted(
        gate_candidates,
        key=lambda row: int(row[0].get("stargazers_count") or 0),
        reverse=True,
    )[:limit]
    return fallback, bool(fallback)


def relevance_label(score: int) -> str:
    if score >= 15:
        return "high"
    if score >= 9:
        return "medium"
    return "low"


def get_github_tool(api_limiter=None, api_cache=None, tool_call_log=None):
    """Return the search_github_repos tool bound to the given limiter/cache."""
    limiter = api_limiter or _api_limiter
    cache = api_cache if api_cache is not None else _api_cache
    call_log = tool_call_log

    @tool
    def search_github_repos(query: str) -> str:
        """Search GitHub repositories for LangChain implementation references. Pass English domain keywords only; do not include the word langchain."""
        normalized_query = normalize_github_query(query)
        log_entry = {"tool": "search_github_repos", "raw_query": query, "query": normalized_query, "result": ""}
        if call_log is not None:
            call_log.append(log_entry)
        cache_key = ("github", normalized_query)
        if cache_key in cache:
            result = cache[cache_key]
            log_entry["result"] = result
            return result
        try:
            response = github_search_request(normalized_query, per_page=10, api_limiter=limiter)
            response.raise_for_status()
            items = response.json().get("items", [])
            selected, fallback_used = select_relevant_repos(items, normalized_query, limit=3)

            # One broad retry stays inside a single tool-call budget.
            if not selected and normalized_query != "rag chatbot":
                normalized_query = "rag chatbot"
                response = github_search_request_unbudgeted(normalized_query, per_page=10)
                response.raise_for_status()
                items = response.json().get("items", [])
                selected, fallback_used = select_relevant_repos(items, normalized_query, limit=3)

            if not selected:
                result = "No relevant LangChain GitHub repository found. Try different English keywords."
                cache[cache_key] = result
                log_entry["result"] = result
                return result

            results = []
            for item, score, matched in selected:
                results.append(
                    f"- {item['full_name']} (stars: {item['stargazers_count']})\n"
                    f"  description: {item.get('description') or 'N/A'}\n"
                    f"  url: {item['html_url']}\n"
                    f"  relevance: {relevance_label(score)} (score: {score})\n"
                    f"  evidence: {', '.join(matched) or 'N/A'}"
                )
            result = "\n\n".join(results)
            cache[cache_key] = result
            log_entry["result"] = result
            return result
        except Exception as exc:
            result = f"GitHub search failed: {exc}"
            log_entry["result"] = result
            return result

    return search_github_repos


search_github_repos = get_github_tool()
