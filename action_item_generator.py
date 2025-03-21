import logging
from transformers import AutoTokenizer, AutoModelForCausalLM
import re
import torch
import os
from dotenv import load_dotenv
import slack
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
import pytz
from openai import OpenAI

# 환경 변수 로드
load_dotenv()

logger = logging.getLogger(__name__)

ModelType = Literal["huggingface", "openai"]

class ActionItemGenerator:
    def __init__(self, slack_app=None, model_type: ModelType = "huggingface", model_name: str = None):
        """LLM 모델 초기화"""
        self.logger = logger
        self.slack_app = slack_app
        self.model_type = model_type
        
        try:
            self.logger.info(f"액션 아이템 생성기 초기화 시작 (모델: {model_type})")
            
            if model_type == "huggingface":
                self._init_huggingface(model_name)
            else:
                self._init_openai()
                
            self.logger.info("액션 아이템 생성기 초기화 완료")
        except Exception as e:
            self.logger.error(f"액션 아이템 생성기 초기화 중 에러 발생: {str(e)}", exc_info=True)
            raise

    def _init_huggingface(self, model_name: str = None):
        """Hugging Face 모델 초기화"""
        self.hf_token = os.getenv("HUGGINGFACE_TOKEN")
        if not self.hf_token:
            raise ValueError("HUGGINGFACE_TOKEN이 환경 변수에 설정되지 않았습니다.")
        
        # 모델 이름이 지정되지 않은 경우 기본값 사용
        self.model_name = model_name or os.getenv("HUGGINGFACE_MODEL", "mistralai/Mistral-7B-v0.1")
        self.logger.info(f"Hugging Face 모델: {self.model_name}")
        
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            token=self.hf_token,
            use_fast=False
        )
        
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            token=self.hf_token,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True
        )

    def _init_openai(self):
        """OpenAI API 초기화"""
        self.openai_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_key:
            raise ValueError("OPENAI_API_KEY가 환경 변수에 설정되지 않았습니다.")
        
        self.client = OpenAI(api_key=self.openai_key)
        
    def _prepare_conversation(self, messages):
        """Slack 메시지들을 하나의 대화 텍스트로 변환"""
        conversation = []
        for msg in messages[:-1]:
            if "text" in msg:
                if not msg.get("bot_id"):
                    text = msg["text"]
                    user = msg.get("user", "Unknown")
                    
                    try:
                        user_info = self.slack_app.client.users_info(user=user)
                        display_name = user_info["user"]["profile"].get("display_name") or \
                                     user_info["user"]["profile"].get("real_name") or \
                                     user
                    except Exception as e:
                        self.logger.warning(f"사용자 정보 조회 실패: {str(e)}")
                        display_name = user
                    
                    # @이름: 패턴 확인 및 치환
                    name_pattern = r'@([^:]+):'
                    if re.search(name_pattern, text):
                        matched_name = re.search(name_pattern, text).group(1)
                        text = re.sub(r'@[^:]+:', '', text, 1).strip()
                        display_name = matched_name
                    
                    text = re.sub(r'<[^>]+>', '', text)
                    if text.strip():
                        conversation.append(f"{display_name}: {text.strip()}")
        
        return "\n".join(conversation)

    def _generate_with_huggingface(self, prompt: str) -> str:
        """Hugging Face 모델을 사용하여 응답 생성"""
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=2048,
            add_special_tokens=True
        )
        
        if 'token_type_ids' in inputs:
            del inputs['token_type_ids']
        
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=512,
            num_return_sequences=1,
            do_sample=True,
            temperature=0.1,
            top_p=0.9,
            no_repeat_ngram_size=3,
            pad_token_id=self.tokenizer.eos_token_id,
            eos_token_id=self.tokenizer.eos_token_id
        )
        
        input_length = inputs["input_ids"].shape[1]
        response = self.tokenizer.decode(
            outputs[0][input_length:],
            skip_special_tokens=True
        ).strip()
        
        return response

    def _generate_with_openai(self, prompt: str) -> str:
        """OpenAI API를 사용하여 응답 생성"""
        completion = self.client.chat.completions.create(
            model="gpt-4o-mini",  # OpenAI API는 gpt-4 사용
            messages=[
                {"role": "system", "content": "당신은 대화에서 액션 아이템을 추출하는 전문가입니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=512
        )
        return completion.choices[0].message.content.strip()

    def generate(self, thread_messages):
        """대화에서 액션 아이템 추출"""
        try:
            conversation = self._prepare_conversation(thread_messages.get("messages", []))
            conversation = conversation
            self.logger.info(f"대화 내용 길이: {len(conversation)} 문자")
            self.logger.info(f"************* 대화 내용: {conversation}")
            
            # 오늘 날짜 가져오기
            seoul_tz = pytz.timezone('Asia/Seoul')
            today = datetime.now(seoul_tz).strftime('%Y-%m-%d')
            
            prompt = f"""아래는 Slack 대화입니다. 이 대화에서 참가자가 해야 할 일을 명확하게 정리해 주세요.

### **지침** :
**할 일 목록 작성**  
   - 각 할 일은 담당자, 구체적인 작업 내용, 마감 기한(있는 경우 포함)을 포함해야 합니다.  
   - 형식: `- [담당자]: [구체적인 할 일] (마감 기한: YYYY-MM-DD)`  
   - 담당자가 명확하지 않을 경우 `미정`으로 표시하세요.  

### **출력 형식** :
- [담당자]: [할 일 내용] (마감 기한: YYYY-MM-DD)
- [담당자]: [할 일 내용] (마감 기한: YYYY-MM-DD)

### **대화내용** :
날짜: {today}
{conversation}

### **출력** :
"""
            self.logger.info(f"************* 프롬프트 *************")
            self.logger.info(f"{prompt}")
            self.logger.info(f"************* 프롬프트 끝 *************")
            self.logger.info("LLM 추론 시작")
            
            if self.model_type == "huggingface":
                response = self._generate_with_huggingface(f"<s>[INST] {prompt}[/INST]</s>")
            else:
                response = self._generate_with_openai(prompt)
                
            self.logger.info("LLM 추론 완료")
            self.logger.info(f"생성된 응답: {response}")
            
            action_items = []
            for line in response.split("\n"):
                line = line.strip()
                if line.startswith("-"):
                    item = line[1:].strip()
                    if item:
                        # 이름 부분을 *[이름]* 형식으로 변경
                        name_pattern = r'\[(.*?)\]:'
                        if re.search(name_pattern, item):
                            name = re.search(name_pattern, item).group(1)
                            item = re.sub(r'\[(.*?)\]:', f'@*[{name}]*:', item)
                        action_items.append(item)
            
            self.logger.info(f"추출된 액션 아이템: {action_items}")
            return action_items
            
        except Exception as e:
            self.logger.error(f"액션 아이템 생성 중 에러 발생: {str(e)}", exc_info=True)
            return [] 