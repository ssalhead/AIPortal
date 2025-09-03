"""
Canvas 공유 서비스
"""

import secrets
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy import and_, or_, desc, func
from sqlalchemy.orm import Session

from app.db.models.canvas_share import (
    CanvasShare, CanvasShareAnalytics, CanvasShareReport,
    SharePermission, ShareVisibility, ShareDuration
)
from app.db.models.image_history import ImageHistory
from app.models.canvas_share_models import (
    CreateShareRequest, UpdateShareRequest, ShareResponse,
    ShareAnalyticsResponse, ShareAccessRequest, ShareAccessResponse,
    ShareReportRequest, SocialShareData, OpenGraphData, TwitterCardData
)
from app.core.config import settings
from app.services.canvas_cache_manager import CanvasCacheManager
from app.services.canvas_og_image_service import CanvasOGImageService
from app.utils.timezone import now_kst


class CanvasShareService:
    """Canvas 공유 관리 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.cache_manager = CanvasCacheManager(db)
        self.og_service = CanvasOGImageService()
    
    def create_share(self, request: CreateShareRequest, creator_id: str) -> ShareResponse:
        """공유 링크 생성"""
        
        # Canvas 존재 확인
        canvas_exists = self.db.query(ImageHistory).filter(
            ImageHistory.canvas_id == request.canvas_id
        ).first()
        
        if not canvas_exists:
            raise ValueError("Canvas not found")
        
        # 공유 토큰 생성 (32자리 안전한 랜덤 문자열)
        share_token = secrets.token_urlsafe(24)[:32]
        
        # 비밀번호 해시화
        password_hash = None
        if request.password and request.visibility == ShareVisibility.PASSWORD_PROTECTED:
            password_hash = self._hash_password(request.password)
        
        # 만료 시간 계산
        expires_at = None
        if request.duration != ShareDuration.UNLIMITED:
            expires_at = CanvasShare.calculate_expires_at(request.duration)
        
        # 미리보기 이미지 URL 생성
        canvas_data = self._get_canvas_data(request.canvas_id)
        first_image_url = None
        if canvas_data and canvas_data.get('images'):
            first_image_url = canvas_data['images'][0].get('url')
        
        preview_image_url = self._generate_preview_image(request.canvas_id, first_image_url)
        og_image_url = self._generate_og_image(
            request.canvas_id, 
            request.title, 
            request.description,
            first_image_url,
            creator_id
        )
        
        # 공유 링크 생성
        share = CanvasShare(
            share_token=share_token,
            canvas_id=request.canvas_id,
            creator_id=creator_id,
            title=request.title,
            description=request.description,
            permission=request.permission,
            visibility=request.visibility,
            duration=request.duration,
            password_hash=password_hash,
            allowed_users=request.allowed_users,
            max_views=request.max_views,
            expires_at=expires_at,
            preview_image_url=preview_image_url,
            og_image_url=og_image_url
        )
        
        self.db.add(share)
        self.db.commit()
        self.db.refresh(share)
        
        return self._to_share_response(share)
    
    def get_share(self, share_token: str) -> Optional[ShareResponse]:
        """공유 링크 조회"""
        share = self.db.query(CanvasShare).filter(
            CanvasShare.share_token == share_token
        ).first()
        
        if not share:
            return None
        
        return self._to_share_response(share)
    
    def update_share(self, share_token: str, request: UpdateShareRequest, creator_id: str) -> Optional[ShareResponse]:
        """공유 링크 수정"""
        share = self.db.query(CanvasShare).filter(
            and_(
                CanvasShare.share_token == share_token,
                CanvasShare.creator_id == creator_id
            )
        ).first()
        
        if not share:
            return None
        
        # 수정할 필드들 업데이트
        if request.title is not None:
            share.title = request.title
        if request.description is not None:
            share.description = request.description
        if request.permission is not None:
            share.permission = request.permission
        if request.visibility is not None:
            share.visibility = request.visibility
        if request.duration is not None:
            share.duration = request.duration
            share.expires_at = CanvasShare.calculate_expires_at(request.duration) if request.duration != ShareDuration.UNLIMITED else None
        if request.allowed_users is not None:
            share.allowed_users = request.allowed_users
        if request.max_views is not None:
            share.max_views = request.max_views
        if request.is_active is not None:
            share.is_active = request.is_active
        
        # 비밀번호 업데이트
        if request.password is not None:
            if request.password and share.visibility == ShareVisibility.PASSWORD_PROTECTED:
                share.password_hash = self._hash_password(request.password)
            else:
                share.password_hash = None
        
        share.updated_at = now_kst()
        
        self.db.commit()
        self.db.refresh(share)
        
        return self._to_share_response(share)
    
    def delete_share(self, share_token: str, creator_id: str) -> bool:
        """공유 링크 삭제"""
        share = self.db.query(CanvasShare).filter(
            and_(
                CanvasShare.share_token == share_token,
                CanvasShare.creator_id == creator_id
            )
        ).first()
        
        if not share:
            return False
        
        self.db.delete(share)
        self.db.commit()
        
        return True
    
    def access_share(self, share_token: str, access_request: ShareAccessRequest, visitor_info: Dict[str, Any]) -> Tuple[Optional[ShareAccessResponse], str]:
        """
        공유 Canvas에 접근
        Returns: (response, error_message)
        """
        share = self.db.query(CanvasShare).filter(
            CanvasShare.share_token == share_token
        ).first()
        
        if not share:
            return None, "SHARE_NOT_FOUND"
        
        # 접근 가능성 검증
        if not share.can_access():
            if share.is_expired():
                return None, "SHARE_EXPIRED"
            elif share.is_view_limit_exceeded():
                return None, "SHARE_VIEW_LIMIT_EXCEEDED"
            else:
                return None, "SHARE_INACTIVE"
        
        # 권한 검증
        access_error = self._validate_share_access(share, access_request)
        if access_error:
            return None, access_error
        
        # 방문 기록
        self._record_visit(share, visitor_info, "view")
        
        # Canvas 데이터 조회
        canvas_data = self._get_canvas_data(share.canvas_id)
        if not canvas_data:
            return None, "SHARE_CANVAS_NOT_FOUND"
        
        # 액세스 응답 생성
        response = ShareAccessResponse(
            canvas_id=share.canvas_id,
            canvas_data=canvas_data,
            permission=share.permission,
            title=share.title,
            description=share.description,
            created_at=share.created_at,
            last_updated_at=share.updated_at,
            preview_image_url=share.preview_image_url,
            layers_count=len(canvas_data.get('layers', [])),
            elements_count=len(canvas_data.get('elements', []))
        )
        
        # 공개 공유인 경우 작성자 정보 포함
        if share.visibility == ShareVisibility.PUBLIC:
            response.creator_info = {
                "creator_id": share.creator_id,
                "created_at": share.created_at.isoformat()
            }
        
        return response, ""
    
    def get_user_shares(self, creator_id: str, limit: int = 50, offset: int = 0) -> List[ShareResponse]:
        """사용자의 공유 링크 목록 조회"""
        shares = self.db.query(CanvasShare).filter(
            CanvasShare.creator_id == creator_id
        ).order_by(desc(CanvasShare.created_at)).offset(offset).limit(limit).all()
        
        return [self._to_share_response(share) for share in shares]
    
    def get_canvas_shares(self, canvas_id: UUID, creator_id: str) -> List[ShareResponse]:
        """특정 Canvas의 공유 링크 목록 조회"""
        shares = self.db.query(CanvasShare).filter(
            and_(
                CanvasShare.canvas_id == canvas_id,
                CanvasShare.creator_id == creator_id
            )
        ).order_by(desc(CanvasShare.created_at)).all()
        
        return [self._to_share_response(share) for share in shares]
    
    def get_share_analytics(self, share_token: str, creator_id: str) -> Optional[ShareAnalyticsResponse]:
        """공유 링크 분석 데이터 조회"""
        share = self.db.query(CanvasShare).filter(
            and_(
                CanvasShare.share_token == share_token,
                CanvasShare.creator_id == creator_id
            )
        ).first()
        
        if not share:
            return None
        
        # 기본 통계
        total_views = share.view_count
        total_downloads = share.download_count
        
        # 고유 방문자 수
        unique_visitors = self.db.query(
            func.count(func.distinct(CanvasShareAnalytics.visitor_ip))
        ).filter(CanvasShareAnalytics.share_id == share.id).scalar() or 0
        
        # 시간별 통계
        today = datetime.utcnow().date()
        week_ago = datetime.utcnow() - timedelta(days=7)
        month_ago = datetime.utcnow() - timedelta(days=30)
        
        views_today = self._get_views_count(share.id, today, today + timedelta(days=1))
        views_this_week = self._get_views_count(share.id, week_ago, datetime.utcnow())
        views_this_month = self._get_views_count(share.id, month_ago, datetime.utcnow())
        
        # 지역별/디바이스별 분석
        top_countries = self._get_top_countries(share.id)
        top_cities = self._get_top_cities(share.id)
        device_breakdown = self._get_device_breakdown(share.id)
        browser_breakdown = self._get_browser_breakdown(share.id)
        os_breakdown = self._get_os_breakdown(share.id)
        referrer_breakdown = self._get_referrer_breakdown(share.id)
        
        # 시계열 데이터
        daily_views = self._get_daily_views(share.id, 30)
        hourly_views = self._get_hourly_views(share.id, today)
        
        return ShareAnalyticsResponse(
            share_id=share.id,
            total_views=total_views,
            total_downloads=total_downloads,
            unique_visitors=unique_visitors,
            views_today=views_today,
            views_this_week=views_this_week,
            views_this_month=views_this_month,
            top_countries=top_countries,
            top_cities=top_cities,
            device_breakdown=device_breakdown,
            browser_breakdown=browser_breakdown,
            os_breakdown=os_breakdown,
            referrer_breakdown=referrer_breakdown,
            daily_views=daily_views,
            hourly_views=hourly_views
        )
    
    def report_share(self, share_token: str, report_request: ShareReportRequest, visitor_info: Dict[str, Any]) -> Optional[str]:
        """공유 신고"""
        share = self.db.query(CanvasShare).filter(
            CanvasShare.share_token == share_token
        ).first()
        
        if not share:
            return None
        
        # 신고 생성
        report = CanvasShareReport(
            share_id=share.id,
            reporter_ip=visitor_info.get('ip'),
            reporter_email=report_request.reporter_email,
            reason=report_request.reason,
            description=report_request.description
        )
        
        self.db.add(report)
        
        # 분석 기록
        self._record_visit(share, visitor_info, "report")
        
        self.db.commit()
        
        return str(report.id)
    
    def get_social_share_data(self, share_token: str) -> Optional[SocialShareData]:
        """소셜 미디어 공유 데이터 생성"""
        share = self.db.query(CanvasShare).filter(
            CanvasShare.share_token == share_token
        ).first()
        
        if not share or not share.can_access():
            return None
        
        share_url = f"{settings.FRONTEND_URL}/shared/canvas/{share_token}"
        
        title = share.title or f"Canvas by {share.creator_id}"
        description = share.description or "View this amazing Canvas creation"
        
        og_data = OpenGraphData(
            title=title,
            description=description,
            image=share.og_image_url,
            url=share_url,
            type="website",
            site_name="AI Portal"
        )
        
        twitter_data = TwitterCardData(
            title=title,
            description=description,
            image=share.og_image_url
        )
        
        return SocialShareData(og=og_data, twitter=twitter_data)
    
    # Private methods
    
    def _hash_password(self, password: str) -> str:
        """비밀번호 해시화"""
        return hashlib.pbkdf2_hex(password.encode(), b'canvas_share_salt', 100000)
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """비밀번호 검증"""
        return self._hash_password(password) == password_hash
    
    def _validate_share_access(self, share: CanvasShare, access_request: ShareAccessRequest) -> Optional[str]:
        """공유 접근 권한 검증"""
        if share.visibility == ShareVisibility.PASSWORD_PROTECTED:
            if not access_request.password:
                return "SHARE_PASSWORD_REQUIRED"
            if not share.password_hash or not self._verify_password(access_request.password, share.password_hash):
                return "SHARE_PASSWORD_INCORRECT"
        
        elif share.visibility == ShareVisibility.USER_LIMITED:
            if not access_request.user_id:
                return "SHARE_PERMISSION_DENIED"
            if share.allowed_users and access_request.user_id not in share.allowed_users:
                return "SHARE_PERMISSION_DENIED"
        
        elif share.visibility == ShareVisibility.PRIVATE:
            # Private 링크는 creator만 접근 가능하다고 가정
            return "SHARE_PERMISSION_DENIED"
        
        return None
    
    def _get_canvas_data(self, canvas_id: UUID) -> Optional[Dict[str, Any]]:
        """Canvas 데이터 조회"""
        # 캐시에서 먼저 확인
        cache_key = f"canvas_data:{canvas_id}"
        cached_data = self.cache_manager.get(cache_key)
        if cached_data:
            return cached_data
        
        # image_history에서 canvas 관련 이미지들 조회
        images = self.db.query(ImageHistory).filter(
            and_(
                ImageHistory.canvas_id == canvas_id,
                ImageHistory.is_deleted == False
            )
        ).order_by(ImageHistory.canvas_version).all()
        
        if not images:
            return None
        
        # Canvas 데이터 구성
        canvas_data = {
            "canvas_id": str(canvas_id),
            "images": [],
            "layers": [],
            "elements": [],
            "metadata": {
                "total_versions": len(images),
                "created_at": images[0].created_at.isoformat() if images else None,
                "last_updated": images[-1].created_at.isoformat() if images else None
            }
        }
        
        for image in images:
            canvas_data["images"].append({
                "id": str(image.id),
                "version": image.canvas_version,
                "url": image.primary_image_url,
                "prompt": image.prompt,
                "style": image.style,
                "size": image.size,
                "created_at": image.created_at.isoformat(),
                "edit_mode": image.edit_mode
            })
        
        # 캐시에 저장 (5분)
        self.cache_manager.set(cache_key, canvas_data, ttl=300)
        
        return canvas_data
    
    def _record_visit(self, share: CanvasShare, visitor_info: Dict[str, Any], action_type: str):
        """방문 기록"""
        # 조회수 업데이트
        if action_type == "view":
            share.view_count += 1
            share.last_accessed_at = now_kst()
        elif action_type == "download":
            share.download_count += 1
        
        # 분석 기록 생성
        analytics = CanvasShareAnalytics(
            share_id=share.id,
            visitor_ip=visitor_info.get('ip'),
            visitor_country=visitor_info.get('country'),
            visitor_city=visitor_info.get('city'),
            visitor_user_agent=visitor_info.get('user_agent'),
            visitor_referrer=visitor_info.get('referrer'),
            action_type=action_type,
            session_id=visitor_info.get('session_id'),
            device_type=visitor_info.get('device_type'),
            browser=visitor_info.get('browser'),
            os=visitor_info.get('os')
        )
        
        self.db.add(analytics)
    
    def _generate_preview_image(self, canvas_id: UUID, first_image_url: Optional[str] = None) -> Optional[str]:
        """미리보기 이미지 생성"""
        if first_image_url:
            return self.og_service.generate_preview_thumbnail(first_image_url)
        
        # 첫 번째 이미지 URL이 없는 경우 DB에서 조회
        first_image = self.db.query(ImageHistory).filter(
            and_(
                ImageHistory.canvas_id == canvas_id,
                ImageHistory.is_deleted == False
            )
        ).first()
        
        if first_image:
            return self.og_service.generate_preview_thumbnail(first_image.primary_image_url)
        
        return None
    
    def _generate_og_image(
        self, 
        canvas_id: UUID, 
        title: Optional[str] = None,
        description: Optional[str] = None,
        canvas_image_url: Optional[str] = None,
        creator_id: Optional[str] = None
    ) -> Optional[str]:
        """Open Graph 이미지 생성"""
        return self.og_service.generate_og_image(
            canvas_id=canvas_id,
            title=title,
            description=description,
            canvas_image_url=canvas_image_url,
            creator_name=creator_id
        )
    
    def _to_share_response(self, share: CanvasShare) -> ShareResponse:
        """CanvasShare를 ShareResponse로 변환"""
        return ShareResponse(
            id=share.id,
            share_token=share.share_token,
            canvas_id=share.canvas_id,
            creator_id=share.creator_id,
            title=share.title,
            description=share.description,
            permission=share.permission,
            visibility=share.visibility,
            duration=share.duration,
            view_count=share.view_count,
            download_count=share.download_count,
            is_active=share.is_active,
            expires_at=share.expires_at,
            og_image_url=share.og_image_url,
            preview_image_url=share.preview_image_url,
            created_at=share.created_at,
            updated_at=share.updated_at,
            last_accessed_at=share.last_accessed_at,
            share_url=f"{settings.FRONTEND_URL}/shared/canvas/{share.share_token}",
            is_expired=share.is_expired(),
            is_view_limit_exceeded=share.is_view_limit_exceeded(),
            can_access=share.can_access()
        )
    
    # Analytics helper methods
    
    def _get_views_count(self, share_id: UUID, start_date: datetime, end_date: datetime) -> int:
        """특정 기간 조회수 조회"""
        return self.db.query(CanvasShareAnalytics).filter(
            and_(
                CanvasShareAnalytics.share_id == share_id,
                CanvasShareAnalytics.action_type == "view",
                CanvasShareAnalytics.created_at >= start_date,
                CanvasShareAnalytics.created_at < end_date
            )
        ).count()
    
    def _get_top_countries(self, share_id: UUID, limit: int = 10) -> List[Dict[str, Any]]:
        """상위 국가별 통계"""
        results = self.db.query(
            CanvasShareAnalytics.visitor_country,
            func.count().label('views')
        ).filter(
            and_(
                CanvasShareAnalytics.share_id == share_id,
                CanvasShareAnalytics.visitor_country.isnot(None)
            )
        ).group_by(CanvasShareAnalytics.visitor_country).order_by(desc('views')).limit(limit).all()
        
        return [{"country": r[0], "views": r[1]} for r in results]
    
    def _get_top_cities(self, share_id: UUID, limit: int = 10) -> List[Dict[str, Any]]:
        """상위 도시별 통계"""
        results = self.db.query(
            CanvasShareAnalytics.visitor_city,
            func.count().label('views')
        ).filter(
            and_(
                CanvasShareAnalytics.share_id == share_id,
                CanvasShareAnalytics.visitor_city.isnot(None)
            )
        ).group_by(CanvasShareAnalytics.visitor_city).order_by(desc('views')).limit(limit).all()
        
        return [{"city": r[0], "views": r[1]} for r in results]
    
    def _get_device_breakdown(self, share_id: UUID) -> Dict[str, int]:
        """디바이스별 통계"""
        results = self.db.query(
            CanvasShareAnalytics.device_type,
            func.count().label('views')
        ).filter(
            CanvasShareAnalytics.share_id == share_id
        ).group_by(CanvasShareAnalytics.device_type).all()
        
        return {r[0] or "unknown": r[1] for r in results}
    
    def _get_browser_breakdown(self, share_id: UUID) -> Dict[str, int]:
        """브라우저별 통계"""
        results = self.db.query(
            CanvasShareAnalytics.browser,
            func.count().label('views')
        ).filter(
            CanvasShareAnalytics.share_id == share_id
        ).group_by(CanvasShareAnalytics.browser).all()
        
        return {r[0] or "unknown": r[1] for r in results}
    
    def _get_os_breakdown(self, share_id: UUID) -> Dict[str, int]:
        """운영체제별 통계"""
        results = self.db.query(
            CanvasShareAnalytics.os,
            func.count().label('views')
        ).filter(
            CanvasShareAnalytics.share_id == share_id
        ).group_by(CanvasShareAnalytics.os).all()
        
        return {r[0] or "unknown": r[1] for r in results}
    
    def _get_referrer_breakdown(self, share_id: UUID) -> Dict[str, int]:
        """참조사이트별 통계"""
        results = self.db.query(
            CanvasShareAnalytics.visitor_referrer,
            func.count().label('views')
        ).filter(
            CanvasShareAnalytics.share_id == share_id
        ).group_by(CanvasShareAnalytics.visitor_referrer).all()
        
        return {r[0] or "direct": r[1] for r in results}
    
    def _get_daily_views(self, share_id: UUID, days: int) -> List[Dict[str, Any]]:
        """일별 조회수"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        results = self.db.query(
            func.date(CanvasShareAnalytics.created_at).label('date'),
            func.count().label('views')
        ).filter(
            and_(
                CanvasShareAnalytics.share_id == share_id,
                CanvasShareAnalytics.created_at >= start_date,
                CanvasShareAnalytics.action_type == "view"
            )
        ).group_by(func.date(CanvasShareAnalytics.created_at)).all()
        
        return [{"date": r[0].isoformat(), "views": r[1]} for r in results]
    
    def _get_hourly_views(self, share_id: UUID, date: datetime) -> List[Dict[str, Any]]:
        """시간별 조회수"""
        start_of_day = datetime.combine(date, datetime.min.time())
        end_of_day = start_of_day + timedelta(days=1)
        
        results = self.db.query(
            func.extract('hour', CanvasShareAnalytics.created_at).label('hour'),
            func.count().label('views')
        ).filter(
            and_(
                CanvasShareAnalytics.share_id == share_id,
                CanvasShareAnalytics.created_at >= start_of_day,
                CanvasShareAnalytics.created_at < end_of_day,
                CanvasShareAnalytics.action_type == "view"
            )
        ).group_by(func.extract('hour', CanvasShareAnalytics.created_at)).all()
        
        return [{"hour": int(r[0]), "views": r[1]} for r in results]