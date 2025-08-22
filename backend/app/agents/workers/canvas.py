"""
Canvas 에이전트 - 시각적 다이어그램, 차트 및 이미지 생성
"""

import json
import uuid
import asyncio
from typing import Dict, Any, List, Optional, Callable
import logging
from datetime import datetime
import time

from app.agents.base import BaseAgent, AgentInput, AgentOutput
from app.agents.llm_router import llm_router
from app.services.image_generation_service import image_generation_service

logger = logging.getLogger(__name__)


class CanvasAgent(BaseAgent):
    """Canvas 시각화 에이전트"""
    
    agent_type = "canvas"
    name = "Canvas 시각화"
    description = "마인드맵, 플로우차트, 다이어그램 등 시각적 콘텐츠 생성"
    
    def __init__(self):
        super().__init__(agent_id="canvas", name=self.name, description=self.description)
        
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
        """이미지 생성 처리"""
        try:
            # 사용자 ID 가져오기
            user_id = input_data.context.get('user_id', 'anonymous') if input_data.context else 'anonymous'
            
            # 진행 상태 업데이트
            if progress_callback:
                await progress_callback({
                    "step": "image_analysis",
                    "message": "이미지 생성 요청 분석 중...",
                    "progress": 30
                })
            
            # 이미지 생성 파라미터 추출
            image_params = await self._extract_image_parameters(input_data.query, model)
            
            # 진행 상태 업데이트
            if progress_callback:
                await progress_callback({
                    "step": "image_generation",
                    "message": f"{image_params['style']} 스타일로 이미지 생성 중...",
                    "progress": 50
                })
            
            # Imagen 4 서비스 호출
            job_id = str(uuid.uuid4())
            initial_result = await image_generation_service.generate_image(
                job_id=job_id,
                user_id=str(user_id),
                prompt=image_params["prompt"],
                style=image_params["style"],
                size=image_params["size"],
                num_images=image_params["num_images"],
                model="imagen-4"
            )
            
            # 이미지 생성 완료까지 대기 (최대 2분)
            max_wait_time = 120  # 120초
            check_interval = 2   # 2초마다 확인
            waited_time = 0
            
            logger.info(f"이미지 생성 대기 시작, Job ID: {job_id}")
            
            while waited_time < max_wait_time:
                # 진행 상태 확인
                current_status = await image_generation_service.get_job_status(job_id, str(user_id))
                
                if current_status is not None:
                    if current_status.get("status") == "completed":
                        logger.info(f"이미지 생성 완료 확인: {job_id}")
                        result = current_status
                        break
                    elif current_status.get("status") == "failed":
                        logger.error(f"이미지 생성 실패: {job_id}")
                        result = current_status
                        break
                else:
                    logger.warning(f"작업 상태를 찾을 수 없음: {job_id}")
                
                # 대기 시간 업데이트
                await asyncio.sleep(check_interval)
                waited_time += check_interval
                
                # 진행률 업데이트 (50% ~ 95%)
                progress = min(95, 50 + (waited_time / max_wait_time * 45))
                if progress_callback:
                    await progress_callback({
                        "step": "image_generation",
                        "message": f"이미지 생성 중... ({waited_time}초)",
                        "progress": int(progress)
                    })
            
            # 대기 시간 초과 시 현재 상태로 처리
            if waited_time >= max_wait_time:
                logger.warning(f"이미지 생성 대기 시간 초과: {job_id}")
                timeout_status = await image_generation_service.get_job_status(job_id, str(user_id))
                result = timeout_status if timeout_status is not None else initial_result
            
            # 이미지 생성 완료 대기 및 진행 상황 업데이트
            if progress_callback and result and isinstance(result, dict):
                initial_status = result.get("status", "processing")
                if initial_status == "processing":
                    # 이미지 생성 완료 대기 (최대 60초)
                    await progress_callback({
                        "step": "image_processing",
                        "message": "이미지 처리 중...",
                        "progress": 50
                    })
                    
                    # 완료 상태까지 대기
                    max_wait_time = 60  # 최대 60초 대기
                    wait_interval = 2   # 2초마다 확인
                    waited_time = 0
                    
                    while waited_time < max_wait_time:
                        await asyncio.sleep(wait_interval)
                        waited_time += wait_interval
                        
                        # 상태 재확인
                        status_result = await self.image_service.get_generation_status(job_id)
                        logger.info(f"🎨 이미지 생성 상태 확인 - job_id: {job_id}, 대기시간: {waited_time}초, 상태: {status_result.get('status', 'unknown')}")
                        
                        if status_result.get("status") == "completed":
                            result = status_result  # 완성된 결과로 업데이트
                            logger.info(f"🎨 이미지 생성 완료! job_id: {job_id}, 이미지 개수: {len(status_result.get('images', []))}")
                            await progress_callback({
                                "step": "image_completion",
                                "message": "이미지 생성 완료",
                                "progress": 100
                            })
                            break
                        elif status_result.get("status") == "failed":
                            logger.error(f"🎨 이미지 생성 실패 - job_id: {job_id}")
                            break
                        else:
                            # 진행률 업데이트
                            progress = min(50 + (waited_time / max_wait_time * 40), 90)
                            await progress_callback({
                                "step": "image_processing",
                                "message": f"이미지 처리 중... ({waited_time}초)",
                                "progress": int(progress)
                            })
                    
                    if waited_time >= max_wait_time:
                        logger.warning(f"🎨 이미지 생성 타임아웃 - job_id: {job_id}")
                        await progress_callback({
                            "step": "image_timeout", 
                            "message": "이미지 생성이 시간이 오래 걸리고 있습니다",
                            "progress": 90
                        })
                else:
                    await progress_callback({
                        "step": "image_completion",
                        "message": "이미지 생성 완료",
                        "progress": 100
                    })
            
            execution_time = int((time.time() - start_time) * 1000)
            
            # Canvas 활성화 응답 생성
            canvas_response = self._create_image_canvas_response(
                image_params["prompt"], 
                result, 
                image_params
            )
            
            # Canvas 데이터 구조 생성 - 생성된 이미지 URL 직접 포함
            images = result.get("images", []) if isinstance(result, dict) else []
            image_urls = [img.get("url") for img in images if isinstance(img, dict) and img.get("url")]
            
            canvas_data = {
                "type": "image",
                "title": f"AI 이미지: {image_params['prompt'][:50]}",
                "description": canvas_response,
                "image_data": {
                    "job_id": job_id,
                    "prompt": image_params["prompt"],
                    "style": image_params["style"],
                    "size": image_params["size"],
                    "num_images": image_params["num_images"],
                    "status": result.get("status", "processing") if isinstance(result, dict) else "processing",
                    "images": images,
                    "image_urls": image_urls,  # 직접 이미지 URL 포함
                    "generation_result": result
                },
                "metadata": {
                    "created_by": "canvas_agent",
                    "canvas_type": "image_generation"
                }
            }
            
            result_status = result.get('status') if isinstance(result, dict) else 'unknown'
            logger.info(f"Canvas 데이터 생성 완료: status={result_status}, images={len(images)}, urls={len(image_urls)}")
            
            return AgentOutput(
                result=canvas_response,
                metadata={
                    "canvas_type": "이미지",
                    "has_visual_content": True,
                    "image_generation": True,
                    "job_id": job_id
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
    
    async def _extract_image_parameters(self, query: str, model: str) -> Dict[str, Any]:
        """사용자 요청에서 이미지 생성 파라미터 추출"""
        try:
            prompt = f"""
사용자의 이미지 생성 요청을 분석하여 Imagen 4 파라미터를 추출해주세요.

사용자 요청: "{query}"

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
            
            # 기본값 설정
            params = {
                "prompt": query,  # 기본값으로 원본 쿼리 사용
                "style": "realistic",
                "size": "1024x1024",
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
            return {
                "prompt": query,
                "style": "realistic", 
                "size": "1024x1024",
                "num_images": 1
            }
    
    def _create_image_canvas_response(self, prompt: str, generation_result: Dict[str, Any], image_params: Dict[str, Any]) -> str:
        """이미지 Canvas 활성화 응답 생성"""
        # 안전한 데이터 추출
        if isinstance(generation_result, dict):
            status = generation_result.get("status", "processing")
            images = generation_result.get("images", [])
        else:
            status = "processing"
            images = []
        
        if status == "completed":
            response = f"🎨 **Canvas 모드 활성화 - AI 이미지 생성**\n\n"
            response += f"**요청**: {prompt}\n"
            response += f"**스타일**: {image_params['style']}\n"
            response += f"**크기**: {image_params['size']}\n"
            response += f"**생성된 이미지**: {len(images)}개\n\n"
            response += "Canvas에서 생성된 이미지를 확인하고 편집할 수 있습니다!"
        else:
            response = f"🎨 **Canvas 모드 활성화 - AI 이미지 생성**\n\n"
            response += f"**요청**: {prompt}\n"
            response += f"**스타일**: {image_params['style']}\n"
            response += f"**상태**: 이미지 생성 중...\n\n"
            response += "잠시 후 Canvas에서 결과를 확인할 수 있습니다."
        
        return response
    
    def get_capabilities(self) -> List[str]:
        """Canvas 에이전트 기능 목록 반환"""
        return [
            "AI 이미지 생성 (Imagen 4)",
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