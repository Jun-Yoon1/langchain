# Codex 구현 가이드 — LangChain 파이프라인 추천 에이전트

이 문서는 Codex가 따라야 할 구현 하네스다.
구현 후 각 Phase를 커밋하고 Claude에게 검토를 요청한다.

> 전체 계획 → PROJECT_PLAN.md

---

## 역할: 구현자 (Implementer)

- Codex가 각 Phase를 노트북에서 실험하고 src/로 패키지화한다.
- Phase 완료 기준을 통과하면 커밋 후 Claude에게 검토 요청.
- Claude의 피드백을 받아 수정한다.

---

## 프로젝트 개요

**목표**: 사용자 앱 아이디어 → RAG(강의PDF) + GitHub 검색 → 파이프라인 추천

**아키텍처**:
```
입력 (앱 아이디어 텍스트)
    ↓
Agent (create_agent, ReAct)
    ├── RAG Tool: PDFs/*.pdf → Chroma → 관련 패턴 검색
    └── GitHub Tool: GitHub REST API → 유사 레포 3개
    ↓
LLM 종합 → PipelineRecommendation 구조화 출력
```

---

## 폴더 구조 (최종 목표)

```
langchain/
├── PROJECT_PLAN.md
├── AGENTS.md               ← 이 파일
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── practice/
│   ├── 01_rag_explore.ipynb
│   ├── 02_github_explore.ipynb
│   └── 03_agent_explore.ipynb
├── src/
│   └── my_project/
│       ├── __init__.py
│       ├── schemas.py
│       ├── loader.py
│       ├── retriever.py
│       ├── github_tool.py
│       └── chain.py
├── main.py
└── data/
    └── chroma_db/
```

---

## Phase 0 — 환경 세팅

### 작업 목록
1. `.env` 파일 생성 (`.env.example` 복사 후 실제 키 입력)
2. 패키지 설치

```bash
pip install langchain langgraph langchain-upstage langchain-community
pip install chromadb pypdf python-dotenv requests pydantic
pip install langchain-chroma
```

3. 설치 확인

```bash
python -c "import langchain, chromadb, requests, pypdf, langchain_upstage; print('OK')"
```

### 완료 기준
- 위 명령어 오류 없이 `OK` 출력

---

## Phase 1 — RAG Tool 구현

### 파일: `practice/01_rag_explore.ipynb`

#### 셀 1: 환경 로드
```python
from dotenv import load_dotenv
load_dotenv()
import os
print(os.getenv("UPSTAGE_API_KEY")[:8])  # 키 앞부분만 확인
```

#### 셀 2: PDF 로드
```python
from langchain_community.document_loaders import PyPDFLoader
from pathlib import Path

pdf_dir = Path("../PDFs")  # 강의 PDF 폴더
docs = []
for pdf_path in pdf_dir.glob("*.pdf"):
    loader = PyPDFLoader(str(pdf_path))
    docs.extend(loader.load())

print(f"총 {len(docs)}개 페이지 로드")
```

#### 셀 3: 청크 분할
```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
chunks = splitter.split_documents(docs)
print(f"총 {len(chunks)}개 청크")
```

#### 셀 4: Chroma 저장
```python
from langchain_upstage import UpstageEmbeddings
from langchain_chroma import Chroma
from pathlib import Path

CHROMA_DIR = str(Path("../data/chroma_db").resolve())

embeddings = UpstageEmbeddings(model="solar-embedding-1-large")
vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory=CHROMA_DIR
)
print("Chroma 저장 완료")
```

#### 셀 5: 검색 테스트
```python
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
# UpstageEmbeddings는 문서/질문 임베딩을 메서드로 구분하므로 모델명 suffix를 붙이지 않습니다.
results = retriever.invoke("RAG 파이프라인 구성 방법")
for r in results:
    print(r.metadata.get("source", ""), r.page_content[:100])
    print("---")
```

#### 셀 6: @tool 래핑
```python
from langchain_core.tools import tool

@tool
def search_lecture_materials(query: str) -> str:
    """강의 자료에서 LangChain 파이프라인 관련 내용을 검색합니다.
    RAG, Agent, 멀티에이전트, 메모리, LangGraph 등의 패턴을 찾을 때 사용하세요."""
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    docs = retriever.invoke(query)
    results = []
    for doc in docs:
        source = doc.metadata.get("source", "unknown")
        results.append(f"[{Path(source).name}]\n{doc.page_content[:300]}")
    return "\n\n".join(results)

# 테스트
print(search_lecture_materials.invoke("에이전트와 도구 사용법"))
```

### 완료 기준
- 검색 결과에 강의 자료 관련 텍스트가 반환됨
- `@tool` 단독 호출 성공

---

## Phase 2 — GitHub Tool 구현

### 파일: `practice/02_github_explore.ipynb`

#### 셀 1: GitHub API 직접 테스트
```python
import requests
import os
from dotenv import load_dotenv
load_dotenv()

headers = {"Authorization": f"token {os.getenv('GITHUB_TOKEN')}"}
params = {"q": "langchain rag", "sort": "stars", "per_page": 3}
resp = requests.get("https://api.github.com/search/repositories", 
                    headers=headers, params=params)
print(resp.status_code)
print(resp.json().get("items", [])[0].keys())
```

#### 셀 2: 파싱 확인
```python
items = resp.json().get("items", [])
for item in items:
    print(f"- {item['full_name']} ★{item['stargazers_count']}")
    print(f"  {item['description']}")
    print(f"  {item['html_url']}")
    print()
```

#### 셀 3: @tool 래핑
```python
from langchain_core.tools import tool

@tool
def search_github_repos(query: str) -> str:
    """LangChain 관련 GitHub 레포지토리를 검색합니다.
    사용자 아이디어와 유사한 구현 예시를 찾을 때 사용하세요."""
    try:
        headers = {"Authorization": f"token {os.getenv('GITHUB_TOKEN')}"}
        params = {"q": f"langchain {query}", "sort": "stars", "per_page": 3}
        resp = requests.get(
            "https://api.github.com/search/repositories",
            headers=headers,
            params=params,
            timeout=10
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        if not items:
            return "관련 레포지토리를 찾을 수 없습니다."
        result = []
        for item in items:
            result.append(
                f"- {item['full_name']} (★{item['stargazers_count']})\n"
                f"  설명: {item.get('description', 'N/A')}\n"
                f"  URL: {item['html_url']}"
            )
        return "\n\n".join(result)
    except Exception as e:
        return f"GitHub 검색 실패: {str(e)}"

# 테스트
print(search_github_repos.invoke("recipe recommender chatbot"))
```

### 완료 기준
- 검색 결과에 레포 이름, URL, stars 포함
- API 실패 시 str 반환 (raise 아님)

---

## Phase 3 — Agent 조립

### 파일: `practice/03_agent_explore.ipynb`

#### 셀 1: 두 Tool 합치기
```python
from langchain_upstage import ChatUpstage
from langgraph.prebuilt import create_react_agent

llm = ChatUpstage(model="solar-pro")
tools = [search_lecture_materials, search_github_repos]
```

#### 셀 2: 시스템 프롬프트
```python
from langchain_core.prompts import ChatPromptTemplate

system_prompt = """당신은 LangChain 파이프라인 설계 전문가입니다.
사용자의 앱 아이디어를 분석하여 적합한 파이프라인을 추천합니다.

반드시 두 도구를 모두 사용하세요:
1. search_lecture_materials: 강의 자료에서 관련 패턴 검색
2. search_github_repos: 유사한 GitHub 레포지토리 검색

추천 형식:
- 추천 레벨: Level 1 (RAG) / Level 2 (RAG+Agent) / Level 3 (멀티에이전트)
- 추천 이유: (강의 자료 근거 포함)
- 필요한 컴포넌트: loader.py, retriever.py 등
- 복습할 강의 섹션: S1, S2 등
- 참고 GitHub 레포: (검색 결과에서)

과도한 기능 추가 금지. 5일 마감 기준으로 현실적으로 추천."""
```

#### 셀 3: Agent 생성 및 테스트
```python
from langgraph.prebuilt import create_react_agent

agent = create_react_agent(
    model=llm,
    tools=tools,
    state_modifier=system_prompt
)

test_cases = [
    "냉장고 재료를 입력하면 레시피를 추천해주는 챗봇을 만들고 싶어",
    "회사 내부 위키 문서로 Q&A 봇을 만들고 싶어",
    "뉴스를 요약하고 팩트체크하는 봇을 만들고 싶어"
]

for query in test_cases:
    print(f"\n=== 입력: {query} ===")
    result = agent.invoke({"messages": [{"role": "user", "content": query}]})
    print(result["messages"][-1].content)
    print("=" * 50)
```

### 완료 기준
- 3개 입력 모두 레벨 추천 + GitHub 레포 + 강의 섹션 포함
- 무한 루프 없음

---

## Phase 4 — src/ 패키지화

노트북에서 검증된 코드를 아래 구조로 이동:

### `src/my_project/schemas.py`
```python
from pydantic import BaseModel, Field
from typing import List

class GitHubRepo(BaseModel):
    name: str
    url: str
    stars: int
    description: str = ""

class PipelineRecommendation(BaseModel):
    recommended_level: str = Field(description="Level 1 / Level 2 / Level 3")
    reason: str = Field(description="추천 이유")
    components: List[str] = Field(description="필요한 파일 목록")
    lecture_sections: List[str] = Field(description="복습할 강의 섹션")
    github_refs: List[GitHubRepo] = Field(description="참고 GitHub 레포")
```

### `src/my_project/loader.py`
PDF 로드 + 청크 분할 함수

### `src/my_project/retriever.py`
Chroma 빌드 + `search_lecture_materials` @tool

### `src/my_project/github_tool.py`
`search_github_repos` @tool

### `src/my_project/chain.py`
```python
def build_agent():
    from .retriever import search_lecture_materials
    from .github_tool import search_github_repos
    ...
    return agent
```

### `main.py`
```python
import argparse
from dotenv import load_dotenv
load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="LangChain 파이프라인 추천")
    parser.add_argument("--query", required=True, help="앱 아이디어 설명")
    args = parser.parse_args()
    
    from src.my_project.chain import build_agent
    agent = build_agent()
    result = agent.invoke({"messages": [{"role": "user", "content": args.query}]})
    print(result["messages"][-1].content)

if __name__ == "__main__":
    main()
```

### 완료 기준
```bash
python main.py --query "레시피 추천 앱 만들고 싶어"
```
오류 없이 추천 결과 출력

---

## 코드 규칙

- API 키 하드코딩 절대 금지: 반드시 `os.getenv()` + `load_dotenv()`
- `@tool` 에러: `raise` 대신 `return f"실패: {str(e)}"` 패턴
- `@tool` docstring: 한국어로 명확하게 (LLM이 읽음)
- Chroma `persist_directory`: 반드시 절대경로
- 사용자 질문 1회당 외부 API별 호출은 최대 2회로 제한
  - `upstage_chat`: Agent/LLM 호출
  - `upstage_embedding`: 사용자 질문 임베딩 또는 검색용 임베딩 호출
  - `github_search`: GitHub REST API 호출
  - Phase 4 패키지화 시 `src/my_project/api_limits.py`의 `create_query_limiter()`를 사용
- 타입 힌트 사용
- 주석은 WHY 불명확할 때만

---

## Phase 완료 후 커밋 규칙

```bash
git add practice/01_rag_explore.ipynb
git commit -m "phase 1: RAG tool 구현 완료"
# → 이후 Claude에게 검토 요청
```

---

## Claude 검토 요청 방법

Phase 완료 후 Claude Code에서:
```
Phase 1 RAG Tool 구현 완료했어. 
파일: practice/01_rag_explore.ipynb
완료 기준 통과 여부와 개선점 검토해줘.
```

---

## 환경변수 목록 (.env)

```
UPSTAGE_API_KEY=up_...
GITHUB_TOKEN=ghp_...
LANGCHAIN_TRACING_V2=true        # 선택
LANGCHAIN_API_KEY=ls__...        # 선택
LANGCHAIN_PROJECT=pipeline-recommender  # 선택
```

---

## Windows PowerShell 실행 예시

```powershell
# 가상환경 활성화
.\.venv\Scripts\Activate.ps1

# 패키지 설치
pip install -r requirements.txt

# CLI 실행
python main.py --query "레시피 추천 앱 만들고 싶어"

# Streamlit UI (Phase 5 이후)
streamlit run app.py
```

---

## 절대 하지 말 것

- Phase 3 전에 Streamlit UI 작업
- 에이전트가 실제 코드를 생성하거나 실행하게 만들기
- GitHub 코드 내용 파싱 (저장소 메타데이터만 사용)
- 마감 전날 새 Tool 추가
- `.env` 파일 git 커밋
