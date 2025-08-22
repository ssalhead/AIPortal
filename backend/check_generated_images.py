"""
데이터베이스에 저장된 생성 이미지 메타데이터 확인
"""

import asyncio
import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.db.session import engine
from app.db.models.image_generation import GeneratedImage


async def check_generated_images():
    """생성된 이미지 데이터 확인"""
    
    query_sql = """
    SELECT 
        id,
        job_id,
        prompt,
        file_url,
        file_size,
        style,
        sample_image_size,
        aspect_ratio,
        status,
        created_at,
        extra_metadata
    FROM generated_images 
    ORDER BY created_at DESC 
    LIMIT 5;
    """
    
    async with engine.begin() as conn:
        result = await conn.execute(text(query_sql))
        rows = result.fetchall()
        
        print(f"\n=== 생성된 이미지 데이터 ({len(rows)}개) ===")
        
        for row in rows:
            print(f"""
ID: {row[0]}
Job ID: {row[1]}
Prompt: {row[2][:80]}...
File URL: {row[3]}
File Size: {row[4]:,} bytes
Style: {row[5]}
Size: {row[6]}
Aspect Ratio: {row[7]}
Status: {row[8]}
Created: {row[9]}
Metadata: {row[10]}
{'='*80}""")


if __name__ == "__main__":
    asyncio.run(check_generated_images())