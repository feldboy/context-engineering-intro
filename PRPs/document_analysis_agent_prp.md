name: "AI-Powered Document Analysis Agent: PDF to Structured Data Extraction"
description: |

## Purpose
Build a comprehensive PDF document analysis agent for a Pre-Settlement Funding CRM that extracts structured data from legal documents (Civil Complaints, Retainer Agreements) with high accuracy and verification metadata. This agent will automate the "Case Information Gathering & Verification" workflow stage while maintaining human oversight for legal compliance.

## Core Principles
1. **Context is King**: Include ALL necessary documentation, examples, and caveats
2. **Validation Loops**: Provide executable tests/lints the AI can run and fix
3. **Information Dense**: Use keywords and patterns from the codebase
4. **Progressive Success**: Start simple, validate, then enhance
5. **Global rules**: Be sure to follow all rules in CLAUDE.md

---

## Goal
Create a production-ready AI agent that processes PDF legal documents to extract structured data with confidence scoring, source text tracking, and human verification UI. The system must handle both text-based and scanned (OCR) PDFs with accuracy as the highest priority.

## Why
- **Business value**: Automates 80% of manual data entry for case intake
- **Integration**: Core component of Pre-Settlement Funding CRM workflow
- **Problems solved**: Reduces human error, speeds up case processing, ensures data consistency
- **Legal compliance**: Maintains audit trail and human verification requirements

## What
A comprehensive document analysis system where:
- Users upload PDF legal documents
- System extracts text using PyMuPDF or OCR fallback
- LLM processes text against user-provided JSON schema
- Results include confidence scores and source text for verification
- Human verification UI displays side-by-side document and extracted data
- Low-confidence fields are flagged for mandatory review

### Success Criteria
- [ ] Successfully extracts text from both text-based and scanned PDFs
- [ ] Processes documents against flexible JSON schemas
- [ ] Returns structured data with confidence scores and source text
- [ ] Handles large documents through intelligent chunking
- [ ] Provides human verification UI with document highlighting
- [ ] Achieves >95% accuracy on test legal documents
- [ ] Processes first 5-10 pages within 30 seconds

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window
- url: https://pymupdf.readthedocs.io/en/latest/tutorial.html
  why: PDF text extraction, handling text vs image PDFs
  
- url: https://tesseract-ocr.github.io/tessdoc/
  why: OCR for scanned PDFs, configuration options
  
- url: https://github.com/madmaze/pytesseract
  why: Python wrapper for Tesseract OCR
  
- url: https://docs.deepseek.com/api/
  why: LLM API with JSON mode for structured extraction
  
- url: https://docs.anthropic.com/claude/docs/structured-outputs
  why: Structured output patterns for data extraction
  
- url: https://docs.google.com/document/d/1234567890/edit
  why: Internal data model specifications (MongoDB schema)
  
- url: https://fastapi.tiangolo.com/tutorial/
  why: API endpoint patterns for backend/api/ai_agents.py
  
- file: examples/agent/agent.py
  why: Pattern for agent creation and tool registration
  
- file: examples/agent/providers.py  
  why: Multi-provider LLM configuration pattern
```

### Current Codebase tree
```bash
context-engineering-intro/
├── .claude/
│   ├── commands/
│   │   ├── generate-prp.md
│   │   └── execute-prp.md
│   └── settings.local.json
├── PRPs/
│   ├── templates/
│   │   └── prp_base.md
│   └── EXAMPLE_multi_agent_prp.md
├── examples/
│   └── .gitkeep
├── CLAUDE.md
├── INITIAL.md
├── INITIAL_EXAMPLE.md
├── README.md
└── requirements.txt (to be created)
```

### Desired Codebase tree with files to be added
```bash
context-engineering-intro/
├── backend/
│   ├── __init__.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── document_analysis_agent.py    # Main agent with PDF processing
│   │   ├── providers.py                  # LLM provider configuration
│   │   └── models.py                     # Pydantic models for data validation
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── pdf_extractor.py              # PDF text extraction (PyMuPDF)
│   │   ├── ocr_processor.py              # OCR processing (pytesseract)
│   │   ├── text_chunker.py               # Document chunking for large files
│   │   └── llm_extractor.py              # LLM-based data extraction
│   ├── api/
│   │   ├── __init__.py
│   │   ├── ai_agents.py                  # FastAPI endpoints
│   │   └── dependencies.py               # API dependencies
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py                   # Environment and config management
│   └── utils/
│       ├── __init__.py
│       ├── file_utils.py                 # File handling utilities
│       ├── hash_utils.py                 # File hashing for caching
│       └── validation.py                 # Data validation helpers
├── frontend/
│   ├── components/
│   │   ├── DocumentViewer.js             # PDF viewer component
│   │   ├── ExtractionForm.js             # Data extraction form
│   │   └── VerificationUI.js             # Human verification interface
│   └── styles/
│       └── verification.css              # Styles for verification UI
├── tests/
│   ├── __init__.py
│   ├── test_document_analysis_agent.py   # Main agent tests
│   ├── test_pdf_extractor.py             # PDF extraction tests
│   ├── test_ocr_processor.py             # OCR processing tests
│   ├── test_text_chunker.py              # Text chunking tests
│   ├── test_llm_extractor.py             # LLM extraction tests
│   ├── test_api_endpoints.py             # API endpoint tests
│   └── fixtures/
│       ├── sample_complaint.pdf          # Test PDF documents
│       ├── sample_retainer.pdf
│       └── sample_schemas.json           # Test extraction schemas
├── credentials/
│   └── .gitkeep                          # Directory for API credentials
├── .env.example                          # Environment variables template
├── requirements.txt                      # Updated dependencies
└── README.md                             # Comprehensive documentation
```

### Known Gotchas & Library Quirks
```python
# CRITICAL: PyMuPDF extracts text but may return empty for scanned PDFs
# CRITICAL: pytesseract requires Tesseract binary installed on system
# CRITICAL: LLM APIs have token limits - need chunking for large documents
# CRITICAL: PDF coordinate systems are different from screen coordinates
# CRITICAL: OCR accuracy depends heavily on image quality and preprocessing
# CRITICAL: Legal documents have specific formatting - party names, case numbers
# CRITICAL: Confidence scores need calibration - 0.9 threshold may be too high
# CRITICAL: JSON mode responses can still hallucinate - validation essential
# CRITICAL: File hashing prevents reprocessing but consider document versions
# CRITICAL: MongoDB schema alignment critical for CRM integration
```

## Implementation Blueprint

### Data models and structure

```python
# models.py - Core data structures
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum

class DocumentType(str, Enum):
    COMPLAINT = "complaint"
    RETAINER = "retainer_agreement"
    SETTLEMENT = "settlement_agreement"
    MEDICAL_RECORD = "medical_record"
    OTHER = "other"

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REQUIRES_REVIEW = "requires_review"

class ExtractionField(BaseModel):
    value: Optional[Union[str, List[str], int, float]] = None
    source_text: Optional[str] = None
    confidence_score: float = Field(0.0, ge=0.0, le=1.0)
    page_number: Optional[int] = None
    requires_review: bool = False

class DocumentMetadata(BaseModel):
    filename: str
    file_size: int
    page_count: int
    document_type: DocumentType
    processing_method: str  # "direct_text" or "ocr"
    raw_text_md5: str
    processing_timestamp: datetime
    processing_duration: float  # seconds

class ExtractionSchema(BaseModel):
    schema_name: str
    fields: Dict[str, Any]  # JSON schema for extraction
    confidence_threshold: float = Field(0.9, ge=0.0, le=1.0)
    
    @validator('fields')
    def validate_schema(cls, v):
        # Ensure schema has required structure
        if not isinstance(v, dict):
            raise ValueError("Schema must be a dictionary")
        return v

class DocumentAnalysisRequest(BaseModel):
    document_id: str
    extraction_schema: ExtractionSchema
    process_full_document: bool = False  # False = first 5-10 pages only
    force_reprocess: bool = False

class DocumentAnalysisResponse(BaseModel):
    document_id: str
    status: ProcessingStatus
    extracted_data: Dict[str, ExtractionField]
    metadata: DocumentMetadata
    processing_errors: List[str] = []
    chunk_count: Optional[int] = None
    review_required_count: int = 0
```

### List of tasks to be completed

```yaml
Task 1: Setup Configuration and Dependencies
CREATE config/settings.py:
  - PATTERN: Use pydantic-settings for environment variables
  - Load LLM API keys (OpenAI, Anthropic, DeepSeek)
  - Configure file upload paths and size limits
  - Set confidence thresholds and processing timeouts

CREATE .env.example:
  - Include all required environment variables with descriptions
  - API keys for LLM providers
  - File storage paths and limits
  - OCR and processing configuration

CREATE requirements.txt:
  - PyMuPDF for PDF text extraction
  - pytesseract for OCR processing
  - pydantic for data validation
  - FastAPI for API endpoints
  - httpx for async HTTP clients
  - hashlib for file hashing
  - Pillow for image processing

Task 2: Implement PDF Text Extraction
CREATE backend/tools/pdf_extractor.py:
  - PATTERN: Async functions with proper error handling
  - Use PyMuPDF (fitz) for direct text extraction
  - Detect if PDF is text-based or scanned
  - Extract metadata (page count, file size)
  - Return structured text with page numbers

Task 3: Implement OCR Processing
CREATE backend/tools/ocr_processor.py:
  - PATTERN: Fallback processing for scanned PDFs
  - Use pytesseract with optimized configuration
  - Preprocess images for better OCR accuracy
  - Handle multi-page PDFs efficiently
  - Return structured text with confidence scores

Task 4: Implement Text Chunking
CREATE backend/tools/text_chunker.py:
  - PATTERN: Smart chunking for large documents
  - Respect sentence/paragraph boundaries
  - Implement overlapping windows (400 tokens)
  - Maintain source page mapping
  - Handle legal document structure awareness

Task 5: Implement LLM-based Data Extraction
CREATE backend/tools/llm_extractor.py:
  - PATTERN: Multi-provider LLM support
  - Use structured output (JSON mode) for extraction
  - Implement role-based prompting for legal documents
  - Handle chunk-based processing and result synthesis
  - Generate confidence scores and source text mapping

Task 6: Create Document Analysis Agent
CREATE backend/agents/document_analysis_agent.py:
  - PATTERN: Main orchestrator following agent pattern
  - Coordinate PDF extraction -> OCR -> Chunking -> LLM extraction
  - Implement caching based on file hash
  - Handle partial processing (first N pages)
  - Aggregate results from multiple chunks

Task 7: Implement API Endpoints
CREATE backend/api/ai_agents.py:
  - PATTERN: FastAPI endpoints with proper validation
  - File upload endpoint with size/type validation
  - Document analysis endpoint with async processing
  - Status check endpoint for long-running processes
  - Results retrieval endpoint with pagination

Task 8: Create Human Verification UI Components
CREATE frontend/components/DocumentViewer.js:
  - PATTERN: PDF viewer with text highlighting
  - React component with PDF.js integration
  - Coordinate highlighting with extraction form
  - Handle page navigation and zoom

CREATE frontend/components/VerificationUI.js:
  - PATTERN: Side-by-side document and form interface
  - Highlight source text when clicking form fields
  - Flag low-confidence fields for mandatory review
  - Allow manual corrections with tracking

Task 9: Implement Utility Functions
CREATE backend/utils/file_utils.py:
  - PATTERN: File handling with proper validation
  - File type detection and validation
  - Secure file storage and cleanup
  - File hash generation for caching

CREATE backend/utils/validation.py:
  - PATTERN: Data validation helpers
  - Schema validation for extraction templates
  - Confidence score calibration
  - Data sanitization for legal documents

Task 10: Create Comprehensive Tests
CREATE tests/test_document_analysis_agent.py:
  - PATTERN: End-to-end agent testing
  - Test both text and scanned PDF processing
  - Validate extraction accuracy against known documents
  - Test error handling and edge cases

CREATE tests/fixtures/:
  - Sample legal documents for testing
  - Known extraction schemas and expected results
  - Test cases for various document types
```

### Per task pseudocode as needed

```python
# Task 2: PDF Text Extraction
import fitz  # PyMuPDF
from typing import Tuple, List, Optional

async def extract_text_from_pdf(pdf_path: str, max_pages: Optional[int] = None) -> Tuple[str, bool, Dict]:
    """
    Extract text from PDF with detection of text vs scanned content.
    
    Returns:
        (extracted_text, is_text_based, metadata)
    """
    # PATTERN: Always validate input first
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    # CRITICAL: PyMuPDF requires proper resource management
    with fitz.open(pdf_path) as doc:
        total_pages = len(doc)
        process_pages = min(max_pages or total_pages, total_pages)
        
        text_content = []
        char_count = 0
        
        for page_num in range(process_pages):
            page = doc[page_num]
            page_text = page.get_text()
            
            # GOTCHA: Empty text doesn't mean scanned - check character density
            char_count += len(page_text.strip())
            text_content.append({
                "page": page_num + 1,
                "text": page_text,
                "char_count": len(page_text.strip())
            })
        
        # PATTERN: Heuristic for text vs scanned detection
        avg_chars_per_page = char_count / process_pages if process_pages > 0 else 0
        is_text_based = avg_chars_per_page > 100  # Threshold for text-based PDF
        
        metadata = {
            "total_pages": total_pages,
            "processed_pages": process_pages,
            "total_characters": char_count,
            "avg_chars_per_page": avg_chars_per_page,
            "is_text_based": is_text_based
        }
        
        return "\n".join([p["text"] for p in text_content]), is_text_based, metadata

# Task 5: LLM-based Data Extraction
from typing import Dict, List
import json

async def extract_structured_data(text: str, schema: Dict, provider: str = "openai") -> Dict:
    """
    Extract structured data from text using LLM with confidence scoring.
    """
    # PATTERN: Role-based prompting for legal documents
    system_prompt = """You are an expert paralegal specializing in personal injury cases. 
    Your task is to extract specific information from legal documents with extreme accuracy.
    
    CRITICAL RULES:
    1. Extract information ONLY from the provided text
    2. Do not infer or add information not explicitly stated
    3. For each field, provide the exact source text that justifies the extraction
    4. Assign confidence scores from 0.0 to 1.0 based on text clarity
    5. If information is not found, return null values with 0.0 confidence
    """
    
    # PATTERN: Structured prompt with schema and instructions
    user_prompt = f"""
    Extract the following information from this legal document text:
    
    TARGET SCHEMA:
    {json.dumps(schema, indent=2)}
    
    DOCUMENT TEXT:
    {text}
    
    Return a JSON object where each field contains:
    - value: The extracted value (null if not found)
    - source_text: The exact text that supports this extraction
    - confidence_score: A score from 0.0 to 1.0 indicating confidence
    
    Example format:
    {{
        "case_number": {{
            "value": "CIV-2024-1138",
            "source_text": "Case Number: CIV-2024-1138",
            "confidence_score": 0.99
        }}
    }}
    """
    
    # CRITICAL: Use JSON mode for structured output
    response = await llm_client.complete(
        model="gpt-4o",  # Use most capable model for accuracy
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.1  # Low temperature for consistent extraction
    )
    
    # PATTERN: Validate and sanitize LLM response
    try:
        extracted_data = json.loads(response.choices[0].message.content)
        return validate_extraction_response(extracted_data, schema)
    except json.JSONDecodeError:
        raise ValueError("LLM returned invalid JSON response")

# Task 6: Document Analysis Agent (Main Orchestrator)
class DocumentAnalysisAgent:
    def __init__(self, config: Settings):
        self.config = config
        self.pdf_extractor = PDFExtractor()
        self.ocr_processor = OCRProcessor()
        self.text_chunker = TextChunker()
        self.llm_extractor = LLMExtractor()
        self.cache = {}  # Simple in-memory cache
    
    async def analyze_document(self, request: DocumentAnalysisRequest) -> DocumentAnalysisResponse:
        """
        Main orchestration method for document analysis.
        """
        # PATTERN: Check cache first
        file_hash = self._get_file_hash(request.document_id)
        cache_key = f"{file_hash}_{request.extraction_schema.schema_name}"
        
        if not request.force_reprocess and cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            # Step 1: Extract text from PDF
            text, is_text_based, metadata = await self.pdf_extractor.extract(
                request.document_id,
                max_pages=None if request.process_full_document else 10
            )
            
            # Step 2: OCR fallback if needed
            if not is_text_based:
                text = await self.ocr_processor.process(request.document_id)
                metadata["processing_method"] = "ocr"
            else:
                metadata["processing_method"] = "direct_text"
            
            # Step 3: Chunk text if too large
            chunks = self.text_chunker.chunk_text(text, max_tokens=4000)
            
            # Step 4: Extract structured data
            if len(chunks) == 1:
                extracted_data = await self.llm_extractor.extract(
                    chunks[0], request.extraction_schema.fields
                )
            else:
                # PATTERN: Multi-chunk processing with result synthesis
                chunk_results = []
                for chunk in chunks:
                    result = await self.llm_extractor.extract(
                        chunk, request.extraction_schema.fields
                    )
                    chunk_results.append(result)
                
                extracted_data = self._synthesize_results(chunk_results)
            
            # Step 5: Post-process and validate
            processed_data = self._post_process_results(
                extracted_data, request.extraction_schema.confidence_threshold
            )
            
            # Step 6: Create response
            response = DocumentAnalysisResponse(
                document_id=request.document_id,
                status=ProcessingStatus.COMPLETED,
                extracted_data=processed_data,
                metadata=DocumentMetadata(**metadata),
                chunk_count=len(chunks),
                review_required_count=sum(1 for field in processed_data.values() 
                                        if field.requires_review)
            )
            
            # PATTERN: Cache successful results
            self.cache[cache_key] = response
            return response
            
        except Exception as e:
            return DocumentAnalysisResponse(
                document_id=request.document_id,
                status=ProcessingStatus.FAILED,
                extracted_data={},
                metadata=DocumentMetadata(**metadata),
                processing_errors=[str(e)]
            )
```

### Integration Points
```yaml
DATABASE:
  - migration: "Add document_analysis table with extracted_data JSONB column"
  - index: "CREATE INDEX idx_document_hash ON document_analysis(file_hash)"
  - index: "CREATE INDEX idx_processing_status ON document_analysis(status)"
  
CONFIG:
  - add to: config/settings.py
  - pattern: "PDF_UPLOAD_MAX_SIZE = int(os.getenv('PDF_UPLOAD_MAX_SIZE', '50000000'))"
  - pattern: "OCR_CONFIDENCE_THRESHOLD = float(os.getenv('OCR_CONFIDENCE_THRESHOLD', '0.9'))"
  
ROUTES:
  - add to: backend/api/ai_agents.py
  - pattern: "router.include_router(document_router, prefix='/api/documents')"
  
FRONTEND:
  - add to: components/
  - pattern: "Import DocumentViewer and VerificationUI components"
  - pattern: "Create document upload and analysis workflow"
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run these FIRST - fix any errors before proceeding
ruff check backend/ --fix           # Auto-fix what's possible
mypy backend/                       # Type checking
black backend/                      # Code formatting

# Expected: No errors. If errors, READ the error and fix.
```

### Level 2: Unit Tests
```python
# CREATE comprehensive test suite
def test_pdf_text_extraction():
    """Test direct PDF text extraction"""
    extractor = PDFExtractor()
    text, is_text_based, metadata = await extractor.extract("tests/fixtures/sample_complaint.pdf")
    assert len(text) > 100
    assert is_text_based is True
    assert metadata["total_pages"] > 0

def test_ocr_processing():
    """Test OCR fallback for scanned PDFs"""
    processor = OCRProcessor()
    text = await processor.process("tests/fixtures/scanned_document.pdf")
    assert len(text) > 50
    assert "plaintiff" in text.lower()

def test_structured_extraction():
    """Test LLM-based data extraction"""
    extractor = LLMExtractor()
    schema = {"case_number": None, "plaintiff_name": None}
    sample_text = "Case Number: CIV-2024-1138\nJane Doe, Plaintiff"
    
    result = await extractor.extract(sample_text, schema)
    assert result["case_number"]["value"] == "CIV-2024-1138"
    assert result["case_number"]["confidence_score"] > 0.9
    assert "Case Number: CIV-2024-1138" in result["case_number"]["source_text"]

def test_document_analysis_agent():
    """Test end-to-end document analysis"""
    agent = DocumentAnalysisAgent(config)
    request = DocumentAnalysisRequest(
        document_id="sample_complaint.pdf",
        extraction_schema=ExtractionSchema(
            schema_name="civil_complaint",
            fields={"case_number": None, "plaintiff_name": None}
        )
    )
    
    response = await agent.analyze_document(request)
    assert response.status == ProcessingStatus.COMPLETED
    assert len(response.extracted_data) > 0
    assert response.metadata.page_count > 0
```

```bash
# Run and iterate until passing:
pytest tests/ -v --cov=backend/
# If failing: Read error, understand root cause, fix code, re-run
```

### Level 3: Integration Test
```bash
# Start the service
uvicorn backend.api.ai_agents:app --reload --port 8000

# Test document upload
curl -X POST "http://localhost:8000/api/documents/upload" \
  -F "file=@tests/fixtures/sample_complaint.pdf" \
  -F "document_type=complaint"

# Test document analysis
curl -X POST "http://localhost:8000/api/documents/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "sample_complaint.pdf",
    "extraction_schema": {
      "schema_name": "civil_complaint",
      "fields": {"case_number": null, "plaintiff_name": null}
    }
  }'

# Expected: {"status": "completed", "extracted_data": {...}}
```

### Level 4: Accuracy Validation
```bash
# Test with known legal documents
python -m tests.accuracy_test --document tests/fixtures/sample_complaint.pdf --expected tests/fixtures/expected_results.json

# Expected: >95% accuracy on known extractions
# If accuracy is low: Review prompts, adjust confidence thresholds, improve preprocessing
```

## Final validation Checklist
- [ ] All tests pass: `pytest tests/ -v`
- [ ] No linting errors: `ruff check backend/`
- [ ] No type errors: `mypy backend/`
- [ ] API endpoints respond correctly: Manual curl tests
- [ ] PDF text extraction works for both text and scanned PDFs
- [ ] OCR fallback activates for scanned documents
- [ ] Structured data extraction returns proper confidence scores
- [ ] Document analysis agent handles chunking for large documents
- [ ] Human verification UI highlights source text correctly
- [ ] Low-confidence fields are flagged for review
- [ ] Processing time <30 seconds for first 10 pages
- [ ] Accuracy >95% on test legal documents

---

## Anti-Patterns to Avoid
- ❌ Don't process entire documents by default - legal docs can be 100+ pages
- ❌ Don't trust OCR output without validation - preprocessing is critical
- ❌ Don't ignore confidence scores - they're essential for legal accuracy
- ❌ Don't hardcode legal document patterns - use flexible schema approach
- ❌ Don't skip human verification - legal compliance requires human oversight
- ❌ Don't cache based on filename only - use file hash for accuracy
- ❌ Don't use high temperature for LLM extraction - consistency is key
- ❌ Don't assume all PDFs have text - many legal docs are scanned images
- ❌ Don't extract beyond provided text - hallucination is dangerous in legal context
- ❌ Don't ignore chunk boundaries - legal context can span multiple chunks
