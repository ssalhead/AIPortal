"""
Canvas 공유 API 엔드포인트
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.canvas_share_models import (
    CreateShareRequest, UpdateShareRequest, ShareResponse,
    ShareAnalyticsResponse, ShareAccessRequest, ShareAccessResponse,
    ShareReportRequest, ShareReportResponse, SocialShareData,
    ShareErrorResponse
)
from app.services.canvas_share_service import CanvasShareService
from app.core.config import settings


router = APIRouter(prefix="/canvas/share", tags=["Canvas Share"])


def get_visitor_info(request: Request) -> Dict[str, Any]:
    """방문자 정보 추출"""
    user_agent = request.headers.get("user-agent", "")
    
    # 간단한 디바이스/브라우저 감지 (실제로는 user-agents 라이브러리 사용 권장)
    device_type = "desktop"
    if "mobile" in user_agent.lower():
        device_type = "mobile"
    elif "tablet" in user_agent.lower():
        device_type = "tablet"
    
    browser = "unknown"
    if "chrome" in user_agent.lower():
        browser = "chrome"
    elif "firefox" in user_agent.lower():
        browser = "firefox"
    elif "safari" in user_agent.lower():
        browser = "safari"
    elif "edge" in user_agent.lower():
        browser = "edge"
    
    os = "unknown"
    if "windows" in user_agent.lower():
        os = "windows"
    elif "mac" in user_agent.lower():
        os = "macos"
    elif "linux" in user_agent.lower():
        os = "linux"
    elif "android" in user_agent.lower():
        os = "android"
    elif "ios" in user_agent.lower():
        os = "ios"
    
    return {
        "ip": request.client.host,
        "user_agent": user_agent,
        "device_type": device_type,
        "browser": browser,
        "os": os,
        "referrer": request.headers.get("referer"),
        "session_id": request.session.get("session_id") if hasattr(request, 'session') else None
    }


@router.post("/create", response_model=ShareResponse)
async def create_share(
    request: CreateShareRequest,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """공유 링크 생성"""
    try:
        service = CanvasShareService(db)
        return service.create_share(request, current_user["sub"])
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create share link"
        )


@router.get("/{share_token}", response_model=ShareResponse)
async def get_share(
    share_token: str,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """공유 링크 조회 (소유자만)"""
    service = CanvasShareService(db)
    share = service.get_share(share_token)
    
    if not share:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found"
        )
    
    # 소유자 확인
    if share.creator_id != current_user["sub"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return share


@router.put("/{share_token}", response_model=ShareResponse)
async def update_share(
    share_token: str,
    request: UpdateShareRequest,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """공유 링크 수정"""
    service = CanvasShareService(db)
    share = service.update_share(share_token, request, current_user["sub"])
    
    if not share:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found or access denied"
        )
    
    return share


@router.delete("/{share_token}")
async def delete_share(
    share_token: str,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """공유 링크 삭제"""
    service = CanvasShareService(db)
    success = service.delete_share(share_token, current_user["sub"])
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found or access denied"
        )
    
    return {"message": "Share deleted successfully"}


@router.get("/user/shares", response_model=List[ShareResponse])
async def get_user_shares(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """사용자의 공유 링크 목록 조회"""
    service = CanvasShareService(db)
    return service.get_user_shares(current_user["sub"], limit, offset)


@router.get("/canvas/{canvas_id}/shares", response_model=List[ShareResponse])
async def get_canvas_shares(
    canvas_id: UUID,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """특정 Canvas의 공유 링크 목록 조회"""
    service = CanvasShareService(db)
    return service.get_canvas_shares(canvas_id, current_user["sub"])


@router.get("/{share_token}/analytics", response_model=ShareAnalyticsResponse)
async def get_share_analytics(
    share_token: str,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """공유 링크 분석 데이터 조회"""
    service = CanvasShareService(db)
    analytics = service.get_share_analytics(share_token, current_user["sub"])
    
    if not analytics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found or access denied"
        )
    
    return analytics


# 공용 엔드포인트 (인증 불필요)

@router.post("/access/{share_token}", response_model=ShareAccessResponse)
async def access_shared_canvas(
    share_token: str,
    access_request: ShareAccessRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """공유 Canvas 접근"""
    service = CanvasShareService(db)
    visitor_info = get_visitor_info(request)
    
    response, error = service.access_share(share_token, access_request, visitor_info)
    
    if error:
        error_messages = {
            "SHARE_NOT_FOUND": "Share link not found",
            "SHARE_EXPIRED": "Share link has expired",
            "SHARE_VIEW_LIMIT_EXCEEDED": "Share link view limit exceeded",
            "SHARE_INACTIVE": "Share link is inactive",
            "SHARE_PASSWORD_REQUIRED": "Password required",
            "SHARE_PASSWORD_INCORRECT": "Incorrect password",
            "SHARE_PERMISSION_DENIED": "Access denied",
            "SHARE_CANVAS_NOT_FOUND": "Canvas not found"
        }
        
        status_codes = {
            "SHARE_NOT_FOUND": status.HTTP_404_NOT_FOUND,
            "SHARE_EXPIRED": status.HTTP_410_GONE,
            "SHARE_VIEW_LIMIT_EXCEEDED": status.HTTP_429_TOO_MANY_REQUESTS,
            "SHARE_INACTIVE": status.HTTP_410_GONE,
            "SHARE_PASSWORD_REQUIRED": status.HTTP_401_UNAUTHORIZED,
            "SHARE_PASSWORD_INCORRECT": status.HTTP_401_UNAUTHORIZED,
            "SHARE_PERMISSION_DENIED": status.HTTP_403_FORBIDDEN,
            "SHARE_CANVAS_NOT_FOUND": status.HTTP_404_NOT_FOUND
        }
        
        raise HTTPException(
            status_code=status_codes.get(error, status.HTTP_400_BAD_REQUEST),
            detail=ShareErrorResponse(
                error_code=error,
                message=error_messages.get(error, "Access denied")
            ).dict()
        )
    
    return response


@router.get("/public/{share_token}/info")
async def get_public_share_info(
    share_token: str,
    db: Session = Depends(get_db)
):
    """공유 링크 공개 정보 조회 (소셜 미디어용)"""
    service = CanvasShareService(db)
    share = service.get_share(share_token)
    
    if not share or not share.can_access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found or inactive"
        )
    
    return {
        "title": share.title or "Untitled Canvas",
        "description": share.description or "View this Canvas creation",
        "preview_image_url": share.preview_image_url,
        "created_at": share.created_at,
        "creator_id": share.creator_id if share.visibility.value == "public" else None
    }


@router.get("/public/{share_token}/social", response_model=SocialShareData)
async def get_social_share_data(
    share_token: str,
    db: Session = Depends(get_db)
):
    """소셜 미디어 공유 메타데이터"""
    service = CanvasShareService(db)
    social_data = service.get_social_share_data(share_token)
    
    if not social_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found or inactive"
        )
    
    return social_data


@router.post("/{share_token}/report", response_model=Dict[str, str])
async def report_share(
    share_token: str,
    report_request: ShareReportRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """공유 신고"""
    service = CanvasShareService(db)
    visitor_info = get_visitor_info(request)
    
    report_id = service.report_share(share_token, report_request, visitor_info)
    
    if not report_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found"
        )
    
    return {"message": "Report submitted successfully", "report_id": report_id}


@router.post("/{share_token}/download")
async def track_download(
    share_token: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """다운로드 추적 (실제 파일 다운로드는 프론트엔드에서 처리)"""
    service = CanvasShareService(db)
    visitor_info = get_visitor_info(request)
    
    share = service.get_share(share_token)
    if not share or not share.can_access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found or inactive"
        )
    
    # 다운로드 권한 확인
    if share.permission.value == "read_only":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Download not allowed"
        )
    
    # 다운로드 추적
    service._record_visit(
        service.db.query(service.db_model.CanvasShare).filter(
            service.db_model.CanvasShare.share_token == share_token
        ).first(),
        visitor_info,
        "download"
    )
    service.db.commit()
    
    return {"message": "Download tracked"}


# HTML 렌더링 엔드포인트 (소셜 미디어 크롤러용)

@router.get("/public/{share_token}/embed", response_class=Response)
async def get_share_embed_html(
    share_token: str,
    db: Session = Depends(get_db)
):
    """공유 Canvas 임베드 HTML (소셜 미디어 크롤러용)"""
    service = CanvasShareService(db)
    social_data = service.get_social_share_data(share_token)
    
    if not social_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found"
        )
    
    # 간단한 HTML 페이지 생성 (소셜 미디어 메타태그 포함)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{social_data.og.title}</title>
        <meta name="description" content="{social_data.og.description or ''}">
        
        <!-- Open Graph -->
        <meta property="og:title" content="{social_data.og.title}">
        <meta property="og:description" content="{social_data.og.description or ''}">
        <meta property="og:image" content="{social_data.og.image or ''}">
        <meta property="og:url" content="{social_data.og.url}">
        <meta property="og:type" content="{social_data.og.type}">
        <meta property="og:site_name" content="{social_data.og.site_name}">
        
        <!-- Twitter Card -->
        <meta name="twitter:card" content="{social_data.twitter.card}">
        <meta name="twitter:title" content="{social_data.twitter.title}">
        <meta name="twitter:description" content="{social_data.twitter.description or ''}">
        <meta name="twitter:image" content="{social_data.twitter.image or ''}">
        <meta name="twitter:site" content="{social_data.twitter.site}">
        
        <script>
            // 실제 뷰어 페이지로 리디렉션
            window.location.href = "{settings.FRONTEND_URL}/shared/canvas/{share_token}";
        </script>
    </head>
    <body>
        <h1>{social_data.og.title}</h1>
        <p>{social_data.og.description or ''}</p>
        <p><a href="{settings.FRONTEND_URL}/shared/canvas/{share_token}">View Canvas</a></p>
    </body>
    </html>
    """
    
    return Response(content=html_content, media_type="text/html")