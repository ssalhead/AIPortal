# 개별 Canvas 자동 열림 시스템 (Canvas v4.2)

**구현 완료일**: 2025-09-05  
**버전**: Canvas v4.2  
**핵심 기능**: 요청별 개별 Canvas 생성 및 자동 활성화

## 📋 시스템 개요

기존 Canvas v4.0에서는 이미지 생성 요청들이 대화별 공유 Canvas에 모두 추가되는 문제가 있었습니다. v4.2에서는 **각 이미지 생성 요청마다 고유한 Canvas를 생성**하고, **생성 완료 시 해당 Canvas만 자동으로 활성화**하는 시스템을 구현했습니다.

## 🔧 핵심 기술적 변경사항

### 1. 백엔드 - requestCanvasId 생성 시스템

#### 파일: `/backend/app/agents/workers/simple_canvas.py`

```python
# 🎯 각 이미지 생성 요청마다 고유 ID 생성
request_canvas_id = uuid.uuid4()

# Canvas 데이터 구조에 requestCanvasId 추가
canvas_data = {
    "type": "image",
    "title": f"이미지 생성: {self._extract_clean_prompt(image_params['prompt'])[:30]}...",
    # ... 기타 데이터
    "requestCanvasId": str(request_canvas_id),  # 🎯 최상위 레벨
    "request_canvas_id": str(request_canvas_id),  # 호환성
    "metadata": {
        # ... 기타 메타데이터
        "request_canvas_id": str(request_canvas_id)  # metadata에도 저장
    }
}
```

**핵심**: 각 이미지 생성 요청마다 UUID를 생성하여 개별 Canvas를 식별

### 2. 프론트엔드 - 자동 활성화 로직

#### 파일: `/frontend/src/pages/ChatPage.tsx:483`

```typescript
// 🎯 request_canvas_id 확인하여 개별 요청별 Canvas 생성 결정
const requestCanvasId = response.canvas_data.requestCanvasId || 
                        response.canvas_data.request_canvas_id || 
                        response.canvas_data.metadata?.request_canvas_id;

console.log('🔍 sendMessage Canvas 자동 활성화 - requestCanvasId 확인:', {
  requestCanvasId: response.canvas_data.requestCanvasId,
  request_canvas_id: response.canvas_data.request_canvas_id,
  metadata_request_canvas_id: response.canvas_data.metadata?.request_canvas_id,
  hasRequestCanvasId: !!requestCanvasId
});

let canvasId;
if (requestCanvasId) {
  // ✨ 개별 요청별 Canvas 생성 (v4.2 방식)
  console.log('✨ 개별 요청 Canvas ID 감지 (자동 활성화):', requestCanvasId);
  canvasId = useCanvasStore.getState().getOrCreateCanvasV4(
    sessionIdToUse, 
    inferredType, 
    response.canvas_data, 
    requestCanvasId  // 🎯 requestCanvasId 전달
  );
  console.log('✅ 개별 요청별 Canvas 활성화 완료 (자동):', canvasId);
} else {
  // 기존 방식: 대화별 공유 Canvas
  canvasId = getOrCreateCanvas(sessionIdToUse, inferredType, response.canvas_data);
  console.log('✅ 대화별 공유 Canvas 활성화 완료 (자동):', canvasId);
}
```

**핵심**: `requestCanvasId` 감지 시 개별 Canvas 생성, 없으면 기존 공유 Canvas 방식 사용

### 3. Canvas Store - requestCanvasId 보존 시스템

#### 파일: `/frontend/src/stores/canvasStore.ts`

**3-1. syncImageToSessionStore에서 requestCanvasId 저장**

```typescript
// 🎯 requestCanvasId 추출 및 저장
const requestCanvasId = canvasData.requestCanvasId || 
                       canvasData.request_canvas_id || 
                       canvasData.metadata?.request_canvas_id;

const versionId = await imageSessionStore.addVersionHybrid(conversationId, {
  // ... 기타 데이터
  metadata: {
    source: 'canvas_integration',
    canvasSync: true,
    contentHash: contentHash,
    contentData: contentData,
    deduplicationVersion: '5.0',
    requestCanvasId: requestCanvasId  // 🎯 개별 Canvas 요청 ID 저장
  },
  isSelected: true
});
```

**3-2. syncCanvasWithImageSession에서 개별 Canvas ID 생성**

```typescript
// 🎯 requestCanvasId 추출 및 개별 Canvas ID 생성
const requestCanvasId = version.metadata?.requestCanvasId;
let canvasId: string;

if (requestCanvasId) {
  // ✨ 개별 요청별 Canvas ID 형식
  canvasId = `${conversationId}-image-${requestCanvasId}`;
  console.log(`🎯 개별 Canvas ID 생성: ${canvasId}`);
} else {
  // 기존 공유 Canvas ID 형식
  canvasId = `canvas_${conversationId}_${version.id}`;
  console.log(`🔄 공유 Canvas ID 생성: ${canvasId}`);
}

const newCanvasContent = {
  // ... 기타 데이터
  requestCanvasId: requestCanvasId  // 🎯 requestCanvasId 보존
};

const newCanvas: CanvasItem = {
  id: canvasId,  // 🎯 개별 Canvas ID 사용
  type: 'image',
  content: newCanvasContent,
  // ... 기타 설정
  metadata: { 
    fromImageSession: true,
    requestCanvasId: requestCanvasId  // 🎯 metadata에도 저장
  }
};
```

**핵심**: Canvas Store 동기화 과정에서도 `requestCanvasId` 정보를 보존하여 개별 Canvas ID 생성

### 4. 인라인 링크 - 개별 Canvas 감지

#### 파일: `/frontend/src/components/chat/ChatMessage.tsx`

```typescript
// 🎯 requestCanvasId 감지
const hasRequestCanvasId = canvasData.requestCanvasId || 
                          canvasData.request_canvas_id || 
                          canvasData.metadata?.request_canvas_id;

const handleCanvasClick = () => {
  if (hasRequestCanvasId) {
    // ✨ 개별 Canvas 열기
    const requestId = canvasData.requestCanvasId || 
                     canvasData.request_canvas_id || 
                     canvasData.metadata?.request_canvas_id;
    canvasId = useCanvasStore.getState().getOrCreateCanvasV4(
      conversationId, 
      'image', 
      canvasData, 
      requestId
    );
  } else {
    // 기존 공유 Canvas 열기
    canvasId = getOrCreateCanvas(conversationId, 'image', canvasData);
  }
};
```

**핵심**: 인라인 링크 클릭 시에도 `requestCanvasId` 유무에 따라 개별/공유 Canvas 구분

## 🎯 Canvas ID 형식 체계

### v4.2 개별 Canvas ID
```
형식: {conversationId}-image-{requestCanvasId}
예시: "abc123-def456-image-xyz789-uvw012"
```

### 기존 공유 Canvas ID (호환성 유지)
```
형식: canvas_{conversationId}_{versionId}
예시: "canvas_abc123-def456_version789"
```

## 🔄 데이터 플로우

1. **사용자 이미지 생성 요청** → Canvas Agent로 라우팅
2. **Canvas Agent**: `requestCanvasId = uuid.uuid4()` 생성
3. **Canvas 데이터 구조**: `requestCanvasId`를 다중 레벨에 저장 (최상위, metadata)
4. **ChatPage 자동 활성화**: `requestCanvasId` 감지하여 `getOrCreateCanvasV4()` 호출
5. **Canvas Store 동기화**: ImageSession metadata에 `requestCanvasId` 저장
6. **syncCanvasWithImageSession**: metadata에서 `requestCanvasId` 추출하여 개별 Canvas ID 생성
7. **SimpleImageWorkspace**: `requestCanvasId`로 이미지 필터링하여 해당 요청만 표시

## 🚀 사용자 경험 개선

### Before (v4.0)
- 🔴 **문제**: 여러 이미지 생성 요청 시 모든 이미지가 하나의 Canvas에 표시됨
- 🔴 **혼란**: 어느 이미지가 어느 요청인지 구분이 어려움
- 🔴 **자동 활성화**: 새 이미지 생성 후 모든 이미지가 보임

### After (v4.2)
- ✅ **개별성**: 각 요청마다 고유한 Canvas 생성
- ✅ **명확성**: 해당 요청의 이미지만 표시되어 혼란 제거
- ✅ **자동 활성화**: 새 이미지 생성 후 해당 요청의 Canvas만 자동 열림
- ✅ **호환성**: 기존 공유 Canvas 방식도 계속 지원

## 🛠️ 주요 해결된 문제들

### 1. Canvas Store 동기화 중 requestCanvasId 손실
**문제**: `syncCanvasWithImageSession`에서 새 Canvas 생성 시 `requestCanvasId` 정보 손실  
**해결**: ImageSession metadata에 `requestCanvasId` 저장 → 동기화 시 추출하여 개별 Canvas ID 생성

### 2. 자동 활성화 시 모든 이미지 표시
**문제**: 이미지 생성 완료 후 자동 Canvas 활성화 시 `requestCanvasId` 없이 공유 Canvas 열림  
**해결**: ChatPage에서 `requestCanvasId` 감지 로직 추가하여 개별 Canvas 활성화

### 3. 인라인 링크와 자동 활성화 불일치
**문제**: 인라인 링크는 개별 이미지만 표시하지만 자동 활성화는 모든 이미지 표시  
**해결**: 두 경우 모두 동일한 `getOrCreateCanvasV4()` 로직 사용

## 📊 성능 및 효과

- ✅ **사용성 대폭 향상**: 요청별 명확한 Canvas 분리
- ✅ **혼란 제거**: 이미지-요청 1:1 매핑으로 직관적 사용
- ✅ **개발자 경험 개선**: 명확한 로깅과 디버깅 가능
- ✅ **확장성**: 향후 Canvas 기능 확장 시 개별 관리 용이
- ✅ **호환성**: 기존 공유 Canvas 방식도 계속 지원

---

**구현 완료**: 2025-09-05  
**테스트 상태**: ✅ 완료 - 개별 Canvas 자동 열림 정상 동작 확인  
**다음 단계**: Canvas 편집 기능 확장 및 멀티미디어 지원