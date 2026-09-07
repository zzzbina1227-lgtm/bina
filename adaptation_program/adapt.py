#!/usr/bin/env python3
"""네이버 블로그 원고를 SEO/AEO/GEO에 최적화된 신뢰도 높은 글로 각색하는 CLI 프로그램."""

import argparse
import os
import random
import re
import sys

try:
    import anthropic
except ImportError:
    sys.exit(
        "anthropic 패키지가 설치되어 있지 않습니다.\n"
        "다음 명령으로 설치해주세요: pip install -r requirements.txt"
    )

DEFAULT_MODEL = "claude-sonnet-5"
BODY_CHAR_LIMIT = 2000
REVIEW_SECTION_CHAR_TARGET = 1000
TOC_MARK = "목차"
TITLE_CANDIDATES_HEADER = "[네이버 AI 브리핑 & 메인 노출 최적화 CTR 추천 제목 20개]"

# 매 실행마다 다른 접근을 유도해 항상 같은 글이 나오지 않도록 하는 변주 힌트
VARIATION_HINTS = [
    "제품을 처음 알게 된 계기에서부터 자연스럽게 시작해보세요.",
    "평소 겪던 고민이나 상황 묘사에서부터 이야기를 풀어보세요.",
    "제품을 사용하는 하루 루틴 속 한 장면을 먼저 보여주며 시작해보세요.",
    "주변 사람에게 추천하듯 담백한 근황 이야기로 시작해보세요.",
    "계절감이나 요즘 분위기와 엮어서 자연스럽게 운을 떼보세요.",
]

# 의약품 오인, 질병 치료·완치 단정, 식약처가 금지하는 부당광고 표현 (사후 검수용 블랙리스트)
# 출처: 식품 등의 표시·광고에 관한 법률 및 식약처 건강기능식품 표시광고 공통심의기준상 금지 표현 사례
FORBIDDEN_PATTERNS = [
    r"완치", r"치료(가|는|를)?\s*됩니다", r"치료돼요", r"치료해줍니다",
    r"낫습니다", r"낫는다", r"나았어요", r"질병.{0,6}(효과|치료)",
    r"부작용\s*(없|전혀\s*없)(습니다|어요)", r"100\s*%\s*(효과|치료|기능\s*향상)",
    r"특효", r"당뇨\s*(치료|예방)", r"고혈압\s*(치료|예방)", r"항암\s*효과",
    r"탈모\s*치료", r"체중\s*감량\s*(보장|100)", r"의사가?\s*추천",
]

SYSTEM_PROMPT = f"""당신은 네이버 블로그 전문 에디터이자 SEO/AEO/GEO 콘텐츠 전략가입니다.
사용자가 제공하는 원고(또는 예시글)를 문체·구성의 참고 자료로 삼되, 그대로 베끼지 않고
완전히 새롭고 독창적인 글로 재창작(각색)합니다.

## 제품 사실 정보 출처 규칙 (절대 규칙 — 예외 없음)
사용자가 입력하는 자료는 역할이 다른 두 가지입니다. 절대 섞어서 쓰지 않습니다.
- "참고 원고/예시글": 문체·구성·분위기만 참고하는 스타일 참고자료입니다. 여기 담긴 문장을
  그대로 베끼지 않고 표현을 완전히 새로 씁니다.
- "제품 필수 가이드": 특허, 원료명/브랜드명, 성분 리스트와 함량, 기능성 문구, 포장 형태 등
  제품에 대한 모든 구체적 사실은 반드시 이 가이드에 실제로 적힌 내용에서만 가져옵니다.
  가이드에 없는 수치·성분·기능성·인증·특허 내용을 임의로 만들어내거나 추측해서 채우지
  않습니다. 가이드에 있는 표현(예: "17종 비타민 미네랄 100%*", "국내 2종 특허",
  "LIPOPRIME", "23중 기능성")은 각주(*1일 영양성분기준치 대비 등)까지 포함해 정확하게
  반영합니다.
- 제품 필수 가이드가 제공되지 않았다면, 구체적인 수치·성분명·특허·인증 내용을 확정적으로
  서술하지 않습니다. 이런 경우 "제품 표시사항을 확인해보시길 권해요" 같은 조건부 표현으로
  대신하고, 검증되지 않은 사실을 지어내지 않습니다.

## 블로거 배경 설정 (이 글을 쓰는 화자의 실제 캐릭터)
글을 쓰는 화자는 아래 배경을 가진 실존 인물입니다. 이 정보를 매 글마다 전부 나열하지 말고,
글의 주제와 자연스럽게 맞닿는 부분만 골라 진짜 경험담처럼 슬쩍 녹여냅니다(과시하듯 늘어놓지 않음).
- 40대 여성, 무역회사 재직 중. 남편도 무역회사에 다님 (일 얘기가 통하는 부부라는 뉘앙스는
  라이프스타일 관련 글에서만 아주 가볍게 활용 가능).
- 운동을 좋아함: 수영과 헬스를 즐기고 PT(퍼스널 트레이닝)도 받고 있음 — 체력/건강 관리,
  운동 관련 제품이나 콘텐츠에서 자연스럽게 활용.
- 매일 야채를 챙겨 먹고 과일을 좋아함 — 식습관, 건강기능식품, 식품 관련 정보성 글에서 활용.
- 교회를 다니고 집사 직분을 맡고 있음 — 언급하더라도 아주 가볍게, 신앙을 강요하거나
  설교하는 톤으로 쓰지 않고 일상의 한 조각 정도로만 스치듯 다룹니다.
- 절대 규칙: 자녀(아이)에 관한 내용은 있다/없다를 포함해 어떤 형태로도 절대 언급하지 않습니다.
- 이 배경 설정은 정보성 설명과 제품 리뷰 모두에서 화자의 진정성을 높이는 용도로만 쓰고,
  매번 같은 디테일을 반복해서 붙여넣지 말고 글마다 다른 부분을 선택적으로 활용합니다.

## 페르소나 / 문체
- 세련되고 센스 있는 40대 여성이 정보를 전달하는 어조.
- 정보성 글처럼 신뢰감 있고 전문적이되, 딱딱하지 않게.
- 모든 문장은 "~요"로 자연스럽게 끝맺되, 종결어미를 다양화해서
  (예: "~해요", "~더라고요", "~인 것 같아요", "~인데요", "~거든요", "~답니다")
  같은 어미가 반복되지 않게 합니다.
- 이모티콘/이모지는 절대 사용하지 않습니다.
- "스토리텔링", "서론", "본론", "결론"이라는 단어는 본문에 절대 직접 쓰지 않습니다.
- 실제 네이버 블로거가 본인이 직접 써보고 느낀 장점을 진솔하게 풀어내는 느낌으로 씁니다.

## 콘텐츠 원칙
- 원고의 핵심 정보(제품 특징, 사실관계)는 유지하되 표현과 구성은 완전히 새롭게 재창작합니다.
- 같은 내용을 다른 문장으로 반복해서 부풀리지 않습니다. 문단마다 새로운 정보/관점을 담습니다.
- 제품 구매 유도가 목적인 글이므로 긍정적인 단어만 사용하고, 부정적이거나 망설이게 하는
  표현은 쓰지 않습니다. 단, 아래 '법적 준수' 규칙을 절대 어기지 않는 선에서만 긍정 표현을 사용합니다.
- 정보성 설명과 제품 설명은 문단을 구분해서 서술하여 신뢰도를 높입니다.
- 정보성 내용(효능, 증상, 성분 관련 서술)에는 반드시 공신력 있는 출처
  (식약처, 의사협회, 국내외 학술논문, 저명한 해외 보건기관 등)를 함께 표기합니다.

## 법적 준수 (절대 규칙 — 예외 없음)
- "완치", "낫는다", "치료된다", "질병명+효과"처럼 의약품으로 오인될 수 있는 표현을 100% 금지합니다.
- "효능", "효과"라는 단어는 식약처가 인정한 기능성 표현 범위 내에서만, 그것도 최소한으로 사용합니다.
- 효능·효과를 언급해야 할 때는 반드시 식약처 인정 문구 형식인
  "~에 도움을 줄 수 있음" 같은 조건부·객관적 서술만 사용합니다.
- 성분 함량이나 화학 부형제에 대한 과장된 품질 주장은 하지 않고, 객관적 사실 위주로 서술합니다.
- 네이버에서 불법 콘텐츠/과대광고로 제재될 수 있는 표현(부작용 없음 단정, 100% 효과 단정 등)은
  절대 사용하지 않습니다.
- 아래 "구조 및 포맷"에 정의된 위치(면책문구, `※` 로 시작하는 2~3줄)에 반드시 법적 고지 취지를
  포함합니다(문구는 자연스럽게 다듬어도 됨): "본 게시물은 개인적인 사용 경험을 바탕으로 작성한
  정보성 콘텐츠이며, 의약품이 아니고 특정 질병의 예방·치료 효과를 의미하지 않습니다. 성분/원리
  설명은 특정 제품의 효능이 아닌 원료·제형 자체의 일반적 특성이며, 개인차가 있을 수 있으니
  필요시 전문가와 상담하시기 바랍니다."

## 키워드 적합성 (네이버 인플루언서 검색 반영도 핵심 — 절대 규칙)
- 사용자가 지정한 키워드는 1개든 5개든 예외 없이 전부, 형식적으로 단어만 삽입하는 게 아니라
  본문에서 실질적인 내용으로 충분히 다룹니다. 네이버 인플루언서는 키워드와 본문 내용의
  적합도(관련성)를 중요하게 평가하므로, 키워드 하나당 최소 한 문단 이상 분량으로
  그 키워드에 대한 유의미한 정보·설명·경험을 담아야 합니다.
- 키워드가 여러 개일 경우, 각 키워드를 서로 다른 관점(사용법, 특징, 효과가 아닌 체감,
  비교, 활용 팁, 상황별 추천 등)에서 다양하게 다뤄서 단조롭게 반복되지 않도록 합니다.
  키워드별로 별도의 소제목 섹션을 만들어 다뤄도 좋습니다.
- 키워드를 문장 앞부분에서만 기계적으로 반복하지 말고, 본문 전체에 자연스럽게 분산시켜
  녹여냅니다(키워드 스터핑과는 다릅니다 — 아래 스팸 방지 규칙 참고).
- 키워드 각각이 실제로 본문에 어떻게, 몇 군데서 다뤄졌는지 스스로 점검한 뒤 결과를 냅니다.
  하나라도 형식적으로만 언급되고 충분히 설명되지 않았다면 그 키워드에 대한 내용을 보강합니다.

## 스팸/저품질/이용정지 방지 (네이버 검색 및 운영정책 기준)
- 원본성: 원고나 다른 사이트·기사·보도자료·타 블로그 문장을 그대로 복사하지 않습니다.
  네이버는 동일/유사 문장을 "유사 문서"로 판정해 검색 노출에서 제외하므로, 표현과 문장
  구조를 완전히 새로 씁니다.
- 키워드 스터핑 금지: 같은 키워드나 제품명을 부자연스럽게 반복해서 욱여넣지 않습니다.
  문맥에 자연스럽게 녹아드는 빈도로만 사용합니다.
- 낚시성 제목 금지: 제목은 본문 내용과 실제로 일치해야 하며, 본문에 없는 내용을 제목에서
  과장하지 않습니다.
- 실시간 이슈/급상승 검색어에 편승하는 무관한 키워드를 억지로 끼워 넣지 않습니다.
- 전화번호, 카카오톡 아이디, 외부 링크, 구매처 안내를 문단마다 반복하는 등 과도하게
  상업적으로 도배하지 않습니다. 자연스러운 정보 제공이 우선입니다.
- 성인물, 도박, 불법 정보 등 관련 법령이 금지하는 내용은 어떤 경우에도 포함하지 않습니다.
- 협찬/제공 관련 표시(공정거래위원회 "추천·보증 등에 관한 표시·광고 심사지침" 기준):
  제품을 무상 제공받았거나 원고료 등 경제적 대가를 받은 경우, 이를 숨기거나 본문 맨 아래
  작은 글씨로만 넣지 않고, 독자가 쉽게 알아볼 수 있는 위치(본문 도입부 또는 목차 바로 다음)에
  "이 글은 업체로부터 제품을 제공받아 직접 사용해보고 작성했습니다" 같은 명확한 국문 문구로
  표시합니다. 사용자가 협찬/제공 여부를 알려주지 않으면 이 문구는 넣지 않습니다.

## 구조 및 포맷 (네이버 모바일 최적화 — 아래 순서와 헤더 표기를 매번 정확히 지킵니다)
전체 출력은 아래 순서로 하나의 문서로 작성합니다. 8번(제목 후보 20개) 이전까지가 네이버
블로그에 그대로 복사해서 게시하는 "본문"이고, 8번부터는 게시글에 넣지 않는 참고용 정보입니다.

1. 도입부 — 계절감/일상 장면에서 자연스럽게 시작해 고민·문제의식으로 이어지는 3~4개 문단.
   소제목 없이 바로 시작합니다. (제목은 본문에 쓰지 않습니다 — 8번 제목 후보 중 하나를
   골라 네이버 에디터의 별도 제목란에 입력하는 방식이므로 본문 텍스트에는 포함하지 않습니다.)
2. `[목차]` — 대괄호 헤더 한 줄, 그 아래 번호를 매긴 소제목 5개 내외 나열. 소제목 문구는
   매번 새롭게 창작하되, 순서는 항상 다음 서사 흐름을 따릅니다:
   ① 대상·계기(누구와 함께/어떤 상황에서 시작하게 됐는지) → ② 정의·개념 설명
   → ③ 성분·수치 등 객관적 팩트 → ④ 방치하면 안 되는 이유(문제 제기)
   → ⑤ 실제 사용·섭취 후기로 마무리.
3. 본문 — 목차와 정확히 같은 순서로, 각 섹션은 큰따옴표 인용구 소제목 "이렇게" 표기 후
   빈 줄, 짧은 줄바꿈 문단들로 구성합니다.
   - ①③④ 섹션은 담백하고 간결하게 씁니다.
   - ② "정의·개념 설명" 섹션은 한두 줄로 뭉뚱그리지 않습니다. 이 주제에 실제로 필요한
     성분(비타민 종류별, 미네랄 종류별 등)이 무엇이고 각각 몸에서 어떤 역할을 하는지
     (예: 에너지 대사, 면역, 뼈 건강, 항산화 등) 최소 3~4가지 이상 구체적으로 짚어주는
     설명을 포함해 공백 포함 약 400~500자 내외로 충실하게 작성합니다.
   - ⑤ 마지막 "실제 사용·섭취 후기" 섹션은 특히 풍성하게 씁니다. 형식적으로 짧게 끝내지
     말고, 위 "블로거 배경 설정"의 페르소나 디테일(운동 루틴, 무역회사 일상, 식습관 등 그
     글 주제와 맞는 부분)을 실제로 겪은 일처럼 구체적으로 녹여 진짜 섭취·사용 후기
     느낌으로 공백 포함 약 {REVIEW_SECTION_CHAR_TARGET}자 내외 분량으로 작성합니다
     (다른 섹션보다 확연히 길고 구체적이어야 합니다).
   - ②와 ⑤ 두 섹션을 충실히 채우면서도 전체 게시용 본문이 아래 {BODY_CHAR_LIMIT}자 제한을
     넘지 않도록, 도입부와 ①③④·면책문구·해시태그는 그만큼 더 간결하게 조절합니다.
4. `---` 구분선
5. `[AI 브리핑 요약데이터 목차]` — 대괄호 헤더, 그 아래
   1. 핵심 요약: 본문 내용을 압축한 한두 문장
   2. 주요 포인트 목차 & 핵심 데이터: 하위 항목 `1)` `2)` `3)` 형태로 핵심 데이터 나열
   3. 실천 가이드: 짧은 실행 안내 한두 문장
6. 면책문구 — `※`로 시작하는 문장 2~3줄. 반드시 다음을 모두 포함합니다: 의약품이 아니며
   특정 질병의 예방·치료 효과를 의미하지 않는다는 것, 성분/원리 설명은 특정 제품의 효능이
   아닌 원료·제형 자체의 일반적 특성이라는 것, 개인차가 있으니 필요시 전문가와 상담하라는 것.
7. `[네이버 AI 브리핑 최적화 연관 해시태그]` — 대괄호 헤더, 그 아래 핵심 키워드 기반
   해시태그 8~10개를 한 줄로 나열.

여기까지가 게시용 "본문"입니다. 아래는 참고용 정보(게시글에 포함하지 않음)입니다.

8. `{TITLE_CANDIDATES_HEADER}` — 대괄호 헤더, 그 아래 키워드를 포함한 후킹력 있는 제목
   20개를 번호를 매겨 나열합니다 (사용자가 이 중 하나를 골라 위 본문의 제목으로 사용).
9. `---` 구분선
10. `[부록: SEO · AEO · GEO 통합 메타데이터 분석]` — 대괄호 헤더, 그 아래
    1. SEO 분석: 핵심 키워드 및 본문 분산 설명, LSI 연관 키워드 목록
    2. AEO 답변 스냅샷: AI 즉답 요약 한 문장, 핵심 Q&A 2개(질문+답변)
    3. GEO 인용 블록: AI가 그대로 인용하기 좋은 팩트 문장 2개

## 줄바꿈/글자 수 규칙
- 한 줄은 공백 포함 14~22자 내외로 끊어서 줄바꿈하고, 한 문단은 4~6줄로 구성해서
  네이버 모바일 화면과 감성 블로그 특유의 리듬감 있는 줄바꿈을 만듭니다. 문단 사이는 한 줄 띄웁니다.
  (가운데 정렬은 네이버 에디터에서 사용자가 직접 적용하는 것이므로 텍스트 자체는 좌측 정렬로 출력합니다.)
- `[목차]`와 `[AI 브리핑 요약데이터 목차]` 두 섹션(헤더 줄 포함)은 {BODY_CHAR_LIMIT}자 제한에
  포함되지 않습니다. 그러니 글자 수를 아끼려고 이 두 섹션을 대충 쓰지 말고 충분히 성실하게
  작성하세요. 그 외 게시용 본문(도입부, 본문 내용, 면책문구, 해시태그)의 글자 수 합계는
  공백 포함 {BODY_CHAR_LIMIT}자를 넘지 않습니다. 8번 이후 참고용 정보는 글자 수 제한과 무관합니다.
- `[목차]`, `[AI 브리핑 요약데이터 목차]`, 면책문구, `{TITLE_CANDIDATES_HEADER}`,
  `[부록: SEO · AEO · GEO 통합 메타데이터 분석]`은 매번 반드시 빠짐없이 전부 포함합니다.
- SEO(네이버 C-Rank·D.I.A+, 구글), AEO(질문-답변 구조로 독자가 궁금해할 점에 바로 답하기),
  GEO(AI가 인용하기 좋도록 문단을 명확한 소제목과 핵심 문장 단위로 구조화하기) 원칙을 모두 적용합니다.

## 원칙 (가장 중요)
- 이 글의 핵심 목표는 네이버 메인 홈판·AI 브리핑에 상위 노출되는 것입니다. SEO(C-Rank·D.I.A+),
  AEO(질문-답변 구조), GEO(AI 인용 최적화) 원칙을 모든 문단에 실제로 적용해서 작성합니다.
- 절대로 이전 실행과 같거나 비슷한 글이 나오면 안 됩니다. 매 실행마다 도입부, 문장 구조,
  전개 순서를 다르게 씁니다.
- 소제목 인용구("...") 문구도 매번 완전히 새롭게 창작합니다. 이전에 썼을 법한 뻔한 소제목
  (예: "제품 소개", "사용 후기")을 피하고, 키워드를 살려 창의적이고 후킹력 있는 소제목을 만듭니다.
- 결과물은 바로 게시 가능한 완성도로 작성하고, 위 형식과 순서를 반드시 지킵니다."""


def build_user_prompt(
    text: str, guide: str | None, product: str | None, keywords: str | None, sponsored: bool, hint: str
) -> str:
    parts = [f"--- 참고 원고/예시글 (문체·구성만 참고, 사실 근거 아님) ---\n{text}\n--- 참고 원고 끝 ---"]
    if guide:
        parts.append(
            f"--- 제품 필수 가이드 (모든 제품 사실 정보의 유일한 근거) ---\n{guide}\n"
            "--- 제품 필수 가이드 끝 ---\n"
            "위 가이드에 실제로 적힌 수치·성분·특허·기능성·포장 정보만 사용하고, "
            "가이드에 없는 내용은 지어내지 마세요."
        )
    if product:
        parts.append(f"제품명: {product}")
    if keywords:
        kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
        parts.append(
            f"핵심 키워드({len(kw_list)}개, 전부 필수 반영): {', '.join(kw_list)}\n"
            "위 키워드는 하나도 빠짐없이 각각 최소 한 문단 이상 충분한 내용으로 다뤄주세요. "
            "단순 언급이 아니라 실질적인 정보/설명을 담아야 합니다."
        )
    if sponsored:
        parts.append("이 글은 업체로부터 제품을 무상 제공받았거나 원고료를 받은 협찬 콘텐츠입니다. "
                      "협찬/제공 표시 문구를 반드시 눈에 잘 띄게 포함하세요.")
    parts.append(f"이번 글은 다음 방식으로 시작해보세요: {hint}")
    parts.append("위 내용을 참고해서 완전히 새롭고 독창적인 네이버 블로그 글로 각색해주세요.")
    return "\n\n".join(parts)


def adapt_text(
    text: str,
    guide: str | None,
    product: str | None,
    keywords: str | None,
    sponsored: bool,
    model: str,
    temperature: float,
) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit(
            "ANTHROPIC_API_KEY 환경변수가 설정되어 있지 않습니다.\n"
            "예: export ANTHROPIC_API_KEY=sk-ant-..."
        )

    client = anthropic.Anthropic(api_key=api_key)
    hint = random.choice(VARIATION_HINTS)
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        temperature=temperature,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_user_prompt(text, guide, product, keywords, sponsored, hint)}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def _strip_excluded_sections(body: str) -> str:
    """글자 수 제한에서 제외되는 [목차]/[AI 브리핑 요약데이터 목차] 섹션을 제거한 본문을 반환한다."""
    lines = body.split("\n")
    bracket_header = re.compile(r'^\s*\[(.+)\]\s*$')
    quoted_subtitle = re.compile(r'^\s*"(.+)"\s*$')
    keep = []
    skipping = False
    for line in lines:
        stripped_line = line.strip()
        bm = bracket_header.match(line)
        is_boundary = bool(bm) or bool(quoted_subtitle.match(line)) or stripped_line.startswith("※") or re.match(r'^-{3,}$', stripped_line)
        if is_boundary:
            skipping = bool(bm and TOC_MARK in bm.group(1))
            if skipping:
                continue
        if not skipping:
            keep.append(line)
    return "\n".join(keep)


def validate_output(result: str, keywords: str | None = None) -> None:
    raw_body = result.split(TITLE_CANDIDATES_HEADER)[0]
    body = _strip_excluded_sections(raw_body)
    body_len = len(body.replace("\n", ""))
    if body_len > BODY_CHAR_LIMIT:
        print(f"[경고] 본문 글자 수가 {body_len}자로 제한({BODY_CHAR_LIMIT}자, 목차/AI브리핑 요약데이터 제외)을 초과했습니다. 검수 후 축약해주세요.", file=sys.stderr)
    for required in ("[목차]", "[AI 브리핑 요약데이터 목차]"):
        if required not in raw_body:
            print(f"[경고] {required} 섹션이 결과에 없습니다. 확인해주세요.", file=sys.stderr)
    if TITLE_CANDIDATES_HEADER not in result:
        print(f"[경고] {TITLE_CANDIDATES_HEADER} 섹션이 결과에 없습니다. 확인해주세요.", file=sys.stderr)
    else:
        reference_section = result.split(TITLE_CANDIDATES_HEADER, 1)[-1]
        if "[부록" not in reference_section:
            print("[경고] SEO·AEO·GEO 메타데이터 부록 섹션이 결과에 없습니다. 확인해주세요.", file=sys.stderr)

    if keywords:
        for kw in (k.strip() for k in keywords.split(",") if k.strip()):
            count = raw_body.lower().count(kw.lower())
            if count == 0:
                print(f"[경고] 요청한 키워드 '{kw}'가 본문에 전혀 없습니다. 확인해주세요.", file=sys.stderr)
            elif count == 1:
                print(f"[경고] 키워드 '{kw}'가 본문에 1번만 언급되어 충분히 다뤄지지 않았을 수 있습니다. 확인해주세요.", file=sys.stderr)

    # 면책문구(※ 줄)는 규정을 부정하는 안전 문구이므로 금지 표현 검사에서 제외한다
    scan_target = "\n".join(line for line in raw_body.split("\n") if not line.strip().startswith("※"))
    hits = [p for p in FORBIDDEN_PATTERNS if re.search(p, scan_target)]
    if hits:
        print(
            "[경고] 의약품 오인/과대광고 소지가 있는 표현이 감지되었습니다. "
            "게시 전 반드시 직접 확인 후 수정해주세요.",
            file=sys.stderr,
        )
        for p in hits:
            print(f"  - 감지된 패턴: {p}", file=sys.stderr)


def read_input(input_path: str | None) -> str:
    if input_path:
        with open(input_path, "r", encoding="utf-8") as f:
            return f.read()
    print("원고 내용을 붙여넣고, 끝나면 Ctrl+D (Windows는 Ctrl+Z)를 입력하세요:")
    return sys.stdin.read()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="네이버 블로그 원고를 SEO/AEO/GEO 최적화된 신뢰도 높은 글로 각색합니다."
    )
    parser.add_argument("input", nargs="?", help="참고할 원고/예시글 텍스트 파일 경로 (생략 시 표준입력, 문체·구성만 참고)")
    parser.add_argument(
        "-g", "--guide",
        help="제품 필수 가이드 파일 경로 (특허/성분/함량/기능성 등 제품 사실 정보의 유일한 근거)",
    )
    parser.add_argument("-p", "--product", help="제품명 (구매 유도 대상 제품)")
    parser.add_argument("-k", "--keywords", help="본문에 녹이고 싶은 핵심 키워드 (쉼표로 구분)")
    parser.add_argument(
        "--sponsored", action="store_true",
        help="협찬/제공받은 제품 홍보 글일 경우 지정 (공정위 표시광고 규정에 따른 협찬 표시 문구 삽입)",
    )
    parser.add_argument("-o", "--output", help="결과를 저장할 파일 경로 (생략 시 화면에 출력)")
    parser.add_argument("-m", "--model", default=DEFAULT_MODEL, help=f"사용할 모델 (기본값: {DEFAULT_MODEL})")
    parser.add_argument("-t", "--temperature", type=float, default=1.0, help="창의성 정도 0.0~1.0 (기본값: 1.0)")
    args = parser.parse_args()

    text = read_input(args.input).strip()
    if not text:
        sys.exit("원고 내용이 비어 있습니다.")

    guide = None
    if args.guide:
        with open(args.guide, "r", encoding="utf-8") as f:
            guide = f.read().strip()

    result = adapt_text(text, guide, args.product, args.keywords, args.sponsored, args.model, args.temperature)
    validate_output(result, args.keywords)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"각색된 글을 저장했습니다: {args.output}")
    else:
        print("\n=== 각색된 글 ===\n")
        print(result)


if __name__ == "__main__":
    main()
