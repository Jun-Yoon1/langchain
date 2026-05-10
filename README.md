# LangChain 파이프라인 추천 에이전트

사용자가 만들고 싶은 앱 아이디어를 입력하면, 강의 자료(RAG)와 GitHub 검색을 결합해 적합한 LangChain 파이프라인 구성을 추천해주는 에이전트입니다.

## Architecture

```
사용자 입력 (앱 아이디어)
        ↓
    Agent (ReAct / LangGraph)
    ├── Tool 1: RAG
    │   └── 강의 PDF → Chroma → 유사 패턴 검색
    └── Tool 2: GitHub Search
        └── GitHub REST API → langchain + 키워드 → 상위 레포 3개
        ↓
    LLM 종합 (ChatUpstage / solar-pro)
        ↓
    추천 레벨 / 컴포넌트 / 강의 섹션 / GitHub 레포
```

## Tech Stack

| 항목 | 선택 |
|------|------|
| LLM | ChatUpstage (solar-pro) |
| 에이전트 | LangGraph `create_react_agent` |
| 벡터스토어 | Chroma |
| 임베딩 | UpstageEmbeddings |
| GitHub 검색 | `requests` + GitHub REST API |

## Setup

```powershell
cd langchain
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

`.env`에 API 키를 입력합니다.

```
UPSTAGE_API_KEY=your_upstage_api_key
GITHUB_TOKEN=your_github_token
```

## Run

```powershell
python main.py --query "냉장고 재료로 레시피를 추천해주는 챗봇을 만들고 싶어"
python main.py --query "회사 내부 위키 문서로 Q&A 봇을 만들고 싶어"
python main.py --query "뉴스를 요약하고 팩트체크하는 봇을 만들고 싶어"
```

## Output Format

```
추천 레벨: Level 1 / Level 2 / Level 3
추천 이유: 강의 자료 근거 포함 3~5문장
필요한 컴포넌트: loader.py, retriever.py, chain.py, ...
복습할 강의 섹션: 섹션명 + 이유
참고 GitHub 레포: 실제 레포 이름, URL, stars, 설명
```

## Project Structure

```
langchain/
├── main.py                  # CLI 진입점 (argparse)
├── requirements.txt
├── .env.example
├── data/
│   └── chroma_db/           # 벡터스토어 (자동 생성)
├── src/
│   └── my_project/
│       ├── chain.py         # Agent 조립 + fallback
│       ├── retriever.py     # Chroma + RAG tool
│       ├── github_tool.py   # GitHub 검색 tool
│       ├── loader.py        # PDF 로드
│       ├── schemas.py       # Pydantic 모델
│       └── api_limits.py    # API 호출 제한
└── practice/
    ├── 01_rag_explore.ipynb
    ├── 02_github_explore.ipynb
    └── 03_agent_explore.ipynb
```
