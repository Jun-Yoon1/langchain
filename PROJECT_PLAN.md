# 프로젝트 계획: LangChain 파이프라인 추천 에이전트

## 한 줄 설명

사용자가 만들고 싶은 앱 아이디어를 입력하면, 강의 자료(RAG)와 GitHub 검색을 결합해 적합한 LangChain 파이프라인 구성을 추천해주는 에이전트

---

## 역할 분담

| 역할 | 담당 | 작업 방식 |
|------|------|---------|
| 구현 | **Codex** | 각 Phase 노트북 실험 → src/ 패키지화 |
| 검토 | **Claude Code** | Phase 완료 후 `/review` 또는 직접 요청 |

> Codex가 Phase 하나를 완료하고 커밋하면 Claude에게 검토 요청

---

## 아키텍처

```
사용자 입력 (앱 아이디어 설명)
        ↓
    Agent (ReAct / create_agent)
    ├── Tool 1: RAG
    │   └── 강의 PDF (PDFs/*.pdf) → Chroma → 유사 패턴 검색
    └── Tool 2: GitHub Search
        └── GitHub REST API → langchain + 키워드 → 상위 레포 3개
        ↓
    LLM 종합
        ↓
    PipelineRecommendation (Pydantic 구조화 출력)
    ├── recommended_level: "Level 1 / 2 / 3"
    ├── reason: 추천 이유
    ├── components: ["loader.py", "retriever.py", ...]
    ├── lecture_sections: ["S1", "S2"]
    └── github_refs: [{"name": ..., "url": ..., "stars": ...}]
```

---

## 기술 스택

| 항목 | 선택 |
|------|------|
| LLM | ChatUpstage (solar-pro) |
| 에이전트 | `create_react_agent` (LangGraph 방식) |
| 벡터스토어 | Chroma |
| 임베딩 | UpstageEmbeddings |
| GitHub 검색 | `requests` + GitHub REST API |
| 구조화 출력 | Pydantic BaseModel |
| CLI | argparse |
| 트레이싱 | LangSmith (선택) |
| UI | Streamlit (시간 남으면) |

---

## Phase별 계획

### Phase 0 — 환경 세팅 (5/7, 30분)
**Codex 작업:**
- `.env` 파일에 키 입력 (UPSTAGE_API_KEY, GITHUB_TOKEN)
- `pip install -r requirements.txt`
- 임포트 오류 없이 실행되는지 확인

**완료 기준:** `python -c "import langchain, chromadb, requests"` 오류 없음

---

### Phase 1 — RAG Tool 구현 (5/7~5/8)
**Codex 작업:** `practice/01_rag_explore.ipynb`

```
1. PDFs/*.pdf 전체 로드 (PyPDFLoader)
2. RecursiveCharacterTextSplitter로 청크 분할
3. UpstageEmbeddings → Chroma 저장
4. 유사도 검색 테스트 ("RAG 파이프라인이 뭐야?")
5. @tool 함수로 래핑
6. 단독 호출 테스트
```

**완료 기준:** 질문에 강의 자료 관련 청크가 반환됨
**Claude 검토 포인트:** 청크 크기, 검색 품질, tool docstring 명확성

---

### Phase 2 — GitHub Tool 구현 (5/8)
**Codex 작업:** `practice/02_github_explore.ipynb`

```
1. GitHub REST API 호출 테스트
   GET https://api.github.com/search/repositories
   params: q="langchain rag", sort="stars", per_page=10
2. 응답 파싱 (name, url, stars, description만 추출)
2-1. 점수 재정렬 (langchain/도메인 키워드 + stars) → 상위 3개 선택
3. @tool 함수로 래핑
4. 단독 호출 테스트
```

**주의:** GITHUB_TOKEN 없으면 60회/시간 제한. 반드시 토큰 사용.
**완료 기준:** 검색어 입력 → 레포 3개 텍스트 반환
**Claude 검토 포인트:** API 에러 핸들링, 반환값 형식

---

### Phase 3 — Agent 조립 (5/8~5/9)
**Codex 작업:** `practice/03_agent_explore.ipynb`

```
1. Tool 1 (RAG) + Tool 2 (GitHub) 합치기
2. create_agent(model=llm, tools=[rag_tool, github_tool])
3. 시스템 프롬프트 작성 (추천서 형식 지정)
4. 샘플 입력 3개로 테스트
   - "냉장고 재료 레시피 추천 앱"
   - "회사 문서 검색 챗봇"
   - "뉴스 요약 + 팩트체크 봇"
5. 출력이 일관된지 확인
```

**완료 기준:** 3개 입력 모두 레벨 추천 + GitHub 레포 + 강의 섹션 반환
**Claude 검토 포인트:** 추천 품질, 프롬프트 적절성, 루프 탈출 여부

---

### Phase 4 — src/ 패키지화 (5/9)
**Codex 작업:** 노트북 코드 → `src/my_project/`로 이동

```
src/my_project/
├── __init__.py
├── schemas.py       # PipelineRecommendation Pydantic 모델
├── loader.py        # PDF 로드 + 청크 분할
├── retriever.py     # Chroma 빌드 + RAG @tool
├── github_tool.py   # GitHub 검색 @tool (normalize_github_query 포함)
└── chain.py         # Agent 조립 + GraphRecursionError fallback (synthesize_with_single_pass, replace_github_refs_with_tool_results, extract_real_github_blocks 포함)
main.py              # argparse CLI
```

**완료 기준:** `python main.py --query "레시피 추천 앱 만들고 싶어"` 실행 성공
**Claude 검토 포인트:** 모듈 분리 적절성, import 구조, CLI 동작

---

### Phase 5 — 마무리 (5/10)
**Codex 작업:**
- LangSmith 트레이싱 추가 (선택)
- README.md 작성
- `.env.example` 확인
- 에러 핸들링 보완
- (시간 남으면) Streamlit UI

**완료 기준:** GitHub push 완료, README 실행 방법 정확

---

### Phase 6 — 발표 준비 (5/11 오전)
- 데모 시나리오 3개 준비
- 발표 10분 스크립트
- 백업 출력 스크린샷 준비

---

## 검토 요청 방법

### Claude Code에서
```
# Phase 완료 후
/review

# 또는 직접
현재 Phase 2 GitHub Tool 구현 완료했어. 코드 검토해줘.
주요 파일: practice/02_github_explore.ipynb, 
확인해야 할 것: API 에러 핸들링, 반환값 형식
```

### Codex에서
```
이 코드가 Phase 1 완료 기준을 충족하는지 확인해줘.
완료 기준: 질문에 강의 자료 관련 청크가 반환됨
```

---

## 리스크 관리

| 리스크 | 대응 |
|--------|------|
| GitHub API 토큰 없음 | Phase 0에서 반드시 발급 |
| PDF 로딩 실패 | PyPDFLoader 대신 pdfplumber 시도 |
| 에이전트 루프 탈출 안 됨 | max_iterations=5 설정 |
| Chroma 경로 충돌 | persist_directory 절대경로 사용 |
| API 호출 과다 | 사용자 질문 1회당 `upstage_chat`, `upstage_embedding`, `github_search` 각각 최대 2회로 제한 |
| Phase 3에서 시간 부족 | 시스템 프롬프트 단순화, 구조화 출력 포기하고 텍스트로 |

---

## 절대 금지

- Phase 3 전에 UI 작업 시작
- 마감 전날 새 Tool 추가
- 에이전트가 실제로 코드를 생성하거나 실행하게 만들기
- GitHub 코드 검색 (저장소 검색만, 코드 내용 파싱은 과도함)
