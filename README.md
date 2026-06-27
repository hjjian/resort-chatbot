# Re:Sort 분리배출 챗봇

쓰레기 품목을 입력하면 키워드 매칭과 Yes/No 질문 트리를 통해 올바른 분리배출 방법을 안내하는 Streamlit 앱입니다. 사용자의 검색/결과 기록을 남기고, 카테고리별 탄소 절감량도 함께 보여줍니다.

## 주요 기능

- 품목명/유사 키워드 기반 분리배출 품목 검색
- 카테고리별 Yes/No 질문으로 배출 가능 여부 판단
- Gemini AI fallback: 키워드 매칭 실패 시 카테고리 자동 추론
- 결과 화면에서 배출 요령, 주의사항, AI 생성 환경 설명(IMPACT NOTE) 제공
- 탄소 절감량 표시 (카테고리별 CO₂ 절감 계수 기반)
- 분리배출 인증 구글폼 연동
- 관리자 화면에서 검색 로그, 인기 검색어, AI 추론 내역 확인
- Google Sheets 연동으로 품목 데이터와 사용 로그 관리

## 기술 스택

- Python
- Streamlit
- Google Gemini API (`google-genai`, `gemini-2.5-flash-lite`)
- pandas
- gspread / google-auth
- Google Sheets API

## 폴더 구조

```text
resort-chatbot/
├─ app.py                    # 사용자용 Streamlit 메인 앱
├─ admin.py                  # 단독 실행 가능한 관리자 화면
├─ pages/admin.py            # Streamlit 멀티페이지용 관리자 화면
├─ matcher.py                # items 키워드 매칭 로직 (exact / compact_exact)
├─ decision_tree.py          # 카테고리별 Yes/No 질문 트리
├─ carbon.py                 # 탄소 절감량 계산 및 Google Sheets 연동
├─ hybrid_handler.py         # Gemini AI 카테고리 추론 + IMPACT NOTE 생성
├─ data/
│  ├─ items.json             # 로컬 품목 데이터 (Sheets 없을 때 fallback)
│  └─ carbon_factors.json    # 카테고리별 탄소 절감 계수
├─ requirements.txt
└─ .gitignore
```

## 빠른 시작

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 앱 실행

```bash
streamlit run app.py
```

기본 주소:

```text
http://localhost:8501
```

### 3. 관리자 화면 실행

```bash
streamlit run admin.py
```

Streamlit 멀티페이지에서는 메인 앱 실행 후 사이드바의 관리자 페이지를 사용할 수 있습니다.

## 환경 설정

로컬에서 기본 기능만 사용할 때는 별도 설정 없이 실행 가능합니다. 품목 데이터는 `data/items.json`, 사용 로그는 `data/usage_log.json`에 저장됩니다.

Google Sheets 연동, Gemini AI, 관리자 비밀번호를 사용하려면 `.streamlit/secrets.toml` 파일을 생성합니다.

```toml
# ※ GEMINI_API_KEY는 반드시 [section] 헤더보다 위에 위치해야 합니다
GEMINI_API_KEY = "your-gemini-api-key"
ADMIN_PASSWORD = "your-admin-password"
GSHEET_ID = "your-google-sheet-id"
GSHEET_FORM_ID = "your-google-form-response-sheet-id"

[gcp_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "..."
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```

`secrets.toml`은 `.gitignore`에 포함되어 있으므로 저장소에 커밋되지 않습니다.

## Google Sheets 구조

### `items`

품목 데이터를 관리하는 시트입니다.

| 컬럼 | 설명 |
| --- | --- |
| `id` | 품목 고유 ID. 비워두면 카테고리 기반으로 자동 생성됩니다. |
| `name` | 사용자에게 보여줄 품목명 |
| `category` | 분리배출 카테고리 |
| `keywords` | 쉼표로 구분한 검색 키워드 |
| `skip_questions` | 건너뛸 질문 ID 목록 (쉼표 구분) |
| `result` | 품목별 최종 결과 문구 |
| `steps` | `\|`로 구분한 배출 요령 |
| `note` | 결과 화면에 보여줄 설명 (AI 생성 실패 시 fallback) |

### `usage_log`

사용자가 검색을 완료하면 자동으로 행이 추가됩니다.

| 컬럼 | 설명 |
| --- | --- |
| `timestamp` | 검색 완료 시각 |
| `nickname` | 사용자 닉네임 |
| `user_input` | 사용자가 입력한 검색어 |
| `matched_item_id` | 매칭된 품목 ID |
| `matched_by` | 매칭 방식 (`exact` / `compact_exact` / `ai_inferred` / `category_manual`) |
| `category` | 분리배출 카테고리 |
| `final_result` | 최종 안내 결과 |
| `llm_used` | IMPACT NOTE AI 생성 성공 여부 (`True` / `False`) |

### `ai_inferred` (자동 생성)

AI가 카테고리를 추론한 입력값을 별도 시트에 기록합니다. 관리자가 검토 후 `items` 시트에 추가할 수 있습니다.

## 동작 흐름

1. 사용자가 홈 화면에서 품목명을 입력합니다.
2. `matcher.py`가 `items` 데이터의 키워드와 입력값을 비교합니다 (완전 일치 → 공백 제거 완전 일치).
3. 키워드 매칭 실패 시 `hybrid_handler.infer_category()`가 Gemini AI로 카테고리를 추론합니다.
4. 품목에 `extra_questions`가 있으면 품목 전용 질문을 먼저 진행합니다.
5. `decision_tree.py`의 카테고리별 공통 질문 트리를 진행합니다.
6. 최종 결과와 배출 요령을 표시하고 `usage_log`에 기록합니다.
7. `hybrid_handler.generate_impact_note()`가 Gemini AI로 IMPACT NOTE를 동적 생성합니다 (세션 캐싱으로 중복 호출 방지).

## AI 관련 참고 사항

- Gemini API 모델: `gemini-2.5-flash-lite`
- 무료 티어 제한: 분당 10회(RPM), 일 500회(RPD). 동시 요청이 몰리면 429 오류 발생 가능
- 429 / 503 오류 발생 시 exponential backoff(1s → 2s → 4s)으로 최대 3회 재시도
- 유료 전환 시 rate limit이 대폭 상향됨
- `GEMINI_API_KEY`는 Streamlit Cloud secrets에서 반드시 `[gcp_service_account]` 섹션보다 **위**에 위치해야 합니다

## 데이터 파일

### `data/items.json`

Google Sheets 연결 실패 시 사용하는 로컬 fallback 품목 데이터입니다.

```json
{
  "id": "plastic_001",
  "name": "얇은 플라스틱 빨대",
  "keywords": ["플라스틱 빨대", "빨대", "카페 빨대"],
  "category": "플라스틱",
  "skip_questions": [],
  "extra_questions": null,
  "result": "일반쓰레기",
  "steps": ["이물질을 제거하세요.", "일반쓰레기 또는 지정 배출함에 배출하세요."],
  "note": "품목별 안내 문구"
}
```

사용 카테고리: 스티로폼, 유리, 금속·캔, 비닐, 플라스틱, 종이·종이팩, 폐의약품, 전자제품 및 완충재, 기타, 일반쓰레기

### `data/carbon_factors.json`

카테고리별 1회 올바른 분리배출 기준 탄소 절감량 (단위: kg CO₂e)

## 개발 확인 명령

문법 확인:

```bash
python -m py_compile app.py matcher.py carbon.py decision_tree.py admin.py
```

JSON 데이터 확인:

```bash
python -c "import json; json.load(open('data/items.json', encoding='utf-8')); json.load(open('data/carbon_factors.json', encoding='utf-8')); print('json ok')"
```
