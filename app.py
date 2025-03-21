import os
import logging
from datetime import datetime
import pytz
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from action_item_generator import ActionItemGenerator

# 로깅 설정
seoul_tz = pytz.timezone('Asia/Seoul')
class SeoulFormatter(logging.Formatter):
    def converter(self, timestamp):
        dt = datetime.fromtimestamp(timestamp, tz=pytz.UTC)
        return dt.astimezone(seoul_tz)
    
    def formatTime(self, record, datefmt=None):
        dt = self.converter(record.created)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.strftime('%Y-%m-%d %H:%M:%S %Z')

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('slack_bot.log'),
        logging.StreamHandler()
    ]
)

# 로거에 서울 시간 포맷터 적용
for handler in logging.getLogger().handlers:
    handler.setFormatter(SeoulFormatter())

logger = logging.getLogger(__name__)

# 환경 변수 로드
load_dotenv()

# 모델 타입 설정 (기본값: huggingface)
MODEL_TYPE = os.getenv("MODEL_TYPE", "huggingface")

# Hugging Face 모델 이름 설정 (기본값: mistralai/Mistral-7B-v0.1)
HUGGINGFACE_MODEL = os.getenv("HUGGINGFACE_MODEL", "mistralai/Mistral-7B-v0.1")

# Slack 앱 초기화
app = App(token=os.environ["SLACK_BOT_TOKEN"])

# 액션 아이템 생성기 초기화
action_item_generator = ActionItemGenerator(
    slack_app=app, 
    model_type=MODEL_TYPE,
    model_name=HUGGINGFACE_MODEL if MODEL_TYPE == "huggingface" else None
)

def get_channel_id(app, channel_name):
    """채널 이름으로 채널 ID를 찾음 (public/private 모두 검색)"""
    try:
        # 공개 채널 검색
        result = app.client.conversations_list(types="public_channel")
        for channel in result["channels"]:
            if channel["name"] == channel_name:
                return channel["id"]
        
        # 비공개 채널 검색
        result = app.client.conversations_list(types="private_channel")
        for channel in result["channels"]:
            if channel["name"] == channel_name:
                return channel["id"]
                
        logger.warning(f"채널을 찾을 수 없음: {channel_name}")
        return None
    except Exception as e:
        logger.error(f"채널 ID 조회 중 에러 발생: {str(e)}")
        return None

def join_channel(channel_id: str):
    """채널 참여 시도"""
    try:
        # 먼저 public 채널 참여 시도
        app.client.conversations_join(channel=channel_id)
        logger.info(f"Public 채널 {channel_id} 참여 성공")
    except Exception as e:
        try:
            # public 채널 참여 실패시 private 채널 참여 시도
            app.client.conversations_invite(
                channel=channel_id,
                users=[app.client.auth_test()["user_id"]]
            )
            logger.info(f"Private 채널 {channel_id} 참여 성공")
        except Exception as e:
            logger.error(f"채널 {channel_id} 참여 실패: {str(e)}")
            raise

@app.event("app_mention")
def handle_mention(event, say):
    """봇이 언급되었을 때 실행되는 핸들러"""
    try:
        logger.info("=== 봇 멘션 이벤트 시작 ===")
        logger.info(f"전체 이벤트 데이터: {event}")
        
        channel_id = event["channel"]
        thread_ts = event.get("thread_ts", event["ts"])
        user_id = event.get("user")
        text = event.get("text", "")
        
        logger.info(f"채널 ID: {channel_id}")
        logger.info(f"스레드 TS: {thread_ts}")
        logger.info(f"사용자 ID: {user_id}")
        logger.info(f"메시지 텍스트: {text}")
        
        # 스레드의 모든 메시지 가져오기 시도
        try:
            logger.info("스레드 메시지 조회 시작")
            thread_messages = app.client.conversations_replies(
                channel=channel_id,
                ts=thread_ts
            )
            messages_count = len(thread_messages.get('messages', []))
            logger.info(f"스레드 메시지 조회 완료: {messages_count}개 메시지")
            
            if messages_count == 0:
                logger.warning("스레드에서 메시지를 찾을 수 없습니다.")
                return
            
            # 대화 내용 분석 및 액션 아이템 생성
            logger.info("액션 아이템 생성 시작")
            action_items = action_item_generator.generate(thread_messages)
            logger.info(f"액션 아이템 생성 완료: {len(action_items)}개 항목")
            
            if not action_items:
                logger.warning("액션 아이템을 찾을 수 없습니다.")
                return
            
            # 액션 아이템을 #action-items-alarm 채널에 포스팅
            post_action_items(app, action_items, channel_id, thread_ts)
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"처리 중 에러 발생: {error_message}", exc_info=True)
            
            if "not_in_channel" in error_message:
                logger.error("채널 접근 권한이 없습니다.")
            elif "channel_not_found" in error_message:
                logger.error("채널을 찾을 수 없습니다.")
            elif "missing_scope" in error_message:
                logger.error("스레드 메시지를 읽을 수 있는 권한이 없습니다.")
            else:
                logger.error(f"액션 아이템 생성 중 오류가 발생했습니다: {error_message}")
            
    except Exception as e:
        logger.error(f"예상치 못한 에러 발생: {str(e)}", exc_info=True)
    finally:
        logger.info("=== 봇 멘션 이벤트 종료 ===")

def post_action_items(app, action_items, original_channel_id, thread_ts):
    """생성된 액션 아이템을 #action-items-alarm 채널에 포스팅"""
    try:
        channel_name = "action-items-alarm"
        # 채널 ID 조회
        channel_id = get_channel_id(app, channel_name)
        
        if not channel_id:
            raise Exception(f"{channel_name} 채널을 찾을 수 없습니다.")
            
        logger.info(f"액션 아이템 포스팅 시작: {channel_name}")
        
        # 원본 메시지 링크 생성
        original_message_link = f"<https://app.slack.com/archives/{original_channel_id}/p{thread_ts.replace('.', '')}|원본 대화>"
        
        # 액션 아이템 포스팅
        message = f"* 새로운 액션 아이템이 생성되었습니다 *\n"
        message += f"📌 원본 대화: {original_message_link}\n\n"
        
        for item in action_items:
            message += f"• {item}\n"
        
        result = app.client.chat_postMessage(
            channel=channel_id,
            text=message
        )
        logger.info(f"액션 아이템 포스팅 완료: {result['ts']}")
        
    except Exception as e:
        logger.error(f"액션 아이템 포스팅 중 에러 발생: {str(e)}", exc_info=True)
        raise

@app.event("message")
def handle_message_events(body, logger):
    """메시지 이벤트 처리"""
    try:
        event = body["event"]
        if "thread_ts" in event:
            channel_id = event["channel"]
            
            try:
                # 채널 참여 시도
                join_channel(channel_id)
            except Exception as e:
                logger.error(f"채널 참여 실패: {str(e)}")
                return
            
            # 스레드의 메시지 가져오기
            thread_messages = app.client.conversations_replies(
                channel=channel_id,
                ts=event["thread_ts"]
            )
            
            # 액션 아이템 생성
            action_items = action_item_generator.generate(thread_messages)
            
            if action_items:
                # 스레드에 액션 아이템 추가
                app.client.chat_postMessage(
                    channel=channel_id,
                    thread_ts=event["thread_ts"],
                    text=f"*액션 아이템 목록:*\n{action_items}"
                )
            else:
                app.client.chat_postMessage(
                    channel=channel_id,
                    thread_ts=event["thread_ts"],
                    text="액션 아이템을 추출할 수 없습니다."
                )
    except Exception as e:
        logger.error(f"메시지 처리 중 에러 발생: {str(e)}", exc_info=True)

if __name__ == "__main__":
    logger.info("Slack 봇 시작")
    try:
        # Socket Mode 핸들러 시작
        handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
        handler.start()
    except Exception as e:
        logger.error(f"봇 실행 중 에러 발생: {str(e)}", exc_info=True) 