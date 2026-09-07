# 각색 프로그램

네이버 블로그 원고가 다 비슷비슷하고 뻔한 문체로 느껴질 때, Claude API를 이용해
창의적인 문체로 각색해주는 CLI 도구입니다.

## 설치

```bash
cd adaptation_program
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # Anthropic API 키 설정
```

## 사용법

파일로 각색:

```bash
python adapt.py my_draft.txt -s 스토리텔링 -o result.txt
```

붙여넣기로 각색 (파일 없이 바로 입력):

```bash
python adapt.py
# 원고 내용을 붙여넣고 Ctrl+D
```

### 옵션

| 옵션 | 설명 | 기본값 |
| --- | --- | --- |
| `input` | 원고 텍스트 파일 경로 (생략 시 표준입력) | - |
| `-s`, `--style` | 각색 문체: `스토리텔링`, `유머러스`, `감성적`, `전문가톤`, `친근한` | `스토리텔링` |
| `-o`, `--output` | 결과 저장 파일 경로 (생략 시 화면 출력) | - |
| `-m`, `--model` | 사용할 Claude 모델 | `claude-sonnet-5` |

### 예시

```bash
python adapt.py naver_draft.txt -s 유머러스 -o adapted.txt
```

원본의 핵심 정보(사실관계, 추천 대상 등)는 그대로 유지하면서, 문장 구조와
어휘, 도입부/마무리 구성을 다양화하여 뻔한 블로그 말투에서 벗어난 글을 만들어줍니다.
