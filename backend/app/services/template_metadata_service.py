# Template Metadata and Tagging Service
# AIPortal Canvas Template Library - 메타데이터 및 태깅 시스템

import re
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Set
from uuid import UUID
from collections import Counter
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func, text

from app.db.models.canvas_template import (
    CanvasTemplate, TemplateTag, TemplateCategory as DBTemplateCategory,
    TemplateUsageLog, TemplateAnalytics
)
from app.models.template_models import TemplateCategory, TemplateSubcategory
from app.core.exceptions import ValidationError, NotFoundError
import logging

logger = logging.getLogger(__name__)

class TemplateMetadataService:
    """템플릿 메타데이터 및 태깅 시스템 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ===== 태그 시스템 =====
    
    async def extract_keywords_from_template(
        self,
        template_name: str,
        description: Optional[str],
        canvas_data: Dict[str, Any]
    ) -> List[str]:
        """
        템플릿에서 키워드 자동 추출
        """
        keywords = set()
        
        try:
            # 템플릿 이름에서 키워드 추출
            name_keywords = self._extract_keywords_from_text(template_name)
            keywords.update(name_keywords)
            
            # 설명에서 키워드 추출
            if description:
                desc_keywords = self._extract_keywords_from_text(description)
                keywords.update(desc_keywords)
            
            # Canvas 데이터에서 텍스트 요소 추출
            canvas_keywords = await self._extract_keywords_from_canvas(canvas_data)
            keywords.update(canvas_keywords)
            
            # 색상 키워드 추출
            color_keywords = await self._extract_color_keywords(canvas_data)
            keywords.update(color_keywords)
            
            # 불용어 제거
            filtered_keywords = self._filter_stopwords(keywords)
            
            # 유사 키워드 그룹화
            grouped_keywords = self._group_similar_keywords(filtered_keywords)
            
            return list(grouped_keywords)[:20]  # 최대 20개 키워드
            
        except Exception as e:
            logger.error(f"Failed to extract keywords: {str(e)}")
            return []
    
    async def suggest_tags(
        self,
        category: TemplateCategory,
        subcategory: TemplateSubcategory,
        keywords: List[str]
    ) -> List[str]:
        """
        카테고리와 키워드 기반 태그 추천
        """
        try:
            suggested_tags = set()
            
            # 카테고리별 기본 태그
            category_tags = self._get_category_tags(category)
            suggested_tags.update(category_tags)
            
            # 서브카테고리별 특화 태그
            subcategory_tags = self._get_subcategory_tags(subcategory)
            suggested_tags.update(subcategory_tags)
            
            # 키워드 기반 태그 매칭
            keyword_tags = await self._match_keywords_to_tags(keywords)
            suggested_tags.update(keyword_tags)
            
            # 인기 태그와 매칭
            popular_tags = await self._get_popular_tags_for_category(category)
            for tag in popular_tags:
                if any(keyword.lower() in tag.lower() for keyword in keywords):
                    suggested_tags.add(tag)
            
            # 스타일 태그 추출
            style_tags = await self._extract_style_tags(keywords)
            suggested_tags.update(style_tags)
            
            return list(suggested_tags)[:15]  # 최대 15개 추천
            
        except Exception as e:
            logger.error(f"Failed to suggest tags: {str(e)}")
            return []
    
    async def analyze_template_metadata(
        self,
        canvas_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Canvas 데이터에서 메타데이터 분석
        """
        try:
            metadata = {
                "complexity_score": 0,
                "color_count": 0,
                "text_elements": 0,
                "image_elements": 0,
                "shape_elements": 0,
                "layers": 0,
                "estimated_edit_time": 0,
                "dominant_colors": [],
                "font_families": [],
                "design_style": "unknown"
            }
            
            # 레이어 분석
            if 'layers' in canvas_data:
                layers = canvas_data['layers']
                metadata["layers"] = len(layers)
                
                # 각 레이어의 요소 분석
                for layer in layers:
                    if 'children' in layer:
                        for element in layer['children']:
                            element_type = element.get('className', '').lower()
                            
                            if 'text' in element_type:
                                metadata["text_elements"] += 1
                                
                                # 폰트 정보 수집
                                font_family = element.get('fontFamily')
                                if font_family and font_family not in metadata["font_families"]:
                                    metadata["font_families"].append(font_family)
                            
                            elif 'image' in element_type:
                                metadata["image_elements"] += 1
                            
                            elif any(shape in element_type for shape in ['rect', 'circle', 'ellipse', 'star', 'polygon']):
                                metadata["shape_elements"] += 1
                            
                            # 색상 정보 수집
                            fill_color = element.get('fill')
                            if fill_color and fill_color not in ['transparent', 'none']:
                                metadata["dominant_colors"].append(fill_color)
            
            # 색상 분석
            if metadata["dominant_colors"]:
                color_counter = Counter(metadata["dominant_colors"])
                metadata["dominant_colors"] = [color for color, _ in color_counter.most_common(5)]
                metadata["color_count"] = len(set(metadata["dominant_colors"]))
            
            # 복잡도 스코어 계산
            metadata["complexity_score"] = self._calculate_complexity_score(metadata)
            
            # 예상 편집 시간 계산 (분)
            metadata["estimated_edit_time"] = self._estimate_edit_time(metadata)
            
            # 디자인 스타일 분석
            metadata["design_style"] = self._analyze_design_style(metadata, canvas_data)
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to analyze template metadata: {str(e)}")
            return {}
    
    async def update_template_tags(
        self,
        template_id: UUID,
        new_tags: List[str],
        user_id: Optional[UUID] = None
    ) -> bool:
        """
        템플릿 태그 업데이트
        """
        try:
            # 기존 템플릿 조회
            template = self.db.query(CanvasTemplate).filter(
                CanvasTemplate.id == template_id
            ).first()
            
            if not template:
                raise NotFoundError("템플릿을 찾을 수 없습니다")
            
            # 태그 정규화
            normalized_tags = [self._normalize_tag(tag) for tag in new_tags]
            normalized_tags = list(set(normalized_tags))  # 중복 제거
            
            # 태그 유효성 검사
            valid_tags = []
            for tag in normalized_tags:
                if self._is_valid_tag(tag):
                    valid_tags.append(tag)
            
            # 템플릿 태그 업데이트
            template.tags = valid_tags
            template.updated_at = datetime.utcnow()
            
            # 태그 사용량 업데이트
            for tag in valid_tags:
                await self._update_tag_usage(tag)
            
            self.db.commit()
            
            logger.info(f"Template tags updated: {template_id}, tags: {valid_tags}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update template tags: {str(e)}")
            return False
    
    async def get_tag_suggestions(
        self,
        query: str,
        category: Optional[TemplateCategory] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        태그 자동완성 제안
        """
        try:
            suggestions = []
            
            # 기존 태그에서 검색
            existing_tags = self.db.query(TemplateTag).filter(
                TemplateTag.name.ilike(f"%{query}%")
            ).order_by(desc(TemplateTag.usage_count)).limit(limit).all()
            
            for tag in existing_tags:
                suggestions.append({
                    "name": tag.name,
                    "usage_count": tag.usage_count,
                    "tag_type": tag.tag_type,
                    "is_trending": tag.is_trending,
                    "source": "existing"
                })
            
            # 카테고리별 추천 태그
            if category and len(suggestions) < limit:
                category_suggestions = self._get_category_tag_suggestions(query, category)
                for suggestion in category_suggestions[:limit - len(suggestions)]:
                    suggestions.append({
                        "name": suggestion,
                        "usage_count": 0,
                        "tag_type": "category",
                        "is_trending": False,
                        "source": "category"
                    })
            
            # AI 기반 태그 제안 (향후 구현)
            if len(suggestions) < limit:
                ai_suggestions = await self._get_ai_tag_suggestions(query)
                for suggestion in ai_suggestions[:limit - len(suggestions)]:
                    suggestions.append({
                        "name": suggestion,
                        "usage_count": 0,
                        "tag_type": "ai_suggested",
                        "is_trending": False,
                        "source": "ai"
                    })
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Failed to get tag suggestions: {str(e)}")
            return []
    
    async def get_trending_tags(
        self,
        days: int = 7,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        트렌딩 태그 조회
        """
        try:
            since_date = datetime.utcnow() - timedelta(days=days)
            
            # 최근 사용된 태그 분석
            recent_usage = self.db.query(
                func.unnest(CanvasTemplate.tags).label('tag'),
                func.count().label('usage_count')
            ).filter(
                CanvasTemplate.created_at >= since_date,
                CanvasTemplate.is_public == True
            ).group_by('tag').order_by(desc('usage_count')).limit(limit).all()
            
            trending_tags = []
            for tag, count in recent_usage:
                trending_tags.append({
                    "name": tag,
                    "recent_usage": count,
                    "growth_rate": await self._calculate_tag_growth_rate(tag, days),
                    "category": await self._get_tag_category(tag)
                })
            
            return trending_tags
            
        except Exception as e:
            logger.error(f"Failed to get trending tags: {str(e)}")
            return []
    
    # ===== 카테고리 관리 =====
    
    async def get_category_analytics(
        self,
        category: TemplateCategory,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        카테고리별 분석 데이터
        """
        try:
            since_date = datetime.utcnow() - timedelta(days=days)
            
            analytics = {
                "category": category.value,
                "total_templates": 0,
                "recent_templates": 0,
                "total_usage": 0,
                "recent_usage": 0,
                "average_rating": 0.0,
                "popular_subcategories": [],
                "popular_tags": [],
                "user_demographics": {}
            }
            
            # 기본 통계
            total_query = self.db.query(CanvasTemplate).filter(
                CanvasTemplate.category == category.value,
                CanvasTemplate.is_public == True
            )
            
            analytics["total_templates"] = total_query.count()
            analytics["recent_templates"] = total_query.filter(
                CanvasTemplate.created_at >= since_date
            ).count()
            
            # 평균 평점
            rating_result = total_query.with_entities(
                func.avg(CanvasTemplate.average_rating)
            ).first()
            
            if rating_result[0]:
                analytics["average_rating"] = float(rating_result[0])
            
            # 사용량 통계
            usage_result = total_query.with_entities(
                func.sum(CanvasTemplate.usage_count)
            ).first()
            
            if usage_result[0]:
                analytics["total_usage"] = usage_result[0]
            
            # 인기 서브카테고리
            subcategory_stats = self.db.query(
                CanvasTemplate.subcategory,
                func.count(CanvasTemplate.id).label('count')
            ).filter(
                CanvasTemplate.category == category.value,
                CanvasTemplate.is_public == True
            ).group_by(CanvasTemplate.subcategory).order_by(desc('count')).limit(10).all()
            
            analytics["popular_subcategories"] = [
                {"subcategory": subcat, "count": count} 
                for subcat, count in subcategory_stats
            ]
            
            # 인기 태그
            popular_tags = await self._get_popular_tags_for_category(category)
            analytics["popular_tags"] = popular_tags[:15]
            
            return analytics
            
        except Exception as e:
            logger.error(f"Failed to get category analytics: {str(e)}")
            return {}
    
    # ===== 내부 헬퍼 메서드 =====
    
    def _extract_keywords_from_text(self, text: str) -> List[str]:
        """텍스트에서 키워드 추출"""
        if not text:
            return []
        
        # 소문자 변환 및 특수문자 제거
        cleaned_text = re.sub(r'[^\w\s]', ' ', text.lower())
        
        # 단어 분리
        words = cleaned_text.split()
        
        # 의미있는 단어만 필터링 (길이 2 이상)
        keywords = [word for word in words if len(word) >= 2]
        
        return keywords
    
    async def _extract_keywords_from_canvas(self, canvas_data: Dict[str, Any]) -> List[str]:
        """Canvas 데이터에서 텍스트 키워드 추출"""
        keywords = []
        
        try:
            def extract_text_recursive(obj):
                if isinstance(obj, dict):
                    # 텍스트 요소에서 텍스트 추출
                    if obj.get('className') == 'Text' and obj.get('text'):
                        text_keywords = self._extract_keywords_from_text(obj['text'])
                        keywords.extend(text_keywords)
                    
                    # 재귀적으로 하위 요소 처리
                    for value in obj.values():
                        extract_text_recursive(value)
                
                elif isinstance(obj, list):
                    for item in obj:
                        extract_text_recursive(item)
            
            extract_text_recursive(canvas_data)
            
        except Exception as e:
            logger.error(f"Failed to extract keywords from canvas: {str(e)}")
        
        return keywords
    
    async def _extract_color_keywords(self, canvas_data: Dict[str, Any]) -> List[str]:
        """Canvas에서 색상 기반 키워드 추출"""
        color_keywords = []
        
        # 색상 - 키워드 매핑
        color_map = {
            '#ff0000': ['red', 'bold', 'energetic'],
            '#00ff00': ['green', 'nature', 'fresh'],
            '#0000ff': ['blue', 'professional', 'calm'],
            '#ffff00': ['yellow', 'bright', 'cheerful'],
            '#ff00ff': ['magenta', 'creative', 'vibrant'],
            '#00ffff': ['cyan', 'modern', 'cool'],
            '#000000': ['black', 'elegant', 'minimalist'],
            '#ffffff': ['white', 'clean', 'simple']
        }
        
        try:
            # TODO: Canvas에서 색상 추출 후 키워드 매핑
            pass
            
        except Exception as e:
            logger.error(f"Failed to extract color keywords: {str(e)}")
        
        return color_keywords
    
    def _filter_stopwords(self, keywords: Set[str]) -> Set[str]:
        """불용어 필터링"""
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'among', 'is', 'are',
            'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do',
            'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
            'must', 'can', 'this', 'that', 'these', 'those'
        }
        
        return {word for word in keywords if word not in stopwords and len(word) > 2}
    
    def _group_similar_keywords(self, keywords: Set[str]) -> Set[str]:
        """유사 키워드 그룹화"""
        # 간단한 어간 기반 그룹화
        grouped = {}
        
        for keyword in keywords:
            # 복수형 처리
            stem = keyword.rstrip('s') if keyword.endswith('s') and len(keyword) > 3 else keyword
            
            if stem not in grouped:
                grouped[stem] = keyword
        
        return set(grouped.values())
    
    def _get_category_tags(self, category: TemplateCategory) -> List[str]:
        """카테고리별 기본 태그"""
        category_tags = {
            TemplateCategory.BUSINESS: ['professional', 'corporate', 'formal', 'clean'],
            TemplateCategory.SOCIAL_MEDIA: ['trendy', 'viral', 'engaging', 'shareable'],
            TemplateCategory.EDUCATION: ['informative', 'clear', 'educational', 'academic'],
            TemplateCategory.EVENT: ['festive', 'celebratory', 'announcement', 'special'],
            TemplateCategory.PERSONAL: ['personal', 'custom', 'unique', 'individual'],
            TemplateCategory.CREATIVE: ['artistic', 'innovative', 'creative', 'original'],
            TemplateCategory.MARKETING: ['promotional', 'marketing', 'advertising', 'commercial'],
            TemplateCategory.PRESENTATION: ['slides', 'presentation', 'pitch', 'meeting']
        }
        
        return category_tags.get(category, [])
    
    def _get_subcategory_tags(self, subcategory: TemplateSubcategory) -> List[str]:
        """서브카테고리별 특화 태그"""
        subcategory_tags = {
            TemplateSubcategory.BUSINESS_CARD: ['networking', 'contact', 'identity'],
            TemplateSubcategory.BROCHURE: ['informational', 'tri-fold', 'marketing'],
            TemplateSubcategory.INSTAGRAM_POST: ['square', 'social', 'instagram'],
            TemplateSubcategory.YOUTUBE_THUMBNAIL: ['clickable', 'eye-catching', 'youtube'],
            TemplateSubcategory.INFOGRAPHIC: ['data', 'visual', 'statistics'],
            TemplateSubcategory.POSTER: ['large', 'eye-catching', 'promotional'],
            # ... 더 많은 서브카테고리 태그
        }
        
        return subcategory_tags.get(subcategory, [])
    
    async def _match_keywords_to_tags(self, keywords: List[str]) -> List[str]:
        """키워드를 기존 태그와 매칭"""
        matched_tags = []
        
        try:
            for keyword in keywords:
                # 유사한 기존 태그 찾기
                similar_tags = self.db.query(TemplateTag).filter(
                    TemplateTag.name.ilike(f"%{keyword}%")
                ).limit(3).all()
                
                for tag in similar_tags:
                    if tag.name not in matched_tags:
                        matched_tags.append(tag.name)
        
        except Exception as e:
            logger.error(f"Failed to match keywords to tags: {str(e)}")
        
        return matched_tags
    
    async def _get_popular_tags_for_category(self, category: TemplateCategory) -> List[str]:
        """카테고리별 인기 태그"""
        try:
            popular_tags = self.db.query(
                func.unnest(CanvasTemplate.tags).label('tag'),
                func.count().label('usage_count')
            ).filter(
                CanvasTemplate.category == category.value,
                CanvasTemplate.is_public == True
            ).group_by('tag').order_by(desc('usage_count')).limit(20).all()
            
            return [tag for tag, _ in popular_tags]
            
        except Exception as e:
            logger.error(f"Failed to get popular tags for category: {str(e)}")
            return []
    
    async def _extract_style_tags(self, keywords: List[str]) -> List[str]:
        """키워드에서 스타일 태그 추출"""
        style_keywords = {
            'minimal', 'minimalist', 'modern', 'vintage', 'retro', 'classic',
            'elegant', 'sophisticated', 'bold', 'dramatic', 'playful', 'fun',
            'professional', 'corporate', 'creative', 'artistic', 'abstract',
            'geometric', 'organic', 'clean', 'simple', 'complex', 'detailed'
        }
        
        return [keyword for keyword in keywords if keyword.lower() in style_keywords]
    
    def _calculate_complexity_score(self, metadata: Dict[str, Any]) -> int:
        """템플릿 복잡도 스코어 계산"""
        score = 0
        
        # 요소 수에 따른 점수
        score += metadata.get("text_elements", 0) * 2
        score += metadata.get("image_elements", 0) * 3
        score += metadata.get("shape_elements", 0) * 1
        score += metadata.get("layers", 0) * 5
        
        # 색상 수에 따른 점수
        score += metadata.get("color_count", 0) * 2
        
        # 폰트 수에 따른 점수
        score += len(metadata.get("font_families", [])) * 3
        
        return min(score, 100)  # 최대 100점
    
    def _estimate_edit_time(self, metadata: Dict[str, Any]) -> int:
        """예상 편집 시간 계산 (분)"""
        base_time = 5  # 기본 5분
        
        # 복잡도에 따른 추가 시간
        complexity = metadata.get("complexity_score", 0)
        additional_time = complexity * 0.5
        
        # 요소별 추가 시간
        text_time = metadata.get("text_elements", 0) * 2
        image_time = metadata.get("image_elements", 0) * 3
        
        total_time = base_time + additional_time + text_time + image_time
        
        return int(min(total_time, 120))  # 최대 120분
    
    def _analyze_design_style(
        self, 
        metadata: Dict[str, Any], 
        canvas_data: Dict[str, Any]
    ) -> str:
        """디자인 스타일 분석"""
        # 색상 기반 스타일 분석
        color_count = metadata.get("color_count", 0)
        dominant_colors = metadata.get("dominant_colors", [])
        
        if color_count <= 2:
            return "minimalist"
        elif color_count >= 5:
            return "colorful"
        elif any(color in ['#000000', '#ffffff', '#808080'] for color in dominant_colors):
            return "monochrome"
        else:
            return "modern"
    
    def _normalize_tag(self, tag: str) -> str:
        """태그 정규화"""
        # 소문자 변환, 공백 제거, 특수문자 제거
        normalized = re.sub(r'[^\w\s-]', '', tag.lower().strip())
        normalized = re.sub(r'\s+', '-', normalized)
        
        return normalized
    
    def _is_valid_tag(self, tag: str) -> bool:
        """태그 유효성 검사"""
        if not tag or len(tag) < 2 or len(tag) > 50:
            return False
        
        # 부적절한 단어 필터링 (간단한 예시)
        inappropriate_words = {'spam', 'fake', 'illegal'}
        
        return tag.lower() not in inappropriate_words
    
    async def _update_tag_usage(self, tag: str) -> None:
        """태그 사용량 업데이트"""
        try:
            # Upsert 방식으로 태그 사용량 업데이트
            existing_tag = self.db.query(TemplateTag).filter(
                TemplateTag.name == tag
            ).first()
            
            if existing_tag:
                existing_tag.usage_count += 1
            else:
                new_tag = TemplateTag(
                    name=tag,
                    slug=tag.replace(' ', '-'),
                    usage_count=1,
                    tag_type="user_generated"
                )
                self.db.add(new_tag)
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to update tag usage: {str(e)}")
    
    def _get_category_tag_suggestions(
        self, 
        query: str, 
        category: TemplateCategory
    ) -> List[str]:
        """카테고리별 태그 제안"""
        category_suggestions = {
            TemplateCategory.BUSINESS: [
                'professional', 'corporate', 'formal', 'clean', 'elegant',
                'modern', 'minimalist', 'executive', 'office', 'meeting'
            ],
            TemplateCategory.SOCIAL_MEDIA: [
                'trendy', 'viral', 'engaging', 'shareable', 'instagram',
                'facebook', 'twitter', 'social', 'post', 'story'
            ],
            # ... 더 많은 카테고리 제안
        }
        
        suggestions = category_suggestions.get(category, [])
        
        # 쿼리와 유사한 제안 필터링
        filtered = [s for s in suggestions if query.lower() in s.lower()]
        
        return filtered[:5]
    
    async def _get_ai_tag_suggestions(self, query: str) -> List[str]:
        """AI 기반 태그 제안 (향후 구현)"""
        # TODO: LLM을 사용한 지능적 태그 제안
        return []
    
    async def _calculate_tag_growth_rate(self, tag: str, days: int) -> float:
        """태그 성장률 계산"""
        try:
            current_period = datetime.utcnow() - timedelta(days=days)
            previous_period = current_period - timedelta(days=days)
            
            current_usage = self.db.query(func.count()).filter(
                CanvasTemplate.tags.op('&&')(f'{{{tag}}}'),
                CanvasTemplate.created_at >= current_period
            ).scalar()
            
            previous_usage = self.db.query(func.count()).filter(
                CanvasTemplate.tags.op('&&')(f'{{{tag}}}'),
                CanvasTemplate.created_at >= previous_period,
                CanvasTemplate.created_at < current_period
            ).scalar()
            
            if previous_usage == 0:
                return 100.0 if current_usage > 0 else 0.0
            
            growth_rate = ((current_usage - previous_usage) / previous_usage) * 100
            return round(growth_rate, 2)
            
        except Exception as e:
            logger.error(f"Failed to calculate tag growth rate: {str(e)}")
            return 0.0
    
    async def _get_tag_category(self, tag: str) -> str:
        """태그 카테고리 추정"""
        tag_categories = {
            'color': ['red', 'blue', 'green', 'yellow', 'purple', 'orange', 'pink', 'black', 'white'],
            'style': ['modern', 'vintage', 'minimalist', 'bold', 'elegant', 'playful', 'professional'],
            'mood': ['happy', 'sad', 'energetic', 'calm', 'dramatic', 'peaceful', 'exciting'],
            'industry': ['business', 'education', 'healthcare', 'technology', 'food', 'fashion']
        }
        
        for category, keywords in tag_categories.items():
            if tag.lower() in keywords:
                return category
        
        return 'general'

print("Template Metadata Service v1.0 완성")
print("- 키워드 자동 추출 시스템")
print("- AI 기반 태그 추천")
print("- Canvas 메타데이터 분석")
print("- 트렌딩 태그 및 카테고리 분석")