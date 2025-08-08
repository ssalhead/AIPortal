"""
지능형 캐시 관리 시스템
예측적 캐싱, 압축, 사용자 패턴 분석 기반 최적화
"""

import asyncio
import json
import zlib
import pickle
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, field
import hashlib
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.cache_manager import cache_manager
from app.services.performance_monitor import performance_monitor
import logging

logger = logging.getLogger(__name__)


@dataclass
class CacheAccessPattern:
    """캐시 접근 패턴"""
    key: str
    access_time: datetime
    user_id: str
    hit: bool
    frequency: int = 1
    size_bytes: int = 0


@dataclass
class UserCacheProfile:
    """사용자 캐시 프로파일"""
    user_id: str
    access_patterns: List[CacheAccessPattern] = field(default_factory=list)
    preferred_cache_keys: List[str] = field(default_factory=list)
    peak_hours: List[int] = field(default_factory=list)
    avg_session_duration: float = 0.0
    cache_hit_rate: float = 0.0


class IntelligentCacheManager:
    """지능형 캐시 관리자"""
    
    def __init__(self, enable_compression: bool = True, enable_prediction: bool = True):
        self.base_cache = cache_manager
        self.enable_compression = enable_compression
        self.enable_prediction = enable_prediction
        
        # 사용자 프로파일 저장
        self.user_profiles: Dict[str, UserCacheProfile] = {}
        
        # 접근 패턴 추적
        self.access_patterns: deque = deque(maxlen=10000)
        
        # 예측 캐시 큐
        self.prediction_queue: asyncio.Queue = asyncio.Queue()
        
        # 압축 통계
        self.compression_stats = {
            'total_compressed': 0,
            'total_original_size': 0,
            'total_compressed_size': 0,
            'compression_ratio': 0.0
        }
        
        # 백그라운드 태스크
        self.prediction_task: Optional[asyncio.Task] = None
        self.profile_update_task: Optional[asyncio.Task] = None
        self.is_running = False
    
    async def start(self):
        """지능형 캐시 시스템 시작"""
        if not self.is_running:
            self.is_running = True
            
            if self.enable_prediction:
                self.prediction_task = asyncio.create_task(self._prediction_worker())
            
            self.profile_update_task = asyncio.create_task(self._profile_updater())
            
            logger.info("지능형 캐시 시스템이 시작되었습니다.")
    
    async def stop(self):
        """지능형 캐시 시스템 중지"""
        self.is_running = False
        
        if self.prediction_task:
            self.prediction_task.cancel()
        
        if self.profile_update_task:
            self.profile_update_task.cancel()
        
        logger.info("지능형 캐시 시스템이 중지되었습니다.")
    
    def _compress_data(self, data: Any) -> Tuple[bytes, bool]:
        """데이터 압축"""
        if not self.enable_compression:
            return pickle.dumps(data), False
        
        try:
            # 원본 데이터 직렬화
            original_data = pickle.dumps(data)
            original_size = len(original_data)
            
            # 압축 (큰 데이터만 압축)
            if original_size > 1024:  # 1KB 이상만 압축
                compressed_data = zlib.compress(original_data, level=6)
                compressed_size = len(compressed_data)
                
                # 압축 효율성 확인 (최소 10% 이상 압축되어야 함)
                if compressed_size < original_size * 0.9:
                    # 압축 통계 업데이트
                    self.compression_stats['total_compressed'] += 1
                    self.compression_stats['total_original_size'] += original_size
                    self.compression_stats['total_compressed_size'] += compressed_size
                    self.compression_stats['compression_ratio'] = (
                        1 - (self.compression_stats['total_compressed_size'] / 
                             self.compression_stats['total_original_size'])
                    ) * 100
                    
                    return compressed_data, True
            
            return original_data, False
            
        except Exception as e:
            logger.warning(f"데이터 압축 실패: {str(e)}")
            return pickle.dumps(data), False
    
    def _decompress_data(self, data: bytes, is_compressed: bool) -> Any:
        """데이터 압축 해제"""
        try:
            if is_compressed:
                decompressed_data = zlib.decompress(data)
                return pickle.loads(decompressed_data)
            else:
                return pickle.loads(data)
        except Exception as e:
            logger.error(f"데이터 압축 해제 실패: {str(e)}")
            raise
    
    async def get(
        self, 
        key: str, 
        user_id: str,
        session: Optional[AsyncSession] = None
    ) -> Optional[Any]:
        """지능형 캐시 조회"""
        start_time = datetime.utcnow()
        
        # 기본 캐시에서 조회
        cached_data = await self.base_cache.get(key, session)
        
        # 압축된 데이터 처리
        if cached_data is not None:
            # 메타데이터 확인
            if isinstance(cached_data, dict) and '_compressed' in cached_data:
                try:
                    data = self._decompress_data(
                        cached_data['data'], 
                        cached_data['_compressed']
                    )
                    hit = True
                except Exception as e:
                    logger.error(f"압축 해제 실패: {str(e)}")
                    data = None
                    hit = False
            else:
                data = cached_data
                hit = True
        else:
            data = None
            hit = False
        
        # 접근 패턴 기록
        pattern = CacheAccessPattern(
            key=key,
            access_time=start_time,
            user_id=user_id,
            hit=hit,
            size_bytes=len(str(cached_data)) if cached_data else 0
        )
        self.access_patterns.append(pattern)
        
        # 성능 메트릭 기록
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        performance_monitor.record_cache_metrics(
            cache_type="intelligent",
            operation="get",
            hit=hit,
            duration_ms=duration_ms
        )
        
        # 예측 캐싱 트리거 (캐시 미스 시)
        if not hit and self.enable_prediction:
            await self._trigger_prediction(user_id, key)
        
        return data
    
    async def set(
        self,
        key: str,
        value: Any,
        user_id: str,
        session: Optional[AsyncSession] = None,
        ttl_seconds: Optional[int] = None
    ):
        """지능형 캐시 저장"""
        start_time = datetime.utcnow()
        
        # 데이터 압축
        compressed_data, is_compressed = self._compress_data(value)
        
        # 메타데이터와 함께 저장
        cache_entry = {
            'data': compressed_data,
            '_compressed': is_compressed,
            '_user_id': user_id,
            '_stored_at': start_time.isoformat()
        }
        
        # 기본 캐시에 저장
        await self.base_cache.set(key, cache_entry, session, ttl_seconds)
        
        # 접근 패턴 기록
        pattern = CacheAccessPattern(
            key=key,
            access_time=start_time,
            user_id=user_id,
            hit=True,  # 저장은 항상 hit로 기록
            size_bytes=len(compressed_data)
        )
        self.access_patterns.append(pattern)
        
        # 성능 메트릭 기록
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        performance_monitor.record_cache_metrics(
            cache_type="intelligent",
            operation="set",
            hit=True,
            duration_ms=duration_ms
        )
    
    async def _trigger_prediction(self, user_id: str, missed_key: str):
        """예측 캐싱 트리거"""
        if not self.is_running:
            return
        
        try:
            await self.prediction_queue.put({
                'user_id': user_id,
                'missed_key': missed_key,
                'timestamp': datetime.utcnow()
            })
        except asyncio.QueueFull:
            logger.warning("예측 캐싱 큐가 가득참")
    
    async def _prediction_worker(self):
        """예측 캐싱 워커"""
        while self.is_running:
            try:
                # 예측 요청 처리
                prediction_request = await asyncio.wait_for(
                    self.prediction_queue.get(), 
                    timeout=5.0
                )
                
                await self._perform_predictive_caching(prediction_request)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"예측 캐싱 오류: {str(e)}")
                await asyncio.sleep(1)
    
    async def _perform_predictive_caching(self, request: Dict[str, Any]):
        """예측적 캐싱 수행"""
        user_id = request['user_id']
        missed_key = request['missed_key']
        
        # 사용자 프로파일 확인
        profile = self.user_profiles.get(user_id)
        if not profile:
            return
        
        # 관련 키 예측
        predicted_keys = self._predict_related_keys(user_id, missed_key, profile)
        
        # TODO: 예측된 키들에 대한 데이터 사전 로드
        # 실제 구현에서는 데이터베이스에서 미리 로드하여 캐시에 저장
        logger.info(f"사용자 {user_id}에 대해 {len(predicted_keys)}개 키 예측 완료")
    
    def _predict_related_keys(
        self, 
        user_id: str, 
        missed_key: str, 
        profile: UserCacheProfile
    ) -> List[str]:
        """관련 키 예측"""
        predicted_keys = []
        
        # 패턴 기반 예측
        for pattern in profile.access_patterns[-50:]:  # 최근 50개 패턴
            if pattern.key != missed_key:
                # 키 유사도 계산 (간단한 해싱 기반)
                similarity = self._calculate_key_similarity(missed_key, pattern.key)
                if similarity > 0.7:  # 70% 이상 유사
                    predicted_keys.append(pattern.key)
        
        # 시간 패턴 기반 예측
        current_hour = datetime.utcnow().hour
        if current_hour in profile.peak_hours:
            # 피크 시간대에 자주 사용되는 키들 추가
            predicted_keys.extend(profile.preferred_cache_keys[:5])
        
        return list(set(predicted_keys))[:10]  # 최대 10개, 중복 제거
    
    def _calculate_key_similarity(self, key1: str, key2: str) -> float:
        """키 유사도 계산"""
        # 간단한 편집 거리 기반 유사도
        if not key1 or not key2:
            return 0.0
        
        # 공통 접두사 길이
        common_prefix = 0
        min_len = min(len(key1), len(key2))
        
        for i in range(min_len):
            if key1[i] == key2[i]:
                common_prefix += 1
            else:
                break
        
        # 유사도 계산
        max_len = max(len(key1), len(key2))
        return common_prefix / max_len if max_len > 0 else 0.0
    
    async def _profile_updater(self):
        """사용자 프로파일 주기적 업데이트"""
        while self.is_running:
            try:
                await asyncio.sleep(300)  # 5분마다 업데이트
                await self._update_user_profiles()
            except Exception as e:
                logger.error(f"프로파일 업데이트 오류: {str(e)}")
    
    async def _update_user_profiles(self):
        """사용자 프로파일 업데이트"""
        # 최근 접근 패턴 분석
        recent_patterns = [
            p for p in self.access_patterns 
            if p.access_time > datetime.utcnow() - timedelta(hours=24)
        ]
        
        # 사용자별 그룹화
        user_patterns = defaultdict(list)
        for pattern in recent_patterns:
            user_patterns[pattern.user_id].append(pattern)
        
        # 각 사용자 프로파일 업데이트
        for user_id, patterns in user_patterns.items():
            await self._update_single_user_profile(user_id, patterns)
    
    async def _update_single_user_profile(
        self, 
        user_id: str, 
        patterns: List[CacheAccessPattern]
    ):
        """단일 사용자 프로파일 업데이트"""
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = UserCacheProfile(user_id=user_id)
        
        profile = self.user_profiles[user_id]
        
        # 접근 패턴 추가 (최근 1000개만 유지)
        profile.access_patterns.extend(patterns)
        profile.access_patterns = profile.access_patterns[-1000:]
        
        # 선호 키 분석
        key_frequency = defaultdict(int)
        hit_count = 0
        total_count = len(patterns)
        
        for pattern in patterns:
            key_frequency[pattern.key] += 1
            if pattern.hit:
                hit_count += 1
        
        # 가장 자주 사용되는 키들
        profile.preferred_cache_keys = [
            key for key, freq in sorted(
                key_frequency.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:20]
        ]
        
        # 피크 시간대 분석
        hour_frequency = defaultdict(int)
        for pattern in patterns:
            hour_frequency[pattern.access_time.hour] += 1
        
        # 평균보다 많이 사용되는 시간대
        avg_frequency = sum(hour_frequency.values()) / 24 if hour_frequency else 0
        profile.peak_hours = [
            hour for hour, freq in hour_frequency.items() 
            if freq > avg_frequency * 1.2
        ]
        
        # 캐시 적중률
        profile.cache_hit_rate = (hit_count / total_count * 100) if total_count > 0 else 0
        
        logger.debug(f"사용자 {user_id} 프로파일 업데이트 완료 - 적중률: {profile.cache_hit_rate:.1f}%")
    
    def get_intelligent_stats(self) -> Dict[str, Any]:
        """지능형 캐시 통계"""
        total_users = len(self.user_profiles)
        total_patterns = len(self.access_patterns)
        
        # 전체 캐시 적중률
        recent_patterns = [
            p for p in self.access_patterns 
            if p.access_time > datetime.utcnow() - timedelta(hours=1)
        ]
        
        total_hits = sum(1 for p in recent_patterns if p.hit)
        overall_hit_rate = (total_hits / len(recent_patterns) * 100) if recent_patterns else 0
        
        return {
            'intelligent_cache': {
                'total_users': total_users,
                'total_patterns': total_patterns,
                'overall_hit_rate': f"{overall_hit_rate:.2f}%",
                'compression_enabled': self.enable_compression,
                'prediction_enabled': self.enable_prediction,
                'compression_stats': self.compression_stats,
                'active_predictions': self.prediction_queue.qsize() if self.prediction_queue else 0
            },
            'user_profiles': [
                {
                    'user_id': profile.user_id,
                    'cache_hit_rate': f"{profile.cache_hit_rate:.2f}%",
                    'preferred_keys_count': len(profile.preferred_cache_keys),
                    'peak_hours': profile.peak_hours,
                    'pattern_count': len(profile.access_patterns)
                }
                for profile in list(self.user_profiles.values())[:10]  # 상위 10개만
            ]
        }
    
    async def optimize_cache_configuration(self) -> Dict[str, Any]:
        """캐시 설정 자동 최적화"""
        stats = self.get_intelligent_stats()
        recommendations = []
        
        # 압축 효율성 분석
        if self.compression_stats['compression_ratio'] < 10:  # 10% 미만 압축
            recommendations.append({
                'type': 'compression',
                'message': '압축 효율이 낮습니다. 압축 임계값을 조정하는 것을 고려하세요.',
                'current_ratio': self.compression_stats['compression_ratio']
            })
        
        # 캐시 적중률 분석
        overall_hit_rate = float(stats['intelligent_cache']['overall_hit_rate'].replace('%', ''))
        if overall_hit_rate < 70:  # 70% 미만
            recommendations.append({
                'type': 'hit_rate',
                'message': '캐시 적중률이 낮습니다. TTL을 늘리거나 캐시 크기를 증가시키세요.',
                'current_rate': overall_hit_rate
            })
        
        # 예측 캐싱 효과 분석
        if self.enable_prediction and stats['intelligent_cache']['active_predictions'] > 100:
            recommendations.append({
                'type': 'prediction',
                'message': '예측 캐싱 큐가 과부하 상태입니다. 예측 알고리즘을 조정하세요.',
                'queue_size': stats['intelligent_cache']['active_predictions']
            })
        
        return {
            'optimization_timestamp': datetime.utcnow().isoformat(),
            'recommendations': recommendations,
            'current_stats': stats
        }


# 전역 지능형 캐시 매니저 인스턴스
intelligent_cache_manager = IntelligentCacheManager()