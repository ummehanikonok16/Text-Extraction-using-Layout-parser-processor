import os
from typing import List, Dict, Any
from PyPDF2 import PdfWriter, PdfReader
from config.config import Config

class DocumentDivider:
    """Factory class for document division operations"""
    
    def __init__(self) -> None:
        self.config = Config.get_instance()
    
    def check_and_divide_file(self, file_path: str) -> List[str]:
        """
        Check if file meets constraints (max 20MB, max 15 pages for PDF).
        If not, divide into smaller chunks.
        Returns list of file paths (original if no division needed, or chunk paths).
        """
        
        # Check file size
        file_size = os.path.getsize(file_path)
        file_extension = os.path.splitext(file_path)[1].lower()
        
        print(f"File size: {file_size / (1024*1024):.2f} MB")
        
        # For PDF files, check both size and page count
        if file_extension == '.pdf':
            return self._check_and_divide_pdf(file_path)
        
        # For non-PDF files, only check size
        else:
            if file_size <= self.config.MAX_FILE_SIZE_BYTES:
                print("File meets size requirements.")
                return [file_path]
            else:
                print("File exceeds size limit. Dividing file...")
                return self._divide_large_file(file_path)
    
    def _check_and_divide_pdf(self, file_path: str) -> List[str]:
        """Check and divide PDF files based on size and page count"""
        
        try:
            # Read PDF to get page count
            with open(file_path, 'rb') as file:
                pdf_reader = PdfReader(file)
                total_pages = len(pdf_reader.pages)
            
            print(f"PDF has {total_pages} pages")
            
            file_size = os.path.getsize(file_path)
            
            # Check if file meets both constraints
            if file_size <= self.config.MAX_FILE_SIZE_BYTES and total_pages <= self.config.MAX_PDF_PAGES:
                print("PDF meets all requirements.")
                return [file_path]
            
            # Need to divide the PDF
            print("PDF exceeds constraints. Dividing...")
            
            # Calculate pages per chunk based on constraints
            if total_pages > self.config.MAX_PDF_PAGES:
                pages_per_chunk = self.config.MAX_PDF_PAGES
            else:
                # If page count is fine but file is too large, estimate pages per chunk
                pages_per_chunk = max(1, int(self.config.MAX_PDF_PAGES * self.config.MAX_FILE_SIZE_BYTES / file_size))
            
            return self._divide_pdf_by_pages(file_path, pages_per_chunk)
            
        except Exception as e:
            print(f"Error reading PDF: {e}")
            # If we can't read as PDF, treat as regular file
            if os.path.getsize(file_path) <= self.config.MAX_FILE_SIZE_BYTES:
                return [file_path]
            else:
                return self._divide_large_file(file_path)
    
    def _divide_pdf_by_pages(self, file_path: str, pages_per_chunk: int) -> List[str]:
        """Divide PDF into smaller PDFs with specified pages per chunk"""
        
        chunk_paths = []
        base_name = os.path.splitext(file_path)[0]
        
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PdfReader(file)
                total_pages = len(pdf_reader.pages)
                
                chunk_num = 1
                start_page = 0
                
                while start_page < total_pages:
                    end_page = min(start_page + pages_per_chunk, total_pages)
                    
                    # Create new PDF for this chunk
                    pdf_writer = PdfWriter()
                    
                    # Add pages to this chunk
                    for page_num in range(start_page, end_page):
                        pdf_writer.add_page(pdf_reader.pages[page_num])
                    
                    # Save chunk
                    chunk_path = f"{base_name}_chunk_{chunk_num}.pdf"
                    with open(chunk_path, 'wb') as output_file:
                        pdf_writer.write(output_file)
                    
                    chunk_paths.append(chunk_path)
                    print(f"Created chunk {chunk_num}: pages {start_page+1}-{end_page} -> {os.path.basename(chunk_path)}")
                    
                    start_page = end_page
                    chunk_num += 1
                    
        except Exception as e:
            print(f"Error dividing PDF: {e}")
            # Fallback to original file if division fails
            return [file_path]
        
        return chunk_paths
    
    def _divide_large_file(self, file_path: str) -> List[str]:
        """Divide large non-PDF files into smaller chunks"""
        
        chunk_paths = []
        base_name = os.path.splitext(file_path)[0]
        file_extension = os.path.splitext(file_path)[1]
        
        try:
            with open(file_path, 'rb') as input_file:
                chunk_num = 1
                
                while True:
                    chunk_data = input_file.read(self.config.MAX_FILE_SIZE_BYTES)
                    
                    if not chunk_data:
                        break
                    
                    chunk_path = f"{base_name}_chunk_{chunk_num}{file_extension}"
                    
                    with open(chunk_path, 'wb') as chunk_file:
                        chunk_file.write(chunk_data)
                    
                    chunk_paths.append(chunk_path)
                    print(f"Created chunk {chunk_num}: {len(chunk_data)} bytes -> {os.path.basename(chunk_path)}")
                    
                    chunk_num += 1
                    
        except Exception as e:
            print(f"Error dividing file: {e}")
            # Fallback to original file if division fails
            return [file_path]
        
        return chunk_paths
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get basic information about a file"""
        
        if not os.path.exists(file_path):
            return None
        
        file_size = os.path.getsize(file_path)
        file_extension = os.path.splitext(file_path)[1].lower()
        
        info = {
            'path': file_path,
            'size_bytes': file_size,
            'size_mb': file_size / (1024*1024),
            'extension': file_extension
        }
        
        # Add PDF-specific info
        if file_extension == '.pdf':
            try:
                with open(file_path, 'rb') as file:
                    pdf_reader = PdfReader(file)
                    info['pages'] = len(pdf_reader.pages)
            except:
                info['pages'] = 'Unknown'
        
        return info
    
    def cleanup_chunks(self, original_file: str, chunk_files: List[str]) -> None:
        """Clean up temporary chunk files while keeping the original"""
        for chunk_file in chunk_files:
            if chunk_file != original_file and os.path.exists(chunk_file):
                try:
                    os.remove(chunk_file)
                    print(f"Cleaned up temporary chunk: {os.path.basename(chunk_file)}")
                except Exception as e:
                    print(f"Error cleaning up {chunk_file}: {e}")
    
    def validate_file_constraints(self, file_path: str) -> Dict[str, Any]:
        """Validate file against constraints and return detailed info"""
        info = self.get_file_info(file_path)
        if not info:
            return {'valid': False, 'reason': 'File does not exist'}
        
        validation = {
            'valid': True,
            'reasons': [],
            'file_info': info,
            'needs_division': False
        }
        
        # Check file size
        if info['size_bytes'] > self.config.MAX_FILE_SIZE_BYTES:
            validation['valid'] = False
            validation['needs_division'] = True
            validation['reasons'].append(f"File size ({info['size_mb']:.2f} MB) exceeds limit ({self.config.MAX_FILE_SIZE_MB} MB)")
        
        # Check PDF pages if applicable
        if info['extension'] == '.pdf' and 'pages' in info:
            if isinstance(info['pages'], int) and info['pages'] > self.config.MAX_PDF_PAGES:
                validation['valid'] = False
                validation['needs_division'] = True
                validation['reasons'].append(f"PDF pages ({info['pages']}) exceed limit ({self.config.MAX_PDF_PAGES} pages)")
        
        return validation