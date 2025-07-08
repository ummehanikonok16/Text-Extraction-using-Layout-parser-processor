import os
import mimetypes
from typing import Optional, Dict, Any
from google.api_core.client_options import ClientOptions
from google.cloud import documentai
from config.config import Config

class TextExtractor:
    """Factory class for text extraction operations using Google Document AI"""
    
    def __init__(self) -> None:
        self.config = Config.get_instance()
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize Document AI client"""
        try:
            self.client = documentai.DocumentProcessorServiceClient(
                client_options=ClientOptions(
                    api_endpoint=f"{self.config.LOCATION}-documentai.googleapis.com"
                )
            )
            print("Document AI client initialized successfully")
        except Exception as e:
            print(f"Error initializing Document AI client: {e}")
            self.client = None
    
    def process_document(self, file_path: str, mime_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Process document and extract text using Google Document AI or direct text reading
        Returns a dictionary with extraction results
        """
        
        try:
            print(f"    Processing document: {os.path.basename(file_path)}")
            
            # Get MIME type if not provided
            if not mime_type:
                mime_type = self.get_mime_type(file_path)
            
            print(f"    MIME type: {mime_type}")
            
            # Handle text files directly without Document AI
            if mime_type == 'text/plain' or file_path.lower().endswith('.txt'):
                return self._process_text_file_directly(file_path)
            
            # Use Document AI for other file types
            if not self.client:
                return {
                    'success': False,
                    'text': '',
                    'error': 'Document AI client not initialized',
                    'metadata': {}
                }
            
            # Get processor path
            name = self.client.processor_version_path(
                self.config.PROJECT_ID, 
                self.config.LOCATION, 
                self.config.PROCESSOR_ID, 
                self.config.PROCESSOR_VERSION
            )

            print(f"    Reading file: {os.path.basename(file_path)}")
            # Read file
            with open(file_path, "rb") as image:
                image_content = image.read()
            
            print(f"    File size: {len(image_content)} bytes")

            # Configure process options for layout analysis
            process_options = documentai.ProcessOptions(
                layout_config=documentai.ProcessOptions.LayoutConfig(
                    chunking_config=documentai.ProcessOptions.LayoutConfig.ChunkingConfig(
                        chunk_size=1000,
                        include_ancestor_headings=True,
                    )
                )
            )

            print(f"    Sending request to Document AI...")
            # Process document
            request = documentai.ProcessRequest(
                name=name,
                raw_document=documentai.RawDocument(content=image_content, mime_type=mime_type),
                process_options=process_options,
            )

            result = self.client.process_document(request=request)
            document = result.document
            
            print(f"    Document AI processing completed")

            # Extract text using multiple methods
            extracted_text, extraction_method = self._extract_text_from_document(document)
            
            # Prepare metadata
            metadata = {
                'file_path': file_path,
                'file_size': len(image_content),
                'mime_type': mime_type,
                'extraction_method': extraction_method,
                'text_length': len(extracted_text) if extracted_text else 0
            }
            
            # Add document-specific metadata if available
            if hasattr(document, 'pages') and document.pages:
                metadata['page_count'] = len(document.pages)
            
            return {
                'success': True,
                'text': extracted_text,
                'error': None,
                'metadata': metadata
            }
            
        except Exception as e:
            print(f"    Error in process_document: {str(e)}")
            return {
                'success': False,
                'text': '',
                'error': f"Error processing document: {str(e)}",
                'metadata': {'file_path': file_path}
            }
    
    def _extract_text_from_document(self, document) -> tuple[str, str]:
        """Extract text using multiple methods and return text with method used"""
        
        # Method 1: Direct text
        if document.text and document.text.strip():
            print(f"    Using direct text extraction - {len(document.text)} characters")
            return document.text, "direct_text"

        # Method 2: From chunks
        if hasattr(document, 'chunked_document') and document.chunked_document:
            if document.chunked_document.chunks:
                chunk_text = ""
                chunk_count = len(document.chunked_document.chunks)
                print(f"    Using chunked text extraction - {chunk_count} chunks found")
                for chunk in document.chunked_document.chunks:
                    if hasattr(chunk, 'content'):
                        chunk_text += chunk.content + "\n"
                if chunk_text.strip():
                    print(f"    Chunked text extraction successful - {len(chunk_text)} characters")
                    return chunk_text, "chunked_text"

        # Method 3: From layout blocks
        if hasattr(document, 'document_layout') and document.document_layout:
            if document.document_layout.blocks:
                layout_text = ""
                block_count = len(document.document_layout.blocks)
                print(f"    Using layout block extraction - {block_count} blocks found")
                for block in document.document_layout.blocks:
                    if hasattr(block, 'text_block') and block.text_block:
                        if hasattr(block.text_block, 'text'):
                            layout_text += block.text_block.text + "\n"
                if layout_text.strip():
                    print(f"    Layout block extraction successful - {len(layout_text)} characters")
                    return layout_text, "layout_blocks"

        print(f"    Warning: No text extraction method succeeded")
        return "No text could be extracted from the document.", "none"
    
    def _process_text_file_directly(self, file_path: str) -> Dict[str, Any]:
        """Process text files directly without Document AI"""
        try:
            print(f"    Reading text file directly: {os.path.basename(file_path)}")
            
            # Read text file with multiple encoding attempts
            encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252', 'ascii', 'cp1253']
            text_content = None
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        text_content = f.read()
                    print(f"    Successfully read with {encoding} encoding")
                    break
                except UnicodeDecodeError:
                    continue
            
            # If all encodings fail, read as binary and decode with errors='ignore'
            if text_content is None:
                with open(file_path, 'rb') as f:
                    text_content = f.read().decode('utf-8', errors='ignore')
                print(f"    Read with fallback binary method")
            
            if not text_content or not text_content.strip():
                text_content = "The text file appears to be empty or contains no readable content."
            
            file_size = os.path.getsize(file_path)
            
            return {
                'success': True,
                'text': text_content,
                'error': None,
                'metadata': {
                    'file_path': file_path,
                    'file_size': file_size,
                    'mime_type': 'text/plain',
                    'extraction_method': 'direct_read',
                    'text_length': len(text_content)
                }
            }
            
        except Exception as e:
            print(f"    Error reading text file: {str(e)}")
            return {
                'success': False,
                'text': '',
                'error': f"Error reading text file: {str(e)}",
                'metadata': {'file_path': file_path}
            }
    
    def get_mime_type(self, file_path: str) -> str:
        """Get MIME type for file"""
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type is None:
            extension = os.path.splitext(file_path)[1].lower()
            mime_map = {
                '.pdf': 'application/pdf',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.tiff': 'image/tiff',
                '.tif': 'image/tiff',
                '.bmp': 'image/bmp',
                '.gif': 'image/gif',
                '.webp': 'image/webp',
                '.txt': 'text/plain',
                '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                '.doc': 'application/msword',
                '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                '.ppt': 'application/vnd.ms-powerpoint',
                '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                '.xls': 'application/vnd.ms-excel'
            }
            mime_type = mime_map.get(extension, 'application/pdf')
        return mime_type
    
    def extract_text_from_multiple_files(self, file_paths: list) -> Dict[str, Any]:
        """Extract text from multiple files and return combined results"""
        results = {
            'success': True,
            'files_processed': 0,
            'files_failed': 0,
            'combined_text': '',
            'individual_results': [],
            'errors': []
        }
        
        for file_path in file_paths:
            result = self.process_document(file_path)
            results['individual_results'].append(result)
            
            if result['success']:
                results['files_processed'] += 1
                if result['text']:
                    results['combined_text'] += f"\n\n--- FILE: {os.path.basename(file_path)} ---\n\n"
                    results['combined_text'] += result['text']
            else:
                results['files_failed'] += 1
                results['errors'].append({
                    'file': file_path,
                    'error': result['error']
                })
        
        if results['files_failed'] > 0:
            results['success'] = results['files_processed'] > 0
        
        return results
    
    def validate_document_ai_setup(self) -> Dict[str, Any]:
        """Validate Document AI configuration and connectivity"""
        validation = {
            'valid': True,
            'issues': [],
            'config_status': {}
        }
        
        # Check configuration
        required_configs = [
            ('GOOGLE_APPLICATION_CREDENTIALS', self.config.GOOGLE_APPLICATION_CREDENTIALS),
            ('PROJECT_ID', self.config.PROJECT_ID),
            ('PROCESSOR_ID', self.config.PROCESSOR_ID),
            ('LOCATION', self.config.LOCATION)
        ]
        
        for config_name, config_value in required_configs:
            validation['config_status'][config_name] = bool(config_value)
            if not config_value:
                validation['valid'] = False
                validation['issues'].append(f"Missing {config_name}")
        
        # Check client initialization
        if not self.client:
            validation['valid'] = False
            validation['issues'].append("Document AI client not initialized")
        
        # Check credentials file exists
        if self.config.GOOGLE_APPLICATION_CREDENTIALS:
            if not os.path.exists(self.config.GOOGLE_APPLICATION_CREDENTIALS):
                validation['valid'] = False
                validation['issues'].append("Google credentials file not found")
        
        return validation
    
    def get_supported_formats(self) -> Dict[str, list]:
        """Return list of supported file formats"""
        return {
            'images': ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif', '.webp'],
            'documents': ['.pdf', '.docx', '.doc', '.pptx', '.ppt', '.xlsx', '.xls'],
            'text': ['.txt', '.rtf', '.html', '.htm', '.xml', '.json', '.yaml', '.yml'],
            'code': ['.py', '.js', '.css', '.java', '.cpp', '.c', '.sql'],
            'other': ['.csv']
        }