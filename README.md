# Re:Sort 분리배출 챗봇

쓰레기 품목을 입력하면 키워드 매칭과 Yes/No 질문 트리를 통해 올바른 분리배출 방법을 안내하는 Streamlit 앱입니다. 사용자의 검색/결과 기록을 남기고, 카테고리별 탄소 절감량도 함께 보여줍니다.

## 주요 기능

- 품목명/유사 키워드 기반 분리배출 품목 검색
- 카테고리별 Yes/No 질문으로 배출 가능 여부 판단
- 결과 화면에서 배출 요령, 주의사항, 환경 설명 제공
- 오늘의 검색 기록 기반 탄소 절감량 표시
- 관리자 화면에서 검색 로그와 인기 검색어 확인
- Google Sheets 연동 시 품목 데이터와 사용 로그를 시트로 관리

## 기술 스택

- Python
- Streamlit
- pandas
- gspread / google-auth
- Google Sheets API

## 폴더 구조

```text
resort-chatbot-main/
├─ app.py                    # 사용자용 Streamlit 메인 앱
├─ admin.py                  # 단독 실행 가능한 관리자 화면
├─ pages/admin.py            # Streamlit 멀티페이지용 관리자 화면
├─ matcher.py                # items.json 키워드 매칭 로직
├─ decision_tree.py          # 카테고리별 Yes/No 질문 트리
├─ carbon.py                 # 탄소 절감량 계산 및 Google Sheets 연동
├─ hybrid_handler.py         # LLM fallback 구현 예정 파일
├─ data/
│  ├─ items.json             # 로컬 품목 데이터
│  └─ carbon_factors.json    # 카테고리별 탄소 절감 계수
├─ requirements.txt
└─ .devcontainer/
   └─ devcontainer.json
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

기본 주소는 다음과 같습니다.

```text
http://localhost:8501
```

### 3. 관리자 화면 실행

단독 관리자 화면:

```bash
streamlit run admin.py
```

Streamlit 멀티페이지에서는 메인 앱 실행 후 사이드바의 관리자 페이지를 사용할 수 있습니다.

## 환경 설정

로컬에서 기본 기능만 사용할 때는 별도 설정 없이 실행할 수 있습니다. 이 경우 품목 데이터는 `data/items.json`에서 읽고, 사용 로그는 `data/usage_log.json`에 저장됩니다.

Google Sheets 연동과 관리자 비밀번호를 사용하려면 `.streamlit/secrets.toml` 파일을 생성합니다.

```toml
ADMIN_PASSWORD = "your-admin-password"
GSHEET_ID = "your-google-sheet-id"

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

Google Sheets가 설정되어 있으면 `carbon.py`가 다음 워크시트를 사용합니다.

### `items`

품목 데이터를 관리하는 시트입니다.

| 컬럼 | 설명 |
| --- | --- |
| `id` | 품목 고유 ID. 비워두면 일부 카테고리는 자동 생성됩니다. |
| `name` | 사용자에게 보여줄 품목명 |
| `category` | 분리배출 카테고리 |
| `keywords` | 쉼표로 구분한 검색 키워드 |
| `skip_questions` | 건너뛸 질문 ID 목록 |
| `steps` | `|`로 구분한 배출 요령 |
| `note` | 결과 화면에 보여줄 설명 |

### `usage_log`

사용자가 검색을 완료하면 로그가 추가됩니다.

| 컬럼 | 설명 |
| --- | --- |
| `timestamp` | 검색 완료 시각 |
| `nickname` | 사용자 닉네임 |
| `user_input` | 사용자가 입력한 검색어 |
| `matched_item_id` | 매칭된 품목 ID |
| `matched_by` | 매칭 방식 |
| `category` | 분리배출 카테고리 |
| `final_result` | 최종 안내 결과 |
| `llm_used` | LLM fallback 사용 여부 |

## 데이터 파일

### `data/items.json`

로컬 fallback 품목 데이터입니다. 각 품목은 아래 필드를 사용합니다.

```json
{
  "id": "plastic_001",
  "name": "얇은 플라스틱 빨대",
  "keywords": ["플라스틱 빨대", "빨대", "카페 빨대"],
  "category": "플라스틱",
  "skip_questions": [],
  "extra_questions": null,
  "steps": ["이물질을 제거하세요.", "일반쓰레기 또는 지정 배출함에 배출하세요."],
  "note": "품목별 안내 문구"
}
```

현재 사용하는 주요 카테고리는 다음과 같습니다.

- 스티로폼
- 유리
- 금속·캔
- 비닐
- 플라스틱
- 종이·종이팩
- 폐의약품
- 전자제품
- 기타

### `data/carbon_factors.json`

카테고리별 1회 올바른 분리배출 기준 탄소 절감량입니다. 단위는 kg CO2e입니다.

## 동작 흐름

1. 사용자가 홈 화면에서 품목명을 입력합니다.
2. `matcher.py`가 `items` 데이터의 키워드와 입력값을 비교해 품목을 찾습니다.
3. 품목에 `extra_questions`가 있으면 품목 전용 질문을 먼저 진행합니다.
4. 이후 `decision_tree.py`의 카테고리별 공통 질문 트리를 진행합니다.
5. 최종 결과와 배출 요령을 보여주고 `usage_log`에 기록합니다.
6. 매칭에 실패하면 안내 메시지를 보여줍니다.

## 현재 참고 사항

- `hybrid_handler.py`는 아직 구현 예정 상태입니다.
- LLM fallback은 관리자 화면에 집계 항목이 있지만 현재 메인 흐름에는 연결되어 있지 않습니다.
- 로컬 사용 로그 파일인 `data/usage_log.json`은 실행 중 자동 생성되며 Git 추적 대상에서 제외됩니다.
- 품목 데이터가 많지 않으므로 실제 사용 전에는 `data/items.json` 또는 Google Sheets의 `items` 시트를 보강하는 것이 좋습니다.

## 개발 확인 명령

문법 확인:

```bash
python -m py_compile app.py matcher.py carbon.py decision_tree.py admin.py pages/admin.py
```

JSON 데이터 확인:

```bash
python -c "import json; json.load(open('data/items.json', encoding='utf-8')); json.load(open('data/carbon_factors.json', encoding='utf-8')); print('json ok')"
```
