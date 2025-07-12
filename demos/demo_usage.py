#!/usr/bin/env python3
"""
Quick demo of the Document Analysis Agent
"""
import asyncio
import json
import os
from pathlib import Path

# For real usage, set your actual API keys:
# os.environ['OPENAI_API_KEY'] = 'sk-your-openai-key-here'
# os.environ['ANTHROPIC_API_KEY'] = 'sk-ant-your-anthropic-key-here'

# For demo purposes, use test keys
os.environ['OPENAI_API_KEY'] = 'test-key-demo'
os.environ['ANTHROPIC_API_KEY'] = 'test-key-demo'

from backend.agents.document_analysis_agent import DocumentAnalysisAgent
from backend.agents.models import DocumentAnalysisRequest, ExtractionSchema

def create_sample_document():
    """Create a sample legal document for testing."""
    content = """
SUPERIOR COURT OF CALIFORNIA
COUNTY OF LOS ANGELES

JOHN DOE,                                    Case No.: CV-2024-123456
    Plaintiff,                               Filed: March 15, 2024

vs.

JANE SMITH,
    Defendant.

COMPLAINT FOR DAMAGES

TO THE HONORABLE COURT:

Plaintiff JOHN DOE alleges as follows:

1. JURISDICTION AND VENUE
This Court has jurisdiction over this matter pursuant to California Code of Civil Procedure Section 410.10.

2. PARTIES
Plaintiff JOHN DOE is a resident of Los Angeles County, California.
Defendant JANE SMITH is a resident of Los Angeles County, California.

3. FACTUAL ALLEGATIONS
On or about January 1, 2024, plaintiff and defendant entered into a written contract
for the provision of consulting services. Under the terms of said contract, defendant
agreed to provide business consulting services for a period of six months.

4. BREACH OF CONTRACT
Defendant failed to perform her obligations under the contract by failing to
provide the agreed-upon services. As a result of defendant's breach, plaintiff
has suffered damages in the amount of $50,000.

5. NEGLIGENCE
Defendant owed plaintiff a duty of care in the performance of consulting services.
Defendant breached this duty by failing to exercise reasonable care, resulting
in additional damages of $25,000.

WHEREFORE, plaintiff prays for judgment against defendant as follows:
1. For damages in the amount of $75,000;
2. For costs of suit incurred herein;
3. For attorney's fees;
4. For such other relief as the Court deems just and proper.

Dated: March 15, 2024

                                    _______________________
                                    ROBERT ATTORNEY, ESQ.
                                    State Bar No. 123456
                                    Attorney for Plaintiff
                                    123 Main Street
                                    Los Angeles, CA 90210
                                    Tel: (555) 123-4567
"""
    
    # Create the document
    doc_path = Path("sample_legal_complaint.txt")
    with open(doc_path, "w") as f:
        f.write(content)
    
    print(f"✅ Created sample document: {doc_path}")
    return doc_path

async def demo_document_analysis():
    """Demonstrate the document analysis system."""
    
    print("🚀 Document Analysis Agent Demo")
    print("=" * 50)
    
    # Create sample document
    sample_file = create_sample_document()
    
    # Define what we want to extract
    extraction_schema = ExtractionSchema(
        schema_name="civil_complaint_demo",
        fields={
            "case_number": {
                "type": "string",
                "description": "The case number (e.g., CV-2024-123456)"
            },
            "plaintiff_name": {
                "type": "string",
                "description": "Name of the plaintiff (person filing the lawsuit)"
            },
            "defendant_name": {
                "type": "string", 
                "description": "Name of the defendant (person being sued)"
            },
            "court_name": {
                "type": "string",
                "description": "Name of the court where case is filed"
            },
            "filing_date": {
                "type": "string",
                "description": "Date the complaint was filed"
            },
            "total_damages": {
                "type": "string",
                "description": "Total amount of damages being sought"
            },
            "attorney_name": {
                "type": "string",
                "description": "Name of the attorney representing plaintiff"
            },
            "causes_of_action": {
                "type": "array",
                "description": "List of legal claims (e.g., breach of contract, negligence)"
            }
        }
    )
    
    # Create analysis request
    request = DocumentAnalysisRequest(
        document_id=str(sample_file),
        extraction_schema=extraction_schema,
        process_full_document=True
    )
    
    try:
        print("🔍 Initializing Document Analysis Agent...")
        
        # Note: This will fail without real API keys, but shows the process
        agent = DocumentAnalysisAgent()
        
        print("📄 Analyzing document...")
        print(f"   Document: {sample_file}")
        print(f"   Schema: {extraction_schema.schema_name}")
        print(f"   Fields to extract: {len(extraction_schema.fields)}")
        
        # This would normally perform the analysis
        result = await agent.analyze_document(request)
        
        print(f"✅ Analysis completed!")
        print(f"   Status: {result.status}")
        print(f"   Processing time: {result.metadata.processing_duration:.2f}s")
        
        print("\n📋 Extracted Information:")
        print("-" * 30)
        
        for field_name, field_data in result.extracted_data.items():
            confidence_indicator = "🟢" if field_data.confidence_score > 0.8 else "🟡" if field_data.confidence_score > 0.5 else "🔴"
            print(f"{field_name}: {field_data.value}")
            print(f"   {confidence_indicator} Confidence: {field_data.confidence_score:.1%}")
            if field_data.requires_review:
                print(f"   ⚠️  Requires human review")
            print()
        
        await agent.close()
        return result
        
    except Exception as e:
        print(f"❌ Demo failed: {str(e)}")
        print()
        print("💡 To run with real analysis:")
        print("   1. Set your OpenAI API key: export OPENAI_API_KEY='sk-your-key'")
        print("   2. Or set Anthropic API key: export ANTHROPIC_API_KEY='sk-ant-your-key'")
        print("   3. Run: python test_real_usage.py")
        print()
        print("📋 Expected output format:")
        show_expected_output()
        return None

def show_expected_output():
    """Show what the output would look like with real API keys."""
    print("-" * 30)
    print("case_number: CV-2024-123456")
    print("   🟢 Confidence: 95%")
    print()
    print("plaintiff_name: JOHN DOE")
    print("   🟢 Confidence: 92%")
    print()
    print("defendant_name: JANE SMITH")
    print("   🟢 Confidence: 90%")
    print()
    print("court_name: SUPERIOR COURT OF CALIFORNIA")
    print("   🟢 Confidence: 88%")
    print()
    print("filing_date: March 15, 2024")
    print("   🟢 Confidence: 85%")
    print()
    print("total_damages: $75,000")
    print("   🟡 Confidence: 78%")
    print("   ⚠️  Requires human review")
    print()
    print("attorney_name: ROBERT ATTORNEY, ESQ.")
    print("   🟢 Confidence: 82%")
    print()
    print("causes_of_action: ['breach of contract', 'negligence']")
    print("   🟢 Confidence: 86%")

if __name__ == "__main__":
    asyncio.run(demo_document_analysis())
