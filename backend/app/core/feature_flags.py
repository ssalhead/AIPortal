"""
Feature Flag 시스템 - LangGraph 점진적 도입을 위한 안전한 기능 토글 시스템
"""

import hashlib
import logging
from typing import Optional, Dict, Any
from enum import Enum
from datetime import datetime, timedelta

from app.core.config import settings

logger = logging.getLogger(__name__)


class FeatureFlagType(Enum):
    """Feature Flag 유형"""
    PERCENTAGE_ROLLOUT = "percentage_rollout"  # 비율 기반 활성화
    USER_WHITELIST = "user_whitelist"          # 특정 사용자만
    TIME_WINDOW = "time_window"                # 특정 시간대만
    A_B_TEST = "a_b_test"                      # A/B 테스트


class LangGraphFeatureFlags:
    """LangGraph 기능들의 Feature Flag 관리 시스템"""
    
    # LangGraph 기능별 Feature Flag 정의
    LANGGRAPH_WEB_SEARCH = "langgraph_web_search"
    LANGGRAPH_CANVAS = "langgraph_canvas"
    LANGGRAPH_INFORMATION_GAP = "langgraph_information_gap"
    LANGGRAPH_SUPERVISOR = "langgraph_supervisor"
    LANGGRAPH_PARALLEL_PROCESSING = "langgraph_parallel_processing"
    LANGGRAPH_TOOL_CALLING = "langgraph_tool_calling"
    
    def __init__(self):
        """Feature Flag 설정 초기화"""
        
        # 🚀 대담한 전면 활성화 설정 (운영 중단 제약 없음)
        self.flag_configs = {
            self.LANGGRAPH_WEB_SEARCH: {
                "enabled": True,
                "type": FeatureFlagType.PERCENTAGE_ROLLOUT,
                "percentage": 100,  # 🚀 100% 전면 활성화!
                "description": "WebSearchAgent LangGraph 완전 전환"
            },
            self.LANGGRAPH_CANVAS: {
                "enabled": True,   # 🚀 즉시 활성화!
                "type": FeatureFlagType.PERCENTAGE_ROLLOUT,
                "percentage": 100,  # 전면 전환
                "description": "Canvas LangGraph 워크플로우 완전 전환"
            },
            self.LANGGRAPH_INFORMATION_GAP: {
                "enabled": True,   # 🚀 즉시 활성화!
                "type": FeatureFlagType.PERCENTAGE_ROLLOUT,
                "percentage": 100,  # 전면 전환
                "description": "InformationGap LangGraph 지능형 분석"
            },
            self.LANGGRAPH_SUPERVISOR: {
                "enabled": True,   # 🚀 즉시 활성화!
                "type": FeatureFlagType.PERCENTAGE_ROLLOUT,
                "percentage": 100,  # 전면 전환
                "description": "SupervisorAgent LangGraph 완전 통합"
            },
            self.LANGGRAPH_PARALLEL_PROCESSING: {
                "enabled": True,   # 🚀 즉시 활성화!
                "type": FeatureFlagType.PERCENTAGE_ROLLOUT,
                "percentage": 100,  # A/B 테스트 → 전면 적용
                "description": "고성능 병렬 처리 워크플로우"
            },
            self.LANGGRAPH_TOOL_CALLING: {
                "enabled": True,   # 🚀 즉시 활성화!
                "type": FeatureFlagType.PERCENTAGE_ROLLOUT,
                "percentage": 100,  # 전면 전환
                "description": "지능형 Tool-calling 기반 에이전트 협업"
            }
        }
        
        # 화이트리스트 사용자 (개발/테스트 목적)
        self.whitelist_users = {
            "dev_team_user_1",
            "dev_team_user_2", 
            "qa_tester_1"
        }
        
        # 시간 기반 활성화 설정
        self.time_windows = {}
        
        # 성능 모니터링을 위한 메트릭
        self.metrics = {
            "flag_checks": 0,
            "langgraph_activations": 0,
            "legacy_fallbacks": 0
        }
    
    def is_enabled(self, flag_name: str, user_id: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Feature Flag 활성화 여부 확인
        
        Args:
            flag_name: Feature Flag 이름
            user_id: 사용자 ID (옵셔널)
            context: 추가 컨텍스트 정보
            
        Returns:
            bool: 기능 활성화 여부
        """
        
        self.metrics["flag_checks"] += 1
        
        # Flag 설정 존재 확인
        if flag_name not in self.flag_configs:
            logger.warning(f"Unknown feature flag: {flag_name}")
            return False
        
        config = self.flag_configs[flag_name]
        
        # 전역 비활성화 확인
        if not config.get("enabled", False):
            return False
        
        # 개발 환경에서는 항상 활성화 (환경변수로 제어)
        if settings.ENVIRONMENT == "development" and settings.DEBUG:
            return True
        
        # 화이트리스트 사용자 확인
        if user_id and user_id in self.whitelist_users:
            logger.info(f"Feature flag {flag_name} enabled for whitelisted user: {user_id}")
            return True
        
        # Flag 유형별 처리
        flag_type = config.get("type", FeatureFlagType.PERCENTAGE_ROLLOUT)
        
        if flag_type == FeatureFlagType.PERCENTAGE_ROLLOUT:
            return self._check_percentage_rollout(flag_name, config, user_id)
        
        elif flag_type == FeatureFlagType.TIME_WINDOW:
            return self._check_time_window(flag_name, config)
        
        elif flag_type == FeatureFlagType.A_B_TEST:
            return self._check_ab_test(flag_name, config, user_id, context)
        
        else:
            logger.warning(f"Unknown flag type: {flag_type}")
            return False
    
    def _check_percentage_rollout(self, flag_name: str, config: Dict[str, Any], user_id: Optional[str]) -> bool:
        """비율 기반 활성화 확인"""
        
        percentage = config.get("percentage", 0)
        
        if percentage <= 0:
            return False
        
        if percentage >= 100:
            return True
        
        # 사용자 ID 기반 해시로 일관된 할당
        if user_id:
            hash_input = f"{flag_name}:{user_id}:{settings.FEATURE_FLAG_SALT}"
        else:
            # 익명 사용자의 경우 시간 기반 해시 (주기적 변경)
            hour_slot = datetime.now().hour // 4  # 4시간 단위
            hash_input = f"{flag_name}:anonymous:{hour_slot}:{settings.FEATURE_FLAG_SALT}"
        
        user_hash = int(hashlib.md5(hash_input.encode()).hexdigest()[:8], 16)
        user_percentage = user_hash % 100
        
        is_enabled = user_percentage < percentage
        
        if is_enabled:
            self.metrics["langgraph_activations"] += 1
            logger.debug(f"Feature flag {flag_name} enabled for user {user_id} (hash: {user_percentage}% < {percentage}%)")
        
        return is_enabled
    
    def _check_time_window(self, flag_name: str, config: Dict[str, Any]) -> bool:
        """시간 기반 활성화 확인"""
        
        if flag_name not in self.time_windows:
            return False
        
        window = self.time_windows[flag_name]
        current_time = datetime.now()
        
        return window["start"] <= current_time <= window["end"]
    
    def _check_ab_test(self, flag_name: str, config: Dict[str, Any], user_id: Optional[str], context: Optional[Dict[str, Any]]) -> bool:
        """A/B 테스트 기반 활성화 확인"""
        
        # A/B 테스트는 50/50 분할
        if not user_id:
            return False
        
        hash_input = f"ab_test:{flag_name}:{user_id}"
        user_hash = int(hashlib.md5(hash_input.encode()).hexdigest()[:8], 16)
        
        # Group A: LangGraph, Group B: Legacy
        return user_hash % 2 == 0
    
    def update_flag_percentage(self, flag_name: str, new_percentage: int) -> bool:
        """
        Feature Flag 비율 동적 업데이트
        
        Args:
            flag_name: Feature Flag 이름
            new_percentage: 새로운 활성화 비율 (0-100)
            
        Returns:
            bool: 업데이트 성공 여부
        """
        
        if flag_name not in self.flag_configs:
            logger.error(f"Cannot update unknown feature flag: {flag_name}")
            return False
        
        if not (0 <= new_percentage <= 100):
            logger.error(f"Invalid percentage: {new_percentage}. Must be 0-100")
            return False
        
        old_percentage = self.flag_configs[flag_name].get("percentage", 0)
        self.flag_configs[flag_name]["percentage"] = new_percentage
        
        logger.info(f"Feature flag {flag_name} percentage updated: {old_percentage}% → {new_percentage}%")
        
        return True
    
    def enable_flag(self, flag_name: str) -> bool:
        """Feature Flag 활성화"""
        if flag_name in self.flag_configs:
            self.flag_configs[flag_name]["enabled"] = True
            logger.info(f"Feature flag {flag_name} enabled")
            return True
        return False
    
    def disable_flag(self, flag_name: str) -> bool:
        """Feature Flag 비활성화 (긴급 상황용)"""
        if flag_name in self.flag_configs:
            self.flag_configs[flag_name]["enabled"] = False
            logger.warning(f"Feature flag {flag_name} disabled")
            return True
        return False
    
    def add_whitelist_user(self, user_id: str) -> None:
        """화이트리스트 사용자 추가"""
        self.whitelist_users.add(user_id)
        logger.info(f"User {user_id} added to feature flag whitelist")
    
    def remove_whitelist_user(self, user_id: str) -> None:
        """화이트리스트 사용자 제거"""
        self.whitelist_users.discard(user_id)
        logger.info(f"User {user_id} removed from feature flag whitelist")
    
    def set_time_window(self, flag_name: str, start_time: datetime, end_time: datetime) -> None:
        """시간 기반 활성화 설정"""
        self.time_windows[flag_name] = {
            "start": start_time,
            "end": end_time
        }
        logger.info(f"Time window set for {flag_name}: {start_time} - {end_time}")
    
    def get_flag_status(self) -> Dict[str, Any]:
        """모든 Feature Flag 상태 조회"""
        return {
            "flags": self.flag_configs,
            "whitelist_users": list(self.whitelist_users),
            "time_windows": self.time_windows,
            "metrics": self.metrics
        }
    
    def record_fallback(self, flag_name: str, reason: str) -> None:
        """Legacy로 fallback 발생 기록"""
        self.metrics["legacy_fallbacks"] += 1
        logger.warning(f"LangGraph fallback for {flag_name}: {reason}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """성능 메트릭 조회"""
        total_checks = self.metrics["flag_checks"]
        activations = self.metrics["langgraph_activations"]
        fallbacks = self.metrics["legacy_fallbacks"]
        
        return {
            "total_flag_checks": total_checks,
            "langgraph_activations": activations,
            "legacy_fallbacks": fallbacks,
            "activation_rate": (activations / total_checks * 100) if total_checks > 0 else 0,
            "fallback_rate": (fallbacks / activations * 100) if activations > 0 else 0
        }


# 전역 Feature Flag 인스턴스
feature_flags = LangGraphFeatureFlags()


def is_langgraph_enabled(flag_name: str, user_id: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> bool:
    """
    편의 함수: LangGraph 기능 활성화 여부 확인
    
    Args:
        flag_name: Feature Flag 이름
        user_id: 사용자 ID
        context: 추가 컨텍스트
        
    Returns:
        bool: 기능 활성화 여부
    """
    return feature_flags.is_enabled(flag_name, user_id, context)


def record_langgraph_fallback(flag_name: str, reason: str) -> None:
    """
    편의 함수: LangGraph fallback 기록
    
    Args:
        flag_name: Feature Flag 이름
        reason: Fallback 이유
    """
    feature_flags.record_fallback(flag_name, reason)