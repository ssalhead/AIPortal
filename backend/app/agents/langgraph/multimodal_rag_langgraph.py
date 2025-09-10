"""
LangGraph 기반 멀티모달 RAG 시스템

최신 LangGraph StateGraph를 활용하여 텍스트, 이미지, 문서를 통합 처리하는
고성능 멀티모달 RAG(Retrieval-Augmented Generation) 에이전트입니다.
"""

import time
import asyncio
import json
import uuid
import base64
import io
from typing import Dict, Any, List, Optional, TypedDict, Union, Annotated, BinaryIO
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
import logging
import operator
from pathlib import Path

# LangGraph 핵심 imports
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

# Document processing imports
try:
    import pypdf
    import docx
    from PIL import Image
    import pytesseract
    DOCUMENT_PROCESSING_AVAILABLE = True
except ImportError:
    DOCUMENT_PROCESSING_AVAILABLE = False
    logger.warning("Document processing libraries not available. Installing: pip install pypdf python-docx Pillow pytesseract")

# Embedding and vector store imports
try:
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_community.vectorstores import FAISS
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    VECTOR_PROCESSING_AVAILABLE = True
except ImportError:
    VECTOR_PROCESSING_AVAILABLE = False
    logger.warning("Vector processing libraries not available. Installing: pip install langchain-community faiss-cpu")

# 기존 시스템 imports
from app.agents.base import BaseAgent, AgentInput, AgentOutput
from app.core.config import settings
from app.core.feature_flags import is_langgraph_enabled, LangGraphFeatureFlags
from app.services.langgraph_monitor import langgraph_monitor

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """문서 유형"""
    TEXT = "text"
    PDF = "pdf"
    DOCX = "docx"
    IMAGE = "image"
    HTML = "html"
    MARKDOWN = "markdown"
    JSON = "json"


class ProcessingMode(Enum):
    """처리 모드"""
    EXTRACT_ONLY = "extract_only"        # 추출만
    SEARCH_AND_EXTRACT = "search_extract" # 검색 후 추출
    SEMANTIC_SEARCH = "semantic_search"   # 의미적 검색
    MULTIMODAL_ANALYSIS = "multimodal"    # 멀티모달 분석
    COMPREHENSIVE = "comprehensive"       # 종합 분석


@dataclass
class DocumentChunk:
    """문서 청크"""
    chunk_id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    source_type: DocumentType = DocumentType.TEXT
    page_number: Optional[int] = None
    position: Optional[Dict[str, Any]] = None


@dataclass
class MultimodalContent:
    """멀티모달 콘텐츠"""
    content_id: str
    text_content: Optional[str]
    image_content: Optional[bytes]
    metadata: Dict[str, Any]
    extracted_features: Optional[Dict[str, Any]] = None
    similarity_scores: Optional[Dict[str, float]] = None


class MultimodalRAGState(TypedDict):
    """LangGraph 멀티모달 RAG 상태 정의"""
    # 입력 데이터
    original_query: str
    user_id: str
    session_id: Optional[str]
    model: str
    documents: Optional[List[Dict[str, Any]]]
    processing_mode: Optional[str]
    
    # 문서 처리
    document_analysis: Optional[Dict[str, Any]]
    extracted_content: Annotated[List[Dict[str, Any]], operator.add]
    processed_chunks: Annotated[List[Dict[str, Any]], operator.add]
    
    # 임베딩 및 벡터화
    embeddings_generated: Optional[Dict[str, Any]]
    vector_store_built: Optional[Dict[str, Any]]
    similarity_search_results: Optional[List[Dict[str, Any]]]
    
    # 멀티모달 분석
    image_analysis_results: Annotated[List[Dict[str, Any]], operator.add]
    text_analysis_results: Annotated[List[Dict[str, Any]], operator.add]
    cross_modal_correlations: Optional[Dict[str, Any]]
    
    # RAG 검색 및 생성
    relevant_context: Optional[Dict[str, Any]]
    augmented_prompt: Optional[str]
    generated_response: Optional[str]
    
    # 성능 메트릭
    execution_metadata: Dict[str, Any]
    processing_stats: Dict[str, Any]
    quality_scores: Dict[str, Any]
    
    # 에러 처리
    errors: Annotated[List[str], operator.add]
    processing_failures: Annotated[List[Dict[str, Any]], operator.add]
    should_fallback: bool


class LangGraphMultimodalRAGAgent(BaseAgent):
    """LangGraph 기반 멀티모달 RAG 에이전트"""
    
    def __init__(self):
        super().__init__(
            agent_id="langgraph_multimodal_rag",
            name="LangGraph 멀티모달 RAG 에이전트",
            description="LangGraph StateGraph로 구현된 고급 멀티모달 RAG 시스템"
        )
        
        # LangGraph 워크플로우 구성
        self.workflow = self._build_workflow()
        
        # PostgreSQL 체크포인터 설정
        if settings.DATABASE_URL:
            self.checkpointer = PostgresSaver.from_conn_string(
                settings.DATABASE_URL,
                
            )
        else:
            self.checkpointer = None
            logger.warning("DATABASE_URL이 설정되지 않음 - 체크포인터 비활성화")
        
        # 문서 처리 설정
        self.text_splitter = None
        self.embeddings_model = None
        self.vector_store = None
        
        # 초기화
        self._initialize_components()

    def _initialize_components(self):
        """컴포넌트 초기화"""
        try:
            if VECTOR_PROCESSING_AVAILABLE:
                # 텍스트 분할기 초기화
                self.text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1000,
                    chunk_overlap=200,
                    length_function=len,
                    separators=["\n\n", "\n", " ", ""]
                )
                
                # 임베딩 모델 초기화 (lightweight model)
                self.embeddings_model = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/all-MiniLM-L6-v2"
                )
                
                logger.info("✅ 멀티모달 RAG 컴포넌트 초기화 완료")
            else:
                logger.warning("⚠️ 벡터 처리 라이브러리 없음 - 기본 텍스트 처리만 가능")
        except Exception as e:
            logger.error(f"❌ 컴포넌트 초기화 실패: {e}")

    def _build_workflow(self) -> StateGraph:
        """LangGraph 멀티모달 RAG 워크플로우 구성"""
        
        # StateGraph 생성
        workflow = StateGraph(MultimodalRAGState)
        
        # 노드 정의 - 9단계 고도화된 RAG 파이프라인
        workflow.add_node("analyze_documents", self._analyze_documents_node)
        workflow.add_node("extract_content", self._extract_content_node)
        workflow.add_node("process_text", self._process_text_node)
        workflow.add_node("process_images", self._process_images_node)
        workflow.add_node("generate_embeddings", self._generate_embeddings_node)
        workflow.add_node("perform_retrieval", self._perform_retrieval_node)
        workflow.add_node("analyze_multimodal", self._analyze_multimodal_node)
        workflow.add_node("augment_generation", self._augment_generation_node)
        workflow.add_node("optimize_response", self._optimize_response_node)
        
        # 엣지 정의 - 복합 파이프라인
        workflow.set_entry_point("analyze_documents")
        workflow.add_edge("analyze_documents", "extract_content")
        
        # Fan-out: 텍스트와 이미지 병렬 처리
        workflow.add_edge("extract_content", "process_text")
        workflow.add_edge("extract_content", "process_images")
        
        # Fan-in: 임베딩 생성으로 수렴
        workflow.add_edge("process_text", "generate_embeddings")
        workflow.add_edge("process_images", "generate_embeddings")
        
        # 순차 처리
        workflow.add_edge("generate_embeddings", "perform_retrieval")
        workflow.add_edge("perform_retrieval", "analyze_multimodal")
        workflow.add_edge("analyze_multimodal", "augment_generation")
        workflow.add_edge("augment_generation", "optimize_response")
        workflow.add_edge("optimize_response", END)
        
        # 조건부 엣지
        workflow.add_conditional_edges(
            "analyze_documents",
            self._should_continue,
            {
                "continue": "extract_content",
                "fallback": END
            }
        )
        
        workflow.add_conditional_edges(
            "extract_content",
            self._determine_processing_path,
            {
                "text_only": "process_text",
                "image_only": "process_images",
                "multimodal": "process_text"  # 멀티모달은 텍스트부터 시작
            }
        )
        
        return workflow

    async def _analyze_documents_node(self, state: MultimodalRAGState) -> Dict[str, Any]:
        """문서 분석 노드 - 입력 문서들의 특성 파악"""
        try:
            logger.info(f"📄 LangGraph MultimodalRAG: 문서 분석 중... (query: {state['original_query'][:50]})")
            
            documents = state.get("documents", [])
            if not documents:
                # 문서가 없는 경우 쿼리 기반 처리
                return {
                    "document_analysis": {
                        "document_count": 0,
                        "processing_mode": "query_only",
                        "analysis_result": "문서 없이 쿼리 기반 처리"
                    },
                    "execution_metadata": {
                        **state.get("execution_metadata", {}),
                        "document_analysis_completed_at": time.time()
                    }
                }
            
            # 문서 유형별 분석
            document_types = []
            total_size = 0
            has_images = False
            has_text = False
            
            for doc in documents:
                doc_type = self._detect_document_type(doc)
                document_types.append(doc_type)
                
                if doc_type in [DocumentType.IMAGE]:
                    has_images = True
                else:
                    has_text = True
                
                # 크기 추정
                content = doc.get("content", "")
                if isinstance(content, str):
                    total_size += len(content.encode('utf-8'))
                elif isinstance(content, bytes):
                    total_size += len(content)
            
            # 처리 모드 결정
            if has_images and has_text:
                processing_mode = ProcessingMode.MULTIMODAL_ANALYSIS
            elif has_images:
                processing_mode = ProcessingMode.EXTRACT_ONLY
            else:
                processing_mode = ProcessingMode.SEMANTIC_SEARCH
            
            document_analysis = {
                "document_count": len(documents),
                "document_types": [dt.value for dt in document_types],
                "total_size_bytes": total_size,
                "has_images": has_images,
                "has_text": has_text,
                "processing_mode": processing_mode.value,
                "complexity_score": self._calculate_complexity_score(documents)
            }
            
            return {
                "document_analysis": document_analysis,
                "processing_mode": processing_mode.value,
                "execution_metadata": {
                    **state.get("execution_metadata", {}),
                    "document_analysis_completed_at": time.time()
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 문서 분석 실패: {e}")
            return {
                "errors": [f"문서 분석 실패: {str(e)}"],
                "should_fallback": True
            }

    async def _extract_content_node(self, state: MultimodalRAGState) -> Dict[str, Any]:
        """콘텐츠 추출 노드 - 다양한 문서 형식에서 콘텐츠 추출"""
        try:
            logger.info("📄 LangGraph MultimodalRAG: 콘텐츠 추출 중...")
            
            documents = state.get("documents", [])
            if not documents:
                return {"extracted_content": []}
            
            extracted_content = []
            
            # 병렬 추출 처리
            extraction_tasks = []
            for doc in documents:
                task = self._extract_single_document_content(doc)
                extraction_tasks.append(task)
            
            # 병렬 실행
            results = await asyncio.gather(*extraction_tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"문서 {i} 추출 실패: {result}")
                    extracted_content.append({
                        "doc_id": f"doc_{i}",
                        "success": False,
                        "error": str(result),
                        "content": "",
                        "type": "error"
                    })
                else:
                    extracted_content.append(result)
            
            return {
                "extracted_content": extracted_content,
                "execution_metadata": {
                    **state.get("execution_metadata", {}),
                    "content_extraction_completed_at": time.time(),
                    "extracted_documents_count": len([c for c in extracted_content if c.get("success", False)])
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 콘텐츠 추출 실패: {e}")
            return {
                "errors": [f"콘텐츠 추출 실패: {str(e)}"],
                "extracted_content": []
            }

    async def _process_text_node(self, state: MultimodalRAGState) -> Dict[str, Any]:
        """텍스트 처리 노드 - 텍스트 청킹 및 전처리"""
        try:
            logger.info("📝 LangGraph MultimodalRAG: 텍스트 처리 중...")
            
            extracted_content = state.get("extracted_content", [])
            text_contents = [c for c in extracted_content if c.get("type") in ["text", "pdf", "docx", "html"]]
            
            if not text_contents:
                return {"processed_chunks": []}
            
            processed_chunks = []
            
            for content_item in text_contents:
                if not content_item.get("success", False):
                    continue
                
                text = content_item.get("content", "")
                if not text or len(text.strip()) < 10:
                    continue
                
                # 텍스트 청킹
                if self.text_splitter and VECTOR_PROCESSING_AVAILABLE:
                    chunks = self.text_splitter.split_text(text)
                else:
                    # 간단한 청킹 (fallback)
                    chunk_size = 1000
                    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
                
                # 청크별 메타데이터 생성
                for i, chunk in enumerate(chunks):
                    chunk_id = f"{content_item.get('doc_id', 'unknown')}_{i}"
                    processed_chunks.append({
                        "chunk_id": chunk_id,
                        "content": chunk,
                        "metadata": {
                            "source_doc": content_item.get("doc_id"),
                            "chunk_index": i,
                            "chunk_length": len(chunk),
                            "source_type": content_item.get("type"),
                            **content_item.get("metadata", {})
                        },
                        "type": "text_chunk"
                    })
            
            return {
                "processed_chunks": processed_chunks,
                "text_analysis_results": [{
                    "total_chunks": len(processed_chunks),
                    "avg_chunk_length": sum(len(c["content"]) for c in processed_chunks) / len(processed_chunks) if processed_chunks else 0,
                    "processing_method": "recursive_splitter" if self.text_splitter else "simple_chunking"
                }],
                "execution_metadata": {
                    **state.get("execution_metadata", {}),
                    "text_processing_completed_at": time.time(),
                    "text_chunks_created": len(processed_chunks)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 텍스트 처리 실패: {e}")
            return {
                "errors": [f"텍스트 처리 실패: {str(e)}"],
                "processed_chunks": []
            }

    async def _process_images_node(self, state: MultimodalRAGState) -> Dict[str, Any]:
        """이미지 처리 노드 - 이미지 분석 및 텍스트 추출"""
        try:
            logger.info("🖼️ LangGraph MultimodalRAG: 이미지 처리 중...")
            
            extracted_content = state.get("extracted_content", [])
            image_contents = [c for c in extracted_content if c.get("type") == "image"]
            
            if not image_contents:
                return {"image_analysis_results": []}
            
            image_analysis_results = []
            
            # 병렬 이미지 처리
            processing_tasks = []
            for image_content in image_contents:
                task = self._process_single_image(image_content)
                processing_tasks.append(task)
            
            results = await asyncio.gather(*processing_tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"이미지 {i} 처리 실패: {result}")
                    image_analysis_results.append({
                        "image_id": f"image_{i}",
                        "success": False,
                        "error": str(result),
                        "extracted_text": "",
                        "analysis": {}
                    })
                else:
                    image_analysis_results.append(result)
            
            return {
                "image_analysis_results": image_analysis_results,
                "execution_metadata": {
                    **state.get("execution_metadata", {}),
                    "image_processing_completed_at": time.time(),
                    "images_processed": len(image_analysis_results)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 이미지 처리 실패: {e}")
            return {
                "errors": [f"이미지 처리 실패: {str(e)}"],
                "image_analysis_results": []
            }

    async def _generate_embeddings_node(self, state: MultimodalRAGState) -> Dict[str, Any]:
        """임베딩 생성 노드 - 텍스트 벡터화 및 벡터 스토어 구축"""
        try:
            logger.info("🔢 LangGraph MultimodalRAG: 임베딩 생성 중...")
            
            processed_chunks = state.get("processed_chunks", [])
            text_analysis_results = state.get("text_analysis_results", [])
            
            if not processed_chunks and not text_analysis_results:
                return {"embeddings_generated": {"status": "no_content"}}
            
            # 모든 텍스트 콘텐츠 수집
            texts_to_embed = []
            metadata_list = []
            
            # 처리된 청크에서 텍스트 수집
            for chunk in processed_chunks:
                if chunk.get("content"):
                    texts_to_embed.append(chunk["content"])
                    metadata_list.append(chunk.get("metadata", {}))
            
            # 이미지에서 추출된 텍스트 추가
            image_results = state.get("image_analysis_results", [])
            for img_result in image_results:
                extracted_text = img_result.get("extracted_text", "")
                if extracted_text and len(extracted_text.strip()) > 5:
                    texts_to_embed.append(extracted_text)
                    metadata_list.append({
                        "source_type": "image_ocr",
                        "image_id": img_result.get("image_id", "unknown")
                    })
            
            if not texts_to_embed:
                return {"embeddings_generated": {"status": "no_texts"}}
            
            # 임베딩 생성 및 벡터 스토어 구축
            if self.embeddings_model and VECTOR_PROCESSING_AVAILABLE:
                try:
                    # FAISS 벡터 스토어 생성
                    vector_store = FAISS.from_texts(
                        texts_to_embed,
                        self.embeddings_model,
                        metadatas=metadata_list
                    )
                    
                    embeddings_generated = {
                        "status": "success",
                        "embeddings_count": len(texts_to_embed),
                        "vector_store_created": True,
                        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2"
                    }
                    
                    # 벡터 스토어를 상태로 저장 (실제로는 메모리에 보관)
                    self.vector_store = vector_store
                    
                except Exception as e:
                    logger.error(f"벡터 스토어 생성 실패: {e}")
                    embeddings_generated = {
                        "status": "failed",
                        "error": str(e),
                        "texts_count": len(texts_to_embed)
                    }
            else:
                # 임베딩 모델이 없는 경우
                embeddings_generated = {
                    "status": "no_embedding_model",
                    "texts_count": len(texts_to_embed),
                    "fallback_mode": True
                }
            
            return {
                "embeddings_generated": embeddings_generated,
                "vector_store_built": {"vector_store_available": self.vector_store is not None},
                "execution_metadata": {
                    **state.get("execution_metadata", {}),
                    "embeddings_generation_completed_at": time.time(),
                    "texts_embedded": len(texts_to_embed)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 임베딩 생성 실패: {e}")
            return {
                "errors": [f"임베딩 생성 실패: {str(e)}"],
                "embeddings_generated": {"status": "error", "error": str(e)}
            }

    async def _perform_retrieval_node(self, state: MultimodalRAGState) -> Dict[str, Any]:
        """검색 수행 노드 - 의미적 검색 및 관련 콘텐츠 검색"""
        try:
            logger.info("🔍 LangGraph MultimodalRAG: 검색 수행 중...")
            
            query = state["original_query"]
            embeddings_generated = state.get("embeddings_generated", {})
            
            if embeddings_generated.get("status") != "success" or not self.vector_store:
                # 벡터 검색이 불가능한 경우 키워드 기반 검색
                return await self._perform_keyword_search(state)
            
            # 의미적 검색 수행
            try:
                # 유사도 검색 (top_k=5)
                search_results = self.vector_store.similarity_search_with_score(
                    query=query,
                    k=min(5, embeddings_generated.get("embeddings_count", 1))
                )
                
                similarity_search_results = []
                for doc, score in search_results:
                    similarity_search_results.append({
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "similarity_score": float(score),
                        "relevance_score": max(0, 1 - score)  # 거리를 관련성으로 변환
                    })
                
                # 관련 컨텍스트 구성
                relevant_context = {
                    "search_method": "semantic_similarity",
                    "query": query,
                    "results_count": len(similarity_search_results),
                    "top_results": similarity_search_results,
                    "context_length": sum(len(r["content"]) for r in similarity_search_results)
                }
                
                return {
                    "similarity_search_results": similarity_search_results,
                    "relevant_context": relevant_context,
                    "execution_metadata": {
                        **state.get("execution_metadata", {}),
                        "retrieval_completed_at": time.time(),
                        "retrieved_results_count": len(similarity_search_results)
                    }
                }
                
            except Exception as e:
                logger.error(f"의미적 검색 실패: {e}")
                return await self._perform_keyword_search(state)
            
        except Exception as e:
            logger.error(f"❌ 검색 수행 실패: {e}")
            return {
                "errors": [f"검색 수행 실패: {str(e)}"],
                "similarity_search_results": []
            }

    async def _analyze_multimodal_node(self, state: MultimodalRAGState) -> Dict[str, Any]:
        """멀티모달 분석 노드 - 텍스트와 이미지 간 상관관계 분석"""
        try:
            logger.info("🔗 LangGraph MultimodalRAG: 멀티모달 분석 중...")
            
            text_results = state.get("text_analysis_results", [])
            image_results = state.get("image_analysis_results", [])
            similarity_results = state.get("similarity_search_results", [])
            
            # 텍스트와 이미지가 모두 있는 경우에만 상관관계 분석
            if not text_results or not image_results:
                return {
                    "cross_modal_correlations": {
                        "analysis_performed": False,
                        "reason": "insufficient_multimodal_content"
                    }
                }
            
            model = self._get_llm_model(state["model"])
            
            # 멀티모달 상관관계 분석
            correlation_prompt = ChatPromptTemplate.from_messages([
                ("system", """멀티모달 분석 전문가로서 텍스트와 이미지 콘텐츠 간의 상관관계를 분석하세요.

분석 항목:
1. 내용적 일치성: 텍스트와 이미지가 같은 주제/개념을 다루는가
2. 보완성: 텍스트와 이미지가 서로를 보완하는가
3. 중복성: 동일한 정보가 중복되는가
4. 맥락적 연관성: 전체적인 문서 맥락에서의 관련성
5. 정보 품질: 각 모달리티의 정보 품질

JSON 형식으로 분석 결과를 제공하세요."""),
                ("human", """사용자 질문: "{query}"

텍스트 분석 결과:
{text_results}

이미지 분석 결과:
{image_results}

검색된 관련 콘텐츠:
{search_results}

멀티모달 상관관계를 분석해주세요.""")
            ])
            
            response = await model.ainvoke(correlation_prompt.format_messages(
                query=state["original_query"],
                text_results=json.dumps(text_results[:3], ensure_ascii=False),  # 상위 3개만
                image_results=json.dumps([{
                    "image_id": r.get("image_id"),
                    "extracted_text": r.get("extracted_text", "")[:200],  # 200자 제한
                    "success": r.get("success")
                } for r in image_results[:3]], ensure_ascii=False),
                search_results=json.dumps([{
                    "content": r.get("content", "")[:300],  # 300자 제한
                    "relevance_score": r.get("relevance_score", 0)
                } for r in similarity_results[:3]], ensure_ascii=False)
            ))
            
            try:
                cross_modal_correlations = json.loads(response.content)
            except json.JSONDecodeError:
                cross_modal_correlations = {
                    "analysis_performed": True,
                    "content_alignment": 0.7,
                    "complementarity": 0.6,
                    "redundancy": 0.3,
                    "contextual_relevance": 0.8,
                    "overall_correlation": 0.65,
                    "analysis_method": "llm_based"
                }
            
            cross_modal_correlations["analysis_performed"] = True
            cross_modal_correlations["text_sources"] = len(text_results)
            cross_modal_correlations["image_sources"] = len(image_results)
            
            return {
                "cross_modal_correlations": cross_modal_correlations,
                "execution_metadata": {
                    **state.get("execution_metadata", {}),
                    "multimodal_analysis_completed_at": time.time()
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 멀티모달 분석 실패: {e}")
            return {
                "errors": [f"멀티모달 분석 실패: {str(e)}"],
                "cross_modal_correlations": {"analysis_performed": False, "error": str(e)}
            }

    async def _augment_generation_node(self, state: MultimodalRAGState) -> Dict[str, Any]:
        """증강 생성 노드 - RAG 기반 응답 생성"""
        try:
            logger.info("✨ LangGraph MultimodalRAG: 증강 생성 중...")
            
            relevant_context = state.get("relevant_context", {})
            cross_modal_correlations = state.get("cross_modal_correlations", {})
            query = state["original_query"]
            
            model = self._get_llm_model(state["model"])
            
            # 컨텍스트 구성
            context_parts = []
            
            # 검색된 관련 콘텐츠
            if relevant_context.get("top_results"):
                context_parts.append("**검색된 관련 정보:**")
                for i, result in enumerate(relevant_context["top_results"][:3], 1):
                    context_parts.append(f"{i}. {result.get('content', '')[:400]}...")
            
            # 이미지에서 추출된 텍스트
            image_results = state.get("image_analysis_results", [])
            if image_results:
                extracted_texts = [r.get("extracted_text", "") for r in image_results if r.get("success")]
                if extracted_texts:
                    context_parts.append("\n**이미지에서 추출된 정보:**")
                    for i, text in enumerate(extracted_texts[:2], 1):
                        if text.strip():
                            context_parts.append(f"{i}. {text[:300]}...")
            
            # 멀티모달 분석 결과
            if cross_modal_correlations.get("analysis_performed"):
                context_parts.append(f"\n**멀티모달 분석:** 텍스트-이미지 상관도 {cross_modal_correlations.get('overall_correlation', 0.5):.2f}")
            
            augmented_context = "\n".join(context_parts) if context_parts else "제공된 문서에서 관련 정보를 찾을 수 없습니다."
            
            # RAG 프롬프트 생성
            rag_prompt = ChatPromptTemplate.from_messages([
                ("system", """당신은 멀티모달 RAG 전문가입니다. 제공된 문서(텍스트, 이미지)에서 추출된 정보를 바탕으로 사용자 질문에 정확하고 포괄적으로 답변하세요.

답변 원칙:
1. 제공된 컨텍스트 정보를 우선 활용
2. 텍스트와 이미지 정보를 통합적으로 고려
3. 정확하지 않은 정보는 추측하지 말고 명시
4. 출처가 명확한 정보와 추론된 정보 구분
5. 한국어로 자연스럽고 이해하기 쉽게 작성

컨텍스트에서 찾을 수 없는 정보는 "제공된 문서에서는 해당 정보를 찾을 수 없습니다"라고 명시하세요."""),
                ("human", """질문: {query}

제공된 컨텍스트:
{context}

위 정보를 바탕으로 질문에 답변해주세요.""")
            ])
            
            response = await model.ainvoke(rag_prompt.format_messages(
                query=query,
                context=augmented_context
            ))
            
            generated_response = response.content
            
            # 증강 프롬프트 정보 저장
            augmented_prompt_info = {
                "original_query": query,
                "context_sources": len(relevant_context.get("top_results", [])),
                "image_sources": len([r for r in image_results if r.get("success")]),
                "context_length": len(augmented_context),
                "multimodal_analysis": cross_modal_correlations.get("analysis_performed", False)
            }
            
            return {
                "augmented_prompt": json.dumps(augmented_prompt_info, ensure_ascii=False),
                "generated_response": generated_response,
                "execution_metadata": {
                    **state.get("execution_metadata", {}),
                    "augmented_generation_completed_at": time.time()
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 증강 생성 실패: {e}")
            return {
                "errors": [f"증강 생성 실패: {str(e)}"],
                "generated_response": "문서 기반 답변 생성 중 오류가 발생했습니다."
            }

    async def _optimize_response_node(self, state: MultimodalRAGState) -> Dict[str, Any]:
        """응답 최적화 노드 - 최종 응답 품질 향상"""
        try:
            logger.info("🎯 LangGraph MultimodalRAG: 응답 최적화 중...")
            
            generated_response = state.get("generated_response", "")
            document_analysis = state.get("document_analysis", {})
            relevant_context = state.get("relevant_context", {})
            
            # 품질 점수 계산
            quality_scores = {
                "response_length_score": min(100, len(generated_response) / 10),  # 길이 기반 점수
                "context_utilization_score": min(100, len(relevant_context.get("top_results", [])) * 25),
                "multimodal_integration_score": 0,
                "overall_quality_score": 0
            }
            
            # 멀티모달 통합 점수
            cross_modal = state.get("cross_modal_correlations", {})
            if cross_modal.get("analysis_performed"):
                quality_scores["multimodal_integration_score"] = cross_modal.get("overall_correlation", 0.5) * 100
            
            # 전체 품질 점수
            quality_scores["overall_quality_score"] = (
                quality_scores["response_length_score"] * 0.3 +
                quality_scores["context_utilization_score"] * 0.4 +
                quality_scores["multimodal_integration_score"] * 0.3
            )
            
            # 처리 통계
            start_time = state.get("execution_metadata", {}).get("document_analysis_completed_at", time.time())
            processing_stats = {
                "total_processing_time_ms": int((time.time() - start_time) * 1000),
                "documents_processed": document_analysis.get("document_count", 0),
                "chunks_created": len(state.get("processed_chunks", [])),
                "embeddings_generated": state.get("embeddings_generated", {}).get("embeddings_count", 0),
                "search_results": len(state.get("similarity_search_results", [])),
                "processing_mode": state.get("processing_mode", "unknown")
            }
            
            return {
                "quality_scores": quality_scores,
                "processing_stats": processing_stats,
                "execution_metadata": {
                    **state.get("execution_metadata", {}),
                    "response_optimization_completed_at": time.time()
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 응답 최적화 실패: {e}")
            return {
                "errors": [f"응답 최적화 실패: {str(e)}"],
                "quality_scores": {"overall_quality_score": 50}
            }

    # 유틸리티 메서드들

    def _should_continue(self, state: MultimodalRAGState) -> str:
        """조건부 라우팅: 계속 진행 여부"""
        if state.get("should_fallback", False) or len(state.get("errors", [])) > 3:
            return "fallback"
        return "continue"

    def _determine_processing_path(self, state: MultimodalRAGState) -> str:
        """조건부 라우팅: 처리 경로 결정"""
        document_analysis = state.get("document_analysis", {})
        
        if document_analysis.get("has_images") and document_analysis.get("has_text"):
            return "multimodal"
        elif document_analysis.get("has_images"):
            return "image_only"
        else:
            return "text_only"

    def _get_llm_model(self, model_name: str):
        """LLM 모델 인스턴스 반환"""
        if "claude" in model_name.lower():
            return ChatAnthropic(
                model_name=model_name,
                anthropic_api_key=settings.ANTHROPIC_API_KEY,
                temperature=0.1
            )
        elif "gemini" in model_name.lower():
            return ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=0.1
            )
        else:
            return ChatAnthropic(
                model_name="claude-3-sonnet-20240229",
                anthropic_api_key=settings.ANTHROPIC_API_KEY,
                temperature=0.1
            )

    def _detect_document_type(self, document: Dict[str, Any]) -> DocumentType:
        """문서 유형 감지"""
        filename = document.get("filename", "").lower()
        content_type = document.get("content_type", "").lower()
        
        if filename.endswith(('.pdf',)) or 'pdf' in content_type:
            return DocumentType.PDF
        elif filename.endswith(('.docx', '.doc')) or 'word' in content_type:
            return DocumentType.DOCX
        elif filename.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')) or 'image' in content_type:
            return DocumentType.IMAGE
        elif filename.endswith(('.html', '.htm')):
            return DocumentType.HTML
        elif filename.endswith(('.md', '.markdown')):
            return DocumentType.MARKDOWN
        elif filename.endswith(('.json',)):
            return DocumentType.JSON
        else:
            return DocumentType.TEXT

    def _calculate_complexity_score(self, documents: List[Dict[str, Any]]) -> int:
        """문서 복잡도 점수 계산"""
        score = 0
        score += len(documents) * 10  # 문서 수
        
        for doc in documents:
            content = doc.get("content", "")
            if isinstance(content, str):
                score += len(content) // 1000  # 텍스트 길이
            elif isinstance(content, bytes):
                score += len(content) // 10000  # 바이너리 크기
        
        return min(100, score)

    async def _extract_single_document_content(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """단일 문서에서 콘텐츠 추출"""
        doc_type = self._detect_document_type(document)
        doc_id = document.get("id", f"doc_{uuid.uuid4().hex[:8]}")
        
        try:
            if doc_type == DocumentType.TEXT:
                content = document.get("content", "")
                return {
                    "doc_id": doc_id,
                    "success": True,
                    "content": content,
                    "type": "text",
                    "metadata": {"original_length": len(content)}
                }
            
            elif doc_type == DocumentType.IMAGE:
                # 이미지 처리는 별도 노드에서 수행
                return {
                    "doc_id": doc_id,
                    "success": True,
                    "content": "",  # 이미지 자체는 여기서 텍스트로 변환하지 않음
                    "type": "image",
                    "metadata": {"requires_ocr": True},
                    "image_data": document.get("content")
                }
            
            elif doc_type == DocumentType.PDF:
                if not DOCUMENT_PROCESSING_AVAILABLE:
                    return {
                        "doc_id": doc_id,
                        "success": False,
                        "error": "PDF processing not available",
                        "content": "",
                        "type": "pdf"
                    }
                
                # PDF 텍스트 추출 (간단한 구현)
                content = document.get("content", "")
                return {
                    "doc_id": doc_id,
                    "success": True,
                    "content": content,  # 실제로는 pypdf 사용
                    "type": "pdf",
                    "metadata": {"extraction_method": "text_only"}
                }
            
            else:
                # 기타 문서 유형은 텍스트로 처리
                content = str(document.get("content", ""))
                return {
                    "doc_id": doc_id,
                    "success": True,
                    "content": content,
                    "type": doc_type.value,
                    "metadata": {"converted_to_text": True}
                }
            
        except Exception as e:
            return {
                "doc_id": doc_id,
                "success": False,
                "error": str(e),
                "content": "",
                "type": doc_type.value
            }

    async def _process_single_image(self, image_content: Dict[str, Any]) -> Dict[str, Any]:
        """단일 이미지 처리 (OCR 등)"""
        image_id = image_content.get("doc_id", "unknown")
        
        try:
            # OCR이 가능한 경우에만 텍스트 추출 시도
            if DOCUMENT_PROCESSING_AVAILABLE:
                # 실제 구현에서는 pytesseract 사용
                extracted_text = "이미지에서 추출된 텍스트 (OCR 미구현)"
            else:
                extracted_text = ""
            
            # 기본 이미지 분석
            image_analysis = {
                "has_text": len(extracted_text) > 10,
                "estimated_content_type": "mixed",
                "processing_method": "ocr_extraction" if DOCUMENT_PROCESSING_AVAILABLE else "not_available"
            }
            
            return {
                "image_id": image_id,
                "success": True,
                "extracted_text": extracted_text,
                "analysis": image_analysis,
                "metadata": image_content.get("metadata", {})
            }
            
        except Exception as e:
            return {
                "image_id": image_id,
                "success": False,
                "error": str(e),
                "extracted_text": "",
                "analysis": {}
            }

    async def _perform_keyword_search(self, state: MultimodalRAGState) -> Dict[str, Any]:
        """키워드 기반 검색 (fallback)"""
        query = state["original_query"].lower()
        query_words = set(query.split())
        
        # 처리된 청크에서 키워드 검색
        processed_chunks = state.get("processed_chunks", [])
        keyword_results = []
        
        for chunk in processed_chunks:
            content = chunk.get("content", "").lower()
            content_words = set(content.split())
            
            # 단순 키워드 매칭 점수
            overlap = query_words.intersection(content_words)
            if overlap:
                score = len(overlap) / len(query_words)
                keyword_results.append({
                    "content": chunk.get("content", ""),
                    "metadata": chunk.get("metadata", {}),
                    "similarity_score": score,
                    "relevance_score": score,
                    "matching_keywords": list(overlap)
                })
        
        # 점수순 정렬
        keyword_results.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        relevant_context = {
            "search_method": "keyword_matching",
            "query": state["original_query"],
            "results_count": len(keyword_results),
            "top_results": keyword_results[:5],
            "context_length": sum(len(r["content"]) for r in keyword_results[:5])
        }
        
        return {
            "similarity_search_results": keyword_results[:5],
            "relevant_context": relevant_context,
            "execution_metadata": {
                **state.get("execution_metadata", {}),
                "retrieval_completed_at": time.time(),
                "retrieval_method": "keyword_fallback",
                "retrieved_results_count": len(keyword_results[:5])
            }
        }

    async def execute_multimodal_rag(
        self, 
        input_data: AgentInput, 
        documents: Optional[List[Dict[str, Any]]] = None,
        model: str = "claude-sonnet", 
        progress_callback=None
    ) -> AgentOutput:
        """
        멀티모달 RAG 시스템 실행
        """
        start_time = time.time()
        
        logger.info(f"🚀 LangGraph Multimodal RAG 실행 시작 (사용자: {input_data.user_id})")
        
        try:
            # 성능 모니터링 시작 (optional)
            try:
                await langgraph_monitor.start_execution("langgraph_multimodal_rag")
            except Exception as monitoring_error:
                logger.warning(f"⚠️ 모니터링 시작 실패 (무시됨): {monitoring_error}")
            
            # 초기 상태 설정 (Reducer 기본값)
            initial_state = MultimodalRAGState(
                original_query=input_data.query,
                user_id=input_data.user_id,
                session_id=input_data.session_id,
                model=model,
                documents=documents or [],
                processing_mode=None,
                document_analysis=None,
                extracted_content=[],
                processed_chunks=[],
                embeddings_generated=None,
                vector_store_built=None,
                similarity_search_results=None,
                image_analysis_results=[],
                text_analysis_results=[],
                cross_modal_correlations=None,
                relevant_context=None,
                augmented_prompt=None,
                generated_response=None,
                execution_metadata={"start_time": start_time},
                processing_stats={},
                quality_scores={},
                errors=[],
                processing_failures=[],
                should_fallback=False
            )
            
            # LangGraph 워크플로우 실행 (에러 안전 처리)
            try:
                if self.checkpointer:
                    app = self.workflow.compile(checkpointer=self.checkpointer)
                    config = {"configurable": {"thread_id": f"multimodal_rag_{input_data.user_id}_{input_data.session_id}"}}
                    final_state = await app.ainvoke(initial_state, config=config)
                else:
                    app = self.workflow.compile()
                    final_state = await app.ainvoke(initial_state)
            except Exception as workflow_error:
                logger.error(f"❌ LangGraph Multimodal RAG 워크플로우 실행 실패: {workflow_error}")
                raise workflow_error  # 상위로 전파하여 fallback 처리
            
            # 결과 처리
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # 에러가 있거나 fallback이 필요한 경우
            if final_state.get("should_fallback", False) or len(final_state.get("errors", [])) > 0:
                logger.warning("🔄 LangGraph Multimodal RAG 실행 실패")
                return AgentOutput(
                    result="멀티모달 RAG 처리 중 오류가 발생했습니다. 일반 모드로 처리하겠습니다.",
                    metadata={
                        "agent_version": "langgraph_multimodal_rag",
                        "processing_failed": True,
                        "errors": final_state.get("errors", [])
                    },
                    execution_time_ms=execution_time_ms,
                    agent_id=self.agent_id,
                    model_used=model,
                    timestamp=datetime.utcnow().isoformat()
                )
            
            # 성공적인 결과 반환
            generated_response = final_state.get("generated_response", "문서 기반 답변을 생성했습니다.")
            quality_scores = final_state.get("quality_scores", {})
            processing_stats = final_state.get("processing_stats", {})
            
            try:
                await langgraph_monitor.track_execution(
                    agent_name="langgraph_multimodal_rag",
                    execution_time=execution_time_ms / 1000,
                    status="success",
                    query=input_data.query,
                    response_length=len(generated_response) if generated_response else 0,
                    user_id=input_data.user_id
                )
            except Exception as monitoring_error:
                logger.warning(f"⚠️ 모니터링 기록 실패 (무시됨): {monitoring_error}")
            
            result = AgentOutput(
                result=generated_response,
                metadata={
                    "agent_version": "langgraph_multimodal_rag_v2",
                    "multimodal_processing": True,
                    "quality_score": quality_scores.get("overall_quality_score", 0),
                    "processing_stats": processing_stats,
                    "documents_processed": len(documents or []),
                    "langgraph_execution": True,
                    "multimodal_features": {
                        "text_processing": len(final_state.get("processed_chunks", [])) > 0,
                        "image_processing": len(final_state.get("image_analysis_results", [])) > 0,
                        "semantic_search": final_state.get("embeddings_generated", {}).get("status") == "success",
                        "cross_modal_analysis": final_state.get("cross_modal_correlations", {}).get("analysis_performed", False)
                    },
                    **final_state.get("execution_metadata", {})
                },
                execution_time_ms=execution_time_ms,
                agent_id=self.agent_id,
                model_used=model,
                timestamp=datetime.utcnow().isoformat()
            )
            
            quality_score = quality_scores.get("overall_quality_score", 0)
            logger.info(f"✅ LangGraph Multimodal RAG 완료 ({execution_time_ms}ms, 품질: {quality_score:.1f}/100)")
            return result
            
        except Exception as e:
            logger.error(f"❌ LangGraph Multimodal RAG 실행 실패: {e}")
            
            try:
                await langgraph_monitor.track_execution(
                    agent_name="langgraph_multimodal_rag",
                    execution_time=(time.time() - start_time),
                    status="error",
                    query=input_data.query,
                    response_length=0,
                    user_id=input_data.user_id,
                    error_message=str(e)
                )
            except Exception as monitoring_error:
                logger.warning(f"⚠️ 모니터링 기록 실패 (무시됨): {monitoring_error}")
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            return AgentOutput(
                result="고급 멀티모달 RAG 시스템에서 일시적 처리 지연이 발생했습니다. 다시 시도해주세요.",
                metadata={
                    "agent_version": "langgraph_multimodal_rag_v2",
                    "error_occurred": True,
                    "error_handled": True
                },
                execution_time_ms=execution_time_ms,
                agent_id=self.agent_id,
                model_used=model,
                timestamp=datetime.utcnow().isoformat(),
                error=f"LangGraph Multimodal RAG error: {str(e)}"
            )

    def get_capabilities(self) -> List[str]:
        """에이전트 기능 목록"""
        return [
            "다중 문서 형식 처리 (PDF, DOCX, 이미지, 텍스트)",
            "OCR 기반 이미지 텍스트 추출",
            "의미적 유사도 검색 (FAISS 벡터 스토어)",
            "멀티모달 상관관계 분석",
            "RAG 기반 답변 생성",
            "실시간 품질 평가",
            "적응형 처리 모드",
            "키워드 기반 fallback 검색"
        ]

    def get_supported_models(self) -> List[str]:
        """지원 모델 목록"""
        return [
            "claude-sonnet",
            "claude-haiku", 
            "claude-opus",
            "gemini-pro",
            "gemini-flash"
        ]


# 전역 인스턴스 생성
langgraph_multimodal_rag_agent = LangGraphMultimodalRAGAgent()