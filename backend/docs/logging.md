# AI 포탈 로깅 및 모니터링 시스템

## 개요

AI 포탈은 통합된 로깅 및 모니터링 시스템을 통해 다음을 추적합니다:

- **HTTP 요청/응답 로깅**: 모든 API 호출 추적
- **AI 모델 사용 로깅**: Claude, Gemini 모델 사용 통계
- **성능 메트릭**: 응답 시간, 처리량, 느린 요청 감지
- **보안 이벤트**: 의심스러운 활동, 인증 실패, 공격 시도
- **시스템 에러**: 예외, 스택 트레이스, 컨텍스트 정보

## 로그 형식

모든 로그는 JSON 형태로 구조화되어 출력됩니다:

```json
{
  "event": "HTTP 요청",
  "method": "POST",
  "url": "http://localhost:8001/api/v1/chat",
  "user_id": "user_123",
  "ip_address": "127.0.0.1",
  "response_time_ms": 245.7,
  "status_code": 200,
  "timestamp": "2025-01-07T04:48:24.767846Z",
  "request_id": "req_abc123",
  "logger": "app.services.logging_service",
  "level": "info"
}
```

## 로그 레벨

- **DEBUG**: 개발용 상세 디버그 정보
- **INFO**: 일반적인 작업 정보 (요청, 응답, 성공적인 처리)
- **WARNING**: 주의가 필요하지만 치명적이지 않은 상황
- **ERROR**: 에러 발생하지만 서비스는 계속 운영
- **CRITICAL**: 즉시 대응이 필요한 치명적 오류

## 모니터링 통합

### LangSmith 연동 (선택사항)

LangSmith를 통해 AI 모델 사용을 추적할 수 있습니다:

1. LangSmith 계정 생성 (https://smith.langchain.com)
2. API 키 발급
3. `.env` 파일에 추가:
   ```
   LANGSMITH_API_KEY=your-langsmith-api-key-here
   LANGSMITH_PROJECT=ai-portal
   ```

### 로그 수집 시스템

프로덕션에서는 다음과 같은 로그 수집 시스템과 연동 가능:

- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Fluentd** + **Prometheus** + **Grafana**
- **DataDog**, **New Relic** 등 상용 서비스

## 보안 및 개인정보

- **IP 주소**: 보안 목적으로 기록하지만 개인정보 처리방침 준수
- **사용자 ID**: 해시된 형태로 저장 권장
- **API 키/토큰**: 절대 로그에 기록하지 않음
- **민감한 데이터**: 프롬프트와 응답은 처음 500자만 기록

## 성능 모니터링

### 자동 감지 메트릭

- **느린 요청**: 1초 이상 응답
- **높은 에러율**: 5% 이상 4xx/5xx 응답
- **메모리 사용량**: 임계치 초과 시 경고
- **AI 모델 응답 시간**: 모델별 성능 추적

### 대시보드 메트릭

다음 메트릭들이 자동으로 수집됩니다:

```json
{
  "metric_name": "api_response_time",
  "value": 250.0,
  "unit": "ms",
  "context": {
    "endpoint": "/api/v1/chat",
    "model_used": "claude-4",
    "user_id": "user_123"
  }
}
```

## 로깅 API 사용법

### 기본 로깅

```python
from app.services.logging_service import logging_service

# HTTP 요청 로깅
logging_service.log_request(
    method="POST",
    url="/api/v1/chat",
    user_id="user_123",
    ip_address="192.168.1.100"
)

# 응답 로깅
logging_service.log_response(
    method="POST",
    url="/api/v1/chat",
    status_code=200,
    response_time_ms=156.7,
    user_id="user_123"
)
```

### AI 모델 사용 로깅

```python
# 자동 로깅 (데코레이터 사용)
@log_llm_usage
async def generate_response(model_name, prompt, **kwargs):
    # AI 모델 호출
    pass

# 수동 로깅
logging_service.log_ai_model_usage(
    model_name="claude-4",
    prompt="사용자 질문",
    response="AI 응답",
    response_time_ms=890.2,
    user_id="user_123",
    conversation_id="conv_456"
)
```

### 성능 메트릭

```python
# 성능 메트릭 기록
logging_service.log_performance_metric(
    metric_name="database_query_time",
    value=45.6,
    unit="ms",
    context={"table": "conversations", "operation": "select"}
)

# 작업 추적 (컨텍스트 매니저)
async with logging_service.trace_operation("file_upload", user_id="user_123") as op_id:
    # 시간이 오래 걸리는 작업
    await process_large_file()
    # 자동으로 시작/완료 시간 기록
```

### 보안 이벤트

```python
# 보안 이벤트 기록
logging_service.log_security_event(
    event_type="suspicious_login",
    description="여러 번의 로그인 실패 후 성공",
    user_id="user_123",
    ip_address="192.168.1.100",
    severity="MEDIUM"
)
```

### 에러 로깅

```python
try:
    # 위험한 작업
    pass
except Exception as e:
    logging_service.log_error(
        error=e,
        context="파일 처리 중 에러",
        user_id="user_123",
        file_name="document.pdf"
    )
```

## 로그 분석 쿼리 예제

### 느린 요청 찾기
```bash
cat app.log | jq 'select(.response_time_ms > 1000)'
```

### 에러율 계산
```bash
cat app.log | jq 'select(.status_code >= 400)' | wc -l
```

### 모델별 사용 통계
```bash
cat app.log | jq 'select(.model_name) | .model_name' | sort | uniq -c
```

### 보안 이벤트 모니터링
```bash
cat app.log | jq 'select(.severity == "HIGH" or .severity == "CRITICAL")'
```

## 설정

### 환경 변수

```bash
# 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# 로그 형식 (json, text)
LOG_FORMAT=json

# LangSmith 모니터링 (선택사항)
LANGSMITH_API_KEY=your-api-key
LANGSMITH_PROJECT=ai-portal

# 개발/프로덕션 환경
ENVIRONMENT=development
DEBUG=true
```

### 로그 파일 로테이션

프로덕션에서는 로그 로테이션 설정을 권장합니다:

```bash
# logrotate 설정 예제 (/etc/logrotate.d/aiportal)
/var/log/aiportal/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 aiportal aiportal
}
```

## 트러블슈팅

### 로그가 출력되지 않는 경우
1. `LOG_LEVEL` 환경변수 확인
2. 파일 권한 확인
3. 디스크 공간 확인

### LangSmith 연동 실패
1. API 키 유효성 확인
2. 네트워크 연결 확인
3. 프로젝트 이름 확인

### 성능 저하
1. 로그 레벨을 INFO 이상으로 설정
2. 구조화된 로깅 비활성화 (개발 시에만)
3. 비동기 로깅 사용

## 보안 고려사항

- 로그 파일 접근 권한 제한
- 민감한 정보 마스킹
- 로그 전송 시 암호화
- 로그 보존 기간 정책 수립
- 감사 로그 무결성 보장