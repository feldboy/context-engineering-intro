import asyncio
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import logging
from ..config.settings import settings
from ..agents.models import (
    DocumentAnalysisRequest, 
    DocumentAnalysisResponse, 
    DocumentMetadata,
    ProcessingStatus,
    ExtractionField,
    DocumentType
)
from ..tools.pdf_extractor import PDFExtractor
from ..tools.ocr_processor import OCRProcessor
from ..tools.text_chunker import TextChunker
from ..tools.llm_extractor import LLMExtractor

logger = logging.getLogger(__name__)


class DocumentAnalysisAgent:
    """
    Main orchestrator for PDF document analysis and structured data extraction.
    """
    
    def __init__(self):
        self.pdf_extractor = PDFExtractor()
        self.ocr_processor = OCRProcessor()
        self.text_chunker = TextChunker(
            max_tokens=settings.chunk_size_tokens,
            overlap_tokens=settings.chunk_overlap_tokens
        )
        self.llm_extractor = LLMExtractor()
        
        # Simple in-memory cache (in production, use Redis or similar)
        self.cache = {}
    
    async def analyze_document(self, request: DocumentAnalysisRequest) -> DocumentAnalysisResponse:
        """
        Main orchestration method for document analysis.
        
        Args:
            request: Document analysis request
            
        Returns:
            Document analysis response with extracted data
        """
        start_time = datetime.now()
        
        try:
            # Step 1: Check cache first
            cache_key = self._generate_cache_key(request)
            
            if not request.force_reprocess and cache_key in self.cache:
                logger.info("Returning cached result for document: %s", request.document_id)
                return self.cache[cache_key]
            
            # Step 2: Extract text from PDF
            logger.info("Starting PDF text extraction for: %s", request.document_id)
            text, is_text_based, pdf_metadata = await self.pdf_extractor.extract(
                request.document_id,
                max_pages=None if request.process_full_document else settings.max_pages_default
            )
            
            # Step 3: OCR fallback if needed
            if not is_text_based:
                logger.info("PDF appears to be scanned, switching to OCR processing")
                text = await self.ocr_processor.process(request.document_id)
                pdf_metadata["processing_method"] = "ocr"
            else:
                pdf_metadata["processing_method"] = "direct_text"
            
            # Step 4: Generate file hash for caching
            file_hash = self._generate_file_hash(text)
            
            # Step 5: Chunk text if too large
            chunks = self.text_chunker.chunk_text(text, max_tokens=settings.chunk_size_tokens)
            logger.info("Text chunked into %d chunks", len(chunks))
            
            # Step 6: Extract structured data
            if len(chunks) == 1:
                # Single chunk processing
                extracted_data = await self.llm_extractor.extract(
                    chunks[0].text, 
                    request.extraction_schema.fields
                )
            else:
                # PATTERN: Multi-chunk processing with result synthesis
                chunk_results = []
                for i, chunk in enumerate(chunks):
                    logger.info("Processing chunk %d of %d", i + 1, len(chunks))
                    result = await self.llm_extractor.extract(
                        chunk.text, 
                        request.extraction_schema.fields
                    )
                    chunk_results.append(result)
                
                # Synthesize results from all chunks
                extracted_data = self.llm_extractor.synthesize_chunk_results(chunk_results)
            
            # Step 7: Post-process and validate
            processed_data = self._post_process_results(
                extracted_data, 
                request.extraction_schema.confidence_threshold
            )
            
            # Step 8: Create metadata
            processing_duration = (datetime.now() - start_time).total_seconds()
            
            metadata = DocumentMetadata(
                filename=pdf_metadata["filename"],
                file_size=pdf_metadata["file_size"],
                page_count=pdf_metadata["total_pages"],
                document_type=self._detect_document_type(text),
                processing_method=pdf_metadata["processing_method"],
                raw_text_md5=file_hash,
                processing_duration=processing_duration,
                total_characters=pdf_metadata["total_characters"],
                avg_chars_per_page=pdf_metadata["avg_chars_per_page"]
            )
            
            # Step 9: Create response
            response = DocumentAnalysisResponse(
                document_id=request.document_id,
                status=ProcessingStatus.COMPLETED,
                extracted_data=processed_data,
                metadata=metadata,
                chunk_count=len(chunks)
            )
            
            # Step 10: Cache successful results
            self.cache[cache_key] = response
            
            logger.info(
                "Document analysis completed for %s: %d fields extracted, %d require review",
                request.document_id,
                len(processed_data),
                response.review_required_count
            )
            
            return response
            
        except Exception as e:
            logger.error("Error analyzing document %s: %s", request.document_id, str(e))
            
            # Create error response
            processing_duration = (datetime.now() - start_time).total_seconds()
            
            return DocumentAnalysisResponse(
                document_id=request.document_id,
                status=ProcessingStatus.FAILED,
                extracted_data={},
                metadata=DocumentMetadata(
                    filename=request.document_id,
                    file_size=0,
                    page_count=0,
                    document_type=DocumentType.OTHER,
                    processing_method="error",
                    raw_text_md5="",
                    processing_duration=processing_duration
                ),
                processing_errors=[str(e)]
            )
    
    def _generate_cache_key(self, request: DocumentAnalysisRequest) -> str:
        """
        Generate cache key for the request.
        
        Args:
            request: Document analysis request
            
        Returns:
            Cache key string
        """
        key_components = [
            request.document_id,
            request.extraction_schema.schema_name,
            str(request.process_full_document),
            str(request.extraction_schema.confidence_threshold)
        ]
        
        key_string = "|".join(key_components)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _generate_file_hash(self, text: str) -> str:
        """
        Generate MD5 hash of the text content.
        
        Args:
            text: Text content
            
        Returns:
            MD5 hash string
        """
        return hashlib.md5(text.encode()).hexdigest()
    
    def _post_process_results(
        self, 
        extracted_data: Dict[str, ExtractionField], 
        confidence_threshold: float
    ) -> Dict[str, ExtractionField]:
        """
        Post-process extraction results.
        
        Args:
            extracted_data: Raw extraction results
            confidence_threshold: Confidence threshold for review flagging
            
        Returns:
            Processed extraction results
        """
        processed_data = {}
        
        for field_name, field_data in extracted_data.items():
            # Create a copy to avoid modifying original
            processed_field = ExtractionField(
                value=field_data.value,
                source_text=field_data.source_text,
                confidence_score=field_data.confidence_score,
                page_number=field_data.page_number,
                requires_review=field_data.confidence_score < confidence_threshold
            )
            
            # Additional validation
            if processed_field.value is not None:
                processed_field.value = self._sanitize_value(processed_field.value)
            
            processed_data[field_name] = processed_field
        
        return processed_data
    
    def _sanitize_value(self, value: Any) -> Any:
        """
        Sanitize extracted values.
        
        Args:
            value: Raw extracted value
            
        Returns:
            Sanitized value
        """
        if isinstance(value, str):
            # Remove extra whitespace
            value = value.strip()
            # Remove common OCR artifacts
            value = value.replace('|', 'I').replace('0', 'O') if len(value) < 10 else value
        
        return value
    
    def _detect_document_type(self, text: str) -> DocumentType:
        """
        Detect document type based on text content.
        
        Args:
            text: Document text
            
        Returns:
            Detected document type
        """
        text_lower = text.lower()
        
        # Check for complaint indicators
        complaint_indicators = [
            'complaint for damages',
            'civil complaint',
            'plaintiff',
            'defendant',
            'cause of action',
            'prayer for relief'
        ]
        
        if any(indicator in text_lower for indicator in complaint_indicators):
            return DocumentType.COMPLAINT
        
        # Check for retainer agreement indicators
        retainer_indicators = [
            'retainer agreement',
            'attorney-client agreement',
            'legal services agreement',
            'fee agreement'
        ]
        
        if any(indicator in text_lower for indicator in retainer_indicators):
            return DocumentType.RETAINER
        
        # Check for settlement indicators
        settlement_indicators = [
            'settlement agreement',
            'release and settlement',
            'settlement and release'
        ]
        
        if any(indicator in text_lower for indicator in settlement_indicators):
            return DocumentType.SETTLEMENT
        
        # Check for medical record indicators
        medical_indicators = [
            'medical record',
            'patient',
            'diagnosis',
            'treatment',
            'hospital'
        ]
        
        if any(indicator in text_lower for indicator in medical_indicators):
            return DocumentType.MEDICAL_RECORD
        
        return DocumentType.OTHER
    
    async def get_document_status(self, document_id: str) -> Optional[ProcessingStatus]:
        """
        Get the processing status of a document.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Processing status or None if not found
        """
        # Check cache for status
        for cached_response in self.cache.values():
            if cached_response.document_id == document_id:
                return cached_response.status
        
        return None
    
    async def clear_cache(self):
        """Clear the analysis cache."""
        self.cache.clear()
        logger.info("Analysis cache cleared")
    
    async def close(self):
        """Close resources."""
        await self.llm_extractor.close()
        logger.info("Document analysis agent closed")
