# Slack 액션 아이템 생성 봇

Slack 대화에서 자동으로 액션 아이템을 추출하고 정리하는 봇입니다.

## 개발 환경

이 프로젝트는 [Cursor](https://cursor.sh)를 사용하여 처음부터 끝까지 개발되었습니다. Cursor의 AI 코딩 어시스턴트를 활용하여 코드 작성, 디버깅, 최적화를 진행했습니다.

## 기능

- Slack 스레드의 대화 내용을 분석하여 액션 아이템 추출
- 각 액션 아이템에 담당자, 작업 내용, 마감 기한 포함
- Hugging Face 모델 또는 OpenAI API를 사용한 자연어 처리
- 한국어/영어 대화 지원

## 환경 설정

### 필수 환경 변수

`.env` 파일에 다음 환경 변수들을 설정해야 합니다:

```env
# Slack 설정
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token

# 모델 설정
MODEL_TYPE=huggingface  # 또는 openai

# Hugging Face 설정 (MODEL_TYPE=huggingface인 경우)
HUGGINGFACE_TOKEN=your-huggingface-token
HUGGINGFACE_MODEL=mistralai/Mistral-7B-v0.1  # 사용할 모델 지정

# OpenAI 설정 (MODEL_TYPE=openai인 경우)
OPENAI_API_KEY=your-openai-api-key
```


## 설치 방법

1. 저장소 클론
```bash
git clone [repository-url]
cd [repository-name]
```

2. 가상환경 생성 및 활성화
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
.\venv\Scripts\activate  # Windows
```

3. 의존성 설치
```bash
pip install -r requirements.txt
```

## 실행 방법

```bash
python app.py
```

## 사용 방법

1. Slack 워크스페이스에 봇을 추가합니다.
2. 봇이 참여할 채널에 초대합니다.
3. 스레드에서 대화를 나눕니다.
4. 봇이 자동으로 액션 아이템을 추출하여 스레드에 답글을 달아줍니다.

## 액션 아이템 형식

```
- [담당자]: [구체적인 할 일] (마감 기한: YYYY-MM-DD)
```

## 로그

- `slack_bot.log`: Slack 봇 관련 로그

## 주의사항

- Hugging Face 모델을 사용할 경우 충분한 GPU 메모리가 필요합니다.
- OpenAI API를 사용할 경우 API 사용량에 따른 비용이 발생할 수 있습니다.
- 봇이 채널에 참여할 수 있는 권한이 필요합니다. 