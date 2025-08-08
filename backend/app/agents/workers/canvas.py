"""
Canvas 에이전트 - 시각적 다이어그램 및 차트 생성
"""

import json
from typing import Dict, Any, List, Optional, Callable
import logging
from datetime import datetime
import time

from app.agents.base import BaseAgent, AgentInput, AgentOutput

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
        if any(word in message for word in ["마인드맵", "mindmap", "mind map", "개념도"]):
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
    
    def get_capabilities(self) -> List[str]:
        """Canvas 에이전트 기능 목록 반환"""
        return [
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