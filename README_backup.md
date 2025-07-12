# Document Analysis Agent

An AI-powered document analysis system for pre-settlement funding CRM, designed to extract structured data from legal documents (PDFs) using advanced language models and OCR technology.

## 🚀 Features

- **Multi-format PDF Support**: Handle both text-based and scanned PDF documents
- **Intelligent Data Extraction**: Extract structured data using user-defined JSON schemas
- **Multi-LLM Support**: Compatible with OpenAI, Anthropic, and DeepSeek models
- **Human Verification UI**: Interactive interface for reviewing and correcting extractions
- **Confidence Scoring**: AI-generated confidence scores for extracted data
- **Smart Chunking**: Intelligent document segmentation for large files
- **Caching System**: Efficient caching to avoid duplicate processing
- **Comprehensive API**: RESTful API for integration with existing systems

## 📋 Prerequisites

- Python 3.11+
- Node.js 16+ (for frontend development)
- Docker and Docker Compose (optional, for containerized deployment)
- System dependencies:
  - Poppler (for PDF processing)
  - Tesseract (for OCR)

## 🛠️ Quick Start

### Option 1: Automated Setup (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd document-analysis-agent

# Run the setup script
chmod +x setup.sh
./setup.sh
```

### Option 2: Manual Setup

1. **Install System Dependencies**

   On macOS:
   ```bash
   brew install poppler tesseract
   ```

   On Ubuntu/Debian:
   ```bash
   sudo apt-get install poppler-utils tesseract-ocr tesseract-ocr-eng
   ```

2. **Create Virtual Environment**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Python Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up Environment Variables**

   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

5. **Create Required Directories**

   ```bash
   mkdir -p uploads cache logs credentials
   ```

6. **Run the Application**

   ```bash
   python main.py
   ```
    ├── Confidence scoring
    ├── Human verification UI
    └── Error handling
```

### Data Flow

1. **Document Upload** → Validation → Storage
2. **Text Extraction** → PyMuPDF → OCR (if needed)
3. **Chunking** → Legal-aware text segmentation
4. **LLM Processing** → Structured data extraction
5. **Post-processing** → Validation → Confidence scoring
6. **Human Review** → Low-confidence fields flagged
7. **Results** → Structured JSON with metadata

## Installation

### Prerequisites

- Python 3.8+
- Tesseract OCR
- API keys for at least one LLM provider

### System Dependencies

```bash
# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# Windows
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
```

### Python Dependencies

```bash
pip install -r requirements.txt
```

### Directory Setup

```bash
# Create required directories
mkdir -p uploads storage logs credentials
```

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# LLM API Keys (at least one required)
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
DEEPSEEK_API_KEY=your_deepseek_key_here

# File Configuration
PDF_UPLOAD_MAX_SIZE=50000000  # 50MB
PDF_UPLOAD_DIR=./uploads
PDF_STORAGE_DIR=./storage

# Processing Configuration
MAX_PAGES_DEFAULT=10
CHUNK_SIZE_TOKENS=4000
OCR_CONFIDENCE_THRESHOLD=0.9

# Security
SECRET_KEY=your_secret_key_here
CORS_ORIGINS=["http://localhost:3000"]
```

### Provider Configuration

The system automatically detects available LLM providers based on configured API keys:

- **OpenAI**: Best for JSON mode and consistency
- **Anthropic**: Excellent for complex reasoning
- **DeepSeek**: Cost-effective alternative

## Usage

### Starting the Server

```bash
# Development
python -m backend.api.ai_agents

# Production
uvicorn backend.api.ai_agents:app --host 0.0.0.0 --port 8000
```

### Basic Workflow

1. **Upload Document**
```bash
curl -X POST http://localhost:8000/api/documents/upload \
  -F "file=@sample_complaint.pdf" \
  -F "document_type=complaint"
```

2. **Analyze Document**
```bash
curl -X POST http://localhost:8000/api/documents/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "sample_complaint.pdf",
    "extraction_schema": {
      "schema_name": "civil_complaint",
      "fields": {
        "case_number": null,
        "plaintiff_name": null,
        "defendant_names": [],
        "filing_date": null
      },
      "confidence_threshold": 0.85
    }
  }'
```

3. **Review Results**
```bash
curl -X GET http://localhost:8000/api/documents/sample_complaint.pdf/status
```

### Python API Usage

```python
from backend.agents.document_analysis_agent import DocumentAnalysisAgent
from backend.agents.models import DocumentAnalysisRequest, ExtractionSchema

# Initialize agent
agent = DocumentAnalysisAgent()

# Create request
request = DocumentAnalysisRequest(
    document_id="sample_complaint.pdf",
    extraction_schema=ExtractionSchema(
        schema_name="civil_complaint",
        fields={
            "case_number": None,
            "plaintiff_name": None,
            "defendant_names": []
        }
    )
)

# Analyze document
response = await agent.analyze_document(request)

# Review results
for field_name, field_data in response.extracted_data.items():
    print(f"{field_name}: {field_data.value} (confidence: {field_data.confidence_score})")
```

## API Documentation

### Endpoints

#### Document Management
- `POST /api/documents/upload` - Upload PDF document
- `GET /api/documents` - List all documents
- `GET /api/documents/{id}/status` - Get processing status
- `DELETE /api/documents/{id}` - Delete document

#### Analysis
- `POST /api/documents/analyze` - Analyze document
- `POST /api/schemas/validate` - Validate extraction schema

#### System
- `GET /api/system/info` - System information
- `GET /health` - Health check
- `POST /api/cache/clear` - Clear cache

### Request/Response Models

#### DocumentAnalysisRequest
```json
{
  "document_id": "string",
  "extraction_schema": {
    "schema_name": "string",
    "fields": {},
    "confidence_threshold": 0.9
  },
  "process_full_document": false,
  "force_reprocess": false
}
```

#### DocumentAnalysisResponse
```json
{
  "document_id": "string",
  "status": "completed",
  "extracted_data": {
    "field_name": {
      "value": "extracted_value",
      "source_text": "source text from document",
      "confidence_score": 0.95,
      "requires_review": false
    }
  },
  "metadata": {
    "processing_method": "direct_text",
    "processing_duration": 2.5,
    "page_count": 5
  },
  "review_required_count": 1
}
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend --cov-report=html

# Run specific test file
pytest tests/test_document_analysis_agent.py

# Run integration tests
pytest -m integration
```

### Test Structure

```
tests/
├── test_document_analysis_agent.py  # Main agent tests
├── test_pdf_extractor.py           # PDF processing tests
├── test_ocr_processor.py           # OCR tests
├── test_text_chunker.py            # Text chunking tests
├── test_llm_extractor.py           # LLM extraction tests
├── test_api_endpoints.py           # API tests
└── fixtures/                       # Test documents
```

### Validation Checklist

- [ ] PDF text extraction for text-based documents
- [ ] OCR processing for scanned documents
- [ ] Text chunking for large documents
- [ ] LLM extraction with confidence scoring
- [ ] Multi-provider LLM support
- [ ] API endpoints respond correctly
- [ ] Error handling and edge cases
- [ ] Performance benchmarks (<30s for 10 pages)
- [ ] Accuracy targets (>95% on test documents)

## Deployment

### Docker Deployment

```dockerfile
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application
COPY . /app
WORKDIR /app

# Run application
CMD ["uvicorn", "backend.api.ai_agents:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Production Considerations

- **Security**: Use secure API keys and HTTPS
- **Scaling**: Consider Redis for caching, PostgreSQL for persistence
- **Monitoring**: Add logging, metrics, and health checks
- **Rate Limiting**: Implement rate limiting for API endpoints
- **File Storage**: Use cloud storage for production files

## Contributing

### Development Setup

```bash
# Clone repository
git clone <repository-url>
cd context-engineering-intro

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install pre-commit hooks
pre-commit install

# Run tests
pytest
```

### Code Quality

- **Linting**: `ruff check backend/`
- **Formatting**: `black backend/`
- **Type Checking**: `mypy backend/`
- **Testing**: `pytest --cov=backend/`

### Submission Guidelines

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## Resources

- [PyMuPDF Documentation](https://pymupdf.readthedocs.io/)
- [Tesseract OCR Documentation](https://tesseract-ocr.github.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Anthropic API Documentation](https://docs.anthropic.com/)

## License

This project is licensed under the MIT License - see the LICENSE file for details.