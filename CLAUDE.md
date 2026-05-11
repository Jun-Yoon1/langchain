# Claude Code 가이드 — 파이프라인 추천 에이전트

## 현재 상태 (2026-05-11 발표 당일)

| Phase | 상태 | 비고 |
|-------|------|------|
| Phase 0 환경 세팅 | ✅ 완료 | |
| Phase 1 RAG Tool | ✅ 완료 | practice/01_rag_explore.ipynb |
| Phase 2 GitHub Tool | ✅ 완료 | practice/02_github_explore.ipynb |
| Phase 3 Agent 조립 | ✅ 완료 | practice/03_agent_explore.ipynb |
| Phase 4 src/ 패키지화 | ✅ 완료 | main.py, src/my_project/ |
| Phase 5 마무리 | ✅ 완료 | README.md 업데이트 |
| Phase 6 발표 준비 | 진행 중 | 발표 16:00 |

---

## 내 역할: 검토자 (Reviewer)

Codex가 각 Phase를 구현하면 Claude가 검토한다.

> 전체 계획 → [PROJECT_PLAN.md](PROJECT_PLAN.md)

---

## 프로젝트 개요

**목표**: 사용자 아이디어 입력 → RAG(강의PDF) + GitHub 검색 → LangChain 파이프라인 추천

**아키텍처**:
```
입력 → Agent (create_react_agent / LangGraph)
         ├── RAG Tool: 강의 PDF → Chroma → 유사 패턴 검색
         └── GitHub Tool: REST API → 관련 레포 상위 3개
       → LLM 종합 → 추천 레벨 / 컴포넌트 / 강의 섹션 / GitHub 레포
```

---

## 기술 스택

| 항목 | 선택 |
|------|------|
| LLM | `ChatUpstage(model="solar-pro")` |
| 에이전트 | `create_react_agent` (LangGraph) |
| 벡터스토어 | Chroma (persist_directory 절대경로) |
| 임베딩 | UpstageEmbeddings |
| GitHub | `requests` + GitHub REST API |
| CLI | argparse (`main.py`) |

---

## 폴더 구조

```
langchain/                     ← 프로젝트 루트 (git repo)
├── CLAUDE.md                  ← 이 파일
├── PROJECT_PLAN.md
├── AGENTS.md                  ← Codex 구현 가이드
├── PROMPTS.md                 ← 검토 요청 프롬프트 모음
├── README.md
├── requirements.txt
├── .env.example
├── main.py                    ← CLI 진입점
├── practice/
│   ├── 01_rag_explore.ipynb
│   ├── 02_github_explore.ipynb
│   └── 03_agent_explore.ipynb
├── src/
│   └── my_project/
│       ├── __init__.py
│       ├── schemas.py         ← PipelineRecommendation 모델
│       ├── loader.py          ← PDF 로드
│       ├── retriever.py       ← Chroma + RAG @tool (get_lecture_tool 주입 패턴)
│       ├── github_tool.py     ← GitHub 검색 @tool (get_github_tool 주입 패턴)
│       ├── api_limits.py      ← API 호출 횟수 제한 (질문당 최대 2회)
│       └── chain.py           ← Agent 조립 + fallback
└── data/chroma_db/            ← 벡터스토어 (.gitignore, WSL 이관 시 수동 복사 필요)
```

---

## WSL 이관 시 주의

`data/chroma_db/`는 .gitignore에 포함되어 있어 clone 후 비어 있음.
두 가지 방법 중 선택:

```bash
# 방법 1: Windows에서 WSL로 복사 (빠름)
cp -r /mnt/c/Users/USER/Desktop/AI/langchain/PJ/langchain/data/chroma_db ./data/

# 방법 2: PDF 재임베딩 (느림)
jupyter nbconvert --to notebook --execute practice/01_rag_explore.ipynb
```

---

## 실행 방법

```bash
# 환경 세팅
python -m venv .venv
source .venv/bin/activate   # WSL/Linux
pip install -r requirements.txt
cp .env.example .env        # UPSTAGE_API_KEY, GITHUB_TOKEN 입력

# 실행
python main.py --query "냉장고 재료로 레시피 추천 챗봇 만들고 싶어"

# import 검증
python -c "from src.my_project.chain import ask_agent; print('OK')"
```

---

## chain.py 핵심 구조

```
ask_agent(query)
  → agent.invoke()          # LangGraph ReAct 에이전트
  → GraphRecursionError 시  # synthesize_with_single_pass() fallback
  → replace_github_refs_with_tool_results()  # LLM 환각 방지, tool 결과로 교체
```

**api_limiter / api_cache**: chain.py에서 생성해서 두 tool에 주입. 질문당 API 호출 횟수 추적.

---

## 코드 규칙 (검토 기준)

- `@tool` docstring: 영어로 작성 (ChatUpstage tool calling 안정성)
- API 키: 반드시 `os.getenv()` + `python-dotenv`
- Tool 에러: `raise` 대신 에러 메시지 str 반환
- Stack 제약: Chroma(not FAISS), ChatUpstage(not OpenAI), src/my_project/ 파일명만

---

## 검토 명령어

```bash
python main.py --query "레시피 추천 앱"
python -c "from src.my_project.chain import ask_agent; print('OK')"
grep -r "sk-" src/ main.py
grep -r "ghp_" src/ main.py
```
