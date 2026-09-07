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
BODY_DELIMITER = "=====참고용 정보 (게시글 본문 아님)====="

# 매 실행마다 다른 접근을 유도해 항상 같은 글이 나오지 않도록 하는 변주 힌트
VARIATION_HINTS = [
    "제품을 처음 알게 된 계기에서부터 자연스럽게 시작해보세요.",
    "평소 겪던 고민이나 상황 묘사에서부터 이야기를 풀어보세요.",
    "제품을 사용하는 하루 루틴 속 한 장면을 먼저 보여주며 시작해보세요.",
    "주변 사람에게 추천하듯 담백한 근황 이야기로 시작해보세요.",
    "계절감이나 요즘 분위기와 엮어서 자연스럽게 운을 떼보세요.",
]

# 의약품 오인, 질병 치료·완치 단정 등 절대 사용 금지 표현 (사후 검수용 블랙리스트)
FORBIDDEN_PATTERNS = [
    r"완치", r"치료(가|는|를)?\s*됩니다", r"치료돼요", r"치료해줍니다",
    r"낫습니다", r"낫는다", r"나았어요", r"질병.{0,6}(효과|치료)",
    r"부작용\s*없(습니다|어요)", r"100%\s*(효과|치료)",
]

SYSTEM_PROMPT = f"""당신은 네이버 블로그 전문 에디터이자 SEO/AEO/GEO 콘텐츠 전략가입니다.
사용자가 제공하는 원고(또는 예시글, 제품 정보)를 참고하되, 그대로 베끼지 않고
완전히 새롭고 독창적인 글로 재창작(각색)합니다.

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
- 본문 마지막에는 반드시 아래와 같은 취지의 법적 고지문을 포함합니다(문구는 자연스럽게 다듬어도 됨):
  "본 게시물은 개인적인 사용 경험을 바탕으로 작성되었으며, 특정 질병의 예방·치료 효과를 의미하지
  않습니다. 제품의 효과는 개인차가 있을 수 있으며, 구매 및 섭취/사용 전 제품 설명서를 확인하시고
  필요시 전문가와 상담하시기 바랍니다."

## 구조 및 포맷 (네이버 모바일 최적화)
- 전체 출력은 두 부분으로 나눕니다: (1) 그대로 복사해서 게시할 수 있는 "본문",
  (2) "{BODY_DELIMITER}" 구분선 아래에 오는 참고용 SEO 정보.
- 본문 구성 순서: 제목, 목차(간단한 소제목 나열), 본문 내용(소제목은 반드시 큰따옴표
  인용구 형태로 "이렇게" 표기), 마지막 요약(본문 내용을 바탕으로 한 짧은 정리),
  법적 고지문, #해시태그.
- 한 줄은 공백 포함 14~22자 내외로 끊어서 줄바꿈하고, 한 문단은 4~6줄로 구성해서
  네이버 모바일 화면과 감성 블로그 특유의 리듬감 있는 줄바꿈을 만듭니다. 문단 사이는 한 줄 띄웁니다.
  (가운데 정렬은 네이버 에디터에서 사용자가 직접 적용하는 것이므로 텍스트 자체는 좌측 정렬로 출력합니다.)
- 본문(고지문·해시태그 포함, 참고용 SEO 정보 제외) 전체 글자 수는 공백 포함 {BODY_CHAR_LIMIT}자를 넘지 않습니다.
- SEO(네이버 C-Rank·D.I.A+, 구글), AEO(질문-답변 구조로 독자가 궁금해할 점에 바로 답하기),
  GEO(AI가 인용하기 좋도록 문단을 명확한 소제목과 핵심 문장 단위로 구조화하기) 원칙을 모두 적용합니다.

## 구분선 아래 참고용 정보 (본문 글자 수에 포함하지 않음)
"{BODY_DELIMITER}" 아래에는 다음을 포함합니다.
1. 연관 키워드: 본문 문맥에 자연스럽게 녹인 핵심 키워드 목록과, 함께 노출하면 좋은 연관 키워드 목록.
2. 참고자료/출처: 정보성 서술에 사용한 출처 목록 (효능·증상 관련 언급이 있었다면 필수).
3. 클릭률(CTR) 높은 제목 후보 20개: 네이버 AI 브리핑·메인 노출에 유리하도록 키워드를 포함한
   후킹력 있는 제목 20개를 번호를 매겨 나열.
4. 추천 해시태그: 네이버 AI 브리핑 노출에 유리한 연관 해시태그 목록 (본문 해시태그와 중복 가능).

## 원칙
- 매 실행마다 이전과 다른 도입부, 다른 문장 구조, 다른 소제목 표현을 사용해 절대 같은 글이
  나오지 않도록 합니다.
- 결과물은 바로 게시 가능한 완성도로 작성하고, 위 형식과 순서를 반드시 지킵니다."""


def build_user_prompt(text: str, product: str | None, keywords: str | None, hint: str) -> str:
    parts = [f"--- 참고 원고/예시글 ---\n{text}\n--- 참고 원고 끝 ---"]
    if product:
        parts.append(f"제품명: {product}")
    if keywords:
        parts.append(f"핵심 키워드(가능하면 활용): {keywords}")
    parts.append(f"이번 글은 다음 방식으로 시작해보세요: {hint}")
    parts.append("위 내용을 참고해서 완전히 새롭고 독창적인 네이버 블로그 글로 각색해주세요.")
    return "\n\n".join(parts)


def adapt_text(text: str, product: str | None, keywords: str | None, model: str, temperature: float) -> str:
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
        messages=[{"role": "user", "content": build_user_prompt(text, product, keywords, hint)}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def validate_output(result: str) -> None:
    body = result.split(BODY_DELIMITER)[0]
    body_len = len(body.replace("\n", ""))
    if body_len > BODY_CHAR_LIMIT:
        print(f"[경고] 본문 글자 수가 {body_len}자로 제한({BODY_CHAR_LIMIT}자)을 초과했습니다. 검수 후 축약해주세요.", file=sys.stderr)

    hits = [p for p in FORBIDDEN_PATTERNS if re.search(p, body)]
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
    parser.add_argument("input", nargs="?", help="참고할 원고/예시글 텍스트 파일 경로 (생략 시 표준입력)")
    parser.add_argument("-p", "--product", help="제품명 (구매 유도 대상 제품)")
    parser.add_argument("-k", "--keywords", help="본문에 녹이고 싶은 핵심 키워드 (쉼표로 구분)")
    parser.add_argument("-o", "--output", help="결과를 저장할 파일 경로 (생략 시 화면에 출력)")
    parser.add_argument("-m", "--model", default=DEFAULT_MODEL, help=f"사용할 모델 (기본값: {DEFAULT_MODEL})")
    parser.add_argument("-t", "--temperature", type=float, default=1.0, help="창의성 정도 0.0~1.0 (기본값: 1.0)")
    args = parser.parse_args()

    text = read_input(args.input).strip()
    if not text:
        sys.exit("원고 내용이 비어 있습니다.")

    result = adapt_text(text, args.product, args.keywords, args.model, args.temperature)
    validate_output(result)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"각색된 글을 저장했습니다: {args.output}")
    else:
        print("\n=== 각색된 글 ===\n")
        print(result)


if __name__ == "__main__":
    main()
