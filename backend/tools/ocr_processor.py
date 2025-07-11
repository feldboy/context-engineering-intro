import pytesseract
from PIL import Image
import fitz  # PyMuPDF for PDF to image conversion
import asyncio
from typing import List, Dict, Optional
from pathlib import Path
import logging
import tempfile
import os
from ..agents.models import OCRResult
from ..config.settings import settings

logger = logging.getLogger(__name__)


class OCRProcessor:
    """
    OCR processing for scanned PDFs using pytesseract.
    """
    
    def __init__(self):
        self.confidence_threshold = settings.ocr_confidence_threshold
        self.tesseract_config = settings.tesseract_config
        
        # Verify tesseract is installed
        try:
            pytesseract.get_tesseract_version()
        except Exception as e:
            logger.error(f"Tesseract not found: {str(e)}")
            raise RuntimeError("Tesseract OCR not installed or not found in PATH")
    
    async def process_pdf(self, pdf_path: str) -> OCRResult:
        """
        Process a PDF file using OCR.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            OCRResult with extracted text and confidence scores
        """
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        try:
            # Convert PDF pages to images and process with OCR
            with fitz.open(str(pdf_path)) as doc:
                page_texts = []
                confidence_scores = []
                page_confidences = {}
                processing_errors = []
                
                for page_num in range(len(doc)):
                    try:
                        page = doc[page_num]
                        
                        # Convert page to image
                        # PATTERN: Use high DPI for better OCR accuracy
                        mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
                        pix = page.get_pixmap(matrix=mat)
                        
                        # Convert to PIL Image
                        img_data = pix.tobytes("ppm")
                        with tempfile.NamedTemporaryFile(suffix='.ppm', delete=False) as temp_file:
                            temp_file.write(img_data)
                            temp_path = temp_file.name
                        
                        try:
                            # Preprocess image for better OCR
                            img = Image.open(temp_path)
                            img = self._preprocess_image(img)
                            
                            # Perform OCR with confidence data
                            ocr_data = pytesseract.image_to_data(
                                img, 
                                config=self.tesseract_config,
                                output_type=pytesseract.Output.DICT
                            )
                            
                            # Extract text and confidence
                            page_text, page_confidence = self._extract_text_and_confidence(ocr_data)
                            
                            page_texts.append(page_text)
                            confidence_scores.append(page_confidence)
                            page_confidences[page_num + 1] = page_confidence
                            
                            logger.info(f"OCR processed page {page_num + 1}: confidence {page_confidence:.2f}")
                            
                        finally:
                            # Clean up temporary file
                            os.unlink(temp_path)
                            
                    except Exception as e:
                        error_msg = f"Error processing page {page_num + 1}: {str(e)}"
                        logger.error(error_msg)
                        processing_errors.append(error_msg)
                        page_texts.append("")
                        confidence_scores.append(0.0)
                        page_confidences[page_num + 1] = 0.0
                
                # Combine all text
                combined_text = "\n".join(page_texts)
                
                logger.info(
                    f"OCR completed for {pdf_path.name}: "
                    f"{len(page_texts)} pages processed, "
                    f"avg confidence: {sum(confidence_scores) / len(confidence_scores):.2f}"
                )
                
                return OCRResult(
                    text=combined_text,
                    confidence_scores=confidence_scores,
                    page_confidences=page_confidences,
                    processing_errors=processing_errors
                )
                
        except Exception as e:
            logger.error(f"Error during OCR processing of {pdf_path}: {str(e)}")
            raise ValueError(f"OCR processing failed: {str(e)}")
    
    def _preprocess_image(self, img: Image.Image) -> Image.Image:
        """
        Preprocess image for better OCR accuracy.
        
        Args:
            img: PIL Image object
            
        Returns:
            Preprocessed PIL Image
        """
        # Convert to grayscale
        img = img.convert('L')
        
        # Enhance contrast (simple approach)
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)
        
        # Optional: Apply threshold to create binary image
        # This can help with low-quality scans
        import numpy as np
        img_array = np.array(img)
        threshold = 128
        img_array = np.where(img_array > threshold, 255, 0).astype(np.uint8)
        img = Image.fromarray(img_array)
        
        return img
    
    def _extract_text_and_confidence(self, ocr_data: Dict) -> tuple[str, float]:
        """
        Extract text and calculate confidence from OCR data.
        
        Args:
            ocr_data: OCR data from pytesseract
            
        Returns:
            Tuple of (text, confidence_score)
        """
        words = []
        confidences = []
        
        for i, conf in enumerate(ocr_data['conf']):
            if int(conf) > 0:  # Only include words with confidence > 0
                text = ocr_data['text'][i].strip()
                if text:  # Only include non-empty text
                    words.append(text)
                    confidences.append(int(conf))
        
        # Combine words into text
        page_text = ' '.join(words)
        
        # Calculate average confidence
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return page_text, avg_confidence / 100.0  # Convert to 0-1 scale
    
    async def process(self, document_id: str) -> str:
        """
        Process document by ID using OCR.
        
        Args:
            document_id: Document identifier (filename)
            
        Returns:
            Extracted text
        """
        pdf_path = Path(settings.pdf_storage_dir) / document_id
        result = await self.process_pdf(str(pdf_path))
        return result.text
    
    def get_page_confidence(self, pdf_path: str, page_number: int) -> float:
        """
        Get OCR confidence for a specific page.
        
        Args:
            pdf_path: Path to PDF file
            page_number: Page number (1-indexed)
            
        Returns:
            Confidence score for the page
        """
        try:
            # This is a simplified version - in practice you'd cache results
            # For now, return a default confidence
            return 0.85  # Placeholder
            
        except Exception as e:
            logger.error(f"Error getting page confidence: {str(e)}")
            return 0.0
