"""
한국 시간대 유틸리티
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
import pytz

# 한국 시간대
KST = timezone(timedelta(hours=9))  # UTC+9
SEOUL_TZ = pytz.timezone('Asia/Seoul')

def now_kst() -> datetime:
    """현재 한국 시간 반환"""
    return datetime.now(KST)

def utc_to_kst(dt: datetime) -> datetime:
    """UTC 시간을 한국 시간으로 변환"""
    if dt.tzinfo is None:
        # naive datetime은 UTC로 간주
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(KST)

def kst_to_utc(dt: datetime) -> datetime:
    """한국 시간을 UTC로 변환"""
    if dt.tzinfo is None:
        # naive datetime은 KST로 간주
        dt = dt.replace(tzinfo=KST)
    return dt.astimezone(timezone.utc)

def format_kst_datetime(dt: Optional[datetime]) -> str:
    """한국 시간으로 포맷팅"""
    if dt is None:
        return ""
    
    # UTC를 한국 시간으로 변환
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) == timedelta(0):
        kst_dt = utc_to_kst(dt)
    else:
        kst_dt = dt.astimezone(KST)
    
    return kst_dt.isoformat()

def parse_kst_datetime(dt_str: str) -> datetime:
    """ISO 형식 한국 시간 문자열을 파싱"""
    try:
        # ISO 형식 파싱
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        
        # timezone 정보가 없으면 KST로 간주
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=KST)
            
        return dt
    except ValueError:
        # 파싱 실패시 현재 시간 반환
        return now_kst()