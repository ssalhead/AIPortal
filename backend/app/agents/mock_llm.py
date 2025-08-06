"""
Mock LLM 응답 생성기
실제 API 키 없이도 테스트 가능한 응답 시스템
"""

import random
import asyncio
from typing import Dict, List, AsyncGenerator
from datetime import datetime

class MockLLMResponse:
    """Mock LLM 응답 생성"""
    
    # 다양한 테마별 응답 템플릿
    RESPONSE_TEMPLATES = {
        "greeting": [
            "안녕하세요! AI 포탈에 오신 것을 환영합니다. 어떻게 도와드릴까요?",
            "반갑습니다! 저는 AI 포탈의 인공지능 어시스턴트입니다. 무엇을 도와드릴까요?",
            "Hello! 저는 여러분의 AI 어시스턴트입니다. 궁금한 것이 있으시면 언제든 물어보세요.",
        ],
        "search": [
            "🔍 검색을 시작합니다...\n\n검색 결과를 분석한 결과, 다음과 같은 정보를 찾았습니다:\n\n• 관련 문서 5개 발견\n• 최신 업데이트: 2일 전\n• 신뢰도: 높음\n\n자세한 내용을 알려드릴까요?",
            "🌐 웹 검색을 수행했습니다.\n\n주요 발견사항:\n✅ 공식 문서 3건\n✅ 커뮤니티 논의 7건\n✅ 최근 업데이트 내역\n\n더 구체적인 정보가 필요하시면 말씀해 주세요.",
            "📊 검색 완료!\n\n검색어와 관련된 정보를 종합한 결과:\n- 핵심 개념 설명\n- 실제 사용 사례\n- 관련 도구 및 리소스\n\n어떤 부분을 더 자세히 알고 싶으신가요?",
        ],
        "help": [
            "도움이 필요하시군요! 다음과 같은 기능을 제공합니다:\n\n🔍 웹 검색 및 정보 조회\n💬 자연어 대화\n📄 문서 분석 (예정)\n🎨 창작 지원\n\n어떤 도움이 필요하신지 구체적으로 말씀해 주세요.",
            "AI 포탈의 주요 기능들을 소개해드리겠습니다:\n\n• 실시간 정보 검색\n• 멀티모달 분석 (텍스트, 이미지)\n• 워크플로우 자동화\n• 협업 도구 통합\n\n지금은 Mock 모드로 실행 중입니다. 실제 기능을 사용하려면 API 키를 설정해주세요.",
            "안녕하세요! 저는 다음과 같은 일들을 도와드릴 수 있습니다:\n\n📝 텍스트 작성 및 편집\n🔎 정보 검색 및 요약\n💡 아이디어 제안\n🛠️ 코딩 및 기술 지원\n\n무엇을 도와드릴까요?",
        ],
        "technical": [
            "기술적인 질문이군요! 현재 Mock 모드에서 실행 중이므로 실제 코드 분석은 제한적입니다.\n\n하지만 일반적인 접근법을 제안드리면:\n1. 문제 상황 파악\n2. 솔루션 설계\n3. 단계별 구현\n4. 테스트 및 검증\n\n구체적인 기술 스택이나 문제에 대해 더 자세히 말씀해 주시면 도움을 드릴 수 있습니다.",
            "🔧 기술 지원 모드입니다.\n\n현재 시스템 상태:\n- Backend: FastAPI + SQLAlchemy\n- Frontend: React + TypeScript\n- Database: PostgreSQL\n- Cache: 2-tier (Memory + DB)\n\n어떤 기술적 도움이 필요하신가요?",
        ],
        "creative": [
            "창작 모드를 시작합니다! ✨\n\n다음과 같은 창작 작업을 도와드릴 수 있습니다:\n• 스토리텔링\n• 브레인스토밍\n• 콘텐츠 기획\n• 아이디어 발전\n\n어떤 창작물을 만들어보고 싶으신가요?",
            "🎨 창의적인 작업을 도와드리겠습니다!\n\n지금까지 많은 사용자들이 다음과 같은 프로젝트를 진행했습니다:\n- 소설 및 시 창작\n- 마케팅 카피\n- 프레젠테이션 기획\n- 제품 아이디어\n\n어떤 분야에 관심이 있으시나요?",
        ],
        "general": [
            "네, 이해했습니다. 조금 더 구체적으로 설명드리겠습니다.\n\n관련 정보들을 종합해보면, 여러 접근 방법이 있을 것 같습니다. 상황에 따라 다르지만, 일반적으로는 다음과 같은 순서로 진행하는 것이 좋습니다:\n\n1. 현재 상황 분석\n2. 목표 설정\n3. 실행 계획 수립\n4. 단계별 실행\n\n더 구체적인 조언이 필요하시면 말씀해 주세요!",
            "좋은 질문이네요! 이런 상황에서는 여러 관점에서 생각해볼 필요가 있습니다.\n\n제가 추천드리는 접근법은:\n• 데이터 수집 및 분석\n• 다양한 옵션 검토\n• 장단점 비교\n• 최적 솔루션 선택\n\n혹시 특별히 고려해야 할 제약사항이나 요구사항이 있으신가요?",
            "흥미로운 주제입니다! 이에 대해 여러 각도에서 살펴볼 수 있을 것 같습니다.\n\n현재 트렌드와 모범 사례를 고려할 때, 다음과 같은 방향이 효과적일 것 같습니다:\n\n✅ 사용자 경험 중심 접근\n✅ 확장 가능한 설계\n✅ 지속 가능한 솔루션\n\n어떤 부분에 대해 더 자세히 알고 싶으신가요?",
        ]
    }
    
    @classmethod
    def classify_query(cls, query: str) -> str:
        """쿼리 유형 분류"""
        query_lower = query.lower()
        
        # 인사말
        if any(word in query_lower for word in ['안녕', 'hello', 'hi', '반가']):
            return "greeting"
        
        # 검색 관련
        if any(word in query_lower for word in ['검색', 'search', '찾', '알려줘', '정보']):
            return "search"
        
        # 도움말
        if any(word in query_lower for word in ['도움', 'help', '기능', '뭘', '어떻게']):
            return "help"
        
        # 기술 관련
        if any(word in query_lower for word in ['코드', 'code', '프로그래밍', '개발', '기술', '버그', 'error']):
            return "technical"
        
        # 창작 관련
        if any(word in query_lower for word in ['작성', '써줘', '만들어', '창작', '아이디어', '기획']):
            return "creative"
        
        return "general"
    
    @classmethod
    def generate_response(cls, query: str, model: str = "mock-llm") -> str:
        """Mock 응답 생성"""
        query_type = cls.classify_query(query)
        templates = cls.RESPONSE_TEMPLATES.get(query_type, cls.RESPONSE_TEMPLATES["general"])
        
        # 랜덤하게 응답 선택
        response = random.choice(templates)
        
        # 메타데이터 추가
        if model and "mock" in model.lower():
            footer = f"\n\n---\n💡 *Mock 모드로 실행 중입니다. 실제 {model.replace('mock-', '').upper()} API를 사용하려면 API 키를 설정해주세요.*"
            response += footer
        
        return response
    
    @classmethod
    async def stream_response(cls, query: str, model: str = "mock-llm") -> AsyncGenerator[str, None]:
        """스트리밍 Mock 응답 생성"""
        response = cls.generate_response(query, model)
        
        # 단어별로 스트리밍 (실제 LLM 동작 시뮬레이션)
        words = response.split()
        
        for i, word in enumerate(words):
            # 마지막 단어가 아닌 경우 공백 추가
            chunk = word + (" " if i < len(words) - 1 else "")
            yield chunk
            
            # 스트리밍 딜레이 (실제 LLM 느낌)
            await asyncio.sleep(random.uniform(0.02, 0.08))
    
    @classmethod
    def get_model_info(cls, model: str) -> Dict:
        """Mock 모델 정보"""
        mock_models = {
            "mock-claude": {
                "name": "Mock Claude 3 Haiku",
                "provider": "Mock Anthropic",
                "max_tokens": 4096,
                "supports_streaming": True,
                "cost_per_1k_tokens": 0.00
            },
            "mock-gemini": {
                "name": "Mock Gemini Pro",
                "provider": "Mock Google",
                "max_tokens": 8192,
                "supports_streaming": True,
                "cost_per_1k_tokens": 0.00
            },
            "mock-gpt": {
                "name": "Mock GPT-4",
                "provider": "Mock OpenAI",
                "max_tokens": 8192,
                "supports_streaming": True,
                "cost_per_1k_tokens": 0.00
            }
        }
        
        return mock_models.get(model, mock_models["mock-claude"])


# 전역 Mock LLM 인스턴스
mock_llm = MockLLMResponse()