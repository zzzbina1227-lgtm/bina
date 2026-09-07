#!/usr/bin/env python3
"""네이버 블로그 원고를 창의적인 글로 각색해주는 CLI 프로그램."""

import argparse
import os
import sys

try:
    import anthropic
except ImportError:
    sys.exit(
        "anthropic 패키지가 설치되어 있지 않습니다.\n"
        "다음 명령으로 설치해주세요: pip install -r requirements.txt"
    )

STYLES = {
    "스토리텔링": "개인적인 경험담처럼 이야기를 풀어가는 스토리텔링 문체로, 독자가 몰입할 수 있는 서사 구조를 사용해서",
    "유머러스": "위트와 유머를 곁들여 재미있고 가볍게 읽히는 문체로",
    "감성적": "감성적이고 서정적인 표현을 살려 마음에 와닿는 문체로",
    "전문가톤": "신뢰감 있는 전문가의 어조로, 근거와 논리를 갖춘 문체로",
    "친근한": "친한 친구에게 말하듯 편안하고 친근한 구어체 문체로",
}

DEFAULT_MODEL = "claude-sonnet-5"

SYSTEM_PROMPT = """당신은 네이버 블로그 원고를 각색하는 전문 에디터입니다.
사용자가 제공하는 원고는 흔하고 뻔한 블로그 말투(도입부 인사, 상투적인 문구, 획일적인 문단 구성 등)로 쓰여 있어
다른 블로그들과 비슷비슷하다는 문제가 있습니다.

다음 원칙을 지켜 원고를 각색하세요:
1. 핵심 정보, 사실관계, 추천/설명 대상은 절대 바꾸지 않습니다.
2. 문장 구조와 어휘를 다양화하여 뻔한 블로그 문구(예: "안녕하세요 여러분", "오늘은 ~에 대해 알아볼게요" 등)를 피합니다.
3. 문단 구성과 도입부/마무리를 창의적으로 재구성합니다.
4. 요청받은 문체를 일관되게 적용합니다.
5. 결과물은 바로 블로그에 게시할 수 있는 완성된 글이어야 합니다.
6. 각색된 글만 출력하고, 별도의 설명이나 주석은 붙이지 않습니다."""


def build_user_prompt(text: str, style: str) -> str:
    style_desc = STYLES[style]
    return (
        f"아래 네이버 블로그 원고를 {style_desc} 창의적으로 각색해주세요.\n\n"
        f"--- 원고 ---\n{text}\n--- 원고 끝 ---"
    )


def adapt_text(text: str, style: str, model: str) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit(
            "ANTHROPIC_API_KEY 환경변수가 설정되어 있지 않습니다.\n"
            "예: export ANTHROPIC_API_KEY=sk-ant-..."
        )

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_user_prompt(text, style)}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def read_input(input_path: str | None) -> str:
    if input_path:
        with open(input_path, "r", encoding="utf-8") as f:
            return f.read()
    print("원고 내용을 붙여넣고, 끝나면 Ctrl+D (Windows는 Ctrl+Z)를 입력하세요:")
    return sys.stdin.read()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="네이버 블로그 원고를 창의적인 글로 각색합니다."
    )
    parser.add_argument("input", nargs="?", help="원고 텍스트 파일 경로 (생략 시 표준입력으로 붙여넣기)")
    parser.add_argument(
        "-s", "--style", choices=STYLES.keys(), default="스토리텔링", help="각색 문체 (기본값: 스토리텔링)"
    )
    parser.add_argument("-o", "--output", help="결과를 저장할 파일 경로 (생략 시 화면에 출력)")
    parser.add_argument("-m", "--model", default=DEFAULT_MODEL, help=f"사용할 모델 (기본값: {DEFAULT_MODEL})")
    args = parser.parse_args()

    text = read_input(args.input).strip()
    if not text:
        sys.exit("원고 내용이 비어 있습니다.")

    result = adapt_text(text, args.style, args.model)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"각색된 글을 저장했습니다: {args.output}")
    else:
        print("\n=== 각색된 글 ===\n")
        print(result)


if __name__ == "__main__":
    main()
