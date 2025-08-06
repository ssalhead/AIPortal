-- PostgreSQL 초기화 스크립트
-- 데이터베이스와 사용자 설정

-- 기본 설정은 이미 환경변수로 처리되므로 추가 설정만 진행

-- 확장 기능 활성화
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";  -- UUID 생성
CREATE EXTENSION IF NOT EXISTS "pg_trgm";    -- 텍스트 유사도 검색
CREATE EXTENSION IF NOT EXISTS "btree_gin";  -- GIN 인덱스 최적화

-- 데이터베이스 설정
ALTER DATABASE ai_portal SET timezone TO 'Asia/Seoul';

-- 초기 사용자 권한 설정
GRANT ALL PRIVILEGES ON DATABASE ai_portal TO aiportal;

-- 스키마 생성 (필요시)
-- CREATE SCHEMA IF NOT EXISTS ai_portal_schema;
-- GRANT ALL ON SCHEMA ai_portal_schema TO aiportal;

-- 로깅 설정
-- ALTER SYSTEM SET log_statement = 'all';  -- 개발 환경에서만
-- SELECT pg_reload_conf();

-- 초기화 완료 메시지
SELECT 'PostgreSQL initialized for AI Portal' AS message;