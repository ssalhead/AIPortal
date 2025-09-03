"""
Canvas v5.0 보안 강화 시스템

엔터프라이즈급 Canvas 보안을 위한 포괄적인 보안 서비스:
- AES-256 데이터 암호화
- XSS/HTML 인젝션 방어
- Canvas 데이터 검증 및 sanitization
- 액세스 제어 및 권한 관리
- 보안 감사 로깅
"""

import re
import json
import base64
import hashlib
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timezone
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import bleach
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session

from ..models.canvas_models import CanvasData, KonvaNodeData, KonvaLayerData
from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class CanvasSecurityError(Exception):
    """Canvas 보안 관련 예외"""
    pass

class SecurityValidationError(CanvasSecurityError):
    """보안 검증 실패 예외"""
    pass

class AccessDeniedError(CanvasSecurityError):
    """액세스 거부 예외"""
    pass

class CanvasEncryptionService:
    """Canvas 데이터 암호화 서비스 (AES-256)"""
    
    def __init__(self, master_key: Optional[str] = None):
        """
        암호화 서비스 초기화
        
        Args:
            master_key: 마스터 암호화 키 (없으면 환경변수에서 가져옴)
        """
        self.master_key = master_key or settings.CANVAS_ENCRYPTION_KEY
        if not self.master_key:
            raise CanvasSecurityError("Canvas 암호화 키가 설정되지 않았습니다.")
        
        # PBKDF2로 키 유도
        salt = b'canvas_v5_salt_2025'  # 프로덕션에서는 랜덤 salt 사용
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # AES-256
            salt=salt,
            iterations=100000,
        )
        key = kdf.derive(self.master_key.encode())
        self.cipher = Fernet(base64.urlsafe_b64encode(key))
        
        logger.info("Canvas 암호화 서비스 초기화 완료")

    def encrypt_canvas_data(self, data: Dict[str, Any]) -> str:
        """Canvas 데이터 암호화"""
        try:
            json_data = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
            encrypted_bytes = self.cipher.encrypt(json_data.encode('utf-8'))
            return base64.urlsafe_b64encode(encrypted_bytes).decode('ascii')
        except Exception as e:
            logger.error(f"Canvas 데이터 암호화 실패: {e}")
            raise CanvasSecurityError(f"암호화 실패: {e}")

    def decrypt_canvas_data(self, encrypted_data: str) -> Dict[str, Any]:
        """Canvas 데이터 복호화"""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode('ascii'))
            decrypted_bytes = self.cipher.decrypt(encrypted_bytes)
            json_data = decrypted_bytes.decode('utf-8')
            return json.loads(json_data)
        except Exception as e:
            logger.error(f"Canvas 데이터 복호화 실패: {e}")
            raise CanvasSecurityError(f"복호화 실패: {e}")

    def encrypt_sensitive_field(self, value: str) -> str:
        """민감한 필드 개별 암호화"""
        try:
            encrypted_bytes = self.cipher.encrypt(value.encode('utf-8'))
            return base64.urlsafe_b64encode(encrypted_bytes).decode('ascii')
        except Exception as e:
            raise CanvasSecurityError(f"필드 암호화 실패: {e}")

    def decrypt_sensitive_field(self, encrypted_value: str) -> str:
        """민감한 필드 개별 복호화"""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_value.encode('ascii'))
            decrypted_bytes = self.cipher.decrypt(encrypted_bytes)
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            raise CanvasSecurityError(f"필드 복호화 실패: {e}")

class CanvasXSSProtection:
    """Canvas XSS 및 HTML 인젝션 방어 시스템"""
    
    # 허용된 HTML 태그 (Canvas 텍스트 편집용)
    ALLOWED_TAGS = [
        'p', 'br', 'span', 'div', 'strong', 'em', 'u', 'i', 'b',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li', 'blockquote'
    ]
    
    # 허용된 HTML 속성
    ALLOWED_ATTRIBUTES = {
        '*': ['style', 'class'],
        'span': ['data-*'],
        'div': ['data-*']
    }
    
    # 허용된 CSS 속성 (인라인 스타일용)
    ALLOWED_STYLES = [
        'color', 'background-color', 'font-size', 'font-family', 'font-weight',
        'text-align', 'text-decoration', 'margin', 'padding',
        'border', 'border-radius', 'width', 'height'
    ]
    
    # 위험한 패턴 감지 정규식
    DANGEROUS_PATTERNS = [
        r'javascript:', r'vbscript:', r'data:', r'about:',
        r'on\w+\s*=', r'<script', r'</script>', r'<iframe', r'</iframe>',
        r'eval\s*\(', r'setTimeout\s*\(', r'setInterval\s*\(',
        r'document\.(write|cookie)', r'window\.(location|open)',
        r'<link', r'<meta', r'<style.*?>.*?</style>'
    ]
    
    def __init__(self):
        """XSS 방어 시스템 초기화"""
        self.bleach_cleaner = bleach.Cleaner(
            tags=self.ALLOWED_TAGS,
            attributes=self.ALLOWED_ATTRIBUTES,
            styles=self.ALLOWED_STYLES,
            strip=True,
            strip_comments=True
        )
        logger.info("Canvas XSS 방어 시스템 초기화 완료")

    def sanitize_html_content(self, content: str) -> str:
        """HTML 콘텐츠 sanitization"""
        if not content:
            return ""
        
        # 1단계: 위험한 패턴 사전 제거
        sanitized = self._remove_dangerous_patterns(content)
        
        # 2단계: bleach로 HTML 정화
        sanitized = self.bleach_cleaner.clean(sanitized)
        
        # 3단계: 추가 검증
        if self._contains_suspicious_content(sanitized):
            logger.warning(f"의심스러운 콘텐츠 감지: {content[:100]}...")
            raise SecurityValidationError("위험한 콘텐츠가 감지되었습니다.")
        
        return sanitized

    def sanitize_text_content(self, content: str) -> str:
        """순수 텍스트 콘텐츠 sanitization"""
        if not content:
            return ""
        
        # HTML 태그 완전 제거
        sanitized = bleach.clean(content, tags=[], strip=True)
        
        # 특수 문자 이스케이프
        sanitized = self._escape_special_characters(sanitized)
        
        return sanitized

    def validate_konva_attributes(self, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Konva.js 속성 검증 및 sanitization"""
        sanitized_attrs = {}
        
        for key, value in attributes.items():
            # 속성명 검증
            if not self._is_valid_konva_attribute(key):
                logger.warning(f"유효하지 않은 Konva 속성: {key}")
                continue
            
            # 속성값 sanitization
            if isinstance(value, str):
                if key in ['text', 'fontFamily']:
                    sanitized_value = self.sanitize_text_content(value)
                else:
                    sanitized_value = self._sanitize_attribute_value(value)
            else:
                sanitized_value = self._validate_non_string_attribute(key, value)
            
            sanitized_attrs[key] = sanitized_value
        
        return sanitized_attrs

    def _remove_dangerous_patterns(self, content: str) -> str:
        """위험한 패턴 제거"""
        for pattern in self.DANGEROUS_PATTERNS:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        return content

    def _contains_suspicious_content(self, content: str) -> bool:
        """의심스러운 콘텐츠 감지"""
        suspicious_keywords = [
            'javascript', 'vbscript', 'onload', 'onerror', 'onclick',
            'eval(', 'setTimeout(', 'document.cookie', 'window.location'
        ]
        
        content_lower = content.lower()
        return any(keyword in content_lower for keyword in suspicious_keywords)

    def _escape_special_characters(self, content: str) -> str:
        """특수 문자 이스케이프"""
        escape_map = {
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#x27;',
            '&': '&amp;'
        }
        
        for char, escaped in escape_map.items():
            content = content.replace(char, escaped)
        return content

    def _is_valid_konva_attribute(self, attr_name: str) -> bool:
        """Konva 속성명 유효성 검증"""
        valid_attributes = {
            # 기본 속성
            'x', 'y', 'width', 'height', 'visible', 'listening', 'id', 'name',
            'opacity', 'scale', 'scaleX', 'scaleY', 'rotation', 'offset', 'offsetX', 'offsetY',
            'draggable', 'dragBoundFunc', 'dragDistance', 'dragOnTop',
            
            # 텍스트 속성
            'text', 'fontFamily', 'fontSize', 'fontStyle', 'fontVariant',
            'textDecoration', 'align', 'verticalAlign', 'padding', 'lineHeight',
            'letterSpacing', 'wrap', 'ellipsis',
            
            # 스타일 속성
            'fill', 'stroke', 'strokeWidth', 'strokeScaleEnabled', 'strokeHitEnabled',
            'perfectDrawEnabled', 'shadowForStrokeEnabled', 'strokeLineCap',
            'strokeLineJoin', 'strokeMiterLimit', 'dash', 'dashOffset',
            
            # 그림자 속성
            'shadowColor', 'shadowBlur', 'shadowOffset', 'shadowOffsetX', 'shadowOffsetY',
            'shadowOpacity', 'shadowEnabled',
            
            # 필터 속성
            'filters', 'cache', 'clearBeforeDraw', 'hitStrokeWidth'
        }
        
        return attr_name in valid_attributes

    def _sanitize_attribute_value(self, value: str) -> str:
        """속성값 sanitization"""
        # 기본적인 특수문자 제거
        sanitized = re.sub(r'[<>"\']', '', value)
        
        # 스크립트 관련 키워드 제거
        dangerous_keywords = ['javascript:', 'vbscript:', 'data:', 'eval(']
        for keyword in dangerous_keywords:
            sanitized = sanitized.replace(keyword, '')
        
        return sanitized.strip()

    def _validate_non_string_attribute(self, key: str, value: Any) -> Any:
        """비문자열 속성 검증"""
        # 숫자 타입 검증
        if key in ['x', 'y', 'width', 'height', 'fontSize', 'opacity', 'rotation']:
            if not isinstance(value, (int, float)):
                raise SecurityValidationError(f"속성 '{key}'는 숫자여야 합니다.")
            
            # 합리적인 범위 검증
            if key in ['width', 'height'] and (value < 0 or value > 10000):
                raise SecurityValidationError(f"속성 '{key}' 값이 허용 범위를 벗어났습니다.")
            elif key == 'opacity' and not (0 <= value <= 1):
                raise SecurityValidationError("opacity는 0-1 사이의 값이어야 합니다.")
        
        # 배열 타입 검증
        if key in ['dash', 'filters'] and isinstance(value, list):
            if len(value) > 20:  # 배열 크기 제한
                raise SecurityValidationError(f"배열 속성 '{key}' 크기가 너무 큽니다.")
        
        return value

class CanvasAccessControl:
    """Canvas 액세스 제어 및 권한 관리"""
    
    # Canvas 권한 레벨
    PERMISSION_LEVELS = {
        'owner': 100,      # 모든 권한 (삭제, 공유 설정 변경 등)
        'editor': 80,      # 편집 권한 (내용 수정, 요소 추가/제거)
        'collaborator': 60, # 협업 권한 (제한적 편집, 댓글)
        'viewer': 40,      # 읽기 권한 (보기만 가능)
        'none': 0          # 액세스 거부
    }
    
    # 작업별 필요 권한 레벨
    OPERATION_PERMISSIONS = {
        'view': 40,
        'edit_text': 60,
        'add_element': 60,
        'delete_element': 80,
        'modify_structure': 80,
        'share': 100,
        'delete_canvas': 100,
        'change_permissions': 100
    }

    def __init__(self, db: Session):
        """액세스 제어 시스템 초기화"""
        self.db = db
        logger.info("Canvas 액세스 제어 시스템 초기화 완료")

    def check_canvas_permission(self, user_id: str, canvas_id: str, 
                              required_operation: str) -> bool:
        """Canvas 작업 권한 확인"""
        try:
            # 사용자의 Canvas 권한 레벨 조회
            user_permission = self._get_user_canvas_permission(user_id, canvas_id)
            
            # 필요한 권한 레벨 확인
            required_level = self.OPERATION_PERMISSIONS.get(required_operation, 100)
            
            has_permission = user_permission >= required_level
            
            if not has_permission:
                logger.warning(
                    f"권한 부족: user_id={user_id}, canvas_id={canvas_id}, "
                    f"operation={required_operation}, user_level={user_permission}, "
                    f"required_level={required_level}"
                )
            
            return has_permission
            
        except Exception as e:
            logger.error(f"권한 확인 중 오류: {e}")
            return False

    def validate_canvas_owner(self, user_id: str, canvas_id: str) -> bool:
        """Canvas 소유자 확인"""
        return self.check_canvas_permission(user_id, canvas_id, 'delete_canvas')

    def get_user_canvas_list(self, user_id: str) -> List[Dict[str, Any]]:
        """사용자가 액세스 가능한 Canvas 목록 조회"""
        # 실제 구현에서는 데이터베이스 쿼리
        # 현재는 기본 구조만 제공
        return []

    def grant_canvas_permission(self, owner_id: str, user_id: str, 
                              canvas_id: str, permission_level: str) -> bool:
        """Canvas 권한 부여 (소유자만 가능)"""
        if not self.validate_canvas_owner(owner_id, canvas_id):
            raise AccessDeniedError("Canvas 권한을 부여할 권한이 없습니다.")
        
        if permission_level not in self.PERMISSION_LEVELS:
            raise SecurityValidationError("유효하지 않은 권한 레벨입니다.")
        
        # 실제 구현에서는 데이터베이스에 권한 저장
        logger.info(
            f"Canvas 권한 부여: owner={owner_id}, user={user_id}, "
            f"canvas={canvas_id}, level={permission_level}"
        )
        return True

    def revoke_canvas_permission(self, owner_id: str, user_id: str, 
                               canvas_id: str) -> bool:
        """Canvas 권한 회수"""
        if not self.validate_canvas_owner(owner_id, canvas_id):
            raise AccessDeniedError("Canvas 권한을 회수할 권한이 없습니다.")
        
        # 실제 구현에서는 데이터베이스에서 권한 제거
        logger.info(f"Canvas 권한 회수: owner={owner_id}, user={user_id}, canvas={canvas_id}")
        return True

    def _get_user_canvas_permission(self, user_id: str, canvas_id: str) -> int:
        """사용자의 Canvas 권한 레벨 조회"""
        # 실제 구현에서는 데이터베이스 쿼리
        # 현재는 임시로 editor 권한 반환
        return self.PERMISSION_LEVELS['editor']

class CanvasSecurityAuditor:
    """Canvas 보안 감사 및 로깅 시스템"""
    
    def __init__(self, db: Session):
        """보안 감사 시스템 초기화"""
        self.db = db
        self.audit_logger = logging.getLogger('canvas_security_audit')
        logger.info("Canvas 보안 감사 시스템 초기화 완료")

    def log_security_event(self, event_type: str, user_id: str, 
                          canvas_id: Optional[str] = None, 
                          details: Optional[Dict[str, Any]] = None,
                          severity: str = 'info'):
        """보안 이벤트 로깅"""
        audit_record = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'event_type': event_type,
            'user_id': user_id,
            'canvas_id': canvas_id,
            'severity': severity,
            'details': details or {},
            'ip_address': self._get_client_ip(),  # 실제 구현 시 request에서 추출
            'user_agent': self._get_user_agent()   # 실제 구현 시 request에서 추출
        }
        
        # 심각도에 따른 로그 레벨 결정
        if severity == 'critical':
            self.audit_logger.critical(json.dumps(audit_record, ensure_ascii=False))
        elif severity == 'warning':
            self.audit_logger.warning(json.dumps(audit_record, ensure_ascii=False))
        else:
            self.audit_logger.info(json.dumps(audit_record, ensure_ascii=False))
        
        # 데이터베이스에도 저장 (실제 구현 시)
        self._store_audit_record(audit_record)

    def log_access_attempt(self, user_id: str, canvas_id: str, 
                          operation: str, success: bool):
        """Canvas 액세스 시도 로깅"""
        self.log_security_event(
            event_type='canvas_access',
            user_id=user_id,
            canvas_id=canvas_id,
            details={
                'operation': operation,
                'success': success
            },
            severity='warning' if not success else 'info'
        )

    def log_data_modification(self, user_id: str, canvas_id: str, 
                            modification_type: str, element_count: int):
        """Canvas 데이터 수정 로깅"""
        self.log_security_event(
            event_type='canvas_modification',
            user_id=user_id,
            canvas_id=canvas_id,
            details={
                'modification_type': modification_type,
                'element_count': element_count
            }
        )

    def log_suspicious_activity(self, user_id: str, activity_description: str, 
                              risk_level: str = 'medium'):
        """의심스러운 활동 로깅"""
        self.log_security_event(
            event_type='suspicious_activity',
            user_id=user_id,
            details={
                'activity': activity_description,
                'risk_level': risk_level
            },
            severity='warning'
        )

    def _get_client_ip(self) -> str:
        """클라이언트 IP 주소 조회 (실제 구현 시 FastAPI Request에서 추출)"""
        return "127.0.0.1"  # 임시

    def _get_user_agent(self) -> str:
        """사용자 에이전트 조회 (실제 구현 시 FastAPI Request에서 추출)"""
        return "Canvas-Client/5.0"  # 임시

    def _store_audit_record(self, record: Dict[str, Any]):
        """감사 기록 데이터베이스 저장"""
        # 실제 구현에서는 audit_logs 테이블에 저장
        pass

class CanvasSecurityManager:
    """Canvas v5.0 통합 보안 관리자"""
    
    def __init__(self, db: Session, encryption_key: Optional[str] = None):
        """통합 보안 관리자 초기화"""
        self.db = db
        self.encryption_service = CanvasEncryptionService(encryption_key)
        self.xss_protection = CanvasXSSProtection()
        self.access_control = CanvasAccessControl(db)
        self.auditor = CanvasSecurityAuditor(db)
        
        logger.info("Canvas 통합 보안 관리자 초기화 완료")

    def secure_canvas_data(self, canvas_data: CanvasData, user_id: str) -> CanvasData:
        """Canvas 데이터 종합 보안 처리"""
        try:
            # 1. 액세스 권한 확인
            if not self.access_control.check_canvas_permission(
                user_id, canvas_data.canvas_id, 'edit_text'
            ):
                raise AccessDeniedError("Canvas 편집 권한이 없습니다.")
            
            # 2. XSS 방어 및 데이터 sanitization
            secured_data = self._sanitize_canvas_data(canvas_data)
            
            # 3. 보안 이벤트 로깅
            self.auditor.log_data_modification(
                user_id=user_id,
                canvas_id=canvas_data.canvas_id,
                modification_type='data_update',
                element_count=len(secured_data.layers)
            )
            
            return secured_data
            
        except Exception as e:
            self.auditor.log_security_event(
                event_type='security_error',
                user_id=user_id,
                canvas_id=canvas_data.canvas_id,
                details={'error': str(e)},
                severity='warning'
            )
            raise

    def encrypt_sensitive_canvas_data(self, canvas_data: Dict[str, Any]) -> str:
        """민감한 Canvas 데이터 암호화"""
        return self.encryption_service.encrypt_canvas_data(canvas_data)

    def decrypt_canvas_data(self, encrypted_data: str, user_id: str, 
                          canvas_id: str) -> Dict[str, Any]:
        """Canvas 데이터 복호화 (권한 확인 포함)"""
        # 액세스 권한 확인
        if not self.access_control.check_canvas_permission(user_id, canvas_id, 'view'):
            self.auditor.log_access_attempt(user_id, canvas_id, 'decrypt', False)
            raise AccessDeniedError("Canvas 조회 권한이 없습니다.")
        
        self.auditor.log_access_attempt(user_id, canvas_id, 'decrypt', True)
        return self.encryption_service.decrypt_canvas_data(encrypted_data)

    def validate_and_sanitize_input(self, user_input: Dict[str, Any], 
                                  input_type: str = 'canvas_data') -> Dict[str, Any]:
        """사용자 입력 검증 및 sanitization"""
        if input_type == 'canvas_data':
            return self._sanitize_canvas_input(user_input)
        elif input_type == 'text_content':
            return {'content': self.xss_protection.sanitize_text_content(
                user_input.get('content', '')
            )}
        else:
            raise SecurityValidationError("지원하지 않는 입력 타입입니다.")

    def _sanitize_canvas_data(self, canvas_data: CanvasData) -> CanvasData:
        """Canvas 데이터 전체 sanitization"""
        sanitized_layers = []
        
        for layer in canvas_data.layers:
            sanitized_nodes = []
            
            for node in layer.children:
                # Konva 속성 검증 및 sanitization
                sanitized_attrs = self.xss_protection.validate_konva_attributes(
                    node.attrs
                )
                
                # 텍스트 노드의 경우 특별 처리
                if node.className == 'Text' and 'text' in sanitized_attrs:
                    sanitized_attrs['text'] = self.xss_protection.sanitize_text_content(
                        sanitized_attrs['text']
                    )
                
                # 새로운 노드 생성
                sanitized_node = KonvaNodeData(
                    className=node.className,
                    attrs=sanitized_attrs,
                    children=node.children  # 자식 노드는 재귀적으로 처리 (필요시)
                )
                sanitized_nodes.append(sanitized_node)
            
            # 새로운 레이어 생성
            sanitized_layer = KonvaLayerData(
                attrs=self.xss_protection.validate_konva_attributes(layer.attrs),
                className=layer.className,
                children=sanitized_nodes
            )
            sanitized_layers.append(sanitized_layer)
        
        # 새로운 Canvas 데이터 반환
        return CanvasData(
            canvas_id=canvas_data.canvas_id,
            width=canvas_data.width,
            height=canvas_data.height,
            layers=sanitized_layers
        )

    def _sanitize_canvas_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Canvas 입력 데이터 sanitization"""
        sanitized = {}
        
        for key, value in input_data.items():
            if key in ['title', 'description', 'notes']:
                # 텍스트 필드 sanitization
                sanitized[key] = self.xss_protection.sanitize_text_content(str(value))
            elif key == 'content' and isinstance(value, str):
                # HTML 콘텐츠 sanitization
                sanitized[key] = self.xss_protection.sanitize_html_content(value)
            elif isinstance(value, dict):
                # 중첩된 객체 재귀 처리
                sanitized[key] = self._sanitize_canvas_input(value)
            elif isinstance(value, (int, float, bool)):
                # 기본 타입은 그대로 유지
                sanitized[key] = value
            else:
                # 기타 타입은 문자열로 변환 후 sanitization
                sanitized[key] = self.xss_protection.sanitize_text_content(str(value))
        
        return sanitized

# 전역 보안 관리자 인스턴스 (실제 사용 시 의존성 주입으로 관리)
_security_manager: Optional[CanvasSecurityManager] = None

def get_canvas_security_manager(db: Session) -> CanvasSecurityManager:
    """Canvas 보안 관리자 싱글톤 인스턴스 반환"""
    global _security_manager
    if _security_manager is None:
        _security_manager = CanvasSecurityManager(db)
    return _security_manager