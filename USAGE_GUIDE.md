# 🚀 Document Analysis Agent - Usage Guide

## Overview
The Document Analysis Agent is an AI-powered system that extracts structured data from PDF legal documents using LLMs (Large Language Models). It supports both direct Python API usage and a FastAPI web service.

## 🔧 Setup & Installation

### Prerequisites
- Python 3.8+
- OpenAI API key OR Anthropic API key
- Tesseract OCR (for scanned documents)

### Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Install Tesseract OCR (macOS)
brew install tesseract

# Install Tesseract OCR (Ubuntu)
sudo apt-get install tesseract-ocr
```

### Environment Setup
```bash
# Set your API keys (choose one or both)
export OPENAI_API_KEY='sk-your-openai-key-here'
export ANTHROPIC_API_KEY='sk-ant-your-anthropic-key-here'

# Optional: Set other configuration
export LOG_LEVEL=INFO
export MAX_CHUNK_SIZE=4000
export CONFIDENCE_THRESHOLD=0.8
```

## 🌐 Web API Usage (Recommended)

### 1. Start the Server
```bash
python -m uvicorn main:app --reload
```
Server runs at: http://localhost:8000

### 2. Interactive Documentation
Visit: http://localhost:8000/docs for complete API documentation with examples

### 3. Basic API Endpoints

#### Health Check
```bash
curl http://localhost:8000/health
```

#### Upload Document
```bash
curl -X POST http://localhost:8000/documents/upload \
  -F 'file=@your_document.pdf' \
  -F 'extraction_schema={
    "schema_name": "legal_complaint",
    "fields": {
      "case_number": {
        "type": "string",
        "description": "Case number (e.g., CV-2024-001)"
      },
      "plaintiff": {
        "type": "string",
        "description": "Name of the plaintiff"
      },
      "defendant": {
        "type": "string",
        "description": "Name of the defendant"
      }
    }
  }'
```

#### Analyze Document
```bash
curl -X POST http://localhost:8000/documents/analyze \
  -H 'Content-Type: application/json' \
  -d '{
    "document_id": "your_document.pdf",
    "extraction_schema": {
      "schema_name": "legal_complaint",
      "fields": {
        "case_number": {"type": "string", "description": "Case number"},
        "plaintiff": {"type": "string", "description": "Plaintiff name"}
      }
    },
    "process_full_document": true
  }'
```

#### Get Results
```bash
curl http://localhost:8000/documents/your_document.pdf/results
```

## 🐍 Python API Usage

### Basic Example
```python
import asyncio
import os
from backend.agents.document_analysis_agent import DocumentAnalysisAgent
from backend.agents.models import DocumentAnalysisRequest, ExtractionSchema

async def analyze_document():
    # Set API key
    os.environ['OPENAI_API_KEY'] = 'your-key-here'
    
    # Create agent
    agent = DocumentAnalysisAgent()
    
    # Define extraction schema
    schema = ExtractionSchema(
        schema_name="contract_analysis",
        fields={
            "party_1": {
                "type": "string",
                "description": "First party to the contract"
            },
            "effective_date": {
                "type": "string",
                "description": "Contract effective date"
            },
            "payment_amount": {
                "type": "string",
                "description": "Payment amount specified"
            }
        }
    )
    
    # Create request
    request = DocumentAnalysisRequest(
        document_id="contract.pdf",
        extraction_schema=schema,
        process_full_document=True
    )
    
    # Analyze
    try:
        result = await agent.analyze_document(request)
        
        print(f"Status: {result.status}")
        print(f"Document Type: {result.metadata.document_type}")
        
        for field, data in result.extracted_data.items():
            print(f"{field}: {data.value} (confidence: {data.confidence_score:.2f})")
            
    finally:
        await agent.close()

# Run the analysis
asyncio.run(analyze_document())
```

## 📋 Extraction Schema Format

The extraction schema defines what data to extract from documents:

```json
{
  "schema_name": "legal_document",
  "fields": {
    "field_name": {
      "type": "string|number|array|object",
      "description": "Clear description of what to extract"
    }
  },
  "confidence_threshold": 0.8
}
```

### Field Types
- **string**: Text values (names, dates, addresses)
- **number**: Numeric values (amounts, quantities)
- **array**: Lists of items (multiple parties, claims)
- **object**: Structured data (addresses with street, city, state)

### Example Schemas

#### Legal Complaint
```json
{
  "schema_name": "civil_complaint",
  "fields": {
    "case_number": {"type": "string", "description": "Case number"},
    "plaintiff_name": {"type": "string", "description": "Plaintiff name"},
    "defendant_name": {"type": "string", "description": "Defendant name"},
    "court_name": {"type": "string", "description": "Court name"},
    "filing_date": {"type": "string", "description": "Filing date"},
    "damages_amount": {"type": "string", "description": "Damages sought"},
    "causes_of_action": {"type": "array", "description": "Legal claims"}
  }
}
```

#### Contract Analysis
```json
{
  "schema_name": "contract_analysis",
  "fields": {
    "parties": {"type": "array", "description": "All parties to contract"},
    "effective_date": {"type": "string", "description": "Effective date"},
    "termination_date": {"type": "string", "description": "Termination date"},
    "payment_terms": {"type": "string", "description": "Payment terms"},
    "key_obligations": {"type": "array", "description": "Main obligations"}
  }
}
```

#### Retainer Agreement
```json
{
  "schema_name": "retainer_agreement",
  "fields": {
    "client_name": {"type": "string", "description": "Client name"},
    "attorney_firm": {"type": "string", "description": "Law firm name"},
    "hourly_rate": {"type": "string", "description": "Hourly rate"},
    "retainer_amount": {"type": "string", "description": "Retainer fee"},
    "case_type": {"type": "string", "description": "Type of legal matter"},
    "scope_of_work": {"type": "string", "description": "Scope of representation"}
  }
}
```

## 🎯 Response Format

The system returns structured results with confidence scores:

```json
{
  "document_id": "contract.pdf",
  "status": "completed",
  "extracted_data": {
    "field_name": {
      "value": "extracted_value",
      "confidence_score": 0.95,
      "source_text": "source text from document",
      "page_number": 1,
      "requires_review": false
    }
  },
  "metadata": {
    "filename": "contract.pdf",
    "document_type": "contract",
    "page_count": 5,
    "processing_duration": 12.34,
    "processing_method": "direct_text"
  },
  "processing_errors": [],
  "review_required_count": 0
}
```

## 🔍 Features

- **Multi-format Support**: PDF (text-based and scanned)
- **OCR Fallback**: Automatic OCR for scanned documents
- **Smart Chunking**: Intelligent text splitting for large documents
- **Confidence Scoring**: Quality assessment for each extracted field
- **Source Tracking**: Links extracted data to source text
- **Multiple LLM Providers**: OpenAI, Anthropic, DeepSeek support
- **Caching**: Avoids reprocessing identical documents
- **Error Handling**: Comprehensive error reporting

## 🛠️ Advanced Usage

### Custom Configuration
```python
# Custom agent configuration
agent = DocumentAnalysisAgent(
    max_chunk_size=2000,
    confidence_threshold=0.9,
    cache_enabled=True
)
```

### Batch Processing
```python
# Process multiple documents
documents = ["doc1.pdf", "doc2.pdf", "doc3.pdf"]
results = []

for doc in documents:
    request = DocumentAnalysisRequest(
        document_id=doc,
        extraction_schema=schema
    )
    result = await agent.analyze_document(request)
    results.append(result)
```

### Error Handling
```python
try:
    result = await agent.analyze_document(request)
    if result.status == "failed":
        print(f"Processing failed: {result.processing_errors}")
    elif result.review_required_count > 0:
        print(f"Review needed for {result.review_required_count} fields")
except Exception as e:
    print(f"Error: {e}")
```

## 🧪 Testing

Run the test suite:
```bash
pytest tests/ -v
```

Run specific test modules:
```bash
pytest tests/test_document_analysis_agent.py -v
pytest tests/test_pdf_extractor.py -v
pytest tests/test_text_chunker.py -v
```

## 📊 Performance Tips

1. **Use appropriate chunk sizes**: Smaller chunks for better accuracy, larger for speed
2. **Set confidence thresholds**: Higher thresholds for critical extractions
3. **Process key pages only**: Set `process_full_document=False` for faster processing
4. **Cache results**: Enable caching to avoid reprocessing identical documents
5. **Use specific schemas**: More specific field descriptions improve accuracy

## 🚀 Production Deployment

See `docker-compose.yml` and `Dockerfile` for containerized deployment:

```bash
# Build and run with Docker
docker-compose up --build

# Or run directly
docker build -t document-analysis .
docker run -p 8000:8000 -e OPENAI_API_KEY=your-key document-analysis
```

## 📝 Logging

The system provides detailed logging:
```bash
# Set log level
export LOG_LEVEL=DEBUG

# Logs are written to logs/ directory
tail -f logs/document_analysis.log
```

## 🔒 Security

- API keys are handled securely via environment variables
- Uploaded files are stored in designated directories
- Input validation prevents malicious uploads
- Rate limiting prevents abuse

## 🤝 Support

- Check the test files for usage examples
- Review the API documentation at `/docs`
- Enable debug logging for troubleshooting
- Ensure API keys are properly configured
