import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from backend.tools.pdf_extractor import PDFExtractor
from backend.agents.models import PDFExtractionResult


class TestPDFExtractor:
    """Test PDF text extraction functionality."""
    
    @pytest.fixture
    def pdf_extractor(self):
        """Create PDF extractor instance."""
        return PDFExtractor()
    
    @pytest.fixture
    def mock_pdf_path(self, tmp_path):
        """Create a mock PDF file path."""
        pdf_file = tmp_path / "test_document.pdf"
        pdf_file.write_text("mock pdf content")
        return str(pdf_file)
    
    @pytest.mark.asyncio
    async def test_extract_text_from_text_based_pdf(self, pdf_extractor):
        """Test direct PDF text extraction."""
        # Mock the fitz (PyMuPDF) module
        with patch('backend.tools.pdf_extractor.fitz') as mock_fitz:
            # Setup mock document
            mock_doc = MagicMock()
            mock_doc.__len__.return_value = 2
            mock_doc.__enter__.return_value = mock_doc
            mock_doc.__exit__.return_value = None
            
            # Setup mock pages with sufficient text for text-based detection
            mock_page1 = MagicMock()
            mock_page1.get_text.return_value = "Sample legal document text with case number CIV-2024-1138 and additional content to make it longer than 100 characters per page for text-based detection"
            mock_page1.rect = MagicMock()
            mock_page1.rotation = 0
            
            mock_page2 = MagicMock()
            mock_page2.get_text.return_value = "Additional content on page 2 with more text content to ensure we pass the minimum character threshold for text-based PDF detection"
            mock_page2.rect = MagicMock()
            mock_page2.rotation = 0
            
            mock_doc.__getitem__.side_effect = [mock_page1, mock_page2]
            mock_fitz.open.return_value = mock_doc
            
            # Mock Path.exists
            with patch('pathlib.Path.exists', return_value=True):
                with patch('pathlib.Path.stat') as mock_stat:
                    mock_stat.return_value.st_size = 1024
                    
                    result = await pdf_extractor.extract_text_from_pdf("test.pdf")
                    
                    assert isinstance(result, PDFExtractionResult)
                    assert result.is_text_based is True
                    assert "CIV-2024-1138" in result.text
                    assert result.metadata["total_pages"] == 2
                    assert result.metadata["processed_pages"] == 2
                    assert len(result.page_texts) == 2
    
    @pytest.mark.asyncio
    async def test_extract_text_from_scanned_pdf(self, pdf_extractor):
        """Test detection of scanned PDFs."""
        with patch('backend.tools.pdf_extractor.fitz') as mock_fitz:
            # Setup mock document with very little text (scanned)
            mock_doc = MagicMock()
            mock_doc.__len__.return_value = 1
            mock_doc.__enter__.return_value = mock_doc
            mock_doc.__exit__.return_value = None
            
            mock_page = MagicMock()
            mock_page.get_text.return_value = "  \n  "  # Minimal text
            mock_page.rect = MagicMock()
            mock_page.rotation = 0
            
            mock_doc.__getitem__.return_value = mock_page
            mock_fitz.open.return_value = mock_doc
            
            with patch('pathlib.Path.exists', return_value=True):
                with patch('pathlib.Path.stat') as mock_stat:
                    mock_stat.return_value.st_size = 1024
                    
                    result = await pdf_extractor.extract_text_from_pdf("test.pdf")
                    
                    assert result.is_text_based is False
                    assert result.metadata["avg_chars_per_page"] < 100
    
    @pytest.mark.asyncio
    async def test_extract_with_max_pages(self, pdf_extractor):
        """Test extraction with page limit."""
        with patch('backend.tools.pdf_extractor.fitz') as mock_fitz:
            mock_doc = MagicMock()
            mock_doc.__len__.return_value = 10  # 10 pages total
            mock_doc.__enter__.return_value = mock_doc
            mock_doc.__exit__.return_value = None
            
            mock_page = MagicMock()
            mock_page.get_text.return_value = "Page content with sufficient text"
            mock_page.rect = MagicMock()
            mock_page.rotation = 0
            
            mock_doc.__getitem__.return_value = mock_page
            mock_fitz.open.return_value = mock_doc
            
            with patch('pathlib.Path.exists', return_value=True):
                with patch('pathlib.Path.stat') as mock_stat:
                    mock_stat.return_value.st_size = 1024
                    
                    result = await pdf_extractor.extract_text_from_pdf("test.pdf", max_pages=3)
                    
                    assert result.metadata["total_pages"] == 10
                    assert result.metadata["processed_pages"] == 3
                    assert len(result.page_texts) == 3
    
    @pytest.mark.asyncio
    async def test_extract_file_not_found(self, pdf_extractor):
        """Test handling of missing PDF file."""
        with pytest.raises(FileNotFoundError, match="PDF not found"):
            await pdf_extractor.extract_text_from_pdf("nonexistent.pdf")
    
    @pytest.mark.asyncio
    async def test_extract_corrupted_pdf(self, pdf_extractor):
        """Test handling of corrupted PDF."""
        with patch('backend.tools.pdf_extractor.fitz') as mock_fitz:
            mock_fitz.open.side_effect = Exception("Corrupted PDF")
            
            with patch('pathlib.Path.exists', return_value=True):
                with pytest.raises(ValueError, match="Failed to extract text from PDF"):
                    await pdf_extractor.extract_text_from_pdf("corrupted.pdf")
    
    def test_get_page_text(self, pdf_extractor):
        """Test getting text from specific page."""
        with patch('backend.tools.pdf_extractor.fitz') as mock_fitz:
            mock_doc = MagicMock()
            mock_doc.__len__.return_value = 2
            mock_doc.__enter__.return_value = mock_doc
            mock_doc.__exit__.return_value = None
            
            mock_page = MagicMock()
            mock_page.get_text.return_value = "Page 1 content"
            mock_doc.__getitem__.return_value = mock_page
            mock_fitz.open.return_value = mock_doc
            
            result = pdf_extractor.get_page_text("test.pdf", 1)
            
            assert result == "Page 1 content"
            mock_doc.__getitem__.assert_called_with(0)  # 1-indexed -> 0-indexed
    
    def test_get_page_text_out_of_range(self, pdf_extractor):
        """Test getting text from page out of range."""
        with patch('backend.tools.pdf_extractor.fitz') as mock_fitz:
            mock_doc = MagicMock()
            mock_doc.__len__.return_value = 2
            mock_doc.__enter__.return_value = mock_doc
            mock_doc.__exit__.return_value = None
            mock_fitz.open.return_value = mock_doc
            
            with pytest.raises(ValueError, match="Page number .* out of range"):
                pdf_extractor.get_page_text("test.pdf", 5)
    
    def test_get_text_with_coordinates(self, pdf_extractor):
        """Test getting text with coordinate information."""
        with patch('backend.tools.pdf_extractor.fitz') as mock_fitz:
            mock_doc = MagicMock()
            mock_doc.__len__.return_value = 1
            mock_doc.__enter__.return_value = mock_doc
            mock_doc.__exit__.return_value = None
            
            mock_page = MagicMock()
            mock_page.get_text.return_value = {
                "blocks": [
                    {
                        "lines": [
                            {
                                "spans": [
                                    {
                                        "text": "Sample text",
                                        "bbox": [10, 20, 100, 30],
                                        "font": "Arial",
                                        "size": 12
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
            mock_doc.__getitem__.return_value = mock_page
            mock_fitz.open.return_value = mock_doc
            
            result = pdf_extractor.get_text_with_coordinates("test.pdf", 1)
            
            assert len(result) == 1
            assert result[0]["text"] == "Sample text"
            assert result[0]["bbox"] == [10, 20, 100, 30]
            assert result[0]["font"] == "Arial"
            assert result[0]["size"] == 12
    
    @pytest.mark.asyncio
    async def test_extract_by_document_id(self, pdf_extractor):
        """Test extraction by document ID."""
        with patch.object(pdf_extractor, 'extract_text_from_pdf') as mock_extract:
            mock_result = PDFExtractionResult(
                text="Test content",
                is_text_based=True,
                metadata={"total_pages": 1},
                page_texts=[]
            )
            mock_extract.return_value = mock_result
            
            text, is_text_based, metadata = await pdf_extractor.extract("test_doc.pdf")
            
            assert text == "Test content"
            assert is_text_based is True
            assert metadata["total_pages"] == 1
            
            # Verify correct path construction
            mock_extract.assert_called_once()
            call_args = mock_extract.call_args[0]
            assert call_args[0].endswith("test_doc.pdf")
