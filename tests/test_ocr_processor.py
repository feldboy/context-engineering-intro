"""
Tests for OCR processor functionality
"""
import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock
from PIL import Image
import numpy as np

# Set test environment
os.environ['ENVIRONMENT'] = 'test'

from backend.tools.ocr_processor import OCRProcessor
from backend.agents.models import ProcessingStatus, ExtractionResult


class TestOCRProcessor:
    """Test suite for OCR processor"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.processor = OCRProcessor()
        
    def test_init_default_config(self):
        """Test OCR processor initialization with default config"""
        processor = OCRProcessor()
        assert processor.config is not None
        assert processor.config.get('oem') == 3
        assert processor.config.get('psm') == 6
        
    def test_init_custom_config(self):
        """Test OCR processor initialization with custom config"""
        custom_config = {'oem': 1, 'psm': 8}
        processor = OCRProcessor(custom_config)
        assert processor.config['oem'] == 1
        assert processor.config['psm'] == 8
        
    @patch('backend.tools.ocr_processor.pytesseract.image_to_string')
    def test_extract_text_from_image_success(self, mock_tesseract):
        """Test successful text extraction from image"""
        # Create a test image
        test_image = Image.new('RGB', (100, 100), color='white')
        
        # Mock tesseract response
        mock_tesseract.return_value = "This is extracted text"
        
        result = self.processor.extract_text_from_image(test_image)
        
        assert result == "This is extracted text"
        mock_tesseract.assert_called_once()
        
    @patch('backend.tools.ocr_processor.pytesseract.image_to_string')
    def test_extract_text_from_image_failure(self, mock_tesseract):
        """Test OCR extraction failure handling"""
        test_image = Image.new('RGB', (100, 100), color='white')
        
        # Mock tesseract failure
        mock_tesseract.side_effect = Exception("OCR failed")
        
        result = self.processor.extract_text_from_image(test_image)
        
        assert result == ""
        
    @patch('backend.tools.ocr_processor.pytesseract.image_to_data')
    def test_get_confidence_scores(self, mock_image_to_data):
        """Test confidence score extraction"""
        test_image = Image.new('RGB', (100, 100), color='white')
        
        # Mock tesseract data response
        mock_image_to_data.return_value = {
            'text': ['This', 'is', 'test', 'text'],
            'conf': [90, 85, 92, 88],
            'word_num': [1, 2, 3, 4]
        }
        
        confidence = self.processor.get_confidence_scores(test_image)
        
        assert confidence == pytest.approx(88.75, rel=1e-2)  # Average confidence
        
    def test_preprocess_image_enhance(self):
        """Test image preprocessing for OCR enhancement"""
        # Create a test image
        test_image = Image.new('RGB', (200, 200), color='gray')
        
        processed = self.processor.preprocess_image(test_image)
        
        assert processed is not None
        assert processed.mode == 'L'  # Should be grayscale
        assert processed.size == (200, 200)
        
    def test_preprocess_image_resize(self):
        """Test image resizing during preprocessing"""
        # Create a small test image
        test_image = Image.new('RGB', (50, 50), color='white')
        
        processed = self.processor.preprocess_image(test_image)
        
        # Should be resized to minimum dimensions
        assert processed.size[0] >= 200 or processed.size[1] >= 200
        
    @patch('backend.tools.ocr_processor.fitz.open')
    def test_process_pdf_pages(self, mock_fitz_open):
        """Test PDF page processing for OCR"""
        # Mock PDF document
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_pix = MagicMock()
        
        mock_doc.__len__.return_value = 1
        mock_doc.__getitem__.return_value = mock_page
        mock_page.get_pixmap.return_value = mock_pix
        mock_pix.pil_tobytes.return_value = b"fake_image_data"
        
        mock_fitz_open.return_value = mock_doc
        
        with patch('PIL.Image.open') as mock_image_open:
            mock_image = MagicMock()
            mock_image_open.return_value = mock_image
            
            with patch.object(self.processor, 'extract_text_from_image') as mock_extract:
                mock_extract.return_value = "Extracted text from page"
                
                result = self.processor.process_pdf_pages("fake_path.pdf")
                
                assert len(result) == 1
                assert result[0]["text"] == "Extracted text from page"
                assert result[0]["page_number"] == 1
                
    def test_merge_extraction_results(self):
        """Test merging of extraction results from multiple pages"""
        page_results = [
            {"text": "Page 1 text", "page_number": 1, "confidence": 90},
            {"text": "Page 2 text", "page_number": 2, "confidence": 85}
        ]
        
        merged = self.processor.merge_extraction_results(page_results)
        
        assert "Page 1 text" in merged.text
        assert "Page 2 text" in merged.text
        assert merged.confidence == pytest.approx(87.5, rel=1e-2)
        assert merged.metadata["total_pages"] == 2
        
    def test_process_document_success(self):
        """Test complete document processing workflow"""
        with patch.object(self.processor, 'process_pdf_pages') as mock_process:
            mock_process.return_value = [
                {"text": "Test document content", "page_number": 1, "confidence": 88}
            ]
            
            result = self.processor.process_document("test.pdf")
            
            assert isinstance(result, ExtractionResult)
            assert result.text == "Test document content"
            assert result.status == ProcessingStatus.COMPLETED
            assert result.confidence == 88
            
    def test_process_document_failure(self):
        """Test document processing failure handling"""
        with patch.object(self.processor, 'process_pdf_pages') as mock_process:
            mock_process.side_effect = Exception("Processing failed")
            
            result = self.processor.process_document("test.pdf")
            
            assert isinstance(result, ExtractionResult)
            assert result.status == ProcessingStatus.FAILED
            assert "Processing failed" in result.error_message
            
    def test_validate_document_type(self):
        """Test document type validation"""
        assert self.processor.validate_document_type("test.pdf") == True
        assert self.processor.validate_document_type("test.jpg") == True
        assert self.processor.validate_document_type("test.png") == True
        assert self.processor.validate_document_type("test.txt") == False
        
    def test_cleanup_temp_files(self):
        """Test temporary file cleanup"""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
            
        assert os.path.exists(tmp_path)
        
        # Test cleanup
        self.processor.cleanup_temp_files([tmp_path])
        
        # File should be removed
        assert not os.path.exists(tmp_path)
        
    def test_get_supported_formats(self):
        """Test getting supported file formats"""
        formats = self.processor.get_supported_formats()
        
        assert isinstance(formats, list)
        assert '.pdf' in formats
        assert '.jpg' in formats
        assert '.png' in formats
        
    def test_estimate_processing_time(self):
        """Test processing time estimation"""
        # Mock file size
        with patch('os.path.getsize') as mock_getsize:
            mock_getsize.return_value = 1024 * 1024  # 1MB
            
            time_estimate = self.processor.estimate_processing_time("test.pdf")
            
            assert isinstance(time_estimate, float)
            assert time_estimate > 0
