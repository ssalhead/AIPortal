"""
AWS OpenSearch 서비스
"""

from typing import Dict, List, Any, Optional
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import logging
import json
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)


class OpenSearchService:
    """AWS OpenSearch 서비스 클래스"""
    
    def __init__(self):
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """OpenSearch 클라이언트 초기화"""
        try:
            if settings.OPENSEARCH_URL:
                # 기본 인증(username/password)이 있는 경우 - 우선 순위
                if settings.OPENSEARCH_USERNAME and settings.OPENSEARCH_PASSWORD:
                    self.client = OpenSearch(
                        hosts=[settings.OPENSEARCH_URL],
                        http_auth=(settings.OPENSEARCH_USERNAME, settings.OPENSEARCH_PASSWORD),
                        use_ssl=True,
                        verify_certs=True,
                        timeout=30,
                        max_retries=10,
                        retry_on_timeout=True
                    )
                
                # AWS 인증이 있는 경우 (fallback)
                elif settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
                    auth = AWS4Auth(
                        settings.AWS_ACCESS_KEY_ID,
                        settings.AWS_SECRET_ACCESS_KEY,
                        settings.AWS_REGION,
                        'es'
                    )
                    
                    self.client = OpenSearch(
                        hosts=[{
                            'host': settings.OPENSEARCH_URL.replace('https://', '').replace('http://', ''),
                            'port': 443
                        }],
                        http_auth=auth,
                        use_ssl=True,
                        verify_certs=True,
                        connection_class=RequestsHttpConnection,
                        timeout=30,
                        max_retries=10,
                        retry_on_timeout=True
                    )
                
                else:
                    # 인증 없는 로컬 연결
                    self.client = OpenSearch(
                        hosts=[settings.OPENSEARCH_URL],
                        use_ssl=False,
                        timeout=30
                    )
                
                logger.info("OpenSearch 클라이언트 초기화 완료")
                
                # 연결 테스트
                if self.client.ping():
                    logger.info("OpenSearch 연결 성공")
                else:
                    logger.warning("OpenSearch 연결 실패")
                    
            else:
                logger.warning("OPENSEARCH_URL이 설정되지 않음")
                
        except Exception as e:
            logger.error(f"OpenSearch 초기화 실패: {e}")
            self.client = None
    
    def is_connected(self) -> bool:
        """OpenSearch 연결 상태 확인"""
        try:
            return self.client is not None and self.client.ping()
        except Exception:
            return False
    
    def get_cluster_info(self) -> Optional[Dict]:
        """클러스터 정보 조회"""
        try:
            if self.client:
                return self.client.info()
        except Exception as e:
            logger.error(f"클러스터 정보 조회 실패: {e}")
        return None
    
    def create_index(
        self, 
        index_name: str, 
        mapping: Dict = None,
        settings_dict: Dict = None
    ) -> bool:
        """인덱스 생성"""
        try:
            if not self.client:
                return False
                
            full_index_name = f"{settings.OPENSEARCH_INDEX_PREFIX}{index_name}"
            
            # 인덱스가 이미 존재하는지 확인
            if self.client.indices.exists(index=full_index_name):
                logger.info(f"인덱스 '{full_index_name}'이 이미 존재합니다")
                return True
            
            body = {}
            if settings_dict:
                body['settings'] = settings_dict
            if mapping:
                body['mappings'] = mapping
            
            response = self.client.indices.create(
                index=full_index_name,
                body=body if body else None
            )
            
            logger.info(f"인덱스 '{full_index_name}' 생성 성공")
            return response.get('acknowledged', False)
            
        except Exception as e:
            logger.error(f"인덱스 생성 실패: {e}")
            return False
    
    def index_document(
        self, 
        index_name: str, 
        doc_id: str, 
        document: Dict,
        refresh: str = 'wait_for'
    ) -> bool:
        """문서 인덱싱"""
        try:
            if not self.client:
                return False
                
            full_index_name = f"{settings.OPENSEARCH_INDEX_PREFIX}{index_name}"
            
            # 타임스탬프 추가
            document['indexed_at'] = datetime.utcnow().isoformat()
            
            response = self.client.index(
                index=full_index_name,
                id=doc_id,
                body=document,
                refresh=refresh
            )
            
            logger.debug(f"문서 인덱싱 성공: {doc_id}")
            return response.get('result') in ['created', 'updated']
            
        except Exception as e:
            logger.error(f"문서 인덱싱 실패 ({doc_id}): {e}")
            return False
    
    def search_documents(
        self,
        index_name: str,
        query: Dict,
        size: int = 10,
        from_: int = 0,
        sort: List[Dict] = None
    ) -> Optional[Dict]:
        """문서 검색"""
        try:
            if not self.client:
                return None
                
            full_index_name = f"{settings.OPENSEARCH_INDEX_PREFIX}{index_name}"
            
            search_body = {
                'query': query,
                'size': size,
                'from': from_
            }
            
            if sort:
                search_body['sort'] = sort
            
            response = self.client.search(
                index=full_index_name,
                body=search_body
            )
            
            return response
            
        except Exception as e:
            logger.error(f"문서 검색 실패: {e}")
            return None
    
    def semantic_search(
        self,
        index_name: str,
        query_text: str,
        vector_field: str = 'embedding_vector',
        size: int = 10,
        min_score: float = 0.5
    ) -> Optional[List[Dict]]:
        """시맨틱 검색 (벡터 유사도 기반)"""
        try:
            if not self.client:
                return None
            
            # 여기에 임베딩 생성 로직이 필요함 (별도 서비스에서 처리)
            # 현재는 기본 텍스트 검색으로 대체
            query = {
                "multi_match": {
                    "query": query_text,
                    "fields": ["content", "title", "description"],
                    "type": "best_fields",
                    "minimum_should_match": "75%"
                }
            }
            
            response = self.search_documents(
                index_name=index_name,
                query=query,
                size=size
            )
            
            if response and 'hits' in response:
                results = []
                for hit in response['hits']['hits']:
                    if hit['_score'] >= min_score:
                        result = {
                            'id': hit['_id'],
                            'score': hit['_score'],
                            'source': hit['_source']
                        }
                        results.append(result)
                
                return results
            
            return []
            
        except Exception as e:
            logger.error(f"시맨틱 검색 실패: {e}")
            return None
    
    def delete_document(self, index_name: str, doc_id: str) -> bool:
        """문서 삭제"""
        try:
            if not self.client:
                return False
                
            full_index_name = f"{settings.OPENSEARCH_INDEX_PREFIX}{index_name}"
            
            response = self.client.delete(
                index=full_index_name,
                id=doc_id,
                refresh='wait_for'
            )
            
            logger.debug(f"문서 삭제 성공: {doc_id}")
            return response.get('result') == 'deleted'
            
        except Exception as e:
            logger.error(f"문서 삭제 실패 ({doc_id}): {e}")
            return False
    
    def delete_index(self, index_name: str) -> bool:
        """인덱스 삭제"""
        try:
            if not self.client:
                return False
                
            full_index_name = f"{settings.OPENSEARCH_INDEX_PREFIX}{index_name}"
            
            if not self.client.indices.exists(index=full_index_name):
                logger.warning(f"인덱스 '{full_index_name}'이 존재하지 않습니다")
                return True
            
            response = self.client.indices.delete(index=full_index_name)
            
            logger.info(f"인덱스 '{full_index_name}' 삭제 성공")
            return response.get('acknowledged', False)
            
        except Exception as e:
            logger.error(f"인덱스 삭제 실패: {e}")
            return False
    
    def get_document_count(self, index_name: str) -> int:
        """인덱스의 문서 수 조회"""
        try:
            if not self.client:
                return 0
                
            full_index_name = f"{settings.OPENSEARCH_INDEX_PREFIX}{index_name}"
            
            response = self.client.count(index=full_index_name)
            return response.get('count', 0)
            
        except Exception as e:
            logger.error(f"문서 수 조회 실패: {e}")
            return 0
    
    def list_indices(self) -> List[str]:
        """인덱스 목록 조회"""
        try:
            if not self.client:
                return []
                
            response = self.client.cat.indices(format='json')
            
            indices = []
            prefix = settings.OPENSEARCH_INDEX_PREFIX
            
            for index_info in response:
                index_name = index_info.get('index', '')
                if index_name.startswith(prefix):
                    # 프리픽스 제거하여 원본 인덱스명 반환
                    clean_name = index_name[len(prefix):]
                    indices.append(clean_name)
            
            return indices
            
        except Exception as e:
            logger.error(f"인덱스 목록 조회 실패: {e}")
            return []


# 서비스 인스턴스
opensearch_service = OpenSearchService()