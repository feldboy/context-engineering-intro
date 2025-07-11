from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum


class DocumentType(str, Enum):
    """Supported document types for analysis."""
    COMPLAINT = "complaint"
    RETAINER = "retainer_agreement"
    SETTLEMENT = "settlement_agreement"
    MEDICAL_RECORD = "medical_record"
    OTHER = "other"


class ProcessingStatus(str, Enum):
    """Document processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REQUIRES_REVIEW = "requires_review"


class ExtractionField(BaseModel):
    """Individual field extraction result with metadata."""
    value: Optional[Union[str, List[str], int, float]] = None
    source_text: Optional[str] = None
    confidence_score: float = Field(0.0, ge=0.0, le=1.0)
    page_number: Optional[int] = None
    requires_review: bool = False
    
    def __init__(self, **data):
        super().__init__(**data)
        # Auto-flag for review if confidence is low
        if self.confidence_score < 0.9:
            self.requires_review = True


class DocumentMetadata(BaseModel):
    """Document processing metadata."""
    filename: str
    file_size: int
    page_count: int
    document_type: DocumentType
    processing_method: str  # "direct_text" or "ocr"
    raw_text_md5: str
    processing_timestamp: datetime = Field(default_factory=datetime.now)
    processing_duration: float  # seconds
    total_characters: int = 0
    avg_chars_per_page: float = 0.0


class ExtractionSchema(BaseModel):
    """Schema definition for data extraction."""
    schema_name: str
    fields: Dict[str, Any]  # JSON schema for extraction
    confidence_threshold: float = Field(0.9, ge=0.0, le=1.0)
    
    @validator('fields')
    def validate_schema(cls, v):
        """Ensure schema has required structure."""
        if not isinstance(v, dict):
            raise ValueError("Schema must be a dictionary")
        return v
    
    @validator('schema_name')
    def validate_schema_name(cls, v):
        """Ensure schema name is not empty."""
        if not v or not v.strip():
            raise ValueError("Schema name cannot be empty")
        return v.strip()


class DocumentAnalysisRequest(BaseModel):
    """Request model for document analysis."""
    document_id: str
    extraction_schema: ExtractionSchema
    process_full_document: bool = False  # False = first 5-10 pages only
    force_reprocess: bool = False
    
    @validator('document_id')
    def validate_document_id(cls, v):
        """Ensure document ID is not empty."""
        if not v or not v.strip():
            raise ValueError("Document ID cannot be empty")
        return v.strip()


class DocumentAnalysisResponse(BaseModel):
    """Response model for document analysis."""
    document_id: str
    status: ProcessingStatus
    extracted_data: Dict[str, ExtractionField]
    metadata: DocumentMetadata
    processing_errors: List[str] = []
    chunk_count: Optional[int] = None
    review_required_count: int = 0
    
    def __init__(self, **data):
        super().__init__(**data)
        # Auto-calculate review required count
        self.review_required_count = sum(
            1 for field in self.extracted_data.values() 
            if field.requires_review
        )


class ChunkResult(BaseModel):
    """Result from processing a single text chunk."""
    chunk_index: int
    extracted_data: Dict[str, ExtractionField]
    source_pages: List[int]
    processing_errors: List[str] = []


class PDFExtractionResult(BaseModel):
    """Result from PDF text extraction."""
    text: str
    is_text_based: bool
    metadata: Dict[str, Any]
    page_texts: List[Dict[str, Any]]  # Page-wise text with metadata


class OCRResult(BaseModel):
    """Result from OCR processing."""
    text: str
    confidence_scores: List[float]
    page_confidences: Dict[int, float]
    processing_errors: List[str] = []


class ExtractionResult(BaseModel):
    """Complete extraction result with aggregated data."""
    document_id: str
    extracted_data: Dict[str, ExtractionField]
    metadata: DocumentMetadata
    processing_errors: List[str] = []
    chunk_results: List[ChunkResult] = []
    overall_confidence: float = 0.0
    
    def __init__(self, **data):
        super().__init__(**data)
        # Calculate overall confidence from extracted fields
        if self.extracted_data:
            confidences = [field.confidence_score for field in self.extracted_data.values()]
            self.overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0
