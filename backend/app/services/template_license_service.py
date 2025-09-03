# Template License Management Service
# AIPortal Canvas Template Library - 프리미엄 템플릿 라이선스 관리 시스템

import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from app.db.models.canvas_template import (
    CanvasTemplate, TemplateLicenseAgreement, TemplateUsageLog
)
from app.models.template_models import LicenseType
from app.core.exceptions import NotFoundError, ValidationError, PermissionError
import logging

logger = logging.getLogger(__name__)

class TemplateLicenseService:
    """템플릿 라이선스 관리 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ===== 라이선스 구매 및 동의 =====
    
    async def purchase_license(
        self,
        template_id: UUID,
        user_id: UUID,
        license_type: LicenseType,
        payment_details: Optional[Dict[str, Any]] = None
    ) -> TemplateLicenseAgreement:
        """
        프리미엄 템플릿 라이선스 구매
        """
        try:
            # 템플릿 조회
            template = self.db.query(CanvasTemplate).filter(
                CanvasTemplate.id == template_id,
                CanvasTemplate.is_public == True,
                CanvasTemplate.is_archived == False
            ).first()
            
            if not template:
                raise NotFoundError("템플릿을 찾을 수 없습니다")
            
            # 이미 구매한 라이선스가 있는지 확인
            existing_license = self.db.query(TemplateLicenseAgreement).filter(
                TemplateLicenseAgreement.template_id == template_id,
                TemplateLicenseAgreement.user_id == user_id,
                TemplateLicenseAgreement.is_active == True,
                or_(
                    TemplateLicenseAgreement.expires_at.is_(None),
                    TemplateLicenseAgreement.expires_at > datetime.utcnow()
                )
            ).first()
            
            if existing_license:
                return existing_license
            
            # 라이선스 정보 생성
            license_details = self._get_license_details(license_type, template)
            
            # 라이선스 동의 생성
            license_agreement = TemplateLicenseAgreement(
                template_id=template_id,
                user_id=user_id,
                license_type=license_type.value,
                license_version="1.0",
                license_text=license_details["license_text"],
                usage_limit=license_details.get("usage_limit"),
                commercial_usage=license_details.get("commercial_usage", False),
                redistribution_allowed=license_details.get("redistribution_allowed", False),
                payment_id=payment_details.get("payment_id") if payment_details else None,
                amount_paid=payment_details.get("amount") if payment_details else 0.0,
                currency=payment_details.get("currency", "KRW") if payment_details else "KRW",
                expires_at=self._calculate_expiry_date(license_type)
            )
            
            self.db.add(license_agreement)
            self.db.commit()
            self.db.refresh(license_agreement)
            
            logger.info(f"License purchased: template={template_id}, user={user_id}, type={license_type}")
            
            return license_agreement
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to purchase license: {str(e)}")
            raise ValidationError(f"라이선스 구매에 실패했습니다: {str(e)}")
    
    async def check_license(self, template_id: UUID, user_id: UUID) -> Dict[str, Any]:
        """
        템플릿 사용 권한 확인
        """
        try:
            # 템플릿 조회
            template = self.db.query(CanvasTemplate).filter(
                CanvasTemplate.id == template_id
            ).first()
            
            if not template:
                raise NotFoundError("템플릿을 찾을 수 없습니다")
            
            # 무료 템플릿인 경우
            if template.license_type == LicenseType.FREE.value:
                return {
                    "has_license": True,
                    "license_type": "free",
                    "usage_remaining": None,
                    "expires_at": None,
                    "commercial_usage": False,
                    "redistribution_allowed": False
                }
            
            # 프리미엄 템플릿 라이선스 확인
            license_agreement = self.db.query(TemplateLicenseAgreement).filter(
                TemplateLicenseAgreement.template_id == template_id,
                TemplateLicenseAgreement.user_id == user_id,
                TemplateLicenseAgreement.is_active == True,
                or_(
                    TemplateLicenseAgreement.expires_at.is_(None),
                    TemplateLicenseAgreement.expires_at > datetime.utcnow()
                )
            ).first()
            
            if not license_agreement:
                return {
                    "has_license": False,
                    "license_type": template.license_type,
                    "price": self._get_template_price(template),
                    "currency": "KRW"
                }
            
            # 사용 제한 확인
            usage_remaining = None
            if license_agreement.usage_limit:
                usage_remaining = license_agreement.usage_limit - license_agreement.usage_count
                if usage_remaining <= 0:
                    return {
                        "has_license": False,
                        "license_type": license_agreement.license_type,
                        "reason": "usage_limit_exceeded",
                        "usage_limit": license_agreement.usage_limit,
                        "usage_count": license_agreement.usage_count
                    }
            
            return {
                "has_license": True,
                "license_type": license_agreement.license_type,
                "usage_remaining": usage_remaining,
                "expires_at": license_agreement.expires_at.isoformat() if license_agreement.expires_at else None,
                "commercial_usage": license_agreement.commercial_usage,
                "redistribution_allowed": license_agreement.redistribution_allowed,
                "purchase_date": license_agreement.agreed_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to check license: {str(e)}")
            raise ValidationError(f"라이선스 확인에 실패했습니다: {str(e)}")
    
    async def record_usage(
        self, 
        template_id: UUID, 
        user_id: UUID, 
        usage_type: str = "apply"
    ) -> bool:
        """
        템플릿 사용 기록 및 라이선스 사용 횟수 업데이트
        """
        try:
            # 라이선스 확인
            license_check = await self.check_license(template_id, user_id)
            
            if not license_check["has_license"]:
                raise PermissionError("템플릿 사용 권한이 없습니다")
            
            # 프리미엄 템플릿인 경우 사용 횟수 업데이트
            if license_check["license_type"] != "free":
                license_agreement = self.db.query(TemplateLicenseAgreement).filter(
                    TemplateLicenseAgreement.template_id == template_id,
                    TemplateLicenseAgreement.user_id == user_id,
                    TemplateLicenseAgreement.is_active == True
                ).first()
                
                if license_agreement:
                    license_agreement.usage_count += 1
                    self.db.commit()
            
            # 사용 로그 기록
            usage_log = TemplateUsageLog(
                template_id=template_id,
                user_id=user_id,
                usage_type=usage_type,
                session_id=str(uuid.uuid4())
            )
            
            self.db.add(usage_log)
            self.db.commit()
            
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to record usage: {str(e)}")
            return False
    
    # ===== 구독 관리 =====
    
    async def create_subscription(
        self,
        user_id: UUID,
        plan_type: str,
        billing_cycle: str = "monthly"
    ) -> Dict[str, Any]:
        """
        프리미엄 구독 생성
        """
        try:
            # 구독 플랜 정보
            plan_details = self._get_subscription_plan(plan_type, billing_cycle)
            
            # TODO: 실제 결제 시스템과 연동
            subscription = {
                "id": str(uuid.uuid4()),
                "user_id": str(user_id),
                "plan_type": plan_type,
                "billing_cycle": billing_cycle,
                "price": plan_details["price"],
                "currency": plan_details["currency"],
                "features": plan_details["features"],
                "starts_at": datetime.utcnow().isoformat(),
                "next_billing_at": (datetime.utcnow() + timedelta(days=30 if billing_cycle == "monthly" else 365)).isoformat(),
                "status": "active"
            }
            
            logger.info(f"Subscription created: user={user_id}, plan={plan_type}")
            
            return subscription
            
        except Exception as e:
            logger.error(f"Failed to create subscription: {str(e)}")
            raise ValidationError(f"구독 생성에 실패했습니다: {str(e)}")
    
    async def check_subscription(self, user_id: UUID) -> Dict[str, Any]:
        """
        사용자 구독 상태 확인
        """
        try:
            # TODO: 실제 구독 시스템에서 조회
            # 임시로 무료 사용자로 반환
            return {
                "has_subscription": False,
                "plan_type": "free",
                "features": {
                    "premium_templates": False,
                    "unlimited_downloads": False,
                    "commercial_usage": False,
                    "priority_support": False
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to check subscription: {str(e)}")
            return {
                "has_subscription": False,
                "plan_type": "free",
                "error": str(e)
            }
    
    # ===== 라이선스 관리 =====
    
    async def get_user_licenses(
        self,
        user_id: UUID,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        사용자가 구매한 모든 라이선스 조회
        """
        try:
            query = self.db.query(TemplateLicenseAgreement).filter(
                TemplateLicenseAgreement.user_id == user_id
            )
            
            if active_only:
                query = query.filter(
                    TemplateLicenseAgreement.is_active == True,
                    or_(
                        TemplateLicenseAgreement.expires_at.is_(None),
                        TemplateLicenseAgreement.expires_at > datetime.utcnow()
                    )
                )
            
            licenses = query.order_by(desc(TemplateLicenseAgreement.agreed_at)).all()
            
            result = []
            for license_agreement in licenses:
                template = self.db.query(CanvasTemplate).filter(
                    CanvasTemplate.id == license_agreement.template_id
                ).first()
                
                if template:
                    result.append({
                        "license_id": license_agreement.id,
                        "template": {
                            "id": template.id,
                            "name": template.name,
                            "thumbnail_url": template.thumbnail_url,
                            "category": template.category
                        },
                        "license_type": license_agreement.license_type,
                        "usage_count": license_agreement.usage_count,
                        "usage_limit": license_agreement.usage_limit,
                        "expires_at": license_agreement.expires_at.isoformat() if license_agreement.expires_at else None,
                        "commercial_usage": license_agreement.commercial_usage,
                        "purchased_at": license_agreement.agreed_at.isoformat(),
                        "amount_paid": license_agreement.amount_paid,
                        "currency": license_agreement.currency
                    })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get user licenses: {str(e)}")
            return []
    
    async def revoke_license(
        self,
        license_id: UUID,
        reason: str = "user_request"
    ) -> bool:
        """
        라이선스 취소
        """
        try:
            license_agreement = self.db.query(TemplateLicenseAgreement).filter(
                TemplateLicenseAgreement.id == license_id
            ).first()
            
            if not license_agreement:
                raise NotFoundError("라이선스를 찾을 수 없습니다")
            
            license_agreement.is_active = False
            self.db.commit()
            
            logger.info(f"License revoked: {license_id}, reason: {reason}")
            
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to revoke license: {str(e)}")
            return False
    
    # ===== 가격 및 할인 관리 =====
    
    async def get_template_pricing(self, template_id: UUID) -> Dict[str, Any]:
        """
        템플릿 가격 정보 조회
        """
        try:
            template = self.db.query(CanvasTemplate).filter(
                CanvasTemplate.id == template_id
            ).first()
            
            if not template:
                raise NotFoundError("템플릿을 찾을 수 없습니다")
            
            if template.license_type == LicenseType.FREE.value:
                return {
                    "license_type": "free",
                    "price": 0,
                    "currency": "KRW"
                }
            
            base_price = self._get_template_price(template)
            
            return {
                "license_type": template.license_type,
                "base_price": base_price,
                "currency": "KRW",
                "license_options": [
                    {
                        "type": "single_use",
                        "name": "단일 사용",
                        "price": base_price,
                        "usage_limit": 1,
                        "commercial_usage": False
                    },
                    {
                        "type": "multi_use",
                        "name": "다중 사용",
                        "price": base_price * 3,
                        "usage_limit": 10,
                        "commercial_usage": False
                    },
                    {
                        "type": "commercial",
                        "name": "상업적 사용",
                        "price": base_price * 5,
                        "usage_limit": None,
                        "commercial_usage": True
                    }
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to get template pricing: {str(e)}")
            raise ValidationError(f"가격 정보 조회에 실패했습니다: {str(e)}")
    
    async def apply_discount(
        self,
        template_id: UUID,
        user_id: UUID,
        discount_code: str
    ) -> Dict[str, Any]:
        """
        할인 코드 적용
        """
        try:
            # TODO: 실제 할인 시스템 구현
            discount_info = self._get_discount_info(discount_code)
            
            if not discount_info:
                raise ValidationError("유효하지 않은 할인 코드입니다")
            
            original_price = self._get_template_price(
                self.db.query(CanvasTemplate).filter(
                    CanvasTemplate.id == template_id
                ).first()
            )
            
            discount_amount = original_price * (discount_info["percentage"] / 100)
            final_price = original_price - discount_amount
            
            return {
                "original_price": original_price,
                "discount_percentage": discount_info["percentage"],
                "discount_amount": discount_amount,
                "final_price": final_price,
                "currency": "KRW",
                "discount_code": discount_code
            }
            
        except Exception as e:
            logger.error(f"Failed to apply discount: {str(e)}")
            raise ValidationError(f"할인 적용에 실패했습니다: {str(e)}")
    
    # ===== 내부 헬퍼 메서드 =====
    
    def _get_license_details(
        self, 
        license_type: LicenseType, 
        template: CanvasTemplate
    ) -> Dict[str, Any]:
        """라이선스 상세 정보 생성"""
        
        license_templates = {
            LicenseType.FREE: {
                "license_text": "이 템플릿은 개인적, 비상업적 용도로만 자유롭게 사용할 수 있습니다.",
                "commercial_usage": False,
                "redistribution_allowed": False,
                "usage_limit": None
            },
            LicenseType.PREMIUM: {
                "license_text": "이 프리미엄 템플릿은 구매자가 개인 프로젝트에서 제한적으로 사용할 수 있습니다.",
                "commercial_usage": False,
                "redistribution_allowed": False,
                "usage_limit": 10
            },
            LicenseType.PRO: {
                "license_text": "이 프로 템플릿은 상업적 용도를 포함하여 무제한으로 사용할 수 있습니다.",
                "commercial_usage": True,
                "redistribution_allowed": False,
                "usage_limit": None
            },
            LicenseType.ENTERPRISE: {
                "license_text": "이 엔터프라이즈 템플릿은 조직 내에서 무제한으로 사용하고 수정할 수 있습니다.",
                "commercial_usage": True,
                "redistribution_allowed": True,
                "usage_limit": None
            }
        }
        
        return license_templates.get(license_type, license_templates[LicenseType.FREE])
    
    def _calculate_expiry_date(self, license_type: LicenseType) -> Optional[datetime]:
        """라이선스 만료일 계산"""
        
        if license_type in [LicenseType.FREE, LicenseType.PRO, LicenseType.ENTERPRISE]:
            return None  # 영구 라이선스
        
        if license_type == LicenseType.PREMIUM:
            return datetime.utcnow() + timedelta(days=365)  # 1년
        
        return None
    
    def _get_template_price(self, template: CanvasTemplate) -> float:
        """템플릿 기본 가격 계산"""
        
        # 카테고리별 기본 가격
        category_prices = {
            "business": 5000,
            "social_media": 3000,
            "education": 4000,
            "event": 3500,
            "personal": 2000,
            "creative": 6000,
            "marketing": 7000,
            "presentation": 8000
        }
        
        base_price = category_prices.get(template.category, 3000)
        
        # 품질 점수 기반 가격 조정
        quality_multiplier = 1.0
        if template.average_rating >= 4.5:
            quality_multiplier = 1.5
        elif template.average_rating >= 4.0:
            quality_multiplier = 1.2
        elif template.average_rating >= 3.5:
            quality_multiplier = 1.0
        else:
            quality_multiplier = 0.8
        
        # 인기도 기반 가격 조정
        popularity_multiplier = 1.0
        if template.usage_count >= 1000:
            popularity_multiplier = 1.3
        elif template.usage_count >= 500:
            popularity_multiplier = 1.1
        
        final_price = base_price * quality_multiplier * popularity_multiplier
        
        # 100원 단위로 반올림
        return round(final_price / 100) * 100
    
    def _get_subscription_plan(self, plan_type: str, billing_cycle: str) -> Dict[str, Any]:
        """구독 플랜 정보"""
        
        plans = {
            "basic": {
                "monthly": {"price": 9900, "currency": "KRW"},
                "yearly": {"price": 99000, "currency": "KRW"}
            },
            "pro": {
                "monthly": {"price": 19900, "currency": "KRW"},
                "yearly": {"price": 199000, "currency": "KRW"}
            },
            "enterprise": {
                "monthly": {"price": 49900, "currency": "KRW"},
                "yearly": {"price": 499000, "currency": "KRW"}
            }
        }
        
        plan_features = {
            "basic": {
                "premium_templates": True,
                "downloads_per_month": 50,
                "commercial_usage": False,
                "priority_support": False
            },
            "pro": {
                "premium_templates": True,
                "downloads_per_month": 200,
                "commercial_usage": True,
                "priority_support": True
            },
            "enterprise": {
                "premium_templates": True,
                "downloads_per_month": -1,  # 무제한
                "commercial_usage": True,
                "priority_support": True,
                "team_collaboration": True,
                "custom_branding": True
            }
        }
        
        plan_info = plans.get(plan_type, {}).get(billing_cycle, plans["basic"]["monthly"])
        plan_info["features"] = plan_features.get(plan_type, plan_features["basic"])
        
        return plan_info
    
    def _get_discount_info(self, discount_code: str) -> Optional[Dict[str, Any]]:
        """할인 코드 정보 조회"""
        
        # 임시 할인 코드 (실제로는 데이터베이스에서 조회)
        discount_codes = {
            "WELCOME10": {"percentage": 10, "expires_at": "2024-12-31"},
            "NEWUSER20": {"percentage": 20, "expires_at": "2024-12-31"},
            "PREMIUM50": {"percentage": 50, "expires_at": "2024-06-30"}
        }
        
        return discount_codes.get(discount_code)

print("Template License Service v1.0 완성")
print("- 프리미엄 템플릿 라이선스 구매 및 관리")
print("- 구독 시스템 통합")
print("- 사용량 추적 및 제한")
print("- 동적 가격 책정 시스템")
print("- 할인 및 프로모션 관리")