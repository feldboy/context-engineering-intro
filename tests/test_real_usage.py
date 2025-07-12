#!/usr/bin/env python3
"""
Real-world test of the Document Analysis Agent
"""
import asyncio
import json
import os
from pathlib import Path

# Set up environment for testing
os.environ['OPENAI_API_KEY'] = 'your-openai-key-here'  # Replace with real key
os.environ['ANTHROPIC_API_KEY'] = 'your-anthropic-key-here'  # Replace with real key

from backend.agents.document_analysis_agent import DocumentAnalysisAgent
from backend.agents.models import DocumentAnalysisRequest, ExtractionSchema

async def test_document_analysis():
    """Test the document analysis agent with a real document."""
    
    # Create the agent
    agent = DocumentAnalysisAgent()
    
    # Define extraction schema for a legal complaint
    schema = ExtractionSchema(
        schema_name="civil_complaint",
        fields={
            "case_number": {
                "type": "string",
                "description": "The case number (e.g., CV-2024-001)"
            },
            "plaintiff_name": {
                "type": "string", 
                "description": "Name of the plaintiff"
            },
            "defendant_name": {
                "type": "string",
                "description": "Name of the defendant"
            },
            "court_name": {
                "type": "string",
                "description": "Name of the court"
            },
            "filing_date": {
                "type": "string",
                "description": "Date the complaint was filed"
            },
            "cause_of_action": {
                "type": "string",
                "description": "Primary cause of action or claim"
            },
            "damages_amount": {
                "type": "string",
                "description": "Amount of damages sought"
            }
        }
    )
    
    # Create analysis request
    request = DocumentAnalysisRequest(
        document_id="sample_complaint.pdf",
        extraction_schema=schema,
        process_full_document=True
    )
    
    try:
        print("🔍 Starting document analysis...")
        
        # Analyze the document
        result = await agent.analyze_document(request)
        
        print(f"✅ Analysis completed with status: {result.status}")
        print(f"📄 Document type detected: {result.metadata.document_type}")
        print(f"⏱️  Processing time: {result.metadata.processing_duration:.2f}s")
        print(f"📊 Pages processed: {result.metadata.page_count}")
        
        print("\n📋 Extracted Data:")
        print("-" * 50)
        
        for field_name, field_data in result.extracted_data.items():
            confidence_emoji = "🟢" if field_data.confidence_score > 0.8 else "🟡" if field_data.confidence_score > 0.5 else "🔴"
            review_needed = "⚠️  REVIEW NEEDED" if field_data.requires_review else ""
            
            print(f"{field_name}: {field_data.value}")
            print(f"  {confidence_emoji} Confidence: {field_data.confidence_score:.2f} {review_needed}")
            if field_data.source_text:
                print(f"  📝 Source: {field_data.source_text[:100]}...")
            print()
        
        # Show processing errors if any
        if result.processing_errors:
            print("⚠️  Processing Errors:")
            for error in result.processing_errors:
                print(f"  - {error}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error during analysis: {str(e)}")
        return None
    
    finally:
        # Clean up
        await agent.close()

def create_sample_pdf():
    """Create a sample PDF for testing."""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        import io
        
        # Create a sample legal complaint PDF
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        
        # Add content
        p.drawString(100, 750, "SUPERIOR COURT OF CALIFORNIA")
        p.drawString(100, 730, "COUNTY OF LOS ANGELES")
        p.drawString(100, 700, "JOHN DOE,")
        p.drawString(150, 680, "Plaintiff,")
        p.drawString(100, 650, "vs.")
        p.drawString(100, 620, "JANE SMITH,")
        p.drawString(150, 600, "Defendant.")
        
        p.drawString(400, 700, "Case No.: CV-2024-123456")
        p.drawString(400, 680, "Filed: March 15, 2024")
        
        p.drawString(100, 550, "COMPLAINT FOR DAMAGES")
        p.drawString(100, 520, "Plaintiff seeks damages in the amount of $50,000")
        p.drawString(100, 500, "for breach of contract and negligence.")
        
        p.showPage()
        p.save()
        
        # Save to file
        pdf_path = Path("sample_complaint.pdf")
        with open(pdf_path, "wb") as f:
            f.write(buffer.getvalue())
        
        print(f"✅ Created sample PDF: {pdf_path}")
        return pdf_path
        
    except ImportError:
        print("📝 reportlab not installed. Creating a simple text file instead...")
        # Create a simple text file that looks like a PDF
        content = """
SUPERIOR COURT OF CALIFORNIA
COUNTY OF LOS ANGELES

JOHN DOE,                                    Case No.: CV-2024-123456
    Plaintiff,                               Filed: March 15, 2024

vs.

JANE SMITH,
    Defendant.

COMPLAINT FOR DAMAGES

Plaintiff seeks damages in the amount of $50,000 
for breach of contract and negligence.

The defendant failed to perform under the agreement
dated January 1, 2024, causing substantial harm
to the plaintiff's business operations.

WHEREFORE, plaintiff prays for judgment against
defendant for damages, costs, and attorney fees.

Dated: March 15, 2024

                    _________________
                    Attorney for Plaintiff
"""
        
        # Save as text file (we'll rename it to .pdf)
        pdf_path = Path("sample_complaint.pdf")
        with open(pdf_path, "w") as f:
            f.write(content)
        
        print(f"✅ Created sample document: {pdf_path}")
        return pdf_path

if __name__ == "__main__":
    print("🚀 Document Analysis Agent - Real World Test")
    print("=" * 50)
    
    # Create sample document
    sample_file = create_sample_pdf()
    
    if sample_file.exists():
        print(f"📄 Using sample document: {sample_file}")
        
        # Run the analysis
        result = asyncio.run(test_document_analysis())
        
        if result:
            print("\n🎉 Analysis completed successfully!")
            print(f"Review required for {result.review_required_count} fields")
        else:
            print("❌ Analysis failed")
    else:
        print("❌ Could not create sample document")
