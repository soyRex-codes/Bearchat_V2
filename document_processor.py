"""
Document Processor for BearChat
================================
Unified pipeline for processing PDFs and images:
1. Images → Convert to PDF
2. PDFs → Extract text
3. Fallback to OCR for scanned documents

Handles: Transcripts, course catalogs, syllabi, degree audits
"""

import os
import io
import tempfile
from typing import Tuple, Optional
from pathlib import Path

# PDF processing
import PyPDF2
from PIL import Image
import pdf2image
import pytesseract

# File type detection
import mimetypes


class DocumentProcessor:
    """Process PDFs and images to extract text for Llama model."""
    
    SUPPORTED_IMAGE_FORMATS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif'}
    SUPPORTED_PDF_FORMATS = {'.pdf'}
    MAX_FILE_SIZE_MB = 50  # Max file size limit
    
    def __init__(self, use_ocr_fallback: bool = True):
        """
        Initialize document processor.
        
        Args:
            use_ocr_fallback: If True, use OCR when PDF text extraction fails
        """
        self.use_ocr_fallback = use_ocr_fallback
        self._verify_dependencies()
    
    def _verify_dependencies(self):
        """Verify that required dependencies are available."""
        try:
            # Test pytesseract
            pytesseract.get_tesseract_version()
        except Exception as e:
            print(f"⚠️  Warning: Tesseract OCR not found. OCR fallback disabled.")
            print(f"   Install with: brew install tesseract (macOS)")
            self.use_ocr_fallback = False
    
    def is_supported_file(self, file_path: str) -> bool:
        """Check if file type is supported."""
        ext = Path(file_path).suffix.lower()
        return ext in (self.SUPPORTED_IMAGE_FORMATS | self.SUPPORTED_PDF_FORMATS)
    
    def get_file_type(self, file_path: str) -> str:
        """Determine file type (image or pdf)."""
        ext = Path(file_path).suffix.lower()
        
        if ext in self.SUPPORTED_IMAGE_FORMATS:
            return 'image'
        elif ext in self.SUPPORTED_PDF_FORMATS:
            return 'pdf'
        else:
            # Fallback to MIME type detection
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type and mime_type.startswith('image/'):
                return 'image'
            elif mime_type == 'application/pdf':
                return 'pdf'
            else:
                return 'unknown'
    
    def check_file_size(self, file_path: str) -> Tuple[bool, float]:
        """
        Check if file size is within limits.
        
        Returns:
            (is_valid, size_in_mb)
        """
        size_bytes = os.path.getsize(file_path)
        size_mb = size_bytes / (1024 * 1024)
        is_valid = size_mb <= self.MAX_FILE_SIZE_MB
        return is_valid, size_mb
    
    def image_to_pdf(self, image_path: str, output_path: Optional[str] = None) -> str:
        """
        Convert image to PDF.
        
        Args:
            image_path: Path to input image
            output_path: Path for output PDF (optional, uses temp file if None)
        
        Returns:
            Path to generated PDF
        """
        try:
            # Open and convert image
            image = Image.open(image_path)
            
            # Convert to RGB if necessary (PDF requires RGB)
            if image.mode in ('RGBA', 'LA', 'P'):
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                rgb_image.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = rgb_image
            elif image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Determine output path
            if output_path is None:
                # Create temp file
                temp_fd, output_path = tempfile.mkstemp(suffix='.pdf')
                os.close(temp_fd)
            
            # Save as PDF
            image.save(output_path, 'PDF', resolution=100.0)
            
            return output_path
            
        except Exception as e:
            raise Exception(f"Failed to convert image to PDF: {str(e)}")
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extract text from PDF using PyPDF2.
        
        Args:
            pdf_path: Path to PDF file
        
        Returns:
            Extracted text
        """
        try:
            text_parts = []
            
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                num_pages = len(pdf_reader.pages)
                
                for page_num in range(num_pages):
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()
                    
                    if text and text.strip():
                        # Add page separator for context
                        text_parts.append(f"\n--- Page {page_num + 1} ---\n{text}")
            
            extracted_text = '\n'.join(text_parts)
            return extracted_text.strip()
            
        except Exception as e:
            raise Exception(f"Failed to extract text from PDF: {str(e)}")
    
    def extract_text_with_ocr(self, pdf_path: str) -> str:
        """
        Extract text from PDF using OCR (for scanned documents).
        
        Args:
            pdf_path: Path to PDF file
        
        Returns:
            Extracted text via OCR
        """
        if not self.use_ocr_fallback:
            return ""
        
        try:
            # Convert PDF pages to images
            images = pdf2image.convert_from_path(pdf_path, dpi=300)
            
            text_parts = []
            for i, image in enumerate(images):
                # Run OCR on each page
                text = pytesseract.image_to_string(image)
                
                if text and text.strip():
                    text_parts.append(f"\n--- Page {i + 1} (OCR) ---\n{text}")
            
            extracted_text = '\n'.join(text_parts)
            return extracted_text.strip()
            
        except Exception as e:
            raise Exception(f"Failed to extract text via OCR: {str(e)}")
    
    def process_document(self, file_path: str, cleanup_temp: bool = True) -> Tuple[str, dict]:
        """
        Main processing pipeline: handle any supported document.
        
        Args:
            file_path: Path to document (PDF or image)
            cleanup_temp: Whether to delete temporary files
        
        Returns:
            (extracted_text, metadata)
        """
        metadata = {
            'file_path': file_path,
            'file_name': Path(file_path).name,
            'file_type': None,
            'processing_method': None,
            'file_size_mb': 0,
            'num_characters': 0,
            'success': False,
            'error': None
        }
        
        temp_pdf_path = None
        
        try:
            # 1. Verify file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # 2. Check file size
            is_valid_size, size_mb = self.check_file_size(file_path)
            metadata['file_size_mb'] = round(size_mb, 2)
            
            if not is_valid_size:
                raise ValueError(f"File too large: {size_mb:.1f}MB (max: {self.MAX_FILE_SIZE_MB}MB)")
            
            # 3. Detect file type
            file_type = self.get_file_type(file_path)
            metadata['file_type'] = file_type
            
            if file_type == 'unknown':
                raise ValueError(f"Unsupported file type: {Path(file_path).suffix}")
            
            # 4. Convert image to PDF if needed
            if file_type == 'image':
                print(f"📄 Converting image to PDF...")
                temp_pdf_path = self.image_to_pdf(file_path)
                pdf_path = temp_pdf_path
                metadata['processing_method'] = 'image_to_pdf'
            else:
                pdf_path = file_path
            
            # 5. Extract text from PDF
            print(f"📖 Extracting text from PDF...")
            text = self.extract_text_from_pdf(pdf_path)
            
            # 6. If extraction failed or produced minimal text, try OCR
            if not text or len(text.strip()) < 50:
                print(f"⚠️  Low/no text extracted. Trying OCR...")
                ocr_text = self.extract_text_with_ocr(pdf_path)
                
                if ocr_text and len(ocr_text) > len(text):
                    text = ocr_text
                    metadata['processing_method'] = 'ocr'
                else:
                    metadata['processing_method'] = 'pdf_extraction'
            else:
                metadata['processing_method'] = 'pdf_extraction'
            
            # 7. Validate we got meaningful text
            if not text or len(text.strip()) < 10:
                raise ValueError("No text could be extracted from document")
            
            # 8. Update metadata
            metadata['num_characters'] = len(text)
            metadata['success'] = True
            
            print(f"✅ Extracted {len(text)} characters using {metadata['processing_method']}")
            
            return text, metadata
            
        except Exception as e:
            metadata['error'] = str(e)
            metadata['success'] = False
            print(f"❌ Error processing document: {e}")
            raise
            
        finally:
            # Cleanup temporary PDF if created
            if cleanup_temp and temp_pdf_path and os.path.exists(temp_pdf_path):
                try:
                    os.remove(temp_pdf_path)
                except:
                    pass
    
    def chunk_text_for_llama(self, text: str, max_tokens: int = 3000) -> list:
        """
        Split text into chunks that fit in Llama's context window.
        
        Args:
            text: Full extracted text
            max_tokens: Maximum tokens per chunk (留 some room for prompts)
        
        Returns:
            List of text chunks
        """
        # Simple character-based chunking (rough approximation: ~4 chars per token)
        max_chars = max_tokens * 4
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        # Split by paragraphs
        paragraphs = text.split('\n\n')
        
        for para in paragraphs:
            para_length = len(para)
            
            if current_length + para_length <= max_chars:
                current_chunk.append(para)
                current_length += para_length
            else:
                # Save current chunk and start new one
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_length = para_length
        
        # Add final chunk
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks


# Convenience functions for quick usage
def process_pdf(pdf_path: str) -> str:
    """Quick function to process a PDF file."""
    processor = DocumentProcessor()
    text, _ = processor.process_document(pdf_path)
    return text


def process_image(image_path: str) -> str:
    """Quick function to process an image file."""
    processor = DocumentProcessor()
    text, _ = processor.process_document(image_path)
    return text


def process_any_document(file_path: str) -> Tuple[str, dict]:
    """Quick function to process any supported document."""
    processor = DocumentProcessor()
    return processor.process_document(file_path)


if __name__ == "__main__":
    # Simple CLI for testing
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python document_processor.py <file_path>")
        print("Example: python document_processor.py sample_transcript.pdf")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    print(f"\n{'='*80}")
    print("DOCUMENT PROCESSOR TEST")
    print(f"{'='*80}\n")
    
    processor = DocumentProcessor()
    
    try:
        text, metadata = processor.process_document(file_path)
        
        print(f"\n{'='*80}")
        print("EXTRACTION RESULTS")
        print(f"{'='*80}")
        print(f"File: {metadata['file_name']}")
        print(f"Type: {metadata['file_type']}")
        print(f"Size: {metadata['file_size_mb']} MB")
        print(f"Method: {metadata['processing_method']}")
        print(f"Characters: {metadata['num_characters']:,}")
        print(f"\n--- Extracted Text (first 500 chars) ---")
        print(text[:500])
        print("...")
        
    except Exception as e:
        print(f"\n❌ Processing failed: {e}")
        sys.exit(1)
