"""
多模态处理API路由
"""

import asyncio
import logging
import tempfile
import os
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import json

from ...security.auth import AuthManager
from ...models.database import User
from ...multimodal import process_file, process_binary, batch_process, get_supported_formats, get_capabilities

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/multimodal", tags=["multimodal"])
security = HTTPBearer()


class ProcessingOptions(BaseModel):
    """处理选项模型"""
    extract_text: Optional[bool] = True
    extract_images: Optional[bool] = False
    extract_audio: Optional[bool] = False
    transcribe: Optional[bool] = False
    detect_faces: Optional[bool] = False
    resize: Optional[List[int]] = None
    normalize: Optional[bool] = False
    compress: Optional[bool] = False
    convert_format: Optional[str] = None
    page_range: Optional[List[int]] = None
    max_rows: Optional[int] = 1000
    enhance: Optional[bool] = False
    detect_motion: Optional[bool] = False
    create_thumbnail: Optional[bool] = True


class ProcessingResponse(BaseModel):
    """处理结果响应模型"""
    success: bool
    media_type: str
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    processed_files: Optional[List[str]] = None
    processing_time: Optional[float] = None


class BatchProcessingResponse(BaseModel):
    """批量处理响应模型"""
    results: List[ProcessingResponse]
    total_files: int
    successful_files: int
    failed_files: int
    total_processing_time: float


class SupportedFormatsResponse(BaseModel):
    """支持格式响应模型"""
    formats: Dict[str, List[str]]
    capabilities: Dict[str, Any]


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """获取当前用户依赖"""
    auth_manager = AuthManager()
    token = credentials.credentials
    user = await auth_manager.get_current_user(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    return user


@router.post("/process", response_model=ProcessingResponse)
async def process_uploaded_file(
    file: UploadFile = File(...),
    options: str = Form("{}"),
    current_user: User = Depends(get_current_user)
):
    """处理上传的文件"""
    import time
    start_time = time.time()
    
    try:
        # 解析处理选项
        try:
            processing_options = json.loads(options)
        except json.JSONDecodeError:
            processing_options = {}
        
        # 验证文件
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No filename provided"
            )
        
        # 读取文件内容
        content = await file.read()
        
        if len(content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file"
            )
        
        # 检查文件大小（100MB限制）
        max_size = 100 * 1024 * 1024
        if len(content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Max size: {max_size} bytes"
            )
        
        # 处理文件
        result = await process_binary(content, file.filename, **processing_options)
        
        processing_time = time.time() - start_time
        
        return ProcessingResponse(
            success=result.success,
            media_type=result.media_type.value,
            content=result.content,
            metadata=result.metadata,
            error=result.error,
            processed_files=result.processed_files,
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File processing error: {e}")
        processing_time = time.time() - start_time
        
        return ProcessingResponse(
            success=False,
            media_type="unknown",
            error=str(e),
            processing_time=processing_time
        )


@router.post("/batch-process", response_model=BatchProcessingResponse)
async def batch_process_files(
    files: List[UploadFile] = File(...),
    options: str = Form("{}"),
    current_user: User = Depends(get_current_user)
):
    """批量处理上传的文件"""
    import time
    start_time = time.time()
    
    try:
        # 解析处理选项
        try:
            processing_options = json.loads(options)
        except json.JSONDecodeError:
            processing_options = {}
        
        # 验证文件数量
        if len(files) > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Too many files. Maximum 10 files per batch"
            )
        
        # 保存文件到临时目录
        temp_files = []
        temp_dir = tempfile.mkdtemp(prefix="batch_process_")
        
        try:
            for file in files:
                if not file.filename:
                    continue
                
                content = await file.read()
                if len(content) == 0:
                    continue
                
                # 保存到临时文件
                temp_path = os.path.join(temp_dir, file.filename)
                with open(temp_path, 'wb') as f:
                    f.write(content)
                
                temp_files.append(temp_path)
            
            if not temp_files:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No valid files to process"
                )
            
            # 批量处理
            results = await batch_process(temp_files, **processing_options)
            
            # 转换结果
            response_results = []
            successful_count = 0
            
            for result in results:
                if result.success:
                    successful_count += 1
                
                response_results.append(ProcessingResponse(
                    success=result.success,
                    media_type=result.media_type.value,
                    content=result.content,
                    metadata=result.metadata,
                    error=result.error,
                    processed_files=result.processed_files
                ))
            
            processing_time = time.time() - start_time
            
            return BatchProcessingResponse(
                results=response_results,
                total_files=len(files),
                successful_files=successful_count,
                failed_files=len(files) - successful_count,
                total_processing_time=processing_time
            )
            
        finally:
            # 清理临时文件
            import shutil
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp dir: {e}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch processing error: {e}")
        processing_time = time.time() - start_time
        
        return BatchProcessingResponse(
            results=[],
            total_files=len(files),
            successful_files=0,
            failed_files=len(files),
            total_processing_time=processing_time
        )


@router.get("/formats", response_model=SupportedFormatsResponse)
async def get_supported_file_formats(
    current_user: User = Depends(get_current_user)
):
    """获取支持的文件格式"""
    try:
        formats = get_supported_formats()
        capabilities = get_capabilities()
        
        return SupportedFormatsResponse(
            formats=formats,
            capabilities=capabilities
        )
        
    except Exception as e:
        logger.error(f"Get formats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get supported formats"
        )


@router.get("/capabilities")
async def get_processing_capabilities(
    current_user: User = Depends(get_current_user)
):
    """获取处理能力详情"""
    try:
        return get_capabilities()
        
    except Exception as e:
        logger.error(f"Get capabilities error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get capabilities"
        )


@router.post("/process-url")
async def process_file_from_url(
    url: str = Form(...),
    options: str = Form("{}"),
    current_user: User = Depends(get_current_user)
):
    """从URL处理文件"""
    import time
    import httpx
    from urllib.parse import urlparse
    
    start_time = time.time()
    
    try:
        # 解析处理选项
        try:
            processing_options = json.loads(options)
        except json.JSONDecodeError:
            processing_options = {}
        
        # 验证URL
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid URL"
            )
        
        # 下载文件
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            
            content = response.content
            
            # 获取文件名
            filename = os.path.basename(parsed_url.path)
            if not filename:
                # 从Content-Disposition头获取文件名
                content_disposition = response.headers.get('content-disposition')
                if content_disposition:
                    import re
                    match = re.search(r'filename="?([^"]+)"?', content_disposition)
                    if match:
                        filename = match.group(1)
                    else:
                        filename = "downloaded_file"
                else:
                    filename = "downloaded_file"
        
        # 检查文件大小
        max_size = 100 * 1024 * 1024
        if len(content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Max size: {max_size} bytes"
            )
        
        # 处理文件
        result = await process_binary(content, filename, **processing_options)
        
        processing_time = time.time() - start_time
        
        return ProcessingResponse(
            success=result.success,
            media_type=result.media_type.value,
            content=result.content,
            metadata=result.metadata,
            error=result.error,
            processed_files=result.processed_files,
            processing_time=processing_time
        )
        
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to download file: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"URL processing error: {e}")
        processing_time = time.time() - start_time
        
        return ProcessingResponse(
            success=False,
            media_type="unknown",
            error=str(e),
            processing_time=processing_time
        )


@router.get("/health")
async def health_check():
    """健康检查"""
    try:
        from ...multimodal import get_statistics
        stats = get_statistics()
        
        return {
            "status": "healthy",
            "message": "Multimodal processing service is running",
            "statistics": stats
        }
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "error",
            "message": f"Multimodal processing service error: {str(e)}"
        }