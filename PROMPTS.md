# 프롬프트 모음 — LangChain 파이프라인 추천 에이전트

> Codex 구현용 프롬프트와 Claude 검토 요청 프롬프트로 구분

---

## Codex 구현 프롬프트

### Phase 0 — 환경 세팅

```
requirements.txt를 보고 패키지를 설치해줘.
그다음 아래를 실행해서 오류가 없는지 확인해줘:
python -c "import langchain, chromadb, requests, pypdf; print('OK')"

.env.example을 참고해서 내가 입력해야 할 환경변수가 뭔지 알려줘.
```

---

### Phase 1 — RAG Tool

```
AGENTS.md의 Phase 1 지침에 따라 practice/01_rag_explore.ipynb를 작성해줘.
PDFs/*.pdf 전체를 로드해서 Chroma에 저장하고, @tool로 래핑까지 해줘.

완료 기준:
- "RAG 파이프라인 구성 방법" 검색 시 강의 자료 텍스트 반환
- search_lecture_materials.invoke("테스트") 단독 호출 성공
```

---

### Phase 2 — GitHub Tool

```
AGENTS.md의 Phase 2 지침에 따라 practice/02_github_explore.ipynb를 작성해줘.
GitHub REST API로 레포를 검색하고 @tool로 래핑해줘.

주의사항:
- GITHUB_TOKEN은 반드시 os.getenv()로 읽기
- API 실패 시 raise 말고 str 반환
- 사용자 질문 1회당 GitHub REST API 호출은 최대 2회로 제한

완료 기준:
- search_github_repos.invoke("recipe recommender") 호출 시
  레포 이름, URL, stars 포함한 텍스트 반환
```

---

### Phase 3 — Agent 조립

```
AGENTS.md의 Phase 3 지침에 따라 practice/03_agent_explore.ipynb를 작성해줘.
01번과 02번 노트북의 두 @tool을 합쳐서 create_react_agent로 Agent를 만들어줘.

시스템 프롬프트에 반드시 포함할 것:
- 두 Tool 모두 사용 지시
- Level 1/2/3 추천 기준
- 5일 마감 기준 현실적 추천
- 사용자 질문 1회당 upstage_chat, upstage_embedding, github_search 각각 최대 2회 제한

테스트 케이스 3개로 실행해서 결과 보여줘:
1. "냉장고 재료로 레시피 추천 챗봇"
2. "회사 위키 문서 Q&A 봇"
3. "뉴스 요약 + 팩트체크 봇"
```

---

### Phase 4 — src/ 패키지화

```
AGENTS.md의 Phase 4 지침에 따라 노트북 코드를 src/my_project/ 아래로 옮겨줘.

파일별 역할:
- schemas.py: PipelineRecommendation Pydantic 모델
- api_limits.py: 사용자 질문 1회당 API별 최대 2회 호출 제한
- loader.py: PDF 로드 함수
- retriever.py: Chroma 빌드 + search_lecture_materials @tool
- github_tool.py: search_github_repos @tool
- chain.py: build_agent() 함수
- main.py: argparse CLI

완료 확인:
python main.py --query "레시피 추천 앱 만들고 싶어"
```

---

### Phase 5 — README 작성

```
현재 src/ 코드와 main.py를 읽고 README.md를 작성해줘.

포함 항목:
- 프로젝트 소개 (2문장)
- 아키텍처 다이어그램 (텍스트 형식)
- 필요한 환경변수 목록
- 설치 및 실행 방법 (Windows PowerShell 기준)
- 사용 예시 출력

발표 데모용으로 간결하게 (스크롤 최소화).
```

---

### Phase 5 — LangSmith 트레이싱 추가

```
main.py 상단에 LangSmith 트레이싱 초기화 코드를 추가해줘.
환경변수가 없으면 조용히 스킵하도록 해줘.
.env.example에도 LangSmith 관련 변수를 추가해줘.
프로젝트 이름: pipeline-recommender
```

---

### 전체 점검 (Phase 5 마무리)

```
프로젝트 전체를 점검해줘.

확인 항목:
1. python main.py --query "..." 실행 시 오류 없이 동작하는가
2. API 키 하드코딩된 곳 없는가 (grep -r "sk-" src/ main.py)
3. requirements.txt가 실제 import와 일치하는가
4. .gitignore에 .env, data/chroma_db/, __pycache__ 포함되는가
5. README 실행 방법이 실제와 일치하는가
```

---

## Claude 검토 요청 프롬프트

### Phase 1 검토 요청 (RAG)

```
Phase 1 RAG Tool 구현 완료했어. 검토해줘.

파일: practice/01_rag_explore.ipynb

확인해야 할 것:
- PDF 전체 로드 여부 (PDFs/*.pdf)
- 청크 크기 적절성 (chunk_size 500~1000)
- 검색 결과가 질문과 관련 있는지
- @tool docstring 명확성
- Chroma persist_directory 절대경로 사용 여부
```

---

### Phase 2 검토 요청 (GitHub Tool)

```
Phase 2 GitHub Tool 구현 완료했어. 검토해줘.

파일: practice/02_github_explore.ipynb

확인해야 할 것:
- GITHUB_TOKEN 환경변수로 읽는지 (하드코딩 없는지)
- API 실패 시 str 반환하는지 (raise 아닌지)
- 반환값에 name, url, stars 포함되는지
- per_page=3~5 제한하는지
```

---

### Phase 3 검토 요청 (Agent)

```
Phase 3 Agent 조립 완료했어. 검토해줘.

파일: practice/03_agent_explore.ipynb

확인해야 할 것:
- 샘플 3개 입력에서 일관된 출력 나오는지
- 두 Tool 모두 실제로 호출되는지
- 무한 루프 없는지
- 시스템 프롬프트에 Level 1/2/3 분류 기준 있는지
```

---

### Phase 4 검토 요청 (src/ 패키지)

```
Phase 4 src/ 패키지화 완료했어. 검토해줘.

확인해야 할 것:
- python main.py --query "레시피 추천 앱" 실행 성공하는지
- 모듈 import 구조 문제 없는지
- API 키 하드코딩 없는지
- requirements.txt 실제 import와 일치하는지
```

---

### 보안 점검 요청

```
/security-review

추가로 확인해줘:
- src/ 와 main.py에서 sk-, ghp_, ls__ 하드코딩 여부
- .gitignore에 .env 포함 여부
- .env.example에 실제 값 없는지
```

---

### 최종 발표 전 검토

```
발표 전 최종 점검해줘.

데모 시나리오:
1. python main.py --query "냉장고 재료로 레시피 추천 챗봇 만들고 싶어"
2. python main.py --query "회사 위키 문서로 Q&A 봇 만들고 싶어"

확인:
- 두 케이스 모두 실행 성공하는지
- 출력에 Level 추천 + GitHub 레포 + 강의 섹션 포함되는지
- README 실행 방법이 실제와 일치하는지
- git log가 Phase별로 커밋되어 있는지
```

---

## Codex CLI 실행 예시

```bash
# Phase별 작업 지시
codex "AGENTS.md의 Phase 1을 따라 practice/01_rag_explore.ipynb를 작성해줘"

# 특정 파일 수정
codex --file src/my_project/github_tool.py "API 에러 핸들링을 str 반환으로 바꿔줘"

# 전체 점검
codex "requirements.txt와 실제 import가 일치하는지 확인하고 필요하면 업데이트해줘"
```
