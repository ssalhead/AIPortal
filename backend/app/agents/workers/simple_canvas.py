"""
단순화된 Canvas 에이전트
이미지 생성에 집중하고 복잡한 세션 관리 제거
"""

import json
import uuid
import time
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime

from app.agents.base import BaseAgent, AgentInput, AgentOutput
from app.agents.llm_router import llm_router
from app.services.image_generation_service import image_generation_service
from app.services.simple_image_history_service import SimpleImageHistoryService
from app.utils.logger import get_logger
from app.db.session import get_db

logger = get_logger(__name__)


class SimpleCanvasAgent(BaseAgent):
    """단순화된 Canvas 에이전트 - 이미지 생성 중심"""
    
    agent_type = "canvas"
    name = "Canvas 시각화"
    description = "AI 이미지 생성 및 시각적 콘텐츠 생성"
    
    def __init__(self):
        super().__init__(agent_id="simple_canvas", name=self.name, description=self.description)
        self.image_history_service = SimpleImageHistoryService()
    
    def get_capabilities(self) -> List[str]:
        """에이전트 능력 목록 반환"""
        return [
            "이미지 생성",
            "AI 아트 생성", 
            "시각적 콘텐츠 생성",
            "텍스트 기반 Canvas 콘텐츠"
        ]
    
    def get_supported_models(self) -> List[str]:
        """지원하는 모델 목록 반환"""
        return ["gemini", "claude", "claude-3.5-sonnet"]
        
    async def execute(self, input_data: AgentInput, model: str = "gemini", progress_callback: Optional[Callable] = None) -> AgentOutput:
        """단순화된 Canvas 콘텐츠 생성 실행"""
        start_time = time.time()
        
        try:
            logger.info(f"🎨 단순화된 Canvas 에이전트 실행: {input_data.query[:100]}...")
            
            # 1. 콘텐츠 타입 결정 (단순화)
            canvas_type = self._determine_simple_canvas_type(input_data.query)
            
            # 2. 이미지 생성 요청인지 확인
            if canvas_type == "image":
                return await self._handle_simple_image_generation(input_data, model, start_time, progress_callback)
            
            # 3. 기타 Canvas 콘텐츠 (텍스트, 다이어그램 등)
            return await self._handle_other_canvas_content(input_data, canvas_type, model, start_time)
            
        except Exception as e:
            logger.error(f"❌ Canvas 에이전트 실행 중 오류: {str(e)}")
            execution_time = int((time.time() - start_time) * 1000)
            
            return AgentOutput(
                result=f"Canvas 생성 중 오류가 발생했습니다: {str(e)}",
                agent_id="simple_canvas",
                agent_used="simple_canvas",
                model_used=model,
                timestamp=datetime.now().isoformat(),
                execution_time_ms=execution_time,
                token_usage={
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0
                },
                canvas_data=None,
                metadata={"error": str(e)}
            )
    
    def _determine_simple_canvas_type(self, query: str) -> str:
        """단순한 콘텐츠 타입 결정 (이미지 vs 기타)"""
        
        image_keywords = [
            "이미지", "그려", "그림", "사진", "picture", "image", "draw", "paint",
            "생성해", "만들어", "그려줘", "그려봐", "그린", "이미지를", "사진을",
            "일러스트", "아트", "art", "illustration", "sketch", "스케치"
        ]
        
        query_lower = query.lower()
        
        # 이미지 키워드가 포함되어 있으면 이미지 생성
        for keyword in image_keywords:
            if keyword in query_lower:
                logger.debug(f"🎯 이미지 생성 키워드 감지: '{keyword}'")
                return "image"
        
        # 기본값: 기타 Canvas 콘텐츠
        return "other"
    
    async def _handle_simple_image_generation(
        self, 
        input_data: AgentInput, 
        model: str, 
        start_time: float, 
        progress_callback: Optional[Callable] = None
    ) -> AgentOutput:
        """단순화된 이미지 생성 처리"""
        
        try:
            # 1. 진행 상태 업데이트
            if progress_callback:
                await progress_callback({
                    "step": "image_analysis",
                    "message": "이미지 생성 요청 분석 중...",
                    "progress": 20
                })
            
            # 2. 기본 이미지 파라미터 추출 (단순화)
            image_params = self._extract_simple_image_parameters(input_data.query)
            
            # 3. 진행 상태 업데이트  
            if progress_callback:
                await progress_callback({
                    "step": "image_generation", 
                    "message": f"{image_params['style']} 스타일로 이미지 생성 중...",
                    "progress": 60
                })
            
            # 4. 이미지 생성 API 호출 (단순화 - 세션 관리 제거)
            import uuid as uuid_lib
            job_id = str(uuid_lib.uuid4())
            user_id = input_data.user_id or "ff8e410a-53a4-4541-a7d4-ce265678d66a"
            
            generation_result = await image_generation_service.generate_image(
                job_id=job_id,
                user_id=user_id,
                prompt=image_params["prompt"],
                style=image_params["style"],
                size=image_params["size"],
                num_images=1,
                model="imagen-4"
            )
            
            # 이미지 생성이 비동기로 처리되므로 완료될 때까지 대기
            max_wait_seconds = 60  # 최대 60초 대기
            wait_interval = 2  # 2초마다 상태 확인
            waited_seconds = 0
            
            while waited_seconds < max_wait_seconds:
                job_status = await image_generation_service.get_job_status(job_id, user_id)
                if job_status and job_status.get("status") == "completed":
                    if job_status.get("images"):
                        generation_result = job_status  # 완료된 결과로 업데이트
                        break
                    else:
                        raise Exception("이미지 생성에 실패했습니다")
                elif job_status and job_status.get("status") == "failed":
                    error_msg = job_status.get("error_message", "알 수 없는 오류")
                    raise Exception(f"이미지 생성에 실패했습니다: {error_msg}")
                
                # 2초 대기 후 재시도
                await asyncio.sleep(wait_interval)
                waited_seconds += wait_interval
            
            # 시간 초과 시 에러
            if waited_seconds >= max_wait_seconds:
                raise Exception("이미지 생성 시간이 초과되었습니다")
            
            if not generation_result.get("images"):
                raise Exception("이미지 생성에 실패했습니다")
            
            # 5. 새로운 이미지 히스토리 서비스로 저장
            conversation_id = input_data.session_id or (input_data.context.get("conversation_id") if input_data.context else None)
            user_id = input_data.user_id or (input_data.context.get("user_id", "ff8e410a-53a4-4541-a7d4-ce265678d66a") if input_data.context else "ff8e410a-53a4-4541-a7d4-ce265678d66a")
            
            if conversation_id:
                logger.info(f"💾 이미지 히스토리 저장 시작: conversation_id={conversation_id}")
                try:
                    # UUID 변환
                    conversation_uuid = uuid.UUID(conversation_id) if isinstance(conversation_id, str) else conversation_id
                    user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
                    
                    # 🎨 개별 요청별 고유 Canvas ID 생성
                    request_canvas_id = uuid.uuid4()
                    logger.info(f"🎨 새로운 요청별 Canvas ID 생성: {request_canvas_id}")
                    
                    # 데이터베이스에 이미지 히스토리 저장
                    async for db in get_db():
                        saved_image = await self.image_history_service.save_generated_image(
                            db=db,
                            conversation_id=conversation_uuid,
                            user_id=user_uuid,
                            prompt=image_params["prompt"],
                            image_urls=generation_result["images"],
                            style=image_params["style"],
                            size=image_params["size"],
                            generation_params=image_params,
                            safety_score=generation_result.get("safety_score", 1.0),
                            request_canvas_id=request_canvas_id
                        )
                        logger.info(f"✅ 이미지 히스토리 저장 완료: {saved_image.id}")
                        break
                except Exception as save_error:
                    logger.error(f"❌ 이미지 히스토리 저장 실패: {str(save_error)}")
                    # 저장 실패해도 Canvas 데이터는 반환
            else:
                logger.warning("⚠️ conversation_id가 없어 이미지 히스토리 저장 건너뜀")
            
            # 6. 진행 상태 완료
            if progress_callback:
                await progress_callback({
                    "step": "image_completed",
                    "message": "이미지 생성이 완료되었습니다!",
                    "progress": 100
                })
            
            # 7. Canvas 데이터 구성 (프론트엔드 표준 형식으로 수정)
            canvas_data = {
                "type": "image",
                "title": f"이미지 생성: {self._extract_clean_prompt(image_params['prompt'])[:30]}...",
                "image_data": {
                    "image_urls": generation_result["images"],
                    "images": generation_result["images"],  # 호환성 유지
                    "generation_result": {
                        "images": generation_result["images"],
                        "safety_score": generation_result.get("safety_score", 1.0)
                    },
                    "prompt": image_params["prompt"],
                    "style": image_params["style"],
                    "size": image_params["size"]
                },
                "conversationId": input_data.context.get("conversation_id") if input_data.context else None,
                "metadata": {
                    "created_by": "simple_canvas_agent",
                    "generation_params": image_params,
                    "safety_score": generation_result.get("safety_score", 1.0),
                    "canvas_version": "v4.0",
                    "structure_format": "standardized"
                }
            }
            
            # 8. 실행 시간 계산
            execution_time = int((time.time() - start_time) * 1000)
            
            # 9. 성공 응답 (깔끔한 프롬프트 사용)
            clean_prompt = self._extract_clean_prompt(image_params['prompt'])
            response_text = f"**🎨 이미지 생성 완료**\n\n**프롬프트**: {clean_prompt}\n**스타일**: {image_params['style']}\n**크기**: {image_params['size']}\n\n*Canvas 영역에서 생성된 이미지를 확인하세요.*"
            
            logger.info(f"✅ 이미지 생성 성공 (실행시간: {execution_time}ms)")
            
            # Canvas 데이터 구조 로깅 (v4.0 디버깅)
            logger.info(f"🎨 Canvas 데이터 구조 (표준 v4.0 형식):", context={
                "canvas_structure": {
                    "type": canvas_data["type"],
                    "title": canvas_data["title"],
                    "has_image_data": "image_data" in canvas_data,
                    "image_urls_count": len(canvas_data["image_data"]["image_urls"]) if canvas_data.get("image_data", {}).get("image_urls") else 0,
                    "structure_format": canvas_data["metadata"]["structure_format"],
                    "canvas_version": canvas_data["metadata"]["canvas_version"]
                }
            })
            
            return AgentOutput(
                result=response_text,
                agent_id="simple_canvas",
                agent_used="simple_canvas",
                model_used=model,
                timestamp=datetime.now().isoformat(),
                execution_time_ms=execution_time,
                token_usage={
                    "input_tokens": len(input_data.query.split()),
                    "output_tokens": len(response_text.split()),
                    "total_tokens": len(input_data.query.split()) + len(response_text.split())
                },
                canvas_data=canvas_data,
                metadata={
                    "canvas_type": "image",
                    "image_generation": True,
                    "generation_params": image_params
                }
            )
            
        except Exception as e:
            logger.error(f"❌ 이미지 생성 중 오류: {str(e)}")
            execution_time = int((time.time() - start_time) * 1000)
            
            return AgentOutput(
                result=f"이미지 생성 중 오류가 발생했습니다: {str(e)}",
                agent_id="simple_canvas",
                agent_used="simple_canvas",
                model_used=model,
                timestamp=datetime.now().isoformat(),
                execution_time_ms=execution_time,
                token_usage={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                canvas_data=None,
                metadata={"error": str(e), "canvas_type": "image"}
            )
    
    async def _handle_other_canvas_content(
        self, 
        input_data: AgentInput, 
        canvas_type: str, 
        model: str, 
        start_time: float
    ) -> AgentOutput:
        """기타 Canvas 콘텐츠 처리 (텍스트, 다이어그램 등)"""
        
        try:
            # LLM을 사용해서 Canvas 콘텐츠 생성
            canvas_content = await self._generate_simple_canvas_content(input_data, model)
            
            # Canvas 데이터 구조로 변환
            canvas_data = {
                "type": "text",
                "content": canvas_content["content"],
                "title": canvas_content.get("title", "Canvas 콘텐츠"),
                "metadata": {
                    "created_by": "simple_canvas_agent",
                    "content_type": canvas_type
                }
            }
            
            execution_time = int((time.time() - start_time) * 1000)
            response = f"**📝 Canvas 콘텐츠 생성 완료**\n\n{canvas_content['content']}\n\n*Canvas 영역에서 내용을 확인하세요.*"
            
            return AgentOutput(
                result=response,
                agent_id="simple_canvas",
                agent_used="simple_canvas",
                model_used=model,
                timestamp=datetime.now().isoformat(),
                execution_time_ms=execution_time,
                token_usage={
                    "input_tokens": len(input_data.query.split()),
                    "output_tokens": len(response.split()),
                    "total_tokens": len(input_data.query.split()) + len(response.split())
                },
                canvas_data=canvas_data,
                metadata={"canvas_type": canvas_type}
            )
            
        except Exception as e:
            logger.error(f"❌ Canvas 콘텐츠 생성 중 오류: {str(e)}")
            execution_time = int((time.time() - start_time) * 1000)
            
            return AgentOutput(
                result=f"Canvas 콘텐츠 생성 중 오류가 발생했습니다: {str(e)}",
                agent_id="simple_canvas",
                agent_used="simple_canvas", 
                model_used=model,
                timestamp=datetime.now().isoformat(),
                execution_time_ms=execution_time,
                token_usage={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                canvas_data=None,
                metadata={"error": str(e)}
            )
    
    def _extract_simple_image_parameters(self, query: str) -> Dict[str, Any]:
        """단순한 이미지 파라미터 추출 (LLM 없이)"""
        
        # 대화 기록이 포함된 경우 실제 사용자 요청만 추출
        clean_prompt = self._extract_clean_prompt(query)
        
        # 기본 파라미터
        params = {
            "prompt": clean_prompt,
            "style": "realistic",
            "size": "1024x1024", 
            "num_images": 1
        }
        
        # 스타일 키워드 감지
        style_keywords = {
            "사실적": "realistic",
            "realistic": "realistic",
            "만화": "cartoon", 
            "cartoon": "cartoon",
            "애니메": "anime",
            "anime": "anime", 
            "예술적": "artistic",
            "artistic": "artistic",
            "수채화": "watercolor",
            "watercolor": "watercolor"
        }
        
        query_lower = query.lower()
        for keyword, style in style_keywords.items():
            if keyword in query_lower:
                params["style"] = style
                logger.debug(f"🎨 스타일 감지: {style}")
                break
        
        # 크기 키워드 감지
        size_keywords = {
            "정사각형": "1024x1024",
            "square": "1024x1024", 
            "세로": "768x1024",
            "portrait": "768x1024",
            "가로": "1024x768", 
            "landscape": "1024x768"
        }
        
        for keyword, size in size_keywords.items():
            if keyword in query_lower:
                params["size"] = size
                logger.debug(f"📐 크기 감지: {size}")
                break
        
        return params
    
    def _extract_clean_prompt(self, query: str) -> str:
        """대화 기록 포맷에서 실제 사용자 요청만 추출"""
        
        # "현재 질문: " 이후의 내용 추출
        if "현재 질문: " in query:
            parts = query.split("현재 질문: ", 1)
            if len(parts) > 1:
                clean_prompt = parts[1].strip()
                logger.debug(f"🧹 대화 기록에서 깔끔한 프롬프트 추출: '{clean_prompt}'")
                return clean_prompt
        
        # "대화 기록:" 패턴이 있지만 "현재 질문:" 없는 경우 원본 반환
        if "대화 기록:" in query and "현재 질문:" not in query:
            logger.debug(f"🧹 대화 기록 있지만 현재 질문 없음, 원본 사용: '{query}'")
            return query
            
        # 일반적인 경우 원본 반환
        logger.debug(f"🧹 일반 프롬프트 사용: '{query}'")
        return query
    
    async def _generate_simple_canvas_content(self, input_data: AgentInput, model: str) -> Dict[str, Any]:
        """단순한 Canvas 콘텐츠 생성"""
        
        system_prompt = """당신은 Canvas 콘텐츠를 생성하는 도우미입니다.
사용자의 요청에 따라 적절한 텍스트 콘텐츠를 생성해주세요.
응답은 다음 JSON 형식으로 해주세요:

{
    "title": "콘텐츠 제목",
    "content": "실제 콘텐츠 내용"
}"""
        
        try:
            # 시스템 프롬프트와 사용자 메시지를 결합
            full_prompt = f"{system_prompt}\n\nUser: {input_data.query}\n\nAssistant:"
            response, model_used = await llm_router.generate_response(
                model_name=model,
                prompt=full_prompt,
                temperature=0.7
            )
            
            # JSON 파싱 시도
            try:
                content_data = json.loads(response)
                return content_data
            except json.JSONDecodeError:
                # JSON 파싱 실패시 기본 형태로 반환
                return {
                    "title": "Canvas 콘텐츠",
                    "content": response
                }
                
        except Exception as e:
            logger.error(f"❌ Canvas 콘텐츠 생성 실패: {str(e)}")
            return {
                "title": "오류",
                "content": f"콘텐츠 생성 중 오류가 발생했습니다: {str(e)}"
            }