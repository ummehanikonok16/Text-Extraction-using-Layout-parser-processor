import os
import shutil
import uuid
from typing import List
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse
import aiofiles

from config.config import Config
from .processor import DocumentProcessor
from .document_schema import (
    MultipleDocumentsResult,
    ProcessingStatusResponse,
    SupportedFormatsResponse
)

# Initialize router
router = APIRouter(prefix="/api/documents", tags=["Document Processing"])

# Initialize services
config = Config.get_instance()
processor = DocumentProcessor()

@router.get("/health", summary="Health check for document processing service")
async def health_check():
    """Check if the document processing service is healthy"""
    try:
        status = processor.get_processing_status()
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service_status": status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Service unhealthy: {str(e)}")

@router.get("/status", response_model=ProcessingStatusResponse, summary="Get processing system status")
async def get_processing_status():
    """Get detailed status of the document processing system"""
    try:
        return processor.get_processing_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting status: {str(e)}")

@router.get("/supported-formats", response_model=SupportedFormatsResponse, summary="Get supported file formats")
async def get_supported_formats():
    """Get list of supported file formats for processing"""
    try:
        return processor.extractor.get_supported_formats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting supported formats: {str(e)}")

@router.post("/process", response_model=MultipleDocumentsResult, summary="Upload and process documents")
async def upload_and_process_documents(
    files: List[UploadFile] = File(...),
    save_output: bool = Query(default=True, description="Save extracted text to files"),
    background_tasks: BackgroundTasks = None
):
    """
    Upload and process one or more documents through the complete workflow.
    This is the main endpoint for document processing.
    
    Features:
    - Supports multiple file formats (PDF, DOCX, images, text files, etc.)
    - Automatic format conversion to PDF when needed
    - Smart file chunking for large documents
    - Text extraction using Google Document AI
    - Automatic cleanup of temporary files
    """
    try:
        # Cleanup old files first
        await cleanup_old_files()
        
        uploaded_files = []
        file_paths = []
        
        # Upload all files first
        for file in files:
            # Generate unique upload ID
            upload_id = str(uuid.uuid4())
            filename = f"{upload_id}_{file.filename}"
            file_path = os.path.join(config.UPLOAD_DIR, filename)
            
            # Save uploaded file
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
            
            uploaded_files.append({
                'original_name': file.filename,
                'saved_path': file_path,
                'size': len(content)
            })
            file_paths.append(file_path)
        
        print(f"Successfully uploaded {len(file_paths)} files")
        
        # Process all uploaded files
        result = processor.process_multiple_files(file_paths, save_output)
        
        # Add cleanup tasks for uploaded files
        if background_tasks:
            for file_path in file_paths:
                background_tasks.add_task(cleanup_uploaded_file, file_path)
        
        # Add file upload information to metadata
        result['upload_info'] = uploaded_files
        result['cleanup_scheduled'] = True
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        # Clean up uploaded files in case of error
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass
        
        raise HTTPException(status_code=500, detail=f"Error processing files: {str(e)}")

@router.get("/list-outputs", summary="List all output files")
async def list_output_files():
    """
    List all available output files
    """
    try:
        output_files = []
        
        if os.path.exists(config.OUTPUT_DIR):
            for filename in os.listdir(config.OUTPUT_DIR):
                if filename.endswith(('.txt', '.pdf')):
                    file_path = os.path.join(config.OUTPUT_DIR, filename)
                    file_stat = os.stat(file_path)
                    output_files.append({
                        'filename': filename,
                        'size': file_stat.st_size,
                        'created': datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
                        'modified': datetime.fromtimestamp(file_stat.st_mtime).isoformat()
                    })
        
        return {
            "success": True,
            "output_directory": config.OUTPUT_DIR,
            "files": output_files,
            "total_files": len(output_files)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing output files: {str(e)}")

@router.get("/download/{filename}", summary="Download processed output file")
async def download_output_file(filename: str):
    """
    Download a processed output file
    """
    try:
        file_path = os.path.join(config.OUTPUT_DIR, filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Output file not found")
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='text/plain'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading file: {str(e)}")

@router.delete("/cleanup", summary="Clean up all temporary and output files")
async def cleanup_all_files():
    """
    Clean up all uploaded and output files
    """
    try:
        upload_count = 0
        output_count = 0
        
        # Clean uploads
        if os.path.exists(config.UPLOAD_DIR):
            for filename in os.listdir(config.UPLOAD_DIR):
                file_path = os.path.join(config.UPLOAD_DIR, filename)
                try:
                    os.remove(file_path)
                    upload_count += 1
                except Exception:
                    pass
        
        # Clean outputs
        if os.path.exists(config.OUTPUT_DIR):
            for filename in os.listdir(config.OUTPUT_DIR):
                file_path = os.path.join(config.OUTPUT_DIR, filename)
                try:
                    os.remove(file_path)
                    output_count += 1
                except Exception:
                    pass
        
        return {
            "success": True,
            "message": f"Cleaned up {upload_count} upload files and {output_count} output files",
            "uploads_deleted": upload_count,
            "outputs_deleted": output_count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cleaning up files: {str(e)}")

# Background task functions
async def cleanup_uploaded_file(file_path: str):
    """Background task to clean up uploaded files after processing"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Cleaned up uploaded file: {os.path.basename(file_path)}")
    except Exception as e:
        print(f"Error cleaning up file {file_path}: {e}")

async def cleanup_old_files():
    """Clean up old files to prevent accumulation"""
    try:
        current_time = datetime.now().timestamp()
        
        # Clean files older than 1 hour from uploads
        if os.path.exists(config.UPLOAD_DIR):
            for filename in os.listdir(config.UPLOAD_DIR):
                file_path = os.path.join(config.UPLOAD_DIR, filename)
                try:
                    file_time = os.path.getctime(file_path)
                    if (current_time - file_time) > 3600:  # 1 hour
                        os.remove(file_path)
                        print(f"Cleaned up old upload: {filename}")
                except Exception:
                    pass
        
        # Clean files older than 24 hours from outputs
        if os.path.exists(config.OUTPUT_DIR):
            for filename in os.listdir(config.OUTPUT_DIR):
                file_path = os.path.join(config.OUTPUT_DIR, filename)
                try:
                    file_time = os.path.getctime(file_path)
                    if (current_time - file_time) > 86400:  # 24 hours
                        os.remove(file_path)
                        print(f"Cleaned up old output: {filename}")
                except Exception:
                    pass
                    
    except Exception as e:
        print(f"Error during automatic cleanup: {e}")