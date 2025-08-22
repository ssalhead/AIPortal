"""
생성된 이미지 테이블을 수동으로 생성하는 스크립트
"""

import asyncio
import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.db.session import engine
from app.db.models.image_generation import GeneratedImage


async def create_generated_images_table():
    """생성된 이미지 테이블 생성"""
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS generated_images (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id),
        job_id VARCHAR(255) UNIQUE NOT NULL,
        prompt TEXT NOT NULL,
        enhanced_prompt TEXT,
        file_path VARCHAR(500) NOT NULL,
        file_url VARCHAR(500) NOT NULL,
        file_size INTEGER NOT NULL,
        content_type VARCHAR(100) DEFAULT 'image/png',
        model_name VARCHAR(100) DEFAULT 'imagen-4.0-generate-001',
        style VARCHAR(50) NOT NULL,
        sample_image_size VARCHAR(10) NOT NULL,
        aspect_ratio VARCHAR(10) NOT NULL,
        num_images INTEGER DEFAULT 1,
        generation_time_ms INTEGER,
        status VARCHAR(20) DEFAULT 'completed',
        error_message TEXT,
        view_count INTEGER DEFAULT 0,
        download_count INTEGER DEFAULT 0,
        is_public BOOLEAN DEFAULT FALSE,
        is_deleted BOOLEAN DEFAULT FALSE,
        extra_metadata JSONB,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        deleted_at TIMESTAMP WITH TIME ZONE
    );
    """
    
    indexes = [
        "CREATE INDEX IF NOT EXISTS ix_generated_images_job_id ON generated_images(job_id);",
        "CREATE INDEX IF NOT EXISTS ix_generated_images_user_id ON generated_images(user_id);",
        "CREATE INDEX IF NOT EXISTS ix_generated_images_created_at ON generated_images(created_at);",
        "CREATE INDEX IF NOT EXISTS ix_generated_images_status ON generated_images(status);",
        "CREATE INDEX IF NOT EXISTS ix_generated_images_is_deleted ON generated_images(is_deleted);"
    ]
    
    async with engine.begin() as conn:
        print("생성된 이미지 테이블 생성 중...")
        await conn.execute(text(create_table_sql))
        print("인덱스 생성 중...")
        for index_sql in indexes:
            await conn.execute(text(index_sql))
        print("테이블 및 인덱스 생성 완료!")


if __name__ == "__main__":
    asyncio.run(create_generated_images_table())