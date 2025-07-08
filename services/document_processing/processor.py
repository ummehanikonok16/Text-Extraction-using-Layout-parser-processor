import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from config.config import Config
from database.database_manager import DatabaseManager
from .conversion import DocumentConverter
from .divide import DocumentDivider
from .extraction import TextExtractor

class DocumentProcessor:
    """Main processor that coordinates conversion → divide → extract workflow"""
    
    def __init__(self) -> None:
        self.config = Config.get_instance()
        self.db_manager = DatabaseManager()
        self.converter = DocumentConverter()
        self.divider = DocumentDivider()
        self.extractor = TextExtractor()
    
    def process_single_file(self, file_path: str, save_output: bool = True) -> Dict[str, Any]:
        """
        Process a single file through the complete workflow
        Returns detailed processing results
        """
        
        print(f"\n{'='*80}")
        print(f"PROCESSING FILE: {os.path.basename(file_path)}")
        print(f"Full path: {file_path}")
        print(f"{'='*80}")
        
        if not os.path.exists(file_path):
            return self._create_error_result(file_path, "File does not exist")
        
        # Initialize result structure
        result = {
            'success': False,
            'file_path': file_path,
            'filename': os.path.basename(file_path),
            'extracted_text': '',
            'text_length': 0,
            'output_file': None,
            'processing_steps': [],
            'metadata': {},
            'error': None,
            'record_id': None
        }
        
        try:
            # Save initial record to database
            file_info = {
                'filename': result['filename'],
                'file_size': os.path.getsize(file_path),
                'status': 'processing'
            }
            result['record_id'] = self.db_manager.save_processing_record(file_info)
            
            # Step 1: Convert to PDF if needed
            print(f"STEP 1: Converting to PDF...")
            pdf_file_path = self.converter.convert_to_pdf(file_path)
            result['processing_steps'].append({
                'step': 'conversion',
                'success': True,
                'output': pdf_file_path,
                'details': f"Converted to: {os.path.basename(pdf_file_path)}"
            })
            print(f"  ✓ Conversion completed: {os.path.basename(pdf_file_path)}")
            
            # Step 2: Check file constraints and divide if necessary
            print(f"STEP 2: Checking file constraints...")
            file_chunks = self.divider.check_and_divide_file(pdf_file_path)
            result['processing_steps'].append({
                'step': 'division',
                'success': True,
                'output': file_chunks,
                'details': f"Created {len(file_chunks)} chunk(s)"
            })
            print(f"  ✓ File division completed. Chunks: {len(file_chunks)}")
            
            # Step 3: Extract text from each chunk
            print(f"STEP 3: Extracting text from {len(file_chunks)} chunk(s)...")
            all_extracted_text = []
            extraction_results = []
            
            for j, chunk_path in enumerate(file_chunks):
                print(f"  Processing chunk {j+1}/{len(file_chunks)}: {os.path.basename(chunk_path)}")
                
                chunk_result = self.extractor.process_document(chunk_path)
                extraction_results.append(chunk_result)
                
                if chunk_result['success'] and chunk_result['text']:
                    text_length = len(chunk_result['text'])
                    print(f"    ✓ Extracted {text_length} characters")
                    all_extracted_text.append(chunk_result['text'])
                    
                    # Show a small preview
                    preview = chunk_result['text'][:100].replace('\n', ' ').strip()
                    print(f"    Preview: \"{preview}...\"")
                else:
                    print(f"    ⚠ No text extracted from this chunk: {chunk_result.get('error', 'Unknown error')}")
                    all_extracted_text.append("No text could be extracted from this chunk.")
                
                # Clean up temporary chunk files (keep original PDF)
                if chunk_path != pdf_file_path and os.path.exists(chunk_path):
                    try:
                        os.remove(chunk_path)
                        print(f"    Cleaned up temporary chunk: {os.path.basename(chunk_path)}")
                    except:
                        pass
            
            result['processing_steps'].append({
                'step': 'extraction',
                'success': True,
                'output': extraction_results,
                'details': f"Processed {len(file_chunks)} chunks"
            })
            
            # Step 4: Merge all extracted text
            print(f"STEP 4: Merging extracted text...")
            if len(file_chunks) > 1:
                final_text = "\n\n--- CHUNK SEPARATOR ---\n\n".join(all_extracted_text)
            else:
                final_text = all_extracted_text[0] if all_extracted_text else "No text could be extracted."
            
            result['extracted_text'] = final_text
            result['text_length'] = len(final_text)
            result['metadata'] = {
                'chunks_processed': len(file_chunks),
                'extraction_methods': [r.get('metadata', {}).get('extraction_method') for r in extraction_results],
                'total_file_size': sum(r.get('metadata', {}).get('file_size', 0) for r in extraction_results)
            }
            
            print(f"  ✓ Total merged text length: {result['text_length']} characters")
            
            # Step 5: Save to output file if requested
            if save_output:
                print(f"STEP 5: Saving to output file...")
                output_file = self._save_extracted_text(file_path, final_text, result['metadata'])
                result['output_file'] = output_file
                print(f"  ✓ Text saved to: {os.path.basename(output_file)}")
            
            # Clean up temporary PDF if it was created
            if pdf_file_path != file_path and os.path.exists(pdf_file_path):
                try:
                    os.remove(pdf_file_path)
                    print(f"  Cleaned up temporary PDF: {os.path.basename(pdf_file_path)}")
                except:
                    pass
            
            result['success'] = True
            
            # Update database record
            if result['record_id']:
                self.db_manager.update_record_status(result['record_id'], 'completed')
            
            print(f"\n✓ SUCCESS: {os.path.basename(file_path)} processed successfully!")
            return result
            
        except Exception as e:
            error_msg = f"Error processing {os.path.basename(file_path)}: {str(e)}"
            print(f"\n✗ ERROR: {error_msg}")
            
            result['error'] = error_msg
            result['success'] = False
            
            # Update database record
            if result['record_id']:
                self.db_manager.update_record_status(result['record_id'], 'failed')
            
            # Save error info to file
            if save_output:
                self._save_error_info(file_path, str(e))
            
            return result
    
    def process_multiple_files(self, file_paths: List[str], save_output: bool = True) -> Dict[str, Any]:
        """
        Process multiple files and return comprehensive results
        """
        total_files = len(file_paths)
        print(f"\n{'='*80}")
        print(f"MULTI-FILE EXTRACTION STARTED")
        print(f"Total files selected: {total_files}")
        print(f"{'='*80}")
        
        # List all selected files first
        print(f"\nSELECTED FILES:")
        for i, file_path in enumerate(file_paths, 1):
            print(f"  {i}. {os.path.basename(file_path)}")
        
        results = {
            'success': True,
            'total_files': total_files,
            'successful_files': 0,
            'failed_files': 0,
            'individual_results': [],
            'combined_text': '',
            'processing_summary': {
                'start_time': datetime.now().isoformat(),
                'end_time': None,
                'duration': None
            }
        }
        
        start_time = datetime.now()
        
        # Process each file individually
        for i, file_path in enumerate(file_paths, 1):
            print(f"\n--- Processing file {i}/{total_files} ---")
            
            file_result = self.process_single_file(file_path, save_output)
            results['individual_results'].append(file_result)
            
            if file_result['success']:
                results['successful_files'] += 1
                if file_result['extracted_text']:
                    results['combined_text'] += f"\n\n=== FILE {i}: {file_result['filename']} ===\n\n"
                    results['combined_text'] += file_result['extracted_text']
            else:
                results['failed_files'] += 1
            
            print(f"Completed {i}/{total_files} files.")
        
        # Calculate final statistics
        end_time = datetime.now()
        results['processing_summary']['end_time'] = end_time.isoformat()
        results['processing_summary']['duration'] = str(end_time - start_time)
        
        if results['failed_files'] > 0:
            results['success'] = results['successful_files'] > 0
        
        # Print final summary
        self._print_processing_summary(results)
        
        return results
    
    def _create_error_result(self, file_path: str, error_message: str) -> Dict[str, Any]:
        """Create a standardized error result"""
        return {
            'success': False,
            'file_path': file_path,
            'filename': os.path.basename(file_path),
            'extracted_text': '',
            'text_length': 0,
            'output_file': None,
            'processing_steps': [],
            'metadata': {},
            'error': error_message,
            'record_id': None
        }
    
    def _save_extracted_text(self, original_file_path: str, text: str, metadata: Dict[str, Any]) -> str:
        """Save extracted text to output file"""
        output_file = os.path.join(
            self.config.OUTPUT_DIR,
            os.path.splitext(os.path.basename(original_file_path))[0] + "_extracted.txt"
        )
        
        # Handle duplicate output file names
        counter = 1
        original_output_file = output_file
        while os.path.exists(output_file):
            base_name = os.path.splitext(original_output_file)[0]
            output_file = f"{base_name}_{counter}.txt"
            counter += 1
        
        # Write the file with header
        with open(output_file, 'w', encoding='utf-8') as f:
            header = f"""Extracted Text from: {os.path.basename(original_file_path)}
Source: {original_file_path}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Characters: {len(text)}
Lines: {len(text.splitlines())}
Chunks Processed: {metadata.get('chunks_processed', 1)}
{'='*60}

"""
            f.write(header)
            f.write(text)
        
        return output_file
    
    def _save_error_info(self, file_path: str, error: str) -> str:
        """Save error information to file"""
        error_file = os.path.join(
            self.config.OUTPUT_DIR,
            os.path.splitext(os.path.basename(file_path))[0] + "_extraction_error.txt"
        )
        
        try:
            with open(error_file, 'w', encoding='utf-8') as f:
                f.write(f"Error extracting text from: {file_path}\n")
                f.write(f"Error: {error}\n")
                f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            print(f"  Error details saved to: {os.path.basename(error_file)}")
            return error_file
        except Exception as e:
            print(f"  Could not save error details to file: {e}")
            return None
    
    def _print_processing_summary(self, results: Dict[str, Any]) -> None:
        """Print comprehensive processing summary"""
        print(f"\n{'='*80}")
        print(f"MULTI-FILE EXTRACTION COMPLETE")
        print(f"{'='*80}")
        print(f"Total files processed: {results['total_files']}")
        print(f"Successful extractions: {results['successful_files']}")
        print(f"Failed extractions: {results['failed_files']}")
        if results['total_files'] > 0:
            print(f"Success rate: {(results['successful_files']/results['total_files'])*100:.1f}%")
        print(f"Processing duration: {results['processing_summary']['duration']}")
        
        print(f"\nDETAILED RESULTS:")
        for i, result in enumerate(results['individual_results'], 1):
            status_symbol = "✓" if result['success'] else "✗"
            status_text = "SUCCESS" if result['success'] else "FAILED"
            print(f"  {i}. {status_symbol} {result['filename']} - {status_text}")
            if not result['success'] and result['error']:
                print(f"     Error: {result['error']}")
        
        if results['successful_files'] > 0:
            print(f"\n✓ Output files saved to: {self.config.OUTPUT_DIR}")
        if results['failed_files'] > 0:
            print(f"\n✗ Check error files in: {self.config.OUTPUT_DIR}")
        
        print(f"{'='*80}")
    
    def get_processing_status(self) -> Dict[str, Any]:
        """Get overall processing system status"""
        return {
            'converter_available': True,
            'divider_available': True,
            'extractor_status': self.extractor.validate_document_ai_setup(),
            'database_available': True,  # Placeholder
            'output_directory': self.config.OUTPUT_DIR,
            'upload_directory': self.config.UPLOAD_DIR,
            'max_file_size_mb': self.config.MAX_FILE_SIZE_MB,
            'max_pdf_pages': self.config.MAX_PDF_PAGES
        }