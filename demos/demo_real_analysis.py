"""
Test the Document Analysis Agent with real documents
"""
import asyncio
import json
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

def create_sample_legal_document():
    """Create a sample legal document PDF for testing"""
    filename = "uploads/sample_legal_complaint.pdf"
    
    # Ensure uploads directory exists
    Path("uploads").mkdir(exist_ok=True)
    
    # Create a simple PDF with legal content
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, height - 100, "CIVIL COMPLAINT")
    
    # Case information
    c.setFont("Helvetica", 12)
    y = height - 150
    content = [
        "Case Number: CIV-2024-123456",
        "Court: Superior Court of California",
        "County: Los Angeles",
        "",
        "PLAINTIFF:",
        "John Smith",
        "123 Main Street",
        "Los Angeles, CA 90210",
        "",
        "vs.",
        "",
        "DEFENDANT:",
        "ABC Corporation",
        "456 Business Ave",
        "Los Angeles, CA 90211",
        "",
        "NATURE OF CASE:",
        "This is a breach of contract action arising from defendant's",
        "failure to deliver goods as specified in the purchase agreement",
        "dated March 15, 2024. Plaintiff seeks damages in the amount",
        "of $50,000 plus costs and attorney fees.",
        "",
        "FACTS:",
        "1. On March 15, 2024, plaintiff entered into a written contract",
        "   with defendant for the purchase of industrial equipment.",
        "2. The contract price was $75,000 with delivery scheduled",
        "   for April 30, 2024.",
        "3. Defendant failed to deliver the equipment by the agreed date.",
        "4. Plaintiff has suffered damages as a result of the breach.",
        "",
        "WHEREFORE, plaintiff prays for judgment against defendant for:",
        "1. Damages in the amount of $50,000",
        "2. Costs of suit",
        "3. Attorney fees",
        "4. Such other relief as the court deems just and proper.",
        "",
        "Dated: July 11, 2025",
        "",
        "________________________",
        "Attorney for Plaintiff",
        "State Bar No. 123456"
    ]
    
    for line in content:
        c.drawString(100, y, line)
        y -= 20
        if y < 100:  # Start new page if needed
            c.showPage()
            y = height - 100
    
    c.save()
    print(f"Created sample document: {filename}")
    return filename

async def test_document_analysis():
    """Test the document analysis with a real document"""
    from backend.agents.document_analysis_agent import DocumentAnalysisAgent
    from backend.agents.models import DocumentAnalysisRequest, ExtractionSchema
    import shutil
    
    # Create sample document
    pdf_path = create_sample_legal_document()
    
    # Ensure storage directory exists and copy the file there
    storage_path = f"storage/{pdf_path}"
    Path("storage").mkdir(exist_ok=True)
    Path("storage/uploads").mkdir(exist_ok=True)
    shutil.copy(pdf_path, storage_path)
    
    # Create the agent with preferred provider
    agent = DocumentAnalysisAgent()
    # Use Anthropic as the preferred provider since we have that API key
    agent.llm_extractor.preferred_provider = "anthropic"
    
    # Define extraction schema for legal complaint
    schema = ExtractionSchema(
        schema_name="legal_complaint",
        fields={
            "case_number": {
                "type": "string", 
                "description": "The court case number"
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
            "damages_amount": {
                "type": "string",
                "description": "Amount of damages sought"
            },
            "contract_date": {
                "type": "string",
                "description": "Date the contract was signed"
            },
            "attorney_bar_number": {
                "type": "string",
                "description": "Attorney's state bar number"
            }
        },
        confidence_threshold=0.8
    )
    
    # Create analysis request
    request = DocumentAnalysisRequest(
        document_id=pdf_path,  # Use the original path as document_id
        extraction_schema=schema,
        process_full_document=True
    )
    
    print(f"🔍 Analyzing document: {pdf_path}")
    print(f"📋 Extraction schema: {schema.schema_name}")
    print("=" * 50)
    
    try:
        # Analyze the document
        result = await agent.analyze_document(request)
        
        print("✅ Analysis completed successfully!")
        print(f"📊 Status: {result.status}")
        print(f"📄 Document: {result.document_id}")
        print(f"📈 Processing time: {result.metadata.processing_duration:.2f}s")
        print(f"📝 Total pages: {result.metadata.page_count}")
        print(f"🔤 Total characters: {result.metadata.total_characters}")
        print(f"⚡ Processing method: {result.metadata.processing_method}")
        
        if result.processing_errors:
            print(f"⚠️  Processing errors: {result.processing_errors}")
        
        print("\n🎯 EXTRACTED DATA:")
        print("=" * 50)
        
        for field_name, field_data in result.extracted_data.items():
            confidence_emoji = "🟢" if field_data.confidence_score >= 0.9 else "🟡" if field_data.confidence_score >= 0.7 else "🔴"
            review_flag = " ⚠️ NEEDS REVIEW" if field_data.requires_review else ""
            
            print(f"{confidence_emoji} {field_name.upper()}:")
            print(f"   Value: {field_data.value}")
            print(f"   Confidence: {field_data.confidence_score:.2f}")
            if field_data.source_text:
                print(f"   Source: {field_data.source_text[:100]}...")
            if field_data.page_number:
                print(f"   Page: {field_data.page_number}")
            print(f"   {review_flag}")
            print()
        
        print(f"📋 Fields requiring review: {result.review_required_count}")
        
        # Close the agent
        await agent.close()
        
    except Exception as e:
        print(f"❌ Error during analysis: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Document Analysis Agent Demo")
    print("=" * 50)
    asyncio.run(test_document_analysis())
