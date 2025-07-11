import fitz  # PyMuPDF
import asyncio
from typing import Tuple, List, Optional, Dict, Any
from pathlib import Path
import logging
from ..agents.models import PDFExtractionResult
from ..config.settings import settings

logger = logging.getLogger(__name__)


class PDFExtractor:
    """
    PDF text extraction using PyMuPDF with detection of text vs scanned content.
    """
    
    def __init__(self):
        self.min_chars_per_page = 100  # Threshold for text-based PDF detection
    
    async def extract_text_from_pdf(
        self, 
        pdf_path: str, 
        max_pages: Optional[int] = None
    ) -> PDFExtractionResult:
        """
        Extract text from PDF with detection of text vs scanned content.
        
        Args:
            pdf_path: Path to the PDF file
            max_pages: Maximum number of pages to process (None for all)
            
        Returns:
            PDFExtractionResult with extracted text and metadata
            
        Raises:
            FileNotFoundError: If PDF file doesn't exist
            ValueError: If PDF is corrupted or invalid
        """
        pdf_path = Path(pdf_path)
        
        # PATTERN: Always validate input first
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        try:
            # CRITICAL: PyMuPDF requires proper resource management
            with fitz.open(str(pdf_path)) as doc:
                total_pages = len(doc)
                process_pages = min(max_pages or total_pages, total_pages)
                
                page_texts = []
                total_char_count = 0
                
                for page_num in range(process_pages):
                    page = doc[page_num]
                    page_text = page.get_text()
                    
                    # GOTCHA: Empty text doesn't mean scanned - check character density
                    char_count = len(page_text.strip())
                    total_char_count += char_count
                    
                    page_info = {
                        "page": page_num + 1,
                        "text": page_text,
                        "char_count": char_count,
                        "bbox": page.rect,  # Page bounding box
                        "rotation": page.rotation
                    }
                    page_texts.append(page_info)
                
                # PATTERN: Heuristic for text vs scanned detection
                avg_chars_per_page = total_char_count / process_pages if process_pages > 0 else 0
                is_text_based = avg_chars_per_page > self.min_chars_per_page
                
                # Combine all text
                combined_text = "\n".join([p["text"] for p in page_texts])
                
                metadata = {
                    "total_pages": total_pages,
                    "processed_pages": process_pages,
                    "total_characters": total_char_count,
                    "avg_chars_per_page": avg_chars_per_page,
                    "is_text_based": is_text_based,
                    "file_size": pdf_path.stat().st_size,
                    "filename": pdf_path.name
                }
                
                logger.info(
                    f"Extracted text from {pdf_path.name}: "
                    f"{process_pages} pages, {total_char_count} characters, "
                    f"text-based: {is_text_based}"
                )
                
                return PDFExtractionResult(
                    text=combined_text,
                    is_text_based=is_text_based,
                    metadata=metadata,
                    page_texts=page_texts
                )
                
        except Exception as e:
            logger.error(f"Error extracting text from PDF {pdf_path}: {str(e)}")
            raise ValueError(f"Failed to extract text from PDF: {str(e)}")
    
    async def extract(
        self, 
        document_id: str, 
        max_pages: Optional[int] = None
    ) -> Tuple[str, bool, Dict[str, Any]]:
        """
        Extract text from document by ID.
        
        Args:
            document_id: Document identifier (filename)
            max_pages: Maximum pages to process
            
        Returns:
            Tuple of (text, is_text_based, metadata)
        """
        # Construct full path
        pdf_path = Path(settings.pdf_storage_dir) / document_id
        
        result = await self.extract_text_from_pdf(str(pdf_path), max_pages)
        
        return result.text, result.is_text_based, result.metadata
    
    def get_page_text(self, pdf_path: str, page_number: int) -> str:
        """
        Get text from a specific page (1-indexed).
        
        Args:
            pdf_path: Path to PDF file
            page_number: Page number (1-indexed)
            
        Returns:
            Text content of the page
        """
        try:
            with fitz.open(pdf_path) as doc:
                if page_number < 1 or page_number > len(doc):
                    raise ValueError(f"Page number {page_number} out of range")
                
                page = doc[page_number - 1]  # Convert to 0-indexed
                return page.get_text()
                
        except Exception as e:
            logger.error(f"Error getting page {page_number} from PDF {pdf_path}: {str(e)}")
            raise ValueError(f"Failed to get page text: {str(e)}")
    
    def get_text_with_coordinates(self, pdf_path: str, page_number: int) -> List[Dict]:
        """
        Get text with coordinate information for highlighting.
        
        Args:
            pdf_path: Path to PDF file
            page_number: Page number (1-indexed)
            
        Returns:
            List of text blocks with coordinates
        """
        try:
            with fitz.open(pdf_path) as doc:
                if page_number < 1 or page_number > len(doc):
                    raise ValueError(f"Page number {page_number} out of range")
                
                page = doc[page_number - 1]
                blocks = page.get_text("dict")["blocks"]
                
                text_blocks = []
                for block in blocks:
                    if "lines" in block:  # Text block
                        for line in block["lines"]:
                            for span in line["spans"]:
                                text_blocks.append({
                                    "text": span["text"],
                                    "bbox": span["bbox"],
                                    "font": span["font"],
                                    "size": span["size"]
                                })
                
                return text_blocks
                
        except Exception as e:
            logger.error(f"Error getting text coordinates from PDF {pdf_path}: {str(e)}")
            raise ValueError(f"Failed to get text coordinates: {str(e)}")
