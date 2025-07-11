#!/usr/bin/env python3
"""
FastAPI Web Service Demo
"""
import uvicorn
import json
from pathlib import Path

# For real usage, set your actual API keys:
# export OPENAI_API_KEY='sk-your-openai-key-here'
# export ANTHROPIC_API_KEY='sk-ant-your-anthropic-key-here'

def create_sample_document():
    """Create a sample document for the web API demo."""
    content = """
RETAINER AGREEMENT

Client: ACME Corporation
Attorney: Smith & Associates Law Firm
Case: Business Litigation Matter
Date: July 11, 2025

This Retainer Agreement is entered into between ACME Corporation (Client) 
and Smith & Associates Law Firm (Attorney) for legal representation in 
connection with a business litigation matter.

SCOPE OF REPRESENTATION:
Attorney agrees to represent Client in litigation against XYZ Company 
regarding breach of contract claims totaling approximately $150,000.

FEES:
- Hourly rate: $350 per hour for partners
- Hourly rate: $200 per hour for associates  
- Retainer amount: $25,000 (due upon signing)

TERM:
This agreement shall remain in effect until the matter is resolved
or either party terminates the representation.

Client Signature: _________________ Date: July 11, 2025
Attorney Signature: _______________ Date: July 11, 2025
"""
    
    # Create uploads directory if it doesn't exist
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(exist_ok=True)
    
    # Save the document
    doc_path = uploads_dir / "sample_retainer.txt"
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"✅ Created sample document: {doc_path}")
    return doc_path

def show_web_api_usage():
    """Show how to use the web API."""
    print("🌐 FastAPI Web Service Usage")
    print("=" * 50)
    
    # Create sample document
    sample_file = create_sample_document()
    
    print("\n📚 How to use the Web API:")
    print("-" * 30)
    
    print("1. Start the server:")
    print("   python -m uvicorn main:app --reload")
    print("   Server will run at: http://localhost:8000")
    print()
    
    print("2. View API documentation:")
    print("   Open: http://localhost:8000/docs")
    print("   This shows all available endpoints with examples")
    print()
    
    print("3. Health check:")
    print("   GET http://localhost:8000/health")
    print()
    
    print("4. Upload a document:")
    print("   POST http://localhost:8000/documents/upload")
    print("   - Upload file as multipart/form-data")
    print("   - Include extraction schema in request")
    print()
    
    print("5. Analyze document:")
    print("   POST http://localhost:8000/documents/analyze")
    print()
    
    print("6. Get results:")
    print("   GET http://localhost:8000/documents/{document_id}/results")
    print()
    
    print("📋 Example API calls:")
    print("-" * 20)
    
    # Example schema for retainer agreement
    schema = {
        "schema_name": "retainer_agreement",
        "fields": {
            "client_name": {
                "type": "string",
                "description": "Name of the client"
            },
            "attorney_firm": {
                "type": "string", 
                "description": "Name of the law firm"
            },
            "hourly_rate": {
                "type": "string",
                "description": "Attorney hourly rate"
            },
            "retainer_amount": {
                "type": "string",
                "description": "Retainer fee amount"
            },
            "case_type": {
                "type": "string",
                "description": "Type of legal matter"
            },
            "signing_date": {
                "type": "string",
                "description": "Date the agreement was signed"
            }
        }
    }
    
    print("Upload document with schema:")
    print("curl -X POST http://localhost:8000/documents/upload \\")
    print("  -F 'file=@sample_retainer.txt' \\")
    print("  -F 'extraction_schema=" + json.dumps(schema, indent=2) + "'")
    print()
    
    print("Analyze document:")
    print("curl -X POST http://localhost:8000/documents/analyze \\")
    print("  -H 'Content-Type: application/json' \\")
    print("  -d '{")
    print("    \"document_id\": \"sample_retainer.txt\",")
    print("    \"extraction_schema\": " + json.dumps(schema) + ",")
    print("    \"process_full_document\": true")
    print("  }'")
    print()
    
    print("Get results:")
    print("curl http://localhost:8000/documents/sample_retainer.txt/results")
    print()
    
    print("💡 Tips:")
    print("- Set API keys as environment variables before starting")
    print("- Use the /docs endpoint for interactive testing")
    print("- Check /health for system status")
    print("- Files are stored in the uploads/ directory")

def start_server():
    """Start the FastAPI server."""
    print("🚀 Starting FastAPI server...")
    print("📖 API docs will be available at: http://localhost:8000/docs")
    print("⚡ Press Ctrl+C to stop the server")
    print()
    
    # Import and run the FastAPI app
    from main import app
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        start_server()
    else:
        show_web_api_usage()
