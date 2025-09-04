# Gemini Image Editing Implementation Guide

## 🎯 **개요**

Gemini 2.5 Flash Image Preview 모델을 이용한 실시간 이미지 편집 시스템의 완전한 구현 가이드입니다.

## 🏗️ **아키텍처 구조**

```
Frontend (React/TypeScript)
├── SimpleImageWorkspace.tsx     # Canvas 편집 UI
├── simpleImageHistoryStore.ts   # Zustand 상태 관리
└── API Client                   # HTTP 요청 처리

Backend (FastAPI/Python)  
├── simple_image_history.py      # REST API 엔드포인트
├── image_generation_service.py  # Gemini API 서비스
└── ImageHistory Model           # PostgreSQL 데이터 모델

Google Cloud Platform
├── Vertex AI (global region)   # Gemini 2.5 Flash Image Preview
├── Service Account Auth         # 인증 및 권한 관리
└── Generated Images Storage     # 이미지 파일 저장소
```

## 🔧 **기술적 구현**

### **1. Backend Implementation**

#### **Google GenAI 라이브러리 설정**
```python
# /backend/app/services/image_generation_service.py

from google import genai
from google.genai.types import GenerateContentConfig
from google.oauth2 import service_account

# Vertex AI 클라이언트 초기화
credentials = service_account.Credentials.from_service_account_file(
    self.google_credentials,
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)

self.gemini_client = genai.Client(
    location="global",  # Image Preview 모델은 global 리전 사용
    project=self.google_project_id,
    credentials=credentials,
    vertexai=True
)
```

#### **이미지 편집 API 호출**
```python
async def edit_image_with_gemini(self, job_id: str, user_id: str, prompt: str, 
                                reference_image_url: str, optimize_prompt: bool = False):
    """Gemini 2.5 Flash Image Preview를 이용한 이미지 편집"""
    
    # 1. 참조 이미지 로드
    reference_image = await self._load_reference_image_with_fallback(reference_image_url)
    
    # 2. 편집 명령 구성
    edit_instruction = f"Edit this image as follows: {prompt}. Keep the original style and composition while making the requested changes naturally."
    
    # 3. Gemini API 호출
    config = GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],
        candidate_count=1,
    )
    
    response = self.gemini_client.models.generate_content(
        model=self.gemini_model_id,
        contents=[edit_instruction, reference_image],
        config=config
    )
    
    # 4. 응답 처리 및 이미지 저장
    images = []
    for i, part in enumerate(response.candidates[0].content.parts):
        if hasattr(part, 'inline_data') and part.inline_data:
            # Google 공식 예제 패턴
            from io import BytesIO
            image = PILImage.open(BytesIO(part.inline_data.data))
            
            # 파일로 저장
            saved_url = await self._save_gemini_image(image, job_id, i)
            images.append(saved_url)
    
    return {"images": images, "status": "completed"}
```

#### **향상된 이미지 저장 로직**
```python
async def _save_gemini_image(self, image, job_id: str, index: int) -> str:
    """향상된 로깅과 함께 Gemini 이미지 저장"""
    
    start_time = time.time()
    logger.info(f"💾 Gemini 이미지 저장 시작: {job_id}_{index}")
    
    try:
        # 파일 경로 설정
        filename = f"{job_id}_gemini_edit_{index}.png"
        file_path = image_dir / filename
        
        # 이미지 정보 로깅
        if hasattr(image, 'size'):
            logger.info(f"🖼️ 이미지 크기: {image.size[0]}x{image.size[1]}")
        
        # 이미지 저장
        save_start = time.time()
        image.save(str(file_path), "PNG")
        save_duration = time.time() - save_start
        
        # 저장 결과 검증
        if file_path.exists():
            file_size = file_path.stat().st_size
            logger.info(f"✅ 이미지 저장 성공: {filename} ({file_size:,} bytes, {save_duration:.3f}초)")
        
        # URL 반환
        image_url = f"{base_url}/api/v1/images/generated/{filename}"
        
        # 파일 접근성 비동기 확인
        asyncio.create_task(self._verify_file_accessibility(file_path, image_url))
        
        return image_url
        
    except Exception as e:
        # Base64 fallback
        logger.error(f"❌ 저장 실패, Base64 대체: {e}")
        # ... fallback logic
```

### **2. Frontend Implementation**

#### **API 응답 매핑 보정**
```typescript
// /frontend/src/stores/simpleImageHistoryStore.ts

// snake_case → camelCase 자동 매핑
const primaryImageUrl = newImage.primaryImageUrl || (newImage as any).primary_image_url;

// fallback을 위한 배열 접근
const finalImageUrl = primaryImageUrl || 
                     (newImage.imageUrls && newImage.imageUrls[0]) || 
                     ((newImage as any).image_urls && (newImage as any).image_urls[0]);

console.log('🔍 최종 이미지 URL:', finalImageUrl);
```

#### **30단계 이미지 접근성 확인**
```typescript
const waitForImageAvailability = async (imageUrl: string, maxRetries: number = 30): Promise<boolean> => {
  // undefined 체크
  if (!imageUrl || imageUrl === 'undefined' || imageUrl === 'null') {
    console.warn(`⚠️ 이미지 접근성 확인 생략 - 잘못된 URL: ${imageUrl}`);
    return false;
  }
  
  for (let i = 0; i < maxRetries; i++) {
    try {
      // 고급 캐시 버스팅
      const timestamp = Date.now();
      const uniqueId = Math.random().toString(36).substring(7);
      const timestampedUrl = `${imageUrl}?t=${timestamp}&retry=${i}&uid=${uniqueId}`;
      
      // HTTP HEAD 요청
      const response = await fetch(timestampedUrl, { 
        method: 'HEAD',
        cache: 'no-cache',
        headers: {
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'Pragma': 'no-cache',
          'Expires': '0',
          'If-None-Match': '*'
        }
      });
      
      if (response.ok && response.status === 200) {
        // 실제 이미지 로딩 검증
        return await verifyImageLoading(timestampedUrl);
      }
      
    } catch (error) {
      console.log(`❌ 이미지 접근 오류 (${i + 1}/${maxRetries}):`, error);
    }
    
    // 적응형 지연 시간
    let delay;
    if (i < 3) delay = 100;        // 첫 3번: 100ms (빠른 확인)
    else if (i < 8) delay = 300;   // 다음 5번: 300ms
    else if (i < 15) delay = 800;  // 다음 7번: 800ms  
    else if (i < 22) delay = 1500; // 다음 7번: 1.5초
    else delay = 2500;             // 나머지: 2.5초
    
    await new Promise(resolve => setTimeout(resolve, delay));
  }
  
  return false;
};
```

#### **실제 이미지 로딩 검증**
```typescript
const verifyImageLoading = async (imageUrl: string): Promise<boolean> => {
  return new Promise((resolve) => {
    const img = new Image();
    const timeout = setTimeout(() => {
      console.warn(`⚠️ 이미진 로딩 타임아웃: ${imageUrl}`);
      resolve(false);
    }, 3000);
    
    img.onload = () => {
      clearTimeout(timeout);
      console.log(`✅ 실제 이미진 로딩 성공: ${imageUrl} (${img.width}x${img.height})`);
      resolve(true);
    };
    
    img.onerror = () => {
      clearTimeout(timeout);
      console.warn(`❌ 실제 이미진 로딩 실패: ${imageUrl}`);
      resolve(false);
    };
    
    img.src = imageUrl;
  });
};
```

#### **강화된 DOM 조작 새로고침**
```typescript
const forceImageRefresh = async (imageUrl: string, retries: number = 3): Promise<void> => {
  // URL 유효성 검증
  if (!imageUrl || imageUrl === 'undefined' || imageUrl === 'null') {
    console.warn(`⚠️ 이미진 새로고침 생략 - 잘못된 URL: ${imageUrl}`);
    return;
  }
  
  for (let i = 0; i < retries; i++) {
    try {
      const imageElements = document.querySelectorAll('img') as NodeListOf<HTMLImageElement>;
      let refreshCount = 0;
      
      const baseUrl = imageUrl.split('?')[0];
      
      imageElements.forEach((img) => {
        if (img.src && img.src.includes(baseUrl)) {
          const originalSrc = img.src.split('?')[0];
          const newSrc = `${originalSrc}?t=${Date.now()}&refresh=${i}&uid=${Math.random().toString(36).substring(7)}`;
          
          // 로딩 상태 추적
          img.onload = () => console.log(`✅ 이미진 새로고침 성공: ${newSrc}`);
          img.onerror = () => console.warn(`❌ 이미진 새로고침 실패: ${newSrc}`);
          
          img.src = newSrc;
          refreshCount++;
        }
      });
      
      if (refreshCount > 0) {
        console.log(`🔄 ${refreshCount}개 이미진 새로고침 적용 (${i + 1}/${retries})`);
        await new Promise(resolve => setTimeout(resolve, 500));
      }
      
    } catch (error) {
      console.warn(`⚠️ 이미진 새로고침 중 오류 (${i + 1}/${retries}):`, error);
    }
  }
};
```

#### **Canvas 컴포넌트 이벤트 처리**
```typescript
// /frontend/src/components/canvas/SimpleImageWorkspace.tsx

useEffect(() => {
  const handleImageUpdate = (event: CustomEvent) => {
    const { conversationId: eventConversationId, imageId, imageUrl } = event.detail;
    
    if (eventConversationId === conversationId) {
      // 히스토리 강제 재로드
      loadHistory(conversationId, true);
      
      // 이미지 새로고침 (undefined 체크 포함)
      setTimeout(() => {
        if (!imageUrl || imageUrl === 'undefined' || imageUrl === 'null') {
          console.warn('⚠️ Canvas 이미지 새로고침 생략 - 잘못된 URL:', imageUrl);
          return;
        }
        
        const baseUrl = imageUrl.split('?')[0];
        const images = document.querySelectorAll('img');
        images.forEach((img) => {
          if (img.src && img.src.includes(baseUrl)) {
            const originalSrc = img.src.split('?')[0];
            img.src = `${originalSrc}?t=${Date.now()}`;
            console.log('🖼️ Canvas 이미지 강제 새로고침:', img.src);
          }
        });
      }, 100);
    }
  };
  
  // 이벤트 리스너 등록
  window.addEventListener('image-updated', handleImageUpdate as EventListener);
  
  // 정리
  return () => {
    window.removeEventListener('image-updated', handleImageUpdate as EventListener);
  };
}, [conversationId, loadHistory]);
```

## 🔍 **디버깅 및 모니터링**

### **Backend 로깅**
```python
# 상세한 성능 및 상태 로깅
logger.info(f"🎨 Gemini 2.5 Flash 이미지 편집 시작: {job_id}")
logger.debug(f"📋 편집 정보: prompt='{prompt[:50]}...', optimize={optimize_prompt}")
logger.info(f"🖼️ 참조 이미지 로드 중: {reference_image_url}")
logger.debug(f"✅ Gemini API 호출 성공 (response_modalities=TEXT,IMAGE)")
logger.info(f"✅ 이미지 저장 성공: {filename} ({file_size:,} bytes, {save_duration:.3f}초)")
logger.info(f"🎉 이미지 파이프라인 완료: {image_url} (총 {total_duration:.3f}초)")
```

### **Frontend 로깅** 
```typescript  
// 단계별 상세 로깅
console.log('✅ 진화 이미지 생성 성공:', newImage);
console.log('🔍 이미지 접근성 확인 시작:', primaryImageUrl);
console.log('🔍 최종 이미지 URL:', finalImageUrl);
console.log('📊 Store 업데이트 완료:', { conversationId, newImageId, totalImages });
console.log('🔄 강화된 이미진 새로고침 시작');
console.log('✅ evolveImage 호출 완료:', newImage);
```

## ⚡ **성능 최적화**

### **1. API 응답 시간 개선**
- Vertex AI global 리전 사용으로 지연시간 감소
- 이미지 압축 및 최적화 파라미터 조정
- 동시 처리 제한으로 서버 부하 관리

### **2. 프론트엔드 렌더링 최적화**
- 적응형 재시도 지연으로 불필요한 API 호출 감소
- DOM 조작 배치 처리로 렌더링 성능 향상
- 메모리 누수 방지를 위한 이벤트 리스너 정리

### **3. 네트워크 최적화**
- 강화된 캐시 버스팅으로 브라우저 캐시 문제 해결
- HTTP/2 병렬 요청 활용
- 이미지 로딩 실패 시 즉시 fallback

## 🧪 **테스트 가이드**

### **기능 테스트 체크리스트**
- [ ] Canvas 편집 버튼 클릭 시 UI 표시
- [ ] 편집 프롬프트 입력 후 Gemini API 호출
- [ ] 이미지 생성 완료 후 파일 저장
- [ ] primaryImageUrl 정상 매핑 확인
- [ ] 자동 새로고침으로 즉시 이미지 표시  
- [ ] Store 및 히스토리 실시간 업데이트
- [ ] JavaScript 에러 발생하지 않음

### **에러 케이스 테스트**
- [ ] undefined URL → 안전한 처리
- [ ] 네트워크 지연 → 30단계 재시도
- [ ] 이미지 로딩 실패 → Image() 검증 후 fallback
- [ ] API 응답 지연 → 타임아웃 처리

## 📋 **배포 가이드**

### **환경 변수 설정**
```bash
# Google Cloud 설정
GOOGLE_PROJECT_ID=your-project-id
GOOGLE_CREDENTIALS=path/to/service-account.json

# Gemini 모델 설정
GEMINI_MODEL_ID=gemini-2.5-flash-image-preview
GEMINI_LOCATION=global
```

### **의존성 설치**
```bash
# Backend
pip install google-genai google-cloud-aiplatform pillow

# Frontend  
npm install zustand uuid
```

### **프로덕션 고려사항**
1. **보안**: 서비스 계정 키 안전한 관리
2. **확장성**: 이미지 저장소 CDN 연동 고려
3. **모니터링**: 에러 추적 및 성능 메트릭 수집
4. **백업**: 생성된 이미지 백업 전략

---

**작성일**: 2025-09-04  
**버전**: v1.0  
**작성자**: AI Portal 개발팀