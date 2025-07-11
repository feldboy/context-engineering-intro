"""
Example usage of the Document Analysis Agent.

This script demonstrates how to use the AI-powered document analysis system
to extract structured data from PDF legal documents.
"""

import asyncio
import json
from pathlib import Path

from backend.agents.document_analysis_agent import DocumentAnalysisAgent
from backend.agents.models import DocumentAnalysisRequest, ExtractionSchema
from backend.config.settings import settings


async def main():
    """Example usage of the document analysis system."""
    
    # Initialize the agent
    agent = DocumentAnalysisAgent()
    
    try:
        # Define extraction schema for a civil complaint
        complaint_schema = ExtractionSchema(
            schema_name="civil_complaint",
            fields={
                "case_number": None,
                "court_name": None,
                "filing_date": None,
                "plaintiff_name": None,
                "defendant_names": [],
                "case_type": None,
                "attorney_name": None,
                "attorney_bar_number": None
            },
            confidence_threshold=0.85
        )
        
        # Create analysis request
        request = DocumentAnalysisRequest(
            document_id="sample_complaint.pdf",  # This would be uploaded via API
            extraction_schema=complaint_schema,
            process_full_document=False,  # Only first 10 pages
            force_reprocess=False
        )
        
        print("Starting document analysis...")
        print(f"Document ID: {request.document_id}")
        print(f"Schema: {request.extraction_schema.schema_name}")
        print(f"Fields to extract: {list(request.extraction_schema.fields.keys())}")
        print("-" * 50)
        
        # Perform analysis
        response = await agent.analyze_document(request)
        
        # Display results
        print(f"Analysis Status: {response.status}")
        print(f"Processing Method: {response.metadata.processing_method}")
        print(f"Document Type: {response.metadata.document_type}")
        print(f"Pages Processed: {response.metadata.page_count}")
        print(f"Processing Time: {response.metadata.processing_duration:.2f} seconds")
        
        if response.chunk_count:
            print(f"Text Chunks: {response.chunk_count}")
        
        print(f"Fields Requiring Review: {response.review_required_count}")
        print("-" * 50)
        
        # Display extracted data
        print("EXTRACTED DATA:")
        for field_name, field_data in response.extracted_data.items():
            print(f"\n{field_name.upper()}:")
            print(f"  Value: {field_data.value}")
            print(f"  Confidence: {field_data.confidence_score:.2f}")
            print(f"  Requires Review: {field_data.requires_review}")
            if field_data.source_text:
                print(f"  Source: {field_data.source_text[:100]}{'...' if len(field_data.source_text) > 100 else ''}")
        
        # Display any errors
        if response.processing_errors:
            print("\nPROCESSING ERRORS:")
            for error in response.processing_errors:
                print(f"  - {error}")
        
        # Example of how to save results to JSON
        results_dict = {
            "document_id": response.document_id,
            "status": response.status,
            "metadata": {
                "filename": response.metadata.filename,
                "document_type": response.metadata.document_type,
                "processing_method": response.metadata.processing_method,
                "processing_duration": response.metadata.processing_duration,
                "page_count": response.metadata.page_count
            },
            "extracted_data": {
                field_name: {
                    "value": field.value,
                    "confidence_score": field.confidence_score,
                    "requires_review": field.requires_review,
                    "source_text": field.source_text
                }
                for field_name, field in response.extracted_data.items()
            },
            "review_required_count": response.review_required_count
        }
        
        # Save to file
        output_file = Path("analysis_results.json")
        with open(output_file, 'w') as f:
            json.dump(results_dict, f, indent=2, default=str)
        
        print(f"\nResults saved to: {output_file}")
        
    except Exception as e:
        print(f"Error during analysis: {str(e)}")
        
    finally:
        # Clean up
        await agent.close()


def example_api_usage():
    """Example of how to use the API endpoints."""
    
    print("API Usage Examples:")
    print("=" * 50)
    
    # Upload document
    print("1. Upload Document:")
    print("   curl -X POST http://localhost:8000/api/documents/upload \\")
    print("     -F 'file=@sample_complaint.pdf' \\")
    print("     -F 'document_type=complaint'")
    print()
    
    # Analyze document
    print("2. Analyze Document:")
    print("   curl -X POST http://localhost:8000/api/documents/analyze \\")
    print("     -H 'Content-Type: application/json' \\")
    print("     -d '{")
    print("       \"document_id\": \"sample_complaint.pdf\",")
    print("       \"extraction_schema\": {")
    print("         \"schema_name\": \"civil_complaint\",")
    print("         \"fields\": {")
    print("           \"case_number\": null,")
    print("           \"plaintiff_name\": null,")
    print("           \"defendant_names\": []")
    print("         }")
    print("       }")
    print("     }'")
    print()
    
    # Get document status
    print("3. Get Document Status:")
    print("   curl -X GET http://localhost:8000/api/documents/sample_complaint.pdf/status")
    print()
    
    # List documents
    print("4. List Documents:")
    print("   curl -X GET http://localhost:8000/api/documents")
    print()
    
    # System info
    print("5. System Information:")
    print("   curl -X GET http://localhost:8000/api/system/info")


def example_schema_templates():
    """Example extraction schema templates for different document types."""
    
    schemas = {
        "civil_complaint": {
            "schema_name": "civil_complaint",
            "fields": {
                "case_number": None,
                "court_name": None,
                "filing_date": None,
                "plaintiff_name": None,
                "defendant_names": [],
                "case_type": None,
                "cause_of_action": None,
                "damages_requested": None,
                "attorney_name": None,
                "attorney_bar_number": None,
                "attorney_firm": None
            },
            "confidence_threshold": 0.85
        },
        
        "retainer_agreement": {
            "schema_name": "retainer_agreement",
            "fields": {
                "client_name": None,
                "attorney_name": None,
                "attorney_firm": None,
                "case_description": None,
                "hourly_rate": None,
                "retainer_amount": None,
                "payment_terms": None,
                "agreement_date": None,
                "client_signature_date": None,
                "attorney_signature_date": None
            },
            "confidence_threshold": 0.90
        },
        
        "medical_records": {
            "schema_name": "medical_records",
            "fields": {
                "patient_name": None,
                "patient_dob": None,
                "medical_record_number": None,
                "provider_name": None,
                "date_of_service": None,
                "diagnosis": [],
                "treatment": [],
                "medications": [],
                "doctor_name": None,
                "follow_up_required": None
            },
            "confidence_threshold": 0.90
        }
    }
    
    print("Schema Templates:")
    print("=" * 50)
    
    for schema_name, schema in schemas.items():
        print(f"\n{schema_name.upper()}:")
        print(json.dumps(schema, indent=2))


if __name__ == "__main__":
    print("Document Analysis Agent - Usage Examples")
    print("=" * 50)
    
    # Show API usage examples
    example_api_usage()
    print()
    
    # Show schema templates
    example_schema_templates()
    print()
    
    # Run the main example (if you have a sample PDF)
    print("To run the analysis example:")
    print("python examples/usage_example.py")
    print()
    print("Note: Make sure to:")
    print("1. Set up your API keys in .env file")
    print("2. Have a sample PDF in the storage directory")
    print("3. Install required dependencies: pip install -r requirements.txt")
