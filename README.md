# LangChain Personal LLM App

LangChain과 LangGraph 학습 내용을 바탕으로 만드는 개인 LLM 앱입니다.
현재 골격은 기본 Chat CLI와 문서 기반 RAG 확장을 지원하도록 구성되어 있습니다.

## Architecture

```text
User Query
  -> main.py
  -> src/my_project/chain.py
  -> LLM

Optional RAG:
Data files
  -> loader.py
  -> retriever.py
  -> Chroma
  -> chain.py
  -> Answer
```

## Setup

```powershell
cd C:\Users\USER\Desktop\AI\langchain\PJ\langchain
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

`.env`에 사용할 API 키를 입력합니다.

```text
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
LANGCHAIN_TRACING_V2=false
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=langchain-project
```

## Run

기본 질문:

```powershell
python main.py --query "LangChain이 뭐야?"
```

문서 기반 RAG:

```powershell
python main.py --query "문서 내용을 요약해줘" --data-path data
```

## Project Structure

```text
.
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── practice/
│   └── 01_explore.ipynb
├── src/
│   └── my_project/
│       ├── __init__.py
│       ├── schemas.py
│       ├── loader.py
│       ├── retriever.py
│       └── chain.py
├── main.py
└── data/
```
