#!/usr/bin/env python3
"""
테스트용 이미지 히스토리 데이터 추가 스크립트
generated_images에서 image_history로 데이터 복사
"""

import asyncio
import uuid
from uuid import UUID
from datetime import datetime
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models.image_generation import GeneratedImage
from app.db.models.image_history import ImageHistory
from app.core.config import settings

async def migrate_generated_to_history():
    """generated_images에서 image_history로 데이터 마이그레이션"""
    
    async with AsyncSessionLocal() as session:
        try:
            # 최신 generated_images 조회
            stmt = select(GeneratedImage).where(
                GeneratedImage.user_id == UUID(settings.MOCK_USER_ID)
            ).order_by(GeneratedImage.created_at.desc()).limit(5)
            
            result = await session.execute(stmt)
            generated_images = result.scalars().all()
            
            print(f"발견된 generated_images: {len(generated_images)}")
            
            for gen_img in generated_images:
                print(f"처리 중: {gen_img.id} - {gen_img.prompt}")
                
                # 대화 ID 생성 (테스트용)
                conversation_id = uuid.uuid4()
                
                # ImageHistory 엔트리 생성
                image_history = ImageHistory.create_from_generation(
                    conversation_id=conversation_id,
                    user_id=gen_img.user_id,
                    prompt=gen_img.prompt,
                    image_urls=[gen_img.file_url],
                    style=gen_img.style,
                    size=gen_img.sample_image_size,
                    generation_params={
                        "model": gen_img.model_name,
                        "aspect_ratio": gen_img.aspect_ratio,
                        "job_id": gen_img.job_id
                    },
                    safety_score=1.0
                )
                
                session.add(image_history)
                print(f"ImageHistory 생성: {image_history.id}")
                
            # 커밋
            await session.commit()
            print("✅ 마이그레이션 완료")
            
            # 결과 확인
            stmt_check = select(ImageHistory).where(
                ImageHistory.user_id == UUID(settings.MOCK_USER_ID)
            ).order_by(ImageHistory.created_at.desc())
            
            result_check = await session.execute(stmt_check)
            image_histories = result_check.scalars().all()
            
            print(f"생성된 image_history 엔트리: {len(image_histories)}")
            for img_hist in image_histories:
                print(f"  - ID: {img_hist.id}, Prompt: {img_hist.prompt[:50]}...")
                
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            await session.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(migrate_generated_to_history())