import pytest
import asyncio
import os
from unittest.mock import Mock, patch, AsyncMock

# Set test environment before importing the agent
os.environ['ENVIRONMENT'] = 'test'
os.environ['OPENAI_API_KEY'] = 'test_openai_key'
os.environ['ANTHROPIC_API_KEY'] = 'test_anthropic_key'
os.environ['DEEPSEEK_API_KEY'] = 'test_deepseek_key'

from backend.agents.document_analysis_agent import DocumentAnalysisAgent
from backend.agents.models import (
    DocumentAnalysisRequest, 
    DocumentAnalysisResponse, 
    ExtractionSchema,
    ProcessingStatus,
    ExtractionField,
    DocumentType,
    DocumentMetadata
)


class TestDocumentAnalysisAgent:
    """Test the main document analysis agent."""
    
    @pytest.fixture
    def agent(self):
        """Create document analysis agent instance."""
        return DocumentAnalysisAgent()
    
    @pytest.fixture
    def sample_request(self):
        """Create a sample analysis request."""
        return DocumentAnalysisRequest(
            document_id="test_document.pdf",
            extraction_schema=ExtractionSchema(
                schema_name="civil_complaint",
                fields={
                    "case_number": None,
                    "plaintiff_name": None,
                    "defendant_names": None,
                    "filing_date": None
                }
            ),
            process_full_document=False,
            force_reprocess=False
        )
    
    @pytest.mark.asyncio
    async def test_analyze_document_success(self, agent, sample_request):
        """Test successful document analysis."""
        # Mock the extraction tools
        with patch.object(agent.pdf_extractor, 'extract') as mock_pdf_extract:
            with patch.object(agent.llm_extractor, 'extract') as mock_llm_extract:
                with patch.object(agent.text_chunker, 'chunk_text') as mock_chunk:
                    # Setup mock responses
                    mock_pdf_extract.return_value = (
                        "SUPERIOR COURT OF CALIFORNIA\nCase Number: CIV-2024-1138\nJane Doe, Plaintiff\nv.\nAcme Corp, Defendant",
                        True,  # is_text_based
                        {
                            "filename": "test_document.pdf",
                            "file_size": 1024,
                            "total_pages": 1,
                            "processing_method": "direct_text",
                            "total_characters": 100,
                            "avg_chars_per_page": 100
                        }
                    )
                    
                    # Mock single chunk (small document)
                    mock_chunk_obj = Mock()
                    mock_chunk_obj.text = "SUPERIOR COURT OF CALIFORNIA\nCase Number: CIV-2024-1138\nJane Doe, Plaintiff\nv.\nAcme Corp, Defendant"
                    mock_chunk.return_value = [mock_chunk_obj]
                    
                    # Mock LLM extraction
                    mock_llm_extract.return_value = {
                        "case_number": ExtractionField(
                            value="CIV-2024-1138",
                            source_text="Case Number: CIV-2024-1138",
                            confidence_score=0.99
                        ),
                        "plaintiff_name": ExtractionField(
                            value="Jane Doe",
                            source_text="Jane Doe, Plaintiff",
                            confidence_score=0.95
                        ),
                        "defendant_names": ExtractionField(
                            value=["Acme Corp"],
                            source_text="Acme Corp, Defendant",
                            confidence_score=0.92
                        ),
                        "filing_date": ExtractionField(
                            value=None,
                            source_text=None,
                            confidence_score=0.0
                        )
                    }
                    
                    # Execute analysis
                    response = await agent.analyze_document(sample_request)
                    
                    # Verify response
                    assert isinstance(response, DocumentAnalysisResponse)
                    assert response.status == ProcessingStatus.COMPLETED
                    assert response.document_id == "test_document.pdf"
                    assert len(response.extracted_data) == 4
                    assert response.extracted_data["case_number"].value == "CIV-2024-1138"
                    assert response.extracted_data["plaintiff_name"].value == "Jane Doe"
                    assert response.extracted_data["defendant_names"].value == ["Acme Corp"]
                    assert response.extracted_data["filing_date"].value is None
                    assert response.metadata.document_type == DocumentType.COMPLAINT
    
    @pytest.mark.asyncio
    async def test_analyze_document_with_ocr(self, agent, sample_request):
        """Test document analysis with OCR fallback."""
        with patch.object(agent.pdf_extractor, 'extract') as mock_pdf_extract:
            with patch.object(agent.ocr_processor, 'process') as mock_ocr_process:
                with patch.object(agent.llm_extractor, 'extract') as mock_llm_extract:
                    with patch.object(agent.text_chunker, 'chunk_text') as mock_chunk:
                        # Setup mock responses for scanned PDF
                        mock_pdf_extract.return_value = (
                            "   ",  # Very little text (scanned)
                            False,  # is_text_based = False
                            {
                                "filename": "test_document.pdf",
                                "file_size": 1024,
                                "total_pages": 1,
                                "processing_method": "direct_text",
                                "total_characters": 3,
                                "avg_chars_per_page": 3
                            }
                        )
                        
                        # Mock OCR processing
                        mock_ocr_process.return_value = "SUPERIOR COURT OF CALIFORNIA\nCase Number: CIV-2024-1138"
                        
                        # Mock chunking
                        mock_chunk_obj = Mock()
                        mock_chunk_obj.text = "SUPERIOR COURT OF CALIFORNIA\nCase Number: CIV-2024-1138"
                        mock_chunk.return_value = [mock_chunk_obj]
                        
                        # Mock LLM extraction
                        mock_llm_extract.return_value = {
                            "case_number": ExtractionField(
                                value="CIV-2024-1138",
                                source_text="Case Number: CIV-2024-1138",
                                confidence_score=0.85
                            )
                        }
                        
                        # Execute analysis
                        response = await agent.analyze_document(sample_request)
                        
                        # Verify OCR was used
                        assert response.metadata.processing_method == "ocr"
                        assert response.extracted_data["case_number"].value == "CIV-2024-1138"
                        mock_ocr_process.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_document_multi_chunk(self, agent, sample_request):
        """Test document analysis with multiple chunks."""
        with patch.object(agent.pdf_extractor, 'extract') as mock_pdf_extract:
            with patch.object(agent.llm_extractor, 'extract') as mock_llm_extract:
                with patch.object(agent.llm_extractor, 'synthesize_chunk_results') as mock_synthesize:
                    with patch.object(agent.text_chunker, 'chunk_text') as mock_chunk:
                        # Setup mock responses
                        mock_pdf_extract.return_value = (
                            "Long document text...",
                            True,
                            {
                                "filename": "test_document.pdf",
                                "file_size": 2048,
                                "total_pages": 5,
                                "processing_method": "direct_text",
                                "total_characters": 1000,
                                "avg_chars_per_page": 200
                            }
                        )
                        
                        # Mock multiple chunks
                        chunk1 = Mock()
                        chunk1.text = "First chunk with case number CIV-2024-1138"
                        chunk2 = Mock()
                        chunk2.text = "Second chunk with plaintiff Jane Doe"
                        mock_chunk.return_value = [chunk1, chunk2]
                        
                        # Mock LLM extraction for each chunk
                        mock_llm_extract.side_effect = [
                            {
                                "case_number": ExtractionField(
                                    value="CIV-2024-1138",
                                    source_text="case number CIV-2024-1138",
                                    confidence_score=0.99
                                ),
                                "plaintiff_name": ExtractionField(
                                    value=None,
                                    source_text=None,
                                    confidence_score=0.0
                                )
                            },
                            {
                                "case_number": ExtractionField(
                                    value=None,
                                    source_text=None,
                                    confidence_score=0.0
                                ),
                                "plaintiff_name": ExtractionField(
                                    value="Jane Doe",
                                    source_text="plaintiff Jane Doe",
                                    confidence_score=0.95
                                )
                            }
                        ]
                        
                        # Mock synthesis
                        mock_synthesize.return_value = {
                            "case_number": ExtractionField(
                                value="CIV-2024-1138",
                                source_text="case number CIV-2024-1138",
                                confidence_score=0.99
                            ),
                            "plaintiff_name": ExtractionField(
                                value="Jane Doe",
                                source_text="plaintiff Jane Doe",
                                confidence_score=0.95
                            )
                        }
                        
                        # Execute analysis
                        response = await agent.analyze_document(sample_request)
                        
                        # Verify multi-chunk processing
                        assert response.chunk_count == 2
                        assert mock_llm_extract.call_count == 2
                        mock_synthesize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_document_error_handling(self, agent, sample_request):
        """Test error handling during document analysis."""
        with patch.object(agent.pdf_extractor, 'extract') as mock_pdf_extract:
            # Setup mock to raise exception
            mock_pdf_extract.side_effect = Exception("PDF extraction failed")
            
            # Execute analysis
            response = await agent.analyze_document(sample_request)
            
            # Verify error response
            assert response.status == ProcessingStatus.FAILED
            assert len(response.processing_errors) == 1
            assert "PDF extraction failed" in response.processing_errors[0]
            assert len(response.extracted_data) == 0
    
    @pytest.mark.asyncio
    async def test_analyze_document_caching(self, agent, sample_request):
        """Test document analysis caching."""
        # First analysis
        with patch.object(agent.pdf_extractor, 'extract') as mock_pdf_extract:
            with patch.object(agent.llm_extractor, 'extract') as mock_llm_extract:
                with patch.object(agent.text_chunker, 'chunk_text') as mock_chunk:
                    # Setup mocks
                    mock_pdf_extract.return_value = (
                        "Sample text",
                        True,
                        {
                            "filename": "test_document.pdf",
                            "file_size": 1024,
                            "total_pages": 1,
                            "processing_method": "direct_text",
                            "total_characters": 100,
                            "avg_chars_per_page": 100
                        }
                    )
                    
                    mock_chunk_obj = Mock()
                    mock_chunk_obj.text = "Sample text"
                    mock_chunk.return_value = [mock_chunk_obj]
                    
                    mock_llm_extract.return_value = {
                        "case_number": ExtractionField(
                            value="CIV-2024-1138",
                            source_text="Case: CIV-2024-1138",
                            confidence_score=0.99
                        )
                    }
                    
                    # First analysis
                    response1 = await agent.analyze_document(sample_request)
                    
                    # Second analysis (should use cache)
                    response2 = await agent.analyze_document(sample_request)
                    
                    # Verify caching
                    assert response1.extracted_data["case_number"].value == response2.extracted_data["case_number"].value
                    # PDF extraction should only be called once
                    assert mock_pdf_extract.call_count == 1
    
    @pytest.mark.asyncio
    async def test_analyze_document_force_reprocess(self, agent, sample_request):
        """Test forcing reprocess bypasses cache."""
        # Setup request with force_reprocess=True
        sample_request.force_reprocess = True
        
        with patch.object(agent.pdf_extractor, 'extract') as mock_pdf_extract:
            with patch.object(agent.llm_extractor, 'extract') as mock_llm_extract:
                with patch.object(agent.text_chunker, 'chunk_text') as mock_chunk:
                    # Setup mocks
                    mock_pdf_extract.return_value = (
                        "Sample text",
                        True,
                        {
                            "filename": "test_document.pdf",
                            "file_size": 1024,
                            "total_pages": 1,
                            "processing_method": "direct_text",
                            "total_characters": 100,
                            "avg_chars_per_page": 100
                        }
                    )
                    
                    mock_chunk_obj = Mock()
                    mock_chunk_obj.text = "Sample text"
                    mock_chunk.return_value = [mock_chunk_obj]
                    
                    mock_llm_extract.return_value = {
                        "case_number": ExtractionField(
                            value="CIV-2024-1138",
                            source_text="Case: CIV-2024-1138",
                            confidence_score=0.99
                        )
                    }
                    
                    # First analysis
                    await agent.analyze_document(sample_request)
                    
                    # Second analysis with force_reprocess
                    await agent.analyze_document(sample_request)
                    
                    # Verify reprocessing
                    assert mock_pdf_extract.call_count == 2
    
    def test_detect_document_type_complaint(self, agent):
        """Test document type detection for complaint."""
        complaint_text = """
        SUPERIOR COURT OF CALIFORNIA
        COMPLAINT FOR DAMAGES
        Jane Doe, Plaintiff
        vs.
        John Smith, Defendant
        PRAYER FOR RELIEF
        """
        
        doc_type = agent._detect_document_type(complaint_text)
        assert doc_type == DocumentType.COMPLAINT
    
    def test_detect_document_type_retainer(self, agent):
        """Test document type detection for retainer agreement."""
        retainer_text = """
        RETAINER AGREEMENT
        This agreement is between Attorney and Client
        for legal services related to personal injury case.
        """
        
        doc_type = agent._detect_document_type(retainer_text)
        assert doc_type == DocumentType.RETAINER
    
    def test_detect_document_type_other(self, agent):
        """Test document type detection for unknown documents."""
        other_text = """
        This is some random document
        that doesn't match any known patterns.
        """
        
        doc_type = agent._detect_document_type(other_text)
        assert doc_type == DocumentType.OTHER
    
    def test_post_process_results(self, agent):
        """Test post-processing of extraction results."""
        raw_data = {
            "case_number": ExtractionField(
                value="  CIV-2024-1138  ",  # Extra whitespace
                source_text="Case Number: CIV-2024-1138",
                confidence_score=0.99
            ),
            "plaintiff_name": ExtractionField(
                value="Jane Doe",
                source_text="Jane Doe, Plaintiff",
                confidence_score=0.85  # Below threshold
            )
        }
        
        processed_data = agent._post_process_results(raw_data, confidence_threshold=0.9)
        
        # Verify sanitization
        assert processed_data["case_number"].value == "CIV-2024-1138"  # Whitespace removed
        assert processed_data["case_number"].requires_review is False
        
        # Verify review flagging
        assert processed_data["plaintiff_name"].requires_review is True
    
    def test_sanitize_value(self, agent):
        """Test value sanitization."""
        # Test string sanitization
        assert agent._sanitize_value("  Test Value  ") == "Test Value"
        assert agent._sanitize_value("Test|Val") == "TestIVal"  # OCR correction (short string)
        assert agent._sanitize_value("Test|Value") == "Test|Value"  # Long string unchanged
        
        # Test None handling
        assert agent._sanitize_value(None) is None
        
        # Test number handling
        assert agent._sanitize_value(123) == 123
    
    def test_generate_cache_key(self, agent):
        """Test cache key generation."""
        request = DocumentAnalysisRequest(
            document_id="test.pdf",
            extraction_schema=ExtractionSchema(
                schema_name="test_schema",
                fields={"field1": None}
            ),
            process_full_document=False
        )
        
        key1 = agent._generate_cache_key(request)
        key2 = agent._generate_cache_key(request)
        
        # Same request should generate same key
        assert key1 == key2
        
        # Different request should generate different key
        request.process_full_document = True
        key3 = agent._generate_cache_key(request)
        assert key1 != key3
    
    def test_generate_file_hash(self, agent):
        """Test file hash generation."""
        text1 = "Sample text content"
        text2 = "Different text content"
        
        hash1 = agent._generate_file_hash(text1)
        hash2 = agent._generate_file_hash(text1)
        hash3 = agent._generate_file_hash(text2)
        
        # Same text should generate same hash
        assert hash1 == hash2
        
        # Different text should generate different hash
        assert hash1 != hash3
        
        # Hash should be 32 characters (MD5)
        assert len(hash1) == 32
    
    @pytest.mark.asyncio
    async def test_get_document_status(self, agent):
        """Test getting document status."""
        # No cached document
        status = await agent.get_document_status("nonexistent.pdf")
        assert status is None
        
        # Add a document to cache
        response = DocumentAnalysisResponse(
            document_id="test.pdf",
            status=ProcessingStatus.COMPLETED,
            extracted_data={},
            metadata=DocumentMetadata(
                filename="test.pdf",
                file_size=1024,
                page_count=1,
                document_type=DocumentType.OTHER,
                processing_method="direct_text",
                raw_text_md5="abc123",
                processing_duration=1.0
            )
        )
        
        # Manually add to cache
        agent.cache["test_key"] = response
        
        # Should find the status
        status = await agent.get_document_status("test.pdf")
        assert status == ProcessingStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_clear_cache(self, agent):
        """Test clearing the cache."""
        # Add something to cache
        agent.cache["test_key"] = "test_value"
        
        # Clear cache
        await agent.clear_cache()
        
        # Verify cache is empty
        assert len(agent.cache) == 0
    
    @pytest.mark.asyncio
    async def test_close_agent(self, agent):
        """Test closing the agent."""
        with patch.object(agent.llm_extractor, 'close') as mock_close:
            await agent.close()
            mock_close.assert_called_once()
