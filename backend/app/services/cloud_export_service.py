"""
클라우드 내보내기 서비스
Google Drive, Dropbox, AWS S3 연동을 지원하는 클라우드 업로드 시스템
"""

import asyncio
import json
import logging
import os
import tempfile
from datetime import datetime, timedelta
from io import BytesIO
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urljoin
import uuid

import aiohttp
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import dropbox
from dropbox.exceptions import AuthError, ApiError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError

from app.models.export_models import CloudProvider, CloudExportOptions
from app.core.config import settings

logger = logging.getLogger(__name__)


class CloudUploadResult:
    """클라우드 업로드 결과"""
    
    def __init__(
        self,
        success: bool,
        provider: CloudProvider,
        file_id: Optional[str] = None,
        file_url: Optional[str] = None,
        share_url: Optional[str] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.success = success
        self.provider = provider
        self.file_id = file_id
        self.file_url = file_url
        self.share_url = share_url
        self.error = error
        self.metadata = metadata or {}


class GoogleDriveUploader:
    """Google Drive 업로드 서비스"""
    
    def __init__(self):
        self.service = None
        self.credentials = None
    
    async def initialize(self, user_token: str):
        """Google Drive API 초기화"""
        try:
            # OAuth 토큰에서 credentials 생성
            token_data = json.loads(user_token)
            self.credentials = Credentials(
                token=token_data.get('access_token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri=token_data.get('token_uri', 'https://oauth2.googleapis.com/token'),
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET
            )
            
            # 토큰 갱신 확인
            if self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())
            
            # Drive API 서비스 구축
            self.service = build('drive', 'v3', credentials=self.credentials)
            return True
            
        except Exception as e:
            logger.error(f"Google Drive 초기화 실패: {e}")
            return False
    
    async def upload_file(
        self,
        file_data: bytes,
        filename: str,
        mime_type: str,
        folder_id: Optional[str] = None,
        options: Optional[CloudExportOptions] = None
    ) -> CloudUploadResult:
        """파일을 Google Drive에 업로드"""
        
        if not self.service:
            return CloudUploadResult(
                success=False,
                provider=CloudProvider.GOOGLE_DRIVE,
                error="Google Drive 서비스가 초기화되지 않았습니다"
            )
        
        try:
            # 파일 메타데이터
            file_metadata = {
                'name': filename,
                'description': f'AIPortal Canvas Export - {datetime.utcnow().isoformat()}'
            }
            
            # 폴더 지정
            if folder_id:
                file_metadata['parents'] = [folder_id]
            elif options and options.folder_path:
                # 폴더 경로로 폴더 ID 찾기 또는 생성
                folder_id = await self._ensure_folder_exists(options.folder_path)
                if folder_id:
                    file_metadata['parents'] = [folder_id]
            
            # 파일 업로드
            media = MediaIoBaseUpload(
                BytesIO(file_data),
                mimetype=mime_type,
                resumable=True
            )
            
            # 업로드 실행
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,webViewLink,webContentLink,size,createdTime'
            ).execute()
            
            # 공유 링크 생성 (옵션)
            share_url = None
            if options and options.generate_share_link:
                share_url = await self._create_share_link(
                    file['id'], 
                    options.share_permissions
                )
            
            return CloudUploadResult(
                success=True,
                provider=CloudProvider.GOOGLE_DRIVE,
                file_id=file['id'],
                file_url=file.get('webContentLink'),
                share_url=share_url or file.get('webViewLink'),
                metadata={
                    'name': file['name'],
                    'size': int(file.get('size', 0)),
                    'created_time': file.get('createdTime'),
                    'view_link': file.get('webViewLink'),
                    'download_link': file.get('webContentLink')
                }
            )
            
        except HttpError as e:
            error_msg = f"Google Drive API 오류: {e.resp.status} - {e.content.decode()}"
            logger.error(error_msg)
            return CloudUploadResult(
                success=False,
                provider=CloudProvider.GOOGLE_DRIVE,
                error=error_msg
            )
        except Exception as e:
            error_msg = f"Google Drive 업로드 실패: {str(e)}"
            logger.error(error_msg)
            return CloudUploadResult(
                success=False,
                provider=CloudProvider.GOOGLE_DRIVE,
                error=error_msg
            )
    
    async def _ensure_folder_exists(self, folder_path: str) -> Optional[str]:
        """폴더 경로 확인 및 생성"""
        try:
            path_parts = [part.strip() for part in folder_path.strip('/').split('/') if part.strip()]
            current_folder_id = 'root'
            
            for folder_name in path_parts:
                # 현재 폴더에서 하위 폴더 찾기
                query = f"name='{folder_name}' and parents in '{current_folder_id}' and mimeType='application/vnd.google-apps.folder'"
                results = self.service.files().list(
                    q=query,
                    fields='files(id, name)'
                ).execute()
                
                folders = results.get('files', [])
                
                if folders:
                    # 존재하는 폴더 사용
                    current_folder_id = folders[0]['id']
                else:
                    # 새 폴더 생성
                    folder_metadata = {
                        'name': folder_name,
                        'mimeType': 'application/vnd.google-apps.folder',
                        'parents': [current_folder_id]
                    }
                    
                    folder = self.service.files().create(
                        body=folder_metadata,
                        fields='id'
                    ).execute()
                    
                    current_folder_id = folder['id']
            
            return current_folder_id
            
        except Exception as e:
            logger.error(f"Google Drive 폴더 생성 실패: {e}")
            return None
    
    async def _create_share_link(self, file_id: str, permission: str) -> Optional[str]:
        """공유 링크 생성"""
        try:
            permission_body = {
                'role': 'reader' if permission == 'view' else 'writer',
                'type': 'anyone'
            }
            
            self.service.permissions().create(
                fileId=file_id,
                body=permission_body
            ).execute()
            
            # 파일 정보 재조회로 공유 링크 가져오기
            file = self.service.files().get(
                fileId=file_id,
                fields='webViewLink'
            ).execute()
            
            return file.get('webViewLink')
            
        except Exception as e:
            logger.error(f"Google Drive 공유 링크 생성 실패: {e}")
            return None


class DropboxUploader:
    """Dropbox 업로드 서비스"""
    
    def __init__(self):
        self.client = None
    
    async def initialize(self, access_token: str):
        """Dropbox API 초기화"""
        try:
            self.client = dropbox.Dropbox(access_token)
            # 계정 정보로 토큰 유효성 확인
            self.client.users_get_current_account()
            return True
            
        except AuthError as e:
            logger.error(f"Dropbox 인증 실패: {e}")
            return False
        except Exception as e:
            logger.error(f"Dropbox 초기화 실패: {e}")
            return False
    
    async def upload_file(
        self,
        file_data: bytes,
        filename: str,
        mime_type: str,
        options: Optional[CloudExportOptions] = None
    ) -> CloudUploadResult:
        """파일을 Dropbox에 업로드"""
        
        if not self.client:
            return CloudUploadResult(
                success=False,
                provider=CloudProvider.DROPBOX,
                error="Dropbox 클라이언트가 초기화되지 않았습니다"
            )
        
        try:
            # 파일 경로 구성
            folder_path = options.dropbox_folder_path if options else None
            if folder_path:
                if not folder_path.startswith('/'):
                    folder_path = '/' + folder_path
                if not folder_path.endswith('/'):
                    folder_path += '/'
                file_path = folder_path + filename
            else:
                file_path = '/' + filename
            
            # 파일 업로드
            if len(file_data) <= 150 * 1024 * 1024:  # 150MB 이하
                # 단일 업로드
                metadata = self.client.files_upload(
                    file_data,
                    file_path,
                    mode=dropbox.files.WriteMode('overwrite'),
                    autorename=True
                )
            else:
                # 청크 업로드
                session_start_result = self.client.files_upload_session_start(file_data[:4 * 1024 * 1024])
                cursor = dropbox.files.UploadSessionCursor(
                    session_id=session_start_result.session_id,
                    offset=4 * 1024 * 1024
                )
                
                # 나머지 청크들 업로드
                remaining_data = file_data[4 * 1024 * 1024:]
                while len(remaining_data) > 4 * 1024 * 1024:
                    self.client.files_upload_session_append_v2(
                        remaining_data[:4 * 1024 * 1024],
                        cursor
                    )
                    cursor.offset += 4 * 1024 * 1024
                    remaining_data = remaining_data[4 * 1024 * 1024:]
                
                # 마지막 청크와 완료
                commit = dropbox.files.CommitInfo(path=file_path, mode=dropbox.files.WriteMode('overwrite'))
                metadata = self.client.files_upload_session_finish(
                    remaining_data,
                    cursor,
                    commit
                )
            
            # 공유 링크 생성 (옵션)
            share_url = None
            if options and options.generate_share_link:
                try:
                    shared_link_metadata = self.client.sharing_create_shared_link_with_settings(
                        file_path,
                        dropbox.sharing.SharedLinkSettings(
                            requested_visibility=dropbox.sharing.RequestedVisibility.public
                        )
                    )
                    share_url = shared_link_metadata.url
                except ApiError as e:
                    # 이미 공유 링크가 존재하는 경우
                    if e.error.is_shared_link_already_exists():
                        existing_links = self.client.sharing_list_shared_links(path=file_path)
                        if existing_links.links:
                            share_url = existing_links.links[0].url
            
            return CloudUploadResult(
                success=True,
                provider=CloudProvider.DROPBOX,
                file_id=metadata.id,
                file_url=f"https://dropbox.com/home{file_path}",
                share_url=share_url,
                metadata={
                    'name': metadata.name,
                    'path': metadata.path_display,
                    'size': metadata.size,
                    'modified_time': metadata.server_modified.isoformat() if metadata.server_modified else None,
                    'content_hash': metadata.content_hash
                }
            )
            
        except ApiError as e:
            error_msg = f"Dropbox API 오류: {str(e)}"
            logger.error(error_msg)
            return CloudUploadResult(
                success=False,
                provider=CloudProvider.DROPBOX,
                error=error_msg
            )
        except Exception as e:
            error_msg = f"Dropbox 업로드 실패: {str(e)}"
            logger.error(error_msg)
            return CloudUploadResult(
                success=False,
                provider=CloudProvider.DROPBOX,
                error=error_msg
            )


class S3Uploader:
    """AWS S3 업로드 서비스"""
    
    def __init__(self):
        self.client = None
        self.bucket_name = None
    
    async def initialize(self, aws_access_key: str, aws_secret_key: str, region: str = 'us-east-1'):
        """AWS S3 클라이언트 초기화"""
        try:
            self.client = boto3.client(
                's3',
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=region
            )
            
            # 연결 테스트
            self.client.list_buckets()
            return True
            
        except NoCredentialsError:
            logger.error("AWS 자격 증명이 없습니다")
            return False
        except ClientError as e:
            logger.error(f"AWS S3 초기화 실패: {e}")
            return False
        except Exception as e:
            logger.error(f"S3 클라이언트 초기화 실패: {e}")
            return False
    
    async def upload_file(
        self,
        file_data: bytes,
        filename: str,
        mime_type: str,
        bucket_name: str,
        options: Optional[CloudExportOptions] = None
    ) -> CloudUploadResult:
        """파일을 S3에 업로드"""
        
        if not self.client:
            return CloudUploadResult(
                success=False,
                provider=CloudProvider.AWS_S3,
                error="S3 클라이언트가 초기화되지 않았습니다"
            )
        
        try:
            # 객체 키 구성
            object_key = filename
            if options and options.s3_object_prefix:
                prefix = options.s3_object_prefix.strip('/')
                object_key = f"{prefix}/{filename}"
            
            # 메타데이터 설정
            metadata = {
                'uploaded-by': 'aiportal-canvas-export',
                'upload-timestamp': datetime.utcnow().isoformat(),
                'original-filename': filename
            }
            
            # 파일 업로드
            self.client.put_object(
                Bucket=bucket_name,
                Key=object_key,
                Body=file_data,
                ContentType=mime_type,
                Metadata=metadata,
                StorageClass='STANDARD'
            )
            
            # 파일 URL 생성
            file_url = f"https://{bucket_name}.s3.amazonaws.com/{object_key}"
            
            # 사전 서명된 URL 생성 (공유 링크)
            share_url = None
            if options and options.generate_share_link:
                try:
                    share_url = self.client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': bucket_name, 'Key': object_key},
                        ExpiresIn=86400  # 24시간
                    )
                except Exception as e:
                    logger.warning(f"S3 사전 서명된 URL 생성 실패: {e}")
            
            # 객체 정보 조회
            response = self.client.head_object(Bucket=bucket_name, Key=object_key)
            
            return CloudUploadResult(
                success=True,
                provider=CloudProvider.AWS_S3,
                file_id=object_key,
                file_url=file_url,
                share_url=share_url,
                metadata={
                    'bucket': bucket_name,
                    'key': object_key,
                    'size': response['ContentLength'],
                    'last_modified': response['LastModified'].isoformat(),
                    'etag': response['ETag'].strip('"'),
                    'content_type': response['ContentType'],
                    's3_metadata': response.get('Metadata', {})
                }
            )
            
        except ClientError as e:
            error_msg = f"S3 업로드 실패: {e.response['Error']['Message']}"
            logger.error(error_msg)
            return CloudUploadResult(
                success=False,
                provider=CloudProvider.AWS_S3,
                error=error_msg
            )
        except Exception as e:
            error_msg = f"S3 업로드 실패: {str(e)}"
            logger.error(error_msg)
            return CloudUploadResult(
                success=False,
                provider=CloudProvider.AWS_S3,
                error=error_msg
            )


class CloudExportService:
    """통합 클라우드 내보내기 서비스"""
    
    def __init__(self):
        self.google_drive = GoogleDriveUploader()
        self.dropbox = DropboxUploader()
        self.s3 = S3Uploader()
    
    async def upload_to_cloud(
        self,
        file_data: bytes,
        filename: str,
        mime_type: str,
        options: CloudExportOptions,
        user_credentials: Dict[str, Any]
    ) -> CloudUploadResult:
        """클라우드에 파일 업로드"""
        
        if options.provider == CloudProvider.NONE:
            return CloudUploadResult(
                success=False,
                provider=CloudProvider.NONE,
                error="클라우드 제공업체가 지정되지 않았습니다"
            )
        
        try:
            if options.provider == CloudProvider.GOOGLE_DRIVE:
                return await self._upload_to_google_drive(
                    file_data, filename, mime_type, options, user_credentials
                )
            
            elif options.provider == CloudProvider.DROPBOX:
                return await self._upload_to_dropbox(
                    file_data, filename, mime_type, options, user_credentials
                )
            
            elif options.provider == CloudProvider.AWS_S3:
                return await self._upload_to_s3(
                    file_data, filename, mime_type, options, user_credentials
                )
            
            else:
                return CloudUploadResult(
                    success=False,
                    provider=options.provider,
                    error=f"지원하지 않는 클라우드 제공업체: {options.provider.value}"
                )
                
        except Exception as e:
            error_msg = f"클라우드 업로드 실패: {str(e)}"
            logger.error(error_msg)
            return CloudUploadResult(
                success=False,
                provider=options.provider,
                error=error_msg
            )
    
    async def _upload_to_google_drive(
        self,
        file_data: bytes,
        filename: str,
        mime_type: str,
        options: CloudExportOptions,
        user_credentials: Dict[str, Any]
    ) -> CloudUploadResult:
        """Google Drive에 업로드"""
        
        google_token = user_credentials.get('google_drive_token')
        if not google_token:
            return CloudUploadResult(
                success=False,
                provider=CloudProvider.GOOGLE_DRIVE,
                error="Google Drive 토큰이 없습니다"
            )
        
        if not await self.google_drive.initialize(google_token):
            return CloudUploadResult(
                success=False,
                provider=CloudProvider.GOOGLE_DRIVE,
                error="Google Drive 초기화 실패"
            )
        
        return await self.google_drive.upload_file(
            file_data, filename, mime_type, options.google_drive_folder_id, options
        )
    
    async def _upload_to_dropbox(
        self,
        file_data: bytes,
        filename: str,
        mime_type: str,
        options: CloudExportOptions,
        user_credentials: Dict[str, Any]
    ) -> CloudUploadResult:
        """Dropbox에 업로드"""
        
        dropbox_token = user_credentials.get('dropbox_token')
        if not dropbox_token:
            return CloudUploadResult(
                success=False,
                provider=CloudProvider.DROPBOX,
                error="Dropbox 토큰이 없습니다"
            )
        
        if not await self.dropbox.initialize(dropbox_token):
            return CloudUploadResult(
                success=False,
                provider=CloudProvider.DROPBOX,
                error="Dropbox 초기화 실패"
            )
        
        return await self.dropbox.upload_file(file_data, filename, mime_type, options)
    
    async def _upload_to_s3(
        self,
        file_data: bytes,
        filename: str,
        mime_type: str,
        options: CloudExportOptions,
        user_credentials: Dict[str, Any]
    ) -> CloudUploadResult:
        """AWS S3에 업로드"""
        
        aws_credentials = user_credentials.get('aws_credentials', {})
        access_key = aws_credentials.get('access_key')
        secret_key = aws_credentials.get('secret_key')
        region = aws_credentials.get('region', 'us-east-1')
        
        if not access_key or not secret_key:
            return CloudUploadResult(
                success=False,
                provider=CloudProvider.AWS_S3,
                error="AWS 자격 증명이 없습니다"
            )
        
        if not await self.s3.initialize(access_key, secret_key, region):
            return CloudUploadResult(
                success=False,
                provider=CloudProvider.AWS_S3,
                error="S3 클라이언트 초기화 실패"
            )
        
        bucket_name = options.s3_bucket_name
        if not bucket_name:
            return CloudUploadResult(
                success=False,
                provider=CloudProvider.AWS_S3,
                error="S3 버킷 이름이 지정되지 않았습니다"
            )
        
        return await self.s3.upload_file(file_data, filename, mime_type, bucket_name, options)
    
    async def batch_upload_to_cloud(
        self,
        files_data: List[Tuple[bytes, str, str]],  # (file_data, filename, mime_type)
        options: CloudExportOptions,
        user_credentials: Dict[str, Any]
    ) -> List[CloudUploadResult]:
        """여러 파일을 클라우드에 일괄 업로드"""
        
        results = []
        
        # 동시 업로드 수 제한 (클라우드 API 제한 고려)
        semaphore = asyncio.Semaphore(3)
        
        async def upload_single_file(file_data: bytes, filename: str, mime_type: str):
            async with semaphore:
                return await self.upload_to_cloud(
                    file_data, filename, mime_type, options, user_credentials
                )
        
        # 비동기 일괄 업로드
        tasks = [
            upload_single_file(file_data, filename, mime_type)
            for file_data, filename, mime_type in files_data
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 예외 처리
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(CloudUploadResult(
                    success=False,
                    provider=options.provider,
                    error=f"파일 {files_data[i][1]} 업로드 실패: {str(result)}"
                ))
            else:
                processed_results.append(result)
        
        return processed_results


# 전역 클라우드 서비스 인스턴스
cloud_export_service = CloudExportService()