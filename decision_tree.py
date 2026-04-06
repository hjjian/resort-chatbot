"""
decision_tree.py — 카테고리별 Yes/No 질문 트리 로직

각 트리는 질문 딕셔너리 리스트로 구성.
질문 딕셔너리 필드:
  - id: 질문 고유 ID
  - text: 질문 본문
  - description: 부연 설명
  - eco_title: 환경 설명 제목
  - eco_desc: 환경 설명 본문
  - yes: YES 선택 시 처리 {"next": <질문ID> | "end"} 또는 {"result": ..., "reason": ...} 또는 {"action": ..., "next": ...}
  - no:  NO  선택 시 처리 (same)

get_next_question(tree, current_id, answer) → 다음 질문 딕셔너리 또는 결과 딕셔너리
결과 딕셔너리: {"type": "result", "result": str, "reason": str}
안내 딕셔너리: {"type": "guide",  "message": str, "next": str}
"""

# ──────────────────────────────────────────────
# 스티로폼 트리
# ──────────────────────────────────────────────
STYRO_TREE = [
    {
        "id": "Q1",
        "text": "테이프·송장·스티커가 붙어있나요?",
        "description": "외부에 부착된 이물질은 재활용 공정을 방해합니다.",
        "eco_title": "왜 제거해야 하나요?",
        "eco_desc": "테이프나 송장 스티커가 붙은 채로 배출되면 선별장에서 재활용 불가 판정을 받을 수 있습니다. 미리 제거하면 재활용률이 크게 높아집니다.",
        "yes": {"action": "테이프·송장·스티커를 모두 제거한 후 다음 질문으로 진행해주세요.", "next": "Q2"},
        "no":  {"next": "Q2"},
    },
    {
        "id": "Q2",
        "text": "음식물·이물질이 묻어있나요?",
        "description": "기름기나 음식 잔여물이 남아있는지 확인해주세요.",
        "eco_title": "왜 이물질이 문제인가요?",
        "eco_desc": "이물질이 묻은 스티로폼은 다른 깨끗한 스티로폼까지 오염시켜 전체 배치가 폐기될 수 있습니다.",
        "yes": {"next": "Q2_1"},
        "no":  {"next": "Q3"},
    },
    {
        "id": "Q2_1",
        "parent": "Q2",
        "text": "물로 씻으면 이물질이 제거되나요?",
        "description": "간단히 헹궈서 이물질이 제거되는지 확인해주세요.",
        "eco_title": "세척 가능 여부가 왜 중요한가요?",
        "eco_desc": "세척으로 이물질을 제거할 수 있다면 재활용이 가능합니다. 그러나 기름이 배어 씻어도 지워지지 않는 경우 재활용 공정 전체를 오염시킵니다.",
        "yes": {"next": "Q3"},
        "no":  {"result": "일반쓰레기", "reason": "세척해도 이물질이 제거되지 않는 스티로폼은 재활용 공정을 오염시키기 때문에 일반쓰레기로 배출해야 합니다."},
    },
    {
        "id": "Q3",
        "text": "색상이 있거나 코팅됐나요?",
        "description": "흰색이 아닌 유색이거나 표면에 코팅 처리가 된 경우 해당합니다.",
        "eco_title": "색상·코팅이 왜 문제인가요?",
        "eco_desc": "유색 또는 코팅 스티로폼은 재생원료 품질을 저하시켜 선별장에서 반입을 거부하는 경우가 많습니다. 흰색 무코팅 스티로폼만 재활용이 가능합니다.",
        "yes": {"result": "일반쓰레기", "reason": "색상이 있거나 코팅된 스티로폼은 재생원료 품질을 저하시켜 선별장 반입이 거부됩니다. 일반쓰레기로 배출하세요."},
        "no":  {"result": "스티로폼 재활용", "reason": "깨끗하고 흰색 무코팅 스티로폼입니다. 스티로폼 전용 수거함에 배출하세요."},
    },
]

# ──────────────────────────────────────────────
# 유리 트리
# ──────────────────────────────────────────────
GLASS_TREE = [
    {
        "id": "Q1",
        "text": "깨진 유리인가요?",
        "description": "금이 가거나 조각난 유리는 수거 담당자의 안전을 위협할 수 있습니다.",
        "eco_title": "왜 깨진 유리는 따로 배출하나요?",
        "eco_desc": "깨진 유리는 수거 담당자가 부상을 입을 위험이 있습니다. 신문지나 두꺼운 종이로 감싸 '깨진 유리'라고 표기한 후 일반쓰레기로 배출해 주세요.",
        "yes": {"result": "일반쓰레기", "reason": "깨진 유리는 수거 담당자 안전을 위해 신문지로 감싸 '깨진 유리'라고 표기한 후 일반쓰레기로 배출하세요."},
        "no":  {"next": "Q2"},
    },
    {
        "id": "Q2",
        "text": "내열유리·도자기·거울인가요?",
        "description": "파이렉스 등 내열유리, 도자기류, 거울 유리가 해당합니다.",
        "eco_title": "왜 따로 배출해야 하나요?",
        "eco_desc": "내열유리, 도자기, 거울은 일반 유리와 용해 온도가 달라 함께 재활용하면 전체 배치의 품질을 저하시킵니다. 함께 넣으면 재활용 자체가 불가능해집니다.",
        "yes": {"result": "일반쓰레기", "reason": "내열유리·도자기·거울은 일반 유리와 용해 온도가 달라 함께 재활용할 수 없습니다. 일반쓰레기로 배출하세요."},
        "no":  {"next": "Q3"},
    },
    {
        "id": "Q3",
        "text": "내용물을 비웠나요?",
        "description": "병 안의 음료, 소스, 잔여물을 모두 비운 상태인지 확인해주세요.",
        "eco_title": "왜 내용물을 비워야 하나요?",
        "eco_desc": "내용물이 남아 있으면 재활용 과정에서 다른 유리병을 오염시키거나 악취를 유발합니다. 깨끗이 헹군 유리병만 재활용이 가능합니다.",
        "yes": {"result": "유리병 재활용", "reason": "내용물을 비운 깨끗한 유리병입니다. 유리병 전용 수거함에 배출하세요."},
        "no":  {"action": "내용물을 완전히 비운 후 재배출해주세요.", "next": "Q3"},
    },
]

# ──────────────────────────────────────────────
# 금속·캔 트리
# ──────────────────────────────────────────────
METAL_TREE = [
    {
        "id": "Q1",
        "text": "스프레이·부탄가스 캔인가요?",
        "description": "헤어스프레이, 방향제 스프레이, 부탄가스 캔 등이 해당합니다.",
        "eco_title": "왜 가스 캔을 따로 처리하나요?",
        "eco_desc": "잔여 가스가 남은 캔은 수거 차량이나 선별장에서 압축·처리 시 폭발 사고를 일으킬 수 있습니다. 반드시 가스를 완전히 제거한 후 배출해야 합니다.",
        "yes": {"next": "Q1_1"},
        "no":  {"next": "Q2"},
    },
    {
        "id": "Q1_1",
        "parent": "Q1",
        "text": "가스를 완전히 뺐나요?",
        "description": "통풍이 잘 되는 곳에서 밸브를 눌러 가스를 완전히 빼주세요.",
        "eco_title": "가스 제거는 어떻게 하나요?",
        "eco_desc": "야외나 통풍이 잘 되는 곳에서 밸브를 끝까지 눌러 가스를 완전히 빼세요. 그 후 캔 몸통에 송곳으로 구멍을 뚫어 잔여 가스가 없는지 확인하면 안전합니다.",
        "yes": {"result": "캔류 재활용", "reason": "가스를 완전히 제거한 스프레이 캔입니다. 캔·금속류 수거함에 배출하세요."},
        "no":  {"result": "주의 필요 — 가스 제거 후 배출", "reason": "잔여 가스가 남은 캔은 폭발 위험이 있습니다. 통풍이 잘 되는 곳에서 밸브를 눌러 가스를 완전히 빼고, 캔에 구멍을 뚫어 확인한 후 배출하세요."},
    },
    {
        "id": "Q2",
        "text": "내용물을 완전히 비웠나요?",
        "description": "음료, 통조림 등 내용물이 남아있는지 확인해주세요.",
        "eco_title": "왜 내용물을 비워야 하나요?",
        "eco_desc": "내용물이 남은 캔은 재활용 과정에서 오염을 유발하고, 악취 및 위생 문제를 일으킵니다. 가능하면 물로 한 번 헹궈 배출하면 더욱 좋습니다.",
        "yes": {"next": "Q3"},
        "no":  {"action": "내용물을 완전히 비운 후 재배출해주세요.", "next": "Q2"},
    },
    {
        "id": "Q3",
        "text": "다른 재질이 붙어있나요?",
        "description": "플라스틱 뚜껑, 종이 라벨 외에 금속이 아닌 부분이 붙어있는지 확인해주세요.",
        "eco_title": "복합 재질이 왜 문제인가요?",
        "eco_desc": "금속이 아닌 다른 재질이 결합된 경우 재활용 공정에서 불순물이 됩니다. 손으로 분리할 수 있는 부분은 떼어내어 각각의 재질에 맞게 배출하면 재활용률이 높아집니다.",
        "yes": {"next": "Q3_1"},
        "no":  {"result": "캔·금속류 재활용", "reason": "깨끗하고 단일 재질의 캔·금속류입니다. 캔·금속류 수거함에 배출하세요."},
    },
    {
        "id": "Q3_1",
        "text": "손으로 분리할 수 있나요?",
        "description": "다른 재질 부분을 도구 없이 손으로 떼어낼 수 있는지 확인해주세요.",
        "eco_title": "분리 가능 여부가 왜 중요한가요?",
        "eco_desc": "분리할 수 있다면 각각의 재질로 배출해 둘 다 재활용할 수 있습니다. 분리가 불가능한 복합 재질은 재활용 공정에서 처리할 수 없어 일반쓰레기로 분류됩니다.",
        "yes": {"result": "분리 후 각각 해당 재질로 배출", "reason": "부착된 다른 재질 부분을 손으로 분리한 후, 금속 부분은 캔·금속류 수거함에, 분리된 부분은 해당 재질에 맞게 각각 배출하세요."},
        "no":  {"result": "일반쓰레기", "reason": "손으로 분리할 수 없는 복합 재질입니다. 재활용 공정에서 처리가 불가능하므로 일반쓰레기로 배출하세요."},
    },
]

# ──────────────────────────────────────────────
# 카테고리 → 트리 매핑
# ──────────────────────────────────────────────
CATEGORY_TREES = {
    "스티로폼":    STYRO_TREE,
    "유리":        GLASS_TREE,
    "금속·캔":     METAL_TREE,
    # 나머지 카테고리는 추후 추가
}


def get_tree(category: str) -> list | None:
    """카테고리명으로 해당 트리를 반환. 없으면 None."""
    return CATEGORY_TREES.get(category)


def get_question(tree: list, question_id: str) -> dict | None:
    """트리에서 question_id로 질문 딕셔너리를 찾아 반환."""
    for q in tree:
        if q["id"] == question_id:
            return q
    return None


def _effective_skip(tree: list, skip_questions: list[str]) -> set:
    """
    skip_questions에 명시된 ID와, 그 ID를 parent로 갖는 서브 질문 ID를 모두 포함한 집합 반환.
    예) skip=['Q1'] → {'Q1', 'Q1_1'}
    """
    skip = set(skip_questions or [])
    for q in tree:
        if q.get("parent") in skip:
            skip.add(q["id"])
    return skip


def get_first_question(tree: list, skip_questions: list[str] = None) -> dict | None:
    """skip_questions(및 그 서브 질문)를 제외한 첫 번째 질문을 반환."""
    skip = _effective_skip(tree, skip_questions or [])
    for q in tree:
        if q["id"] not in skip:
            return q
    return None


def _next_non_skip(tree: list, next_id: str, skip: set) -> dict | None:
    """next_id에서 시작해 skip에 없는 첫 질문을 반환."""
    q = get_question(tree, next_id)
    while q and q["id"] in skip:
        idx = tree.index(q)
        q = tree[idx + 1] if idx + 1 < len(tree) else None
    return q


def process_answer(tree: list, question_id: str, answer: bool, skip_questions: list[str] = None) -> dict:
    """
    현재 질문에 대한 답변을 처리하여 다음 상태를 반환.

    반환값 타입:
      - {"type": "question", "question": dict}                      → 다음 질문
      - {"type": "result",   "result": str, "reason": str}          → 최종 결과
      - {"type": "guide",    "message": str, "next_question": dict} → 안내 후 다음 질문
    """
    skip = _effective_skip(tree, skip_questions or [])
    question = get_question(tree, question_id)
    if question is None:
        return {"type": "result", "result": "오류", "reason": f"질문 ID '{question_id}'를 찾을 수 없습니다."}

    branch = question["yes"] if answer else question["no"]

    # 직접 결과
    if "result" in branch:
        return {"type": "result", "result": branch["result"], "reason": branch.get("reason", "")}

    # 안내 메시지 후 다음 질문으로
    if "action" in branch:
        next_q = _next_non_skip(tree, branch["next"], skip)
        if next_q is None:
            return {"type": "result", "result": "오류", "reason": "다음 질문을 찾을 수 없습니다."}
        return {"type": "guide", "message": branch["action"], "next_question": next_q}

    # 다음 질문으로 이동
    if "next" in branch:
        next_q = _next_non_skip(tree, branch["next"], skip)
        if next_q is None:
            return {"type": "result", "result": "오류", "reason": "다음 질문을 찾을 수 없습니다."}
        return {"type": "question", "question": next_q}

    return {"type": "result", "result": "오류", "reason": "잘못된 트리 구성입니다."}
