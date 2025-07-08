from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class FileInfo(BaseModel):
    """Basic file information"""
    filename: str
    size_bytes: int
    size_mb: float
    extension: str
    mime_type: Optional[str] = None

class ProcessingStep(BaseModel):
    """Individual processing step result"""
    step: str
    success: bool
    output: Any
    details: str
    timestamp: Optional[datetime] = None

class ExtractionMetadata(BaseModel):
    """Metadata from text extraction"""
    chunks_processed: int
    extraction_methods: List[Optional[str]]
    total_file_size: int
    page_count: Optional[int] = None

class DocumentProcessingResult(BaseModel):
    """Result from processing a single document"""
    success: bool
    file_path: str
    filename: str
    extracted_text: str
    text_length: int
    output_file: Optional[str] = None
    processing_steps: List[ProcessingStep]
    metadata: ExtractionMetadata
    error: Optional[str] = None
    record_id: Optional[str] = None
    processing_time: Optional[str] = None

class MultipleDocumentsResult(BaseModel):
    """Result from processing multiple documents"""
    success: bool
    total_files: int
    successful_files: int
    failed_files: int
    individual_results: List[DocumentProcessingResult]
    combined_text: str
    processing_summary: Dict[str, Any]

class UploadResponse(BaseModel):
    """Response from file upload"""
    success: bool
    message: str
    filename: str
    file_path: str
    file_size: int
    upload_id: str

class ProcessingRequest(BaseModel):
    """Request to process uploaded files"""
    file_paths: List[str]
    save_output: bool = Field(default=True, description="Whether to save extracted text to files")
    combine_results: bool = Field(default=False, description="Whether to combine all extracted text")

class ProcessingStatusResponse(BaseModel):
    """System processing status"""
    converter_available: bool
    divider_available: bool
    extractor_status: Dict[str, Any]
    database_available: bool
    output_directory: str
    upload_directory: str
    max_file_size_mb: int
    max_pdf_pages: int

class ValidationResult(BaseModel):
    """File validation result"""
    valid: bool
    reasons: List[str]
    file_info: FileInfo
    needs_division: bool

class ErrorResponse(BaseModel):
    """Standard error response"""
    success: bool = False
    error: str
    details: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class SupportedFormatsResponse(BaseModel):
    """Supported file formats"""
    images: List[str]
    documents: List[str]
    text: List[str]
    code: List[str]
    other: List[str]

class DocumentAIConfig(BaseModel):
    """Document AI configuration status"""
    valid: bool
    issues: List[str]
    config_status: Dict[str, bool]

class DatabaseRecord(BaseModel):
    """Database record for processed documents"""
    id: str
    filename: str
    file_size: int
    status: str
    processed_at: str
    extracted_text_length: int

class ProcessingJobStatus(BaseModel):
    """Status of a processing job"""
    job_id: str
    status: str  # pending, processing, completed, failed
    created_at: datetime
    updated_at: datetime
    file_count: int
    completed_files: int
    failed_files: int
    current_file: Optional[str] = None
    estimated_completion: Optional[datetime] = None

class TextExtractionOptions(BaseModel):
    """Options for text extraction"""
    chunk_size: int = Field(default=1000, description="Size of text chunks for processing")
    include_headings: bool = Field(default=True, description="Include ancestor headings in chunks")
    preserve_layout: bool = Field(default=True, description="Preserve document layout information")
    extract_tables: bool = Field(default=True, description="Extract table content")
    extract_images: bool = Field(default=False, description="Extract image descriptions")

class ConversionOptions(BaseModel):
    """Options for document conversion"""
    force_pdf_conversion: bool = Field(default=False, description="Force conversion to PDF even if already PDF")
    preserve_formatting: bool = Field(default=True, description="Preserve original formatting")
    compress_output: bool = Field(default=False, description="Compress output files")
    image_quality: int = Field(default=85, ge=1, le=100, description="Image quality for conversion (1-100)")

class ProcessingConfig(BaseModel):
    """Configuration for document processing"""
    conversion_options: ConversionOptions = ConversionOptions()
    extraction_options: TextExtractionOptions = TextExtractionOptions()
    save_intermediate_files: bool = Field(default=False, description="Keep intermediate files (chunks, converted PDFs)")
    parallel_processing: bool = Field(default=False, description="Process multiple files in parallel")
    max_concurrent_jobs: int = Field(default=3, ge=1, le=10, description="Maximum concurrent processing jobs")