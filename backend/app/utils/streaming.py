"""
스트리밍 관련 공통 유틸리티
"""

from typing import List, Tuple
from app.utils.logger import get_logger

logger = get_logger(__name__)


def split_response_into_natural_chunks(response: str, chunk_size_range: Tuple[int, int] = (3, 8)) -> List[str]:
    """
    에이전트 응답을 고정 크기 청크로 정확하게 분할 (원본 보존 보장)
    
    Args:
        response: 분할할 에이전트 응답 전체 텍스트
        chunk_size_range: 청크 크기 범위 (최소, 최대 글자 수)
    
    Returns:
        정확하게 분할된 청크 리스트 (원본 재결합 보장)
    """
    if not response.strip():
        return []
    
    min_size, max_size = chunk_size_range
    chunks = []
    start = 0
    
    logger.debug_performance("청킹 시작", {
        "response_length": len(response),
        "chunk_size_range": chunk_size_range
    })
    
    while start < len(response):
        # 기본 청크 크기 설정
        chunk_end = start + max_size
        
        # 텍스트 끝을 넘지 않도록 조정
        if chunk_end >= len(response):
            chunk_end = len(response)
        else:
            # 자연스러운 분할점 찾기 (단어 경계, 문장 경계, 줄바꿈)
            text_segment = response[start:chunk_end + 20]  # 여유분을 두고 검색
            
            # Gemini 스타일: 글자 단위 "스르륵" 흐름 최적화
            # 우선순위: 음절 경계 > 글자 경계 > 쉼표 > 단어 경계
            best_split = chunk_end
            
            # 1. 한글 음절 경계 우선 (자연스러운 읽기 흐름)
            korean_vowels = ['ㅏ', 'ㅑ', 'ㅓ', 'ㅕ', 'ㅗ', 'ㅛ', 'ㅜ', 'ㅠ', 'ㅡ', 'ㅣ']
            for i in range(min_size, min(len(text_segment), max_size)):
                char = text_segment[i] if i < len(text_segment) else ''
                # 한글 완성형 글자 뒤에서 분할 (더 자연스러운 흐름)
                if char and ord(char) >= 0xAC00 and ord(char) <= 0xD7A3:
                    candidate_pos = start + i + 1
                    if candidate_pos <= len(response) and (i + 1) >= min_size:
                        best_split = candidate_pos
                        break
            else:
                # 2. 작은 구두점 찾기 (숨쉬는 지점)
                micro_patterns = [', ', '、 ', ' ']  # 공백도 미세한 멈춤점
                for pattern in micro_patterns:
                    pattern_pos = text_segment.rfind(pattern, max(1, min_size // 3))
                    if pattern_pos != -1:
                        candidate_pos = start + pattern_pos + len(pattern)
                        if candidate_pos <= len(response):
                            best_split = candidate_pos
                            break
                else:
                    # 3. 영문 단어 경계 (알파벳의 경우)
                    for i in range(min_size, min(len(text_segment), max_size)):
                        char = text_segment[i] if i < len(text_segment) else ''
                        if char and (char.isspace() or not char.isalnum()):
                            candidate_pos = start + i + 1
                            if candidate_pos <= len(response):
                                best_split = candidate_pos
                                break
            
            chunk_end = min(best_split, len(response))
        
        # 청크 추출
        chunk = response[start:chunk_end]
        if chunk:  # 빈 청크 방지
            chunks.append(chunk)
            logger.debug_streaming(f"청크 #{len(chunks)}", {
                "length": len(chunk),
                "preview": chunk[:30] + ('...' if len(chunk) > 30 else '')
            })
        
        start = chunk_end
    
    # 재결합 검증 (100% 정확성 보장)
    recombined = ''.join(chunks)
    if recombined != response:
        logger.error("청크 재결합 실패", None, {
            "original_length": len(response),
            "recombined_length": len(recombined),
            "original_preview": response[-50:],
            "recombined_preview": recombined[-50:]
        })
        # 실패 시 단일 청크로 안전하게 처리
        return [response]
    
    logger.debug_performance("청킹 완료", {
        "chunk_count": len(chunks),
        "verification": "passed"
    })
    return chunks


class StreamingConfig:
    """스트리밍 설정 클래스"""
    
    # Gemini 스타일 "스르륵" 타이핑 효과 설정
    DEFAULT_CONFIG = {
        "chunk_size_range": (3, 8),  # 청크 크기 범위 (더욱 작게 - 스르륵 효과)
        "base_delay_range": (0.01, 0.03),  # 기본 타이핑 속도 범위 (초) (더 빠르게)
        "character_delay": 0.002,  # 글자당 추가 딜레이 (2ms)
        "word_pause": 0.005,  # 단어 간 일시정지 (5ms, 더 짧게)
        "sentence_pause": 0.03,  # 문장 끝 일시정지 (30ms, 더 짧게)
        "paragraph_pause": 0.06,   # 단락 끝 일시정지 (60ms, 더 짧게)
        "flow_acceleration": True,  # 스르륵 흐름 가속 효과
        "adaptive_speed": True  # 적응형 속도 조절
    }
    
    def __init__(self, config: dict = None):
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
    
    def get(self, key: str, default=None):
        return self.config.get(key, default)
    
    def update(self, updates: dict):
        self.config.update(updates)