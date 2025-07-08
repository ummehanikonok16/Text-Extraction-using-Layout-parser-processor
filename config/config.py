import os
from typing import Optional
from dotenv import load_dotenv

class Config:
    """Singleton configuration class for the application"""
    
    _instance: Optional['Config'] = None
    _initialized: bool = False
    
    def __new__(cls) -> 'Config':
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
        return cls._instance
    
    def __init__(self) -> None:
        if not self._initialized:
            load_dotenv()
            self._load_config()
            Config._initialized = True
    
    def _load_config(self) -> None:
        """Load configuration from environment variables"""
        # Google Cloud Document AI Configuration
        self.GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        self.PROJECT_ID = os.getenv("PROJECT_ID")
        self.LOCATION = os.getenv("LOCATION", "eu")
        self.PROCESSOR_ID = os.getenv("PROCESSOR_ID")
        self.PROCESSOR_VERSION = os.getenv("PROCESSOR_VERSION", "rc")
        
        # Application Configuration
        self.MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "20"))
        self.MAX_FILE_SIZE_BYTES = self.MAX_FILE_SIZE_MB * 1024 * 1024
        self.MAX_PDF_PAGES = int(os.getenv("MAX_PDF_PAGES", "15"))
        self.UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
        self.OUTPUT_DIR = os.getenv("OUTPUT_DIR", "outputs")
        
        # FastAPI Configuration
        self.APP_NAME = os.getenv("APP_NAME", "Document Processing API")
        self.APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
        self.DEBUG = os.getenv("DEBUG", "True").lower() == "true"
        self.HOST = os.getenv("HOST", "0.0.0.0")
        self.PORT = int(os.getenv("PORT", "8000"))
        
        # Create directories if they don't exist
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)
    
    def validate_required_env_vars(self) -> None:
        """Validate that required environment variables are set"""
        required_vars = [
            "GOOGLE_APPLICATION_CREDENTIALS",
            "PROJECT_ID",
            "PROCESSOR_ID"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not getattr(self, var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    @classmethod
    def get_instance(cls) -> 'Config':
        """Get the singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance