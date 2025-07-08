from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn

from config.config import Config
from database.database_connection import DatabaseConnection
from services.document_processing.document_router import router as document_router

# Initialize configuration
config = Config.get_instance()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("Starting Document Processing API...")
    
    try:
        # Validate required environment variables
        config.validate_required_env_vars()
        print("✓ Configuration validation passed")
        
        # Initialize database connection
        db_connection = DatabaseConnection.get_instance()
        db_connection.connect()
        print("✓ Database connection initialized")
        
        print(f"✓ Upload directory: {config.UPLOAD_DIR}")
        print(f"✓ Output directory: {config.OUTPUT_DIR}")
        print(f"✓ Max file size: {config.MAX_FILE_SIZE_MB} MB")
        print(f"✓ Max PDF pages: {config.MAX_PDF_PAGES}")
        
        print("🚀 Document Processing API is ready!")
        
    except Exception as e:
        print(f"❌ Startup error: {e}")
        print("⚠️  Some features may not work properly")
    
    yield
    
    # Shutdown
    print("Shutting down Document Processing API...")
    
    try:
        db_connection = DatabaseConnection.get_instance()
        db_connection.disconnect()
        print("✓ Database connection closed")
    except:
        pass
    
    print("👋 Document Processing API shutdown complete")

# Create FastAPI application
app = FastAPI(
    title=config.APP_NAME,
    version=config.APP_VERSION,
    description="""
    ## Document Processing API
    
    A streamlined API for processing various document formats and extracting text using Google Document AI.
    
    ### Main Endpoint:
    **POST /api/documents/process** - Upload and process one or more documents
    
    ### Features:
    - **Multi-Format Support**: PDF, DOCX, DOC, PPTX, PPT, XLSX, XLS, Images, Text files
    - **Automatic Conversion**: Converts various formats to PDF when needed
    - **Smart Chunking**: Automatically splits large files into processable chunks
    - **Text Extraction**: Uses Google Document AI for advanced text extraction
    - **Direct Text Reading**: Handles .txt files directly without AI processing
    - **Auto Cleanup**: Automatically cleans up temporary files
    
    ### Supported Formats:
    - **Documents**: PDF, DOCX, DOC, PPTX, PPT, XLSX, XLS
    - **Images**: JPG, JPEG, PNG, TIFF, TIF, BMP, GIF, WEBP
    - **Text**: TXT, RTF, HTML, HTM, XML, JSON, YAML, YML
    - **Code**: PY, JS, CSS, JAVA, CPP, C, SQL
    - **Other**: CSV
    
    ### Simple Workflow:
    1. **Upload** → Select your documents (multiple files supported)
    2. **Process** → Automatic conversion, chunking, and text extraction
    3. **Download** → Get your extracted text files
    
    ### Usage:
    Send a POST request to `/api/documents/process` with your files as form-data.
    The API will handle everything automatically and return detailed results.
    """,
    debug=config.DEBUG,
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(document_router)

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Welcome to Document Processing API",
        "version": config.APP_VERSION,
        "status": "running",
        "main_endpoint": "POST /api/documents/process",
        "description": "Upload and process documents with automatic text extraction",
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/health",
            "process": "/api/documents/process",
            "status": "/api/documents/status",
            "supported_formats": "/api/documents/supported-formats",
            "list_outputs": "/api/documents/list-outputs",
            "download": "/api/documents/download/{filename}",
            "cleanup": "/api/documents/cleanup"
        },
        "features": [
            "Multi-format document processing",
            "Automatic file conversion",
            "Smart file chunking",
            "Google Document AI integration",
            "Direct text file reading",
            "Automatic cleanup"
        ]
    }

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Simple health check endpoint"""
    return {
        "status": "healthy",
        "service": config.APP_NAME,
        "version": config.APP_VERSION
    }

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors"""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "details": str(exc) if config.DEBUG else "An unexpected error occurred"
        }
    )

# Custom exception handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Custom 404 handler"""
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "error": "Endpoint not found",
            "details": f"The requested endpoint '{request.url.path}' was not found"
        }
    )

@app.exception_handler(500)
async def internal_server_error_handler(request, exc):
    """Custom 500 handler"""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "details": str(exc) if config.DEBUG else "An unexpected error occurred"
        }
    )

if __name__ == "__main__":
    # Run the application
    print(f"Starting {config.APP_NAME} v{config.APP_VERSION}")
    print(f"Debug mode: {config.DEBUG}")
    print(f"Server will run on {config.HOST}:{config.PORT}")
    
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.DEBUG,
        log_level="info" if not config.DEBUG else "debug"
    )