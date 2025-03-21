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

## 슬랙 API 설정

1. Slack 앱 생성 및 설정
    - Slack API 웹사이트에서 새 앱을 생성합니다
    - "Create New App" → "From scratch" 선택
    - 앱 이름과 워크스페이스 선택

2. 토큰 발급

- 생성된 앱에서 "OAuth & Permissions" 섹션으로 이동
    - 다음 권한들을 추가해야 합니다:
        - app_mentions:read
        - channels:history
        - channels:join
        - channels:manage
        - channels:read
        - channels:write.invites
        - chat:write
        - groups:history
        - groups:read
        - groups:write.invites
        - im:history
        - im:read
        - mpim:read
        - mpim:write
        - users:read
- "Bot User OAuth Token" (xoxb-로 시작) 복사
- "Basic Information" 섹션에서 "App-Level Token" (xapp-로 시작) 생성 및 복사
- "Event Subscriptions" 섹션 "On"
    - 아래의 "Subscribe to bot events"에서 "Add Bot User Event", "app_mention"
- "Socket Mode" 섹션 "On"

3. 환경 변수 설정

- 프로젝트 루트에 .env 파일 생성
- 다음 내용 추가:
    ```
    SLACK_BOT_TOKEN=xoxb-your-bot-token
    SLACK_APP_TOKEN=xapp-your-app-token
    ```

4. Slack 워크스페이스에 앱 설치

- "Install to Workspace" 버튼 클릭

5. 채널 설정
- Slack 워크스페이스에서 #action-items 채널 생성
- 생성한 앱을 해당 채널에 초대

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