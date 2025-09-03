"""
Canvas v5.0 보안 API 엔드포인트

Canvas 보안 관리를 위한 REST API:
- 권한 관리 (권한 부여/회수)
- 보안 검증 (입력 데이터 sanitization)
- 감사 로그 조회
- 보안 설정 관리
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.security.canvas_security import (
    CanvasSecurityManager, get_canvas_security_manager,
    CanvasSecurityError, SecurityValidationError, AccessDeniedError
)
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# === Pydantic 모델 정의 ===

class CanvasPermissionRequest(BaseModel):
    """Canvas 권한 부여/회수 요청"""
    user_id: str = Field(..., description="권한을 부여받을 사용자 ID")
    canvas_id: str = Field(..., description="Canvas ID")
    permission_level: str = Field(..., description="권한 레벨 (owner, editor, collaborator, viewer)")

class CanvasPermissionResponse(BaseModel):
    """Canvas 권한 응답"""
    success: bool
    message: str
    canvas_id: str
    user_id: str
    permission_level: Optional[str] = None

class SecurityValidationRequest(BaseModel):
    """보안 검증 요청"""
    canvas_data: Dict[str, Any] = Field(..., description="검증할 Canvas 데이터")
    input_type: str = Field(default="canvas_data", description="입력 데이터 타입")

class SecurityValidationResponse(BaseModel):
    """보안 검증 응답"""
    success: bool
    message: str
    sanitized_data: Optional[Dict[str, Any]] = None
    security_warnings: List[str] = Field(default_factory=list)

class CanvasAuditLogQuery(BaseModel):
    """Canvas 감사 로그 조회 파라미터"""
    canvas_id: Optional[str] = None
    user_id: Optional[str] = None
    event_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=50, le=1000)

class CanvasAuditLog(BaseModel):
    """Canvas 감사 로그 항목"""
    timestamp: datetime
    event_type: str
    user_id: str
    canvas_id: Optional[str]
    severity: str
    details: Dict[str, Any]
    ip_address: str
    user_agent: str

class CanvasSecurityStatus(BaseModel):
    """Canvas 보안 상태"""
    canvas_id: str
    encryption_enabled: bool
    access_control_enabled: bool
    audit_logging_enabled: bool
    xss_protection_enabled: bool
    last_security_scan: Optional[datetime]
    security_score: int  # 0-100
    vulnerabilities: List[str] = Field(default_factory=list)

# === API 엔드포인트 ===

@router.post("/permissions/grant", response_model=CanvasPermissionResponse)
async def grant_canvas_permission(
    request: CanvasPermissionRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    security_manager: CanvasSecurityManager = Depends(get_canvas_security_manager)
) -> CanvasPermissionResponse:
    """
    Canvas 권한 부여
    
    소유자만 다른 사용자에게 권한을 부여할 수 있습니다.
    """
    try:
        owner_id = current_user["user_id"]
        
        # 권한 부여 실행
        success = security_manager.access_control.grant_canvas_permission(
            owner_id=owner_id,
            user_id=request.user_id,
            canvas_id=request.canvas_id,
            permission_level=request.permission_level
        )
        
        # 보안 감사 로깅
        security_manager.auditor.log_security_event(
            event_type='permission_granted',
            user_id=owner_id,
            canvas_id=request.canvas_id,
            details={
                'target_user': request.user_id,
                'permission_level': request.permission_level
            }
        )
        
        return CanvasPermissionResponse(
            success=success,
            message=f"권한이 성공적으로 부여되었습니다.",
            canvas_id=request.canvas_id,
            user_id=request.user_id,
            permission_level=request.permission_level
        )
        
    except AccessDeniedError as e:
        logger.warning(f"권한 부여 거부: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Canvas 권한을 부여할 권한이 없습니다."
        )
    except Exception as e:
        logger.error(f"권한 부여 중 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="권한 부여 처리 중 오류가 발생했습니다."
        )

@router.delete("/permissions/revoke", response_model=CanvasPermissionResponse)
async def revoke_canvas_permission(
    request: CanvasPermissionRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    security_manager: CanvasSecurityManager = Depends(get_canvas_security_manager)
) -> CanvasPermissionResponse:
    """
    Canvas 권한 회수
    
    소유자만 다른 사용자의 권한을 회수할 수 있습니다.
    """
    try:
        owner_id = current_user["user_id"]
        
        # 권한 회수 실행
        success = security_manager.access_control.revoke_canvas_permission(
            owner_id=owner_id,
            user_id=request.user_id,
            canvas_id=request.canvas_id
        )
        
        # 보안 감사 로깅
        security_manager.auditor.log_security_event(
            event_type='permission_revoked',
            user_id=owner_id,
            canvas_id=request.canvas_id,
            details={'target_user': request.user_id}
        )
        
        return CanvasPermissionResponse(
            success=success,
            message="권한이 성공적으로 회수되었습니다.",
            canvas_id=request.canvas_id,
            user_id=request.user_id
        )
        
    except AccessDeniedError as e:
        logger.warning(f"권한 회수 거부: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Canvas 권한을 회수할 권한이 없습니다."
        )
    except Exception as e:
        logger.error(f"권한 회수 중 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="권한 회수 처리 중 오류가 발생했습니다."
        )

@router.post("/validate", response_model=SecurityValidationResponse)
async def validate_canvas_data(
    request: SecurityValidationRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    security_manager: CanvasSecurityManager = Depends(get_canvas_security_manager)
) -> SecurityValidationResponse:
    """
    Canvas 데이터 보안 검증 및 sanitization
    
    XSS 방어, HTML 정화, 입력 검증을 수행합니다.
    """
    try:
        user_id = current_user["user_id"]
        security_warnings = []
        
        # 입력 데이터 검증 및 sanitization
        sanitized_data = security_manager.validate_and_sanitize_input(
            request.canvas_data, request.input_type
        )
        
        # 보안 경고 생성 (원본과 sanitized 데이터 비교)
        if request.canvas_data != sanitized_data:
            security_warnings.append("입력 데이터가 보안 정책에 따라 수정되었습니다.")
        
        # 감사 로깅
        security_manager.auditor.log_security_event(
            event_type='data_validation',
            user_id=user_id,
            details={
                'input_type': request.input_type,
                'warnings_count': len(security_warnings)
            }
        )
        
        return SecurityValidationResponse(
            success=True,
            message="보안 검증이 완료되었습니다.",
            sanitized_data=sanitized_data,
            security_warnings=security_warnings
        )
        
    except SecurityValidationError as e:
        logger.warning(f"보안 검증 실패: {e}")
        return SecurityValidationResponse(
            success=False,
            message=f"보안 검증 실패: {str(e)}",
            security_warnings=[str(e)]
        )
    except Exception as e:
        logger.error(f"보안 검증 중 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="보안 검증 처리 중 오류가 발생했습니다."
        )

@router.get("/audit-logs", response_model=List[CanvasAuditLog])
async def get_canvas_audit_logs(
    canvas_id: Optional[str] = None,
    user_id: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    security_manager: CanvasSecurityManager = Depends(get_canvas_security_manager)
) -> List[CanvasAuditLog]:
    """
    Canvas 보안 감사 로그 조회
    
    관리자 권한이 필요합니다.
    """
    try:
        requester_id = current_user["user_id"]
        
        # 관리자 권한 확인 (현재는 모든 사용자에게 허용, 실제로는 관리자만)
        # TODO: 실제 관리자 권한 체크 구현
        
        # 감사 로그 조회 (현재는 Mock 데이터 반환)
        # 실제 구현에서는 데이터베이스에서 조회
        audit_logs = [
            CanvasAuditLog(
                timestamp=datetime.now(timezone.utc),
                event_type="canvas_access",
                user_id=requester_id,
                canvas_id=canvas_id,
                severity="info",
                details={"operation": "view"},
                ip_address="127.0.0.1",
                user_agent="Canvas-Client/5.0"
            )
        ]
        
        # 요청 로깅
        security_manager.auditor.log_security_event(
            event_type='audit_log_access',
            user_id=requester_id,
            details={
                'requested_canvas_id': canvas_id,
                'requested_user_id': user_id,
                'requested_event_type': event_type,
                'limit': limit
            }
        )
        
        return audit_logs
        
    except Exception as e:
        logger.error(f"감사 로그 조회 중 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="감사 로그 조회 중 오류가 발생했습니다."
        )

@router.get("/status/{canvas_id}", response_model=CanvasSecurityStatus)
async def get_canvas_security_status(
    canvas_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    security_manager: CanvasSecurityManager = Depends(get_canvas_security_manager)
) -> CanvasSecurityStatus:
    """
    Canvas 보안 상태 조회
    
    Canvas의 전반적인 보안 설정 및 상태를 확인합니다.
    """
    try:
        user_id = current_user["user_id"]
        
        # Canvas 액세스 권한 확인
        if not security_manager.access_control.check_canvas_permission(
            user_id, canvas_id, 'view'
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Canvas 조회 권한이 없습니다."
            )
        
        # 보안 상태 계산 (현재는 Mock 데이터)
        security_status = CanvasSecurityStatus(
            canvas_id=canvas_id,
            encryption_enabled=True,
            access_control_enabled=True,
            audit_logging_enabled=True,
            xss_protection_enabled=True,
            last_security_scan=datetime.now(timezone.utc),
            security_score=95,  # 높은 보안 점수
            vulnerabilities=[]
        )
        
        # 상태 조회 로깅
        security_manager.auditor.log_security_event(
            event_type='security_status_check',
            user_id=user_id,
            canvas_id=canvas_id,
            details={'security_score': security_status.security_score}
        )
        
        return security_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"보안 상태 조회 중 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="보안 상태 조회 중 오류가 발생했습니다."
        )

@router.post("/encrypt")
async def encrypt_canvas_data(
    canvas_data: Dict[str, Any],
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    security_manager: CanvasSecurityManager = Depends(get_canvas_security_manager)
) -> Dict[str, str]:
    """
    Canvas 데이터 암호화
    
    민감한 Canvas 데이터를 AES-256으로 암호화합니다.
    """
    try:
        user_id = current_user["user_id"]
        
        # 데이터 암호화
        encrypted_data = security_manager.encrypt_sensitive_canvas_data(canvas_data)
        
        # 암호화 로깅
        security_manager.auditor.log_security_event(
            event_type='data_encrypted',
            user_id=user_id,
            details={'data_size_bytes': len(str(canvas_data))}
        )
        
        return {
            "success": True,
            "message": "데이터가 성공적으로 암호화되었습니다.",
            "encrypted_data": encrypted_data
        }
        
    except Exception as e:
        logger.error(f"데이터 암호화 중 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="데이터 암호화 중 오류가 발생했습니다."
        )

@router.post("/decrypt")
async def decrypt_canvas_data(
    encrypted_data: str,
    canvas_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    security_manager: CanvasSecurityManager = Depends(get_canvas_security_manager)
) -> Dict[str, Any]:
    """
    Canvas 데이터 복호화
    
    암호화된 Canvas 데이터를 복호화합니다. (권한 확인 포함)
    """
    try:
        user_id = current_user["user_id"]
        
        # 권한 확인 및 데이터 복호화
        decrypted_data = security_manager.decrypt_canvas_data(
            encrypted_data, user_id, canvas_id
        )
        
        return {
            "success": True,
            "message": "데이터가 성공적으로 복호화되었습니다.",
            "decrypted_data": decrypted_data
        }
        
    except AccessDeniedError as e:
        logger.warning(f"복호화 권한 거부: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="데이터 복호화 권한이 없습니다."
        )
    except Exception as e:
        logger.error(f"데이터 복호화 중 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="데이터 복호화 중 오류가 발생했습니다."
        )