"""
Canvas 에이전트 - 시각적 다이어그램, 차트 및 이미지 생성
"""

import json
import uuid
import asyncio
from typing import Dict, Any, List, Optional, Callable
import logging
from datetime import datetime
from uuid import UUID
import time

from app.agents.base import BaseAgent, AgentInput, AgentOutput
from app.agents.llm_router import llm_router
from app.services.image_generation_service import image_generation_service
from app.services.canvas_workflow_dispatcher import (
    CanvasWorkflowDispatcher, 
    ImageGenerationRequest, 
    RequestSource,
    WorkflowMode
)

logger = logging.getLogger(__name__)


class CanvasAgent(BaseAgent):
    """Canvas 시각화 에이전트"""
    
    agent_type = "canvas"
    name = "Canvas 시각화"
    description = "마인드맵, 플로우차트, 다이어그램 등 시각적 콘텐츠 생성"
    
    def __init__(self):
        super().__init__(agent_id="canvas", name=self.name, description=self.description)
        self.workflow_dispatcher = CanvasWorkflowDispatcher()
        
    async def execute(self, input_data: AgentInput, model: str = "gemini", progress_callback: Optional[Callable] = None) -> AgentOutput:
        """Canvas 콘텐츠 생성 실행"""
        start_time = time.time()
        
        try:
            logger.info(f"Canvas 에이전트 실행: {input_data.query[:100]}...")
            
            # 사용자 메시지 분석
            message = input_data.query.lower()
            
            # Canvas 콘텐츠 타입 결정
            canvas_type = self._determine_canvas_type(message)
            
            # 이미지 생성 처리
            if canvas_type == "이미지":
                return await self._handle_image_generation(input_data, model, start_time, progress_callback)
            
            # LLM을 사용해서 Canvas 콘텐츠 생성
            canvas_content = await self._generate_canvas_content(input_data, canvas_type)
            
            # Canvas 데이터 구조로 변환
            canvas_data = self._create_canvas_data(canvas_content, canvas_type)
            
            response = f"**{canvas_type} 생성 완료**\n\n{canvas_content['description']}\n\n*Canvas 영역에서 시각적 다이어그램을 확인하세요.*"
            
            execution_time = int((time.time() - start_time) * 1000)
            
            return AgentOutput(
                result=response,
                metadata={
                    "canvas_type": canvas_type,
                    "has_visual_content": True
                },
                execution_time_ms=execution_time,
                agent_id=self.agent_id,
                model_used=model,
                timestamp=datetime.now().isoformat(),
                canvas_data=canvas_data
            )
            
        except Exception as e:
            logger.error(f"Canvas 에이전트 실행 오류: {str(e)}")
            execution_time = int((time.time() - start_time) * 1000)
            
            return AgentOutput(
                result="죄송합니다. 시각화 콘텐츠 생성 중 오류가 발생했습니다.",
                metadata={"error": True},
                execution_time_ms=execution_time,
                agent_id=self.agent_id,
                model_used=model,
                timestamp=datetime.now().isoformat(),
                error=str(e)
            )
    
    def _determine_canvas_type(self, message: str) -> str:
        """메시지를 분석해서 Canvas 타입 결정"""
        # 이미지 생성 관련 키워드 우선 체크
        image_keywords = ["그려", "만들어", "생성", "이미지", "그림", "일러스트", "사진", "디자인", "포스터", "로고", "배경", "캐릭터", "풍경"]
        if any(word in message for word in image_keywords):
            return "이미지"
        elif any(word in message for word in ["마인드맵", "mindmap", "mind map", "개념도"]):
            return "마인드맵"
        elif any(word in message for word in ["플로우차트", "flowchart", "flow chart", "흐름도", "순서도"]):
            return "플로우차트"
        elif any(word in message for word in ["다이어그램", "diagram", "구조도", "관계도"]):
            return "다이어그램"
        elif any(word in message for word in ["차트", "chart", "그래프", "graph"]):
            return "차트"
        elif any(word in message for word in ["조직도", "organization", "구조"]):
            return "조직도"
        else:
            return "다이어그램"  # 기본값
    
    async def _generate_canvas_content(self, input_data: AgentInput, canvas_type: str) -> Dict[str, Any]:
        """LLM을 사용해서 Canvas 콘텐츠 생성"""
        try:
            # 프롬프트 생성
            prompt = f"""사용자가 {canvas_type} 생성을 요청했습니다.
            
사용자 요청: {input_data.query}

다음 형식으로 {canvas_type}에 필요한 정보를 생성해주세요:

1. 제목: 명확하고 간결한 제목
2. 설명: 이 {canvas_type}의 목적과 내용
3. 주요 노드/요소들: 시각화에 포함될 핵심 요소들
4. 관계/연결: 요소들 간의 관계나 흐름

JSON 형식으로 응답해주세요:
{{
    "title": "제목",
    "description": "설명",
    "elements": [
        {{
            "id": "요소ID",
            "label": "요소명",
            "type": "node타입",
            "position": {{"x": 0, "y": 0}}
        }}
    ],
    "connections": [
        {{
            "from": "시작요소ID",
            "to": "끝요소ID",
            "label": "연결설명"
        }}
    ]
}}
"""
            
            # 임시로 기본 응답 생성 (실제로는 LLM 호출)
            return {
                "title": f"{canvas_type} - {input_data.query[:50]}",
                "description": f"사용자 요청에 따른 {canvas_type}입니다.",
                "elements": [
                    {"id": "main", "label": "메인 주제", "type": "main", "position": {"x": 400, "y": 200}},
                    {"id": "sub1", "label": "하위 개념 1", "type": "sub", "position": {"x": 200, "y": 300}},
                    {"id": "sub2", "label": "하위 개념 2", "type": "sub", "position": {"x": 600, "y": 300}}
                ],
                "connections": [
                    {"from": "main", "to": "sub1", "label": "연결"},
                    {"from": "main", "to": "sub2", "label": "연결"}
                ]
            }
            
        except Exception as e:
            logger.error(f"Canvas 콘텐츠 생성 오류: {str(e)}")
            return {
                "title": f"{canvas_type} 생성 중 오류",
                "description": "콘텐츠 생성 중 문제가 발생했습니다.",
                "elements": [],
                "connections": []
            }
    
    def _create_canvas_data(self, content: Dict[str, Any], canvas_type: str) -> Dict[str, Any]:
        """Canvas UI에서 사용할 데이터 구조 생성"""
        return {
            "type": canvas_type,
            "title": content["title"],
            "description": content["description"],
            "elements": content["elements"],
            "connections": content["connections"],
            "metadata": {
                "created_by": "canvas_agent",
                "canvas_type": canvas_type.lower().replace(" ", "_")
            }
        }
    
    async def _handle_image_generation(self, input_data: AgentInput, model: str, start_time: float, progress_callback: Optional[Callable] = None) -> AgentOutput:
        """이미지 생성 처리 - CREATE/EDIT 모드 통합"""
        try:
            logger.info("🎨 Canvas 이미지 생성 요청 처리 시작")
            
            # 컨텍스트에서 필수 정보 추출
            context = input_data.context or {}
            user_id = context.get('user_id', 'anonymous')
            conversation_id = context.get('conversation_id')
            db_session = context.get('db_session')  # 데이터베이스 세션
            
            if not conversation_id:
                raise ValueError("conversation_id가 필요합니다")
            
            if not db_session:
                raise ValueError("db_session이 필요합니다")
            
            # 진행 상태 업데이트
            if progress_callback:
                await progress_callback({
                    "step": "request_analysis",
                    "message": "요청 분석 및 모드 결정 중...",
                    "progress": 20
                })
            
            # Canvas 관련 컨텍스트 확인 (EDIT 모드 판단용)
            canvas_id = context.get('canvas_id')
            reference_image_id = context.get('reference_image_id') 
            evolution_type = context.get('evolution_type', 'variation')
            
            # 요청 소스 결정
            request_source = RequestSource.CANVAS if canvas_id else RequestSource.CHAT
            
            # 이미지 생성 파라미터 추출
            image_params = await self._extract_image_parameters(input_data, model)
            
            # ImageGenerationRequest 생성
            if request_source == RequestSource.CANVAS and canvas_id and reference_image_id:
                # EDIT 모드: Canvas 내에서 이미지 진화
                logger.info(f"📝 EDIT 모드 - Canvas: {canvas_id}, 참조 이미지: {reference_image_id}")
                
                generation_request = ImageGenerationRequest(
                    conversation_id=UUID(conversation_id) if isinstance(conversation_id, str) else conversation_id,
                    user_id=UUID(user_id) if isinstance(user_id, str) else user_id,
                    prompt=image_params["prompt"],
                    source=RequestSource.CANVAS,
                    style=image_params["style"],
                    size=image_params["size"],
                    canvas_id=UUID(canvas_id) if isinstance(canvas_id, str) else canvas_id,
                    reference_image_id=UUID(reference_image_id) if isinstance(reference_image_id, str) else reference_image_id,
                    evolution_type=evolution_type,
                    edit_mode_type=context.get('edit_mode_type', 'EDIT_MODE_INPAINT_INSERTION'),
                    generation_params={
                        "num_images": image_params["num_images"],
                        "model": "imagen-4"
                    }
                )
            else:
                # CREATE 모드: 새로운 Canvas 생성
                logger.info(f"🆕 CREATE 모드 - 새 Canvas 생성")
                
                generation_request = ImageGenerationRequest(
                    conversation_id=UUID(conversation_id) if isinstance(conversation_id, str) else conversation_id,
                    user_id=UUID(user_id) if isinstance(user_id, str) else user_id,
                    prompt=image_params["prompt"],
                    source=RequestSource.CHAT,
                    style=image_params["style"],
                    size=image_params["size"],
                    generation_params={
                        "num_images": image_params["num_images"],
                        "model": "imagen-4"
                    }
                )
            
            # 진행 상태 업데이트
            if progress_callback:
                mode = "이미지 진화" if request_source == RequestSource.CANVAS else "새 이미지 생성"
                await progress_callback({
                    "step": "workflow_dispatch",
                    "message": f"{mode} 처리 중...",
                    "progress": 40
                })
            
            # 워크플로우 디스패처를 통한 처리
            dispatch_result = await self.workflow_dispatcher.dispatch_image_generation_request(
                db=db_session,
                request=generation_request
            )
            
            if not dispatch_result.get("success"):
                raise Exception(f"이미지 생성 실패: {dispatch_result.get('error')}")
            
            logger.info(f"✅ 워크플로우 디스패처 처리 완료: {dispatch_result.get('workflow_mode')}")
            
            # 진행 상태 업데이트
            if progress_callback:
                await progress_callback({
                    "step": "image_completion",
                    "message": "이미지 생성 완료!",
                    "progress": 100
                })
            
            execution_time = int((time.time() - start_time) * 1000)
            
            # Canvas 응답 생성 (CREATE vs EDIT에 따라 다른 메시지)
            workflow_mode = dispatch_result.get("workflow_mode", "unknown")
            canvas_response = self._create_workflow_canvas_response(
                dispatch_result, 
                image_params, 
                workflow_mode
            )
            
            # Canvas 데이터 구조 생성
            canvas_data = self._create_workflow_canvas_data(
                dispatch_result,
                image_params,
                workflow_mode
            )
            
            logger.info(f"✅ Canvas 에이전트 이미지 생성 완료: {workflow_mode} 모드")
            
            return AgentOutput(
                result=canvas_response,
                metadata={
                    "canvas_type": "이미지",
                    "has_visual_content": True,
                    "image_generation": True,
                    "workflow_mode": workflow_mode,
                    "canvas_id": dispatch_result.get("canvas_id"),
                    "canvas_version": dispatch_result.get("canvas_version"),
                    "request_source": dispatch_result.get("request_source")
                },
                execution_time_ms=execution_time,
                agent_id=self.agent_id,
                model_used=model,
                timestamp=datetime.now().isoformat(),
                canvas_data=canvas_data
            )
            
        except Exception as e:
            logger.error(f"이미지 생성 처리 실패: {e}")
            execution_time = int((time.time() - start_time) * 1000)
            
            return AgentOutput(
                result=f"이미지 생성 중 오류가 발생했습니다: {str(e)}",
                metadata={"error": True, "canvas_type": "이미지"},
                execution_time_ms=execution_time,
                agent_id=self.agent_id,
                model_used=model,
                timestamp=datetime.now().isoformat(),
                error=str(e)
            )
    
    async def _extract_image_parameters(self, input_data: AgentInput, model: str) -> Dict[str, Any]:
        """사용자 요청에서 이미지 생성 파라미터 추출 (이미지 진화 지원)"""
        query = input_data.query
        conversation_id = input_data.context.get('conversation_id') if input_data.context else None
        user_id = input_data.context.get('user_id', 'anonymous') if input_data.context else 'anonymous'
        
        try:
            # 현재 선택된 이미지 컨텍스트 추출
            selected_context = await self._get_selected_image_context(conversation_id, user_id) if conversation_id else None
            
            # 진화형 프롬프트 생성
            base_prompt = f"""
사용자의 이미지 생성 요청을 분석하여 Imagen 4 파라미터를 추출해주세요.

사용자 요청: "{query}"
"""
            
            # 선택된 이미지 컨텍스트 추가
            if selected_context:
                base_prompt += f"""

**이전 이미진 컨텍스트** (참고용 - 진화/개선에 활용):
- 이전 프롬프트: "{selected_context['prompt']}"
- 이전 스타일: "{selected_context['style']}"
- 이전 크기: "{selected_context['size']}"
- 버전 번호: {selected_context['version_number']}

**진화 전략**: 사용자의 새로운 요청을 이전 이미지의 컨텍스트와 결합하여 더 나은 결과를 생성하세요.
"""
            
            prompt = base_prompt + f"""

**추출할 파라미터**:
1. **prompt**: 영어로 번역된 상세한 이미지 설명 (최대 400자)
2. **style**: realistic, artistic, cartoon, abstract, 3d, anime 중 선택
3. **size**: 512x512, 1024x1024, 1024x768, 768x1024, 1920x1080, 1080x1920 중 선택
4. **num_images**: 1-4 사이의 숫자

**스타일 가이드**:
- realistic: 사실적인 사진, 실제 풍경/인물
- artistic: 예술적, 회화적 표현
- cartoon: 만화, 애니메이션 스타일
- abstract: 추상적, 개념적 표현
- 3d: 3D 렌더링, CGI
- anime: 일본 애니메이션 스타일

다음 형식으로 응답해주세요:
prompt: [영어 프롬프트]
style: [스타일]
size: [크기]
num_images: [개수]
"""
            
            response, _ = await llm_router.generate_response(model, prompt, include_datetime=False)
            lines = response.strip().split('\n')
            
            # 선택된 이미지 컨텍스트에서 기본값 추출
            default_style = selected_context['style'] if selected_context else "realistic"
            default_size = selected_context['size'] if selected_context else "1024x1024"
            
            # 기본값 설정
            params = {
                "prompt": query,  # 기본값으로 원본 쿼리 사용
                "style": default_style,
                "size": default_size,
                "num_images": 1
            }
            
            # 응답 파싱
            for line in lines:
                if line.startswith('prompt:'):
                    params["prompt"] = line.split(':', 1)[1].strip()
                elif line.startswith('style:'):
                    style = line.split(':', 1)[1].strip().lower()
                    if style in ["realistic", "artistic", "cartoon", "abstract", "3d", "anime"]:
                        params["style"] = style
                elif line.startswith('size:'):
                    size = line.split(':', 1)[1].strip()
                    if size in ["512x512", "1024x1024", "1024x768", "768x1024", "1920x1080", "1080x1920"]:
                        params["size"] = size
                elif line.startswith('num_images:'):
                    try:
                        num = int(line.split(':', 1)[1].strip())
                        if 1 <= num <= 4:
                            params["num_images"] = num
                    except:
                        pass
            
            return params
            
        except Exception as e:
            logger.warning(f"이미지 파라미터 추출 실패, 기본값 사용: {e}")
            # 오류 시에도 선택된 컨텍스트 활용 시도
            try:
                selected_context = await self._get_selected_image_context(conversation_id, user_id) if conversation_id else None
                default_style = selected_context['style'] if selected_context else "realistic"
                default_size = selected_context['size'] if selected_context else "1024x1024"
            except:
                default_style = "realistic"
                default_size = "1024x1024"
            
            return {
                "prompt": query,
                "style": default_style, 
                "size": default_size,
                "num_images": 1
            }
    
    def _create_workflow_canvas_response(self, dispatch_result: Dict[str, Any], image_params: Dict[str, Any], workflow_mode: str) -> str:
        """워크플로우 결과 기반 Canvas 응답 생성"""
        prompt = image_params.get("prompt", "")
        style = image_params.get("style", "realistic")
        
        if workflow_mode == "create":
            # CREATE 모드: 새 Canvas 생성
            response = f"🎨 **새 Canvas 생성 - AI 이미지 생성**\n\n"
            response += f"**요청**: {prompt}\n"
            response += f"**스타일**: {style}\n"
            response += f"**Canvas ID**: {dispatch_result.get('canvas_id', 'N/A')}\n"
            response += f"**버전**: v{dispatch_result.get('canvas_version', 1)}\n\n"
            
            if dispatch_result.get("success"):
                image_urls = dispatch_result.get("image_urls", [])
                response += f"**생성된 이미지**: {len(image_urls)}개\n\n"
                response += "✅ 새로운 Canvas가 생성되었습니다! Canvas에서 이미지를 확인하고 추가 편집이 가능합니다."
            else:
                response += "❌ 이미지 생성 중 오류가 발생했습니다."
                
        elif workflow_mode == "edit":
            # EDIT 모드: Canvas 내 이미지 진화
            response = f"✏️ **Canvas 이미지 진화 - AI 편집**\n\n"
            response += f"**새 프롬프트**: {prompt}\n"
            response += f"**스타일**: {style}\n"
            response += f"**Canvas ID**: {dispatch_result.get('canvas_id', 'N/A')}\n"
            response += f"**새 버전**: v{dispatch_result.get('canvas_version', 'N/A')}\n"
            response += f"**진화 타입**: {dispatch_result.get('evolution_type', 'variation')}\n\n"
            
            if dispatch_result.get("success"):
                image_urls = dispatch_result.get("image_urls", [])
                response += f"**진화된 이미지**: {len(image_urls)}개\n\n"
                response += "✅ 이미지 진화가 완료되었습니다! Canvas에서 새로운 버전을 확인할 수 있습니다."
            else:
                response += "❌ 이미지 진화 중 오류가 발생했습니다."
        
        else:
            # 알 수 없는 모드
            response = f"🔄 **Canvas 이미지 처리**\n\n"
            response += f"**요청**: {prompt}\n"
            response += f"**모드**: {workflow_mode}\n\n"
            
            if dispatch_result.get("success"):
                response += "✅ 이미지 처리가 완료되었습니다."
            else:
                response += f"❌ 처리 중 오류: {dispatch_result.get('error', '알 수 없음')}"
        
        return response
    
    def _create_workflow_canvas_data(self, dispatch_result: Dict[str, Any], image_params: Dict[str, Any], workflow_mode: str) -> Dict[str, Any]:
        """워크플로우 결과 기반 Canvas 데이터 생성"""
        
        # 기본 Canvas 데이터 구조
        canvas_data = {
            "type": "image",
            "title": f"AI 이미지: {image_params.get('prompt', '')[:50]}",
            "description": f"{workflow_mode.title()} 모드로 생성된 이미지",
            "workflow_info": {
                "mode": workflow_mode,
                "canvas_id": dispatch_result.get("canvas_id"),
                "canvas_version": dispatch_result.get("canvas_version"),
                "success": dispatch_result.get("success", False),
                "request_source": dispatch_result.get("request_source"),
                "dispatch_timestamp": dispatch_result.get("dispatch_timestamp")
            },
            "image_data": {
                "prompt": image_params.get("prompt"),
                "style": image_params.get("style"),
                "size": image_params.get("size"),
                "num_images": image_params.get("num_images", 1),
                "status": "completed" if dispatch_result.get("success") else "failed"
            },
            "metadata": {
                "created_by": "canvas_agent_v2",
                "canvas_type": "image_generation",
                "workflow_mode": workflow_mode
            }
        }
        
        # 성공적인 결과인 경우 이미지 URL 추가
        if dispatch_result.get("success"):
            image_urls = dispatch_result.get("image_urls", [])
            primary_image_url = dispatch_result.get("primary_image_url")
            
            canvas_data["image_data"].update({
                "images": [{"url": url} for url in image_urls] if image_urls else [],
                "image_urls": image_urls,
                "primary_image_url": primary_image_url,
                "generation_result": {
                    "canvas_id": dispatch_result.get("canvas_id"),
                    "image_history_id": dispatch_result.get("image_history_id"),
                    "status": "completed"
                }
            })
            
            # EDIT 모드인 경우 추가 정보
            if workflow_mode == "edit":
                canvas_data["edit_info"] = {
                    "parent_image_id": dispatch_result.get("parent_image_id"),
                    "evolution_type": dispatch_result.get("evolution_type"),
                    "reference_image_id": dispatch_result.get("parent_image_id")  # 호환성
                }
        
        else:
            # 실패한 경우 오류 정보 추가
            canvas_data["error_info"] = {
                "error_message": dispatch_result.get("error", "Unknown error"),
                "failed_at": workflow_mode
            }
        
        return canvas_data
    
    # 🔥 _add_to_image_session 메서드 제거 - 중복 생성 방지
    # ImageSession 관리는 프론트엔드에서 단일 소스로 처리

    # 🔥 _get_selected_image_context 메서드 제거 - ImageSession 관리 제거
    # 이미지 진화 기능은 프론트엔드에서 직접 처리

    def get_capabilities(self) -> List[str]:
        """Canvas 에이전트 기능 목록 반환"""
        return [
            "AI 이미지 생성 (Imagen 4) - CREATE 모드",
            "AI 이미지 편집 (Imagen 4) - EDIT 모드", 
            "Canvas 기반 이미지 진화 시스템",
            "Request-Based Canvas 워크플로우",
            "마인드맵 생성",
            "플로우차트 생성", 
            "다이어그램 생성",
            "조직도 생성",
            "차트 생성"
        ]
    
    def get_supported_models(self) -> List[str]:
        """지원하는 모델 목록 반환"""
        return ["claude-4", "gemini-pro", "gpt-4"]


# 에이전트 인스턴스 생성
canvas_agent = CanvasAgent()