#!/usr/bin/env python3
"""
How to use the Document Analysis Agent directly in Python
"""
import asyncio
import os
from backend.agents.document_analysis_agent import DocumentAnalysisAgent
from backend.agents.models import DocumentAnalysisRequest, ExtractionSchema

async def analyze_document():
    """Example of direct Python API usage."""
    
    # 1. Set up your API keys
    os.environ['OPENAI_API_KEY'] = 'your-openai-key-here'
    # OR
    # os.environ['ANTHROPIC_API_KEY'] = 'your-anthropic-key-here'
    
    # 2. Create the agent
    agent = DocumentAnalysisAgent()
    
    # 3. Define what you want to extract
    schema = ExtractionSchema(
        schema_name="contract_analysis",
        fields={
            "party_1": {
                "type": "string",
                "description": "First party to the contract"
            },
            "party_2": {
                "type": "string", 
                "description": "Second party to the contract"
            },
            "effective_date": {
                "type": "string",
                "description": "When the contract becomes effective"
            },
            "termination_date": {
                "type": "string",
                "description": "When the contract expires"
            },
            "payment_terms": {
                "type": "string",
                "description": "Payment terms and amounts"
            },
            "key_obligations": {
                "type": "array",
                "description": "Main obligations of each party"
            }
        }
    )
    
    # 4. Create analysis request
    request = DocumentAnalysisRequest(
        document_id="contract.pdf",  # Place your PDF in storage/ directory
        extraction_schema=schema,
        process_full_document=True,
        force_reprocess=False
    )
    
    # 5. Analyze the document
    try:
        result = await agent.analyze_document(request)
        
        print(f"Analysis Status: {result.status}")
        print(f"Document Type: {result.metadata.document_type}")
        print(f"Processing Time: {result.metadata.processing_duration:.2f}s")
        print(f"Pages: {result.metadata.page_count}")
        
        print("\nExtracted Data:")
        for field, data in result.extracted_data.items():
            print(f"  {field}: {data.value}")
            print(f"    Confidence: {data.confidence_score:.2f}")
            if data.requires_review:
                print(f"    ⚠️  Requires Review")
            print()
        
        return result
        
    except Exception as e:
        print(f"Error: {e}")
        return None
    
    finally:
        await agent.close()

if __name__ == "__main__":
    asyncio.run(analyze_document())
