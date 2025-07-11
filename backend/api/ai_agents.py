from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from typing import List, Optional
import aiofiles
import os
from pathlib import Path
import uuid
from datetime import datetime
import logging
from ..config.settings import settings
from ..agents.document_analysis_agent import DocumentAnalysisAgent
from ..agents.models import (
    DocumentAnalysisRequest, 
    DocumentAnalysisResponse, 
    ExtractionSchema,
    ProcessingStatus,
    DocumentType
)
from .dependencies import get_document_analysis_agent
from .pdf_routes import router as pdf_router
from pydantic import BaseModel

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Document Analysis API",
    description="AI-powered PDF document analysis and structured data extraction",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include PDF processing routes
app.include_router(pdf_router)

# Global agent instance (in production, use dependency injection)
agent = DocumentAnalysisAgent()

# Background tasks for processing
processing_tasks = {}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    document_type: Optional[str] = None
):
    """
    Upload a PDF document for analysis.
    
    Args:
        file: PDF file to upload
        document_type: Optional document type hint
        
    Returns:
        Upload confirmation with document ID
    """
    try:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400, 
                detail="Only PDF files are supported"
            )
        
        # Validate file size
        if file.size > settings.pdf_upload_max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds limit of {settings.pdf_upload_max_size} bytes"
            )
        
        # Generate unique document ID
        document_id = f"{uuid.uuid4()}_{file.filename}"
        
        # Save file to storage
        storage_path = Path(settings.pdf_storage_dir) / document_id
        
        async with aiofiles.open(storage_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)
        
        logger.info("Document uploaded successfully: %s", document_id)
        
        return {
            "document_id": document_id,
            "filename": file.filename,
            "size": file.size,
            "document_type": document_type,
            "upload_timestamp": datetime.now().isoformat(),
            "status": "uploaded"
        }
        
    except Exception as e:
        logger.error("Error uploading document: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.post("/api/documents/analyze", response_model=DocumentAnalysisResponse)
async def analyze_document(
    request: DocumentAnalysisRequest,
    background_tasks: BackgroundTasks
):
    """
    Analyze a document and extract structured data.
    
    Args:
        request: Document analysis request
        background_tasks: FastAPI background tasks
        
    Returns:
        Document analysis response
    """
    try:
        # Validate document exists
        document_path = Path(settings.pdf_storage_dir) / request.document_id
        if not document_path.exists():
            raise HTTPException(
                status_code=404, 
                detail=f"Document not found: {request.document_id}"
            )
        
        # For long-running tasks, you might want to process in background
        # For now, process synchronously
        response = await agent.analyze_document(request)
        
        logger.info("Document analysis completed for: %s", request.document_id)
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error analyzing document %s: %s", request.document_id, str(e))
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/api/documents/{document_id}/status")
async def get_document_status(document_id: str):
    """
    Get the processing status of a document.
    
    Args:
        document_id: Document identifier
        
    Returns:
        Document processing status
    """
    try:
        status = await agent.get_document_status(document_id)
        
        if status is None:
            raise HTTPException(
                status_code=404, 
                detail=f"Document not found or not processed: {document_id}"
            )
        
        return {
            "document_id": document_id,
            "status": status,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting document status: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")


@app.get("/api/documents")
async def list_documents():
    """
    List all uploaded documents.
    
    Returns:
        List of document information
    """
    try:
        storage_path = Path(settings.pdf_storage_dir)
        documents = []
        
        for file_path in storage_path.glob("*.pdf"):
            stat = file_path.stat()
            documents.append({
                "document_id": file_path.name,
                "filename": file_path.name.split('_', 1)[1] if '_' in file_path.name else file_path.name,
                "size": stat.st_size,
                "upload_timestamp": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        
        return {
            "documents": documents,
            "total_count": len(documents)
        }
        
    except Exception as e:
        logger.error("Error listing documents: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")


@app.delete("/api/documents/{document_id}")
async def delete_document(document_id: str):
    """
    Delete a document from storage.
    
    Args:
        document_id: Document identifier
        
    Returns:
        Deletion confirmation
    """
    try:
        document_path = Path(settings.pdf_storage_dir) / document_id
        
        if not document_path.exists():
            raise HTTPException(
                status_code=404, 
                detail=f"Document not found: {document_id}"
            )
        
        # Delete the file
        os.remove(document_path)
        
        logger.info("Document deleted: %s", document_id)
        
        return {
            "document_id": document_id,
            "status": "deleted",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting document: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}")


@app.post("/api/schemas/validate")
async def validate_extraction_schema(schema: ExtractionSchema):
    """
    Validate an extraction schema.
    
    Args:
        schema: Extraction schema to validate
        
    Returns:
        Validation result
    """
    try:
        # Schema validation is done by Pydantic automatically
        return {
            "schema_name": schema.schema_name,
            "field_count": len(schema.fields),
            "confidence_threshold": schema.confidence_threshold,
            "status": "valid"
        }
        
    except Exception as e:
        logger.error("Error validating schema: %s", str(e))
        raise HTTPException(status_code=400, detail=f"Schema validation failed: {str(e)}")


@app.get("/api/system/info")
async def get_system_info():
    """
    Get system information and configuration.
    
    Returns:
        System information
    """
    try:
        from ..agents.providers import provider_config
        
        validation_report = provider_config.validate_configuration()
        
        return {
            "system_status": "operational",
            "available_providers": validation_report["valid_providers"],
            "total_providers": validation_report["total_available"],
            "max_file_size": settings.pdf_upload_max_size,
            "max_pages_default": settings.max_pages_default,
            "chunk_size_tokens": settings.chunk_size_tokens,
            "supported_document_types": [dt.value for dt in DocumentType],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("Error getting system info: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get system info: {str(e)}")


@app.post("/api/cache/clear")
async def clear_cache():
    """
    Clear the analysis cache.
    
    Returns:
        Cache clear confirmation
    """
    try:
        await agent.clear_cache()
        
        return {
            "status": "cache_cleared",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("Error clearing cache: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")


@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info("Document Analysis API starting up...")
    
    # Ensure storage directories exist
    os.makedirs(settings.pdf_upload_dir, exist_ok=True)
    os.makedirs(settings.pdf_storage_dir, exist_ok=True)
    
    # Validate LLM provider configuration
    from ..agents.providers import provider_config
    validation_report = provider_config.validate_configuration()
    
    if validation_report["total_available"] == 0:
        logger.warning("No LLM providers configured! Please set API keys.")
    else:
        logger.info("Available LLM providers: %s", validation_report["valid_providers"])


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("Document Analysis API shutting down...")
    await agent.close()


class QAMatchRequest(BaseModel):
    """Request model for question-answer matching."""
    questions_document: str
    answers_document: str

@app.post("/api/documents/match-qa")
async def match_questions_answers(request: QAMatchRequest):
    """Match questions from one document with answers from another."""
    try:
        logger.info(f"Matching Q&A for documents: {request.questions_document} & {request.answers_document}")
        
        # First, analyze the questions document
        questions_schema = ExtractionSchema(
            schema_name="questions_extraction",
            fields={
                "questions": {
                    "type": "array",
                    "description": "List of all questions found in the document. Extract each question as a separate item."
                },
                "question_numbers": {
                    "type": "array",
                    "description": "Question numbers, identifiers, or labels (e.g., 1, 2, 3 or Q1, Q2, etc.)"
                },
                "question_topics": {
                    "type": "array",
                    "description": "Brief topic or subject of each question"
                }
            }
        )
        
        questions_request = DocumentAnalysisRequest(
            document_id=request.questions_document,
            extraction_schema=questions_schema,
            process_full_document=True
        )
        
        questions_result = await agent.analyze_document(questions_request)
        
        # Then analyze the answers document
        answers_schema = ExtractionSchema(
            schema_name="answers_extraction", 
            fields={
                "answers": {
                    "type": "array",
                    "description": "List of all answers found in the document. Extract each complete answer."
                },
                "answer_numbers": {
                    "type": "array",
                    "description": "Answer numbers, identifiers, or labels that correspond to questions"
                },
                "answer_topics": {
                    "type": "array",
                    "description": "Topics or subjects that each answer addresses"
                }
            }
        )
        
        answers_request = DocumentAnalysisRequest(
            document_id=request.answers_document,
            extraction_schema=answers_schema,
            process_full_document=True
        )
        
        answers_result = await agent.analyze_document(answers_request)
        
        # Extract the data
        questions_data = questions_result.extracted_data
        answers_data = answers_result.extracted_data
        
        # Parse the extracted arrays
        questions = []
        answers = []
        
        if "questions" in questions_data and questions_data["questions"].value:
            # Handle both string and list formats
            if isinstance(questions_data["questions"].value, str):
                questions = [q.strip() for q in questions_data["questions"].value.split('\n') if q.strip()]
            else:
                questions = questions_data["questions"].value
                
        if "answers" in answers_data and answers_data["answers"].value:
            if isinstance(answers_data["answers"].value, str):
                answers = [a.strip() for a in answers_data["answers"].value.split('\n') if a.strip()]
            else:
                answers = answers_data["answers"].value
        
        # Simple matching algorithm - match by position or content similarity
        matched_qa = []
        unmatched_questions = []
        unmatched_answers = []
        
        # Match by position first (assuming same order)
        max_pairs = min(len(questions), len(answers))
        
        for i in range(max_pairs):
            question = questions[i]
            answer = answers[i]
            
            # Calculate a simple confidence based on length and content
            question_confidence = min(1.0, len(question) / 50)  # Longer questions get higher confidence
            match_confidence = 0.9 if i < max_pairs else 0.5  # Position-based matching gets high confidence
            
            matched_qa.append({
                "question_number": i + 1,
                "question": question,
                "answer": answer,
                "question_confidence": question_confidence,
                "match_confidence": match_confidence
            })
        
        # Add unmatched items
        if len(questions) > max_pairs:
            unmatched_questions = questions[max_pairs:]
            
        if len(answers) > max_pairs:
            unmatched_answers = answers[max_pairs:]
        
        response_data = {
            "status": "success",
            "total_questions": len(questions),
            "total_answers": len(answers),
            "matched_pairs": len(matched_qa),
            "matched_qa": matched_qa,
            "unmatched_questions": unmatched_questions,
            "unmatched_answers": unmatched_answers,
            "processing_details": {
                "questions_processing_time": questions_result.metadata.processing_duration,
                "answers_processing_time": answers_result.metadata.processing_duration,
                "questions_confidence": questions_data.get("questions", {}).confidence_score if "questions" in questions_data else 0,
                "answers_confidence": answers_data.get("answers", {}).confidence_score if "answers" in answers_data else 0
            },
            "questions_document_path": str(Path(settings.pdf_storage_dir) / request.questions_document),
            "can_generate_pdf": True
        }
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error matching Q&A: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Q&A matching failed: {str(e)}")


@app.post("/api/documents/generate-filled-pdf")
async def generate_filled_pdf(request: QAMatchRequest):
    """Generate a PDF with questions filled with answers."""
    try:
        logger.info(f"Generating filled PDF for: {request.questions_document}")
        
        # First, get the matched Q&A data
        qa_response = await match_questions_answers(request)
        
        # Get the questions document path
        questions_pdf_path = Path(settings.pdf_storage_dir) / request.questions_document
        
        if not questions_pdf_path.exists():
            raise HTTPException(status_code=404, detail="Questions document not found")
        
        # Import PDF processing tools
        from ..tools.pdf_form_analyzer import PDFFormAnalyzer
        from ..tools.pdf_fill_service import PDFFillerService, AnswerData
        from ..tools.coordinate_mapper import CoordinateMapper
        
        # Initialize services
        form_analyzer = PDFFormAnalyzer()
        pdf_filler = PDFFillerService()
        coordinate_mapper = CoordinateMapper()
        
        # Analyze the PDF form structure
        form_structure = await form_analyzer.analyze_pdf_form(str(questions_pdf_path))
        
        # Convert matched Q&A to AnswerData objects
        answer_objects = []
        for qa_pair in qa_response["matched_qa"]:
            answer_obj = AnswerData(
                question_id=str(qa_pair["question_number"]),
                answer_text=qa_pair["answer"],
                confidence=qa_pair["match_confidence"],
                source_text=qa_pair["question"]
            )
            answer_objects.append(answer_obj)
        
        # Create output filename
        base_name = Path(request.questions_document).stem
        output_filename = f"{base_name}_completed.pdf"
        
        # Create temporary output file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as output_file:
            output_path = output_file.name
        
        # Fill the PDF
        filled_pdf_path = await pdf_filler.fill_pdf_with_answers(
            str(questions_pdf_path), form_structure, answer_objects, output_path
        )
        
        # Return the filled PDF
        return FileResponse(
            path=filled_pdf_path,
            filename=output_filename,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={output_filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error generating filled PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")
        questions = []
        answers = []
        
        if "questions" in questions_data and questions_data["questions"].value:
            # Handle both string and list formats
            if isinstance(questions_data["questions"].value, str):
                questions = [q.strip() for q in questions_data["questions"].value.split('\n') if q.strip()]
            else:
                questions = questions_data["questions"].value
                
        if "answers" in answers_data and answers_data["answers"].value:
            if isinstance(answers_data["answers"].value, str):
                answers = [a.strip() for a in answers_data["answers"].value.split('\n') if a.strip()]
            else:
                answers = answers_data["answers"].value
        
        # Simple matching algorithm - match by position or content similarity
        matched_qa = []
        unmatched_questions = []
        unmatched_answers = []
        
        # Match by position first (assuming same order)
        max_pairs = min(len(questions), len(answers))
        
        for i in range(max_pairs):
            question = questions[i]
            answer = answers[i]
            
            # Calculate a simple confidence based on length and content
            question_confidence = min(1.0, len(question) / 50)  # Longer questions get higher confidence
            match_confidence = 0.9 if i < max_pairs else 0.5  # Position-based matching gets high confidence
            
            matched_qa.append({
                "question_number": i + 1,
                "question": question,
                "answer": answer,
                "question_confidence": question_confidence,
                "match_confidence": match_confidence
            })
        
        # Add unmatched items
        if len(questions) > max_pairs:
            unmatched_questions = questions[max_pairs:]
            
        if len(answers) > max_pairs:
            unmatched_answers = answers[max_pairs:]
        
        return {
            "status": "success",
            "total_questions": len(questions),
            "total_answers": len(answers),
            "matched_pairs": len(matched_qa),
            "matched_qa": matched_qa,
            "unmatched_questions": unmatched_questions,
            "unmatched_answers": unmatched_answers,
            "processing_details": {
                "questions_processing_time": questions_result.metadata.processing_duration,
                "answers_processing_time": answers_result.metadata.processing_duration,
                "questions_confidence": questions_data.get("questions", {}).confidence_score if "questions" in questions_data else 0,
                "answers_confidence": answers_data.get("answers", {}).confidence_score if "answers" in answers_data else 0
            }
        }
        
    except Exception as e:
        logger.error(f"Error matching Q&A: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Q&A matching failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
