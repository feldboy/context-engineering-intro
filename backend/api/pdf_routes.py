"""
PDF Routes - API endpoints for PDF generation and filling
"""
from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from fastapi.responses import FileResponse
from typing import List, Dict, Optional
import tempfile
import json
import logging
from pathlib import Path
from ..tools.pdf_form_analyzer import PDFFormAnalyzer
from ..tools.pdf_fill_service import PDFFillerService, AnswerData
from ..tools.coordinate_mapper import CoordinateMapper
from ..config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pdf", tags=["PDF Processing"])

# Initialize services
form_analyzer = PDFFormAnalyzer()
pdf_filler = PDFFillerService()
coordinate_mapper = CoordinateMapper()


@router.post("/analyze-form")
async def analyze_pdf_form(file: UploadFile = File(...)):
    """
    Analyze a PDF form to extract structure and question positions
    
    Args:
        file: PDF file to analyze
        
    Returns:
        Form structure information
    """
    try:
        # Validate file type
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Analyze the PDF form
            form_structure = await form_analyzer.analyze_pdf_form(temp_file_path)
            
            # Get form summary
            summary = form_analyzer.get_form_summary(form_structure)
            
            # Prepare response
            response = {
                "filename": file.filename,
                "form_structure": {
                    "total_pages": form_structure.total_pages,
                    "total_fields": len(form_structure.form_fields),
                    "has_fillable_fields": form_structure.has_fillable_fields,
                    "page_dimensions": form_structure.page_dimensions,
                    "fields": [
                        {
                            "field_id": field.field_id,
                            "question_text": field.question_text,
                            "position": field.position,
                            "page_number": field.page_number,
                            "field_type": field.field_type,
                            "answer_area": field.answer_area
                        }
                        for field in form_structure.form_fields
                    ]
                },
                "summary": summary,
                "analysis_status": "success"
            }
            
            return response
            
        finally:
            # Clean up temporary file
            Path(temp_file_path).unlink(missing_ok=True)
            
    except Exception as e:
        logger.error(f"Error analyzing PDF form: {str(e)}")
        raise HTTPException(status_code=500, detail=f"PDF analysis failed: {str(e)}")


@router.post("/fill-form")
async def fill_pdf_form(
    file: UploadFile = File(...),
    answers: str = Form(...),
    output_filename: Optional[str] = Form(None)
):
    """
    Fill a PDF form with provided answers
    
    Args:
        file: Original PDF file
        answers: JSON string containing answers
        output_filename: Optional custom filename for output
        
    Returns:
        Filled PDF file
    """
    try:
        # Validate inputs
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Parse answers
        try:
            answers_data = json.loads(answers)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON format for answers")
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Analyze the PDF form structure
            form_structure = await form_analyzer.analyze_pdf_form(temp_file_path)
            
            # Convert answers to AnswerData objects
            answer_objects = []
            for answer_dict in answers_data:
                answer_obj = AnswerData(
                    question_id=answer_dict.get("question_id", ""),
                    answer_text=answer_dict.get("answer", ""),
                    confidence=answer_dict.get("confidence", 1.0),
                    source_text=answer_dict.get("source_text", "")
                )
                answer_objects.append(answer_obj)
            
            # Create output filename
            if not output_filename:
                base_name = Path(file.filename).stem
                output_filename = f"{base_name}_filled.pdf"
            
            # Create temporary output file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as output_file:
                output_path = output_file.name
            
            # Fill the PDF
            filled_pdf_path = await pdf_filler.fill_pdf_with_answers(
                temp_file_path, form_structure, answer_objects, output_path
            )
            
            # Return the filled PDF
            return FileResponse(
                path=filled_pdf_path,
                filename=output_filename,
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename={output_filename}"}
            )
            
        finally:
            # Clean up temporary input file
            Path(temp_file_path).unlink(missing_ok=True)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error filling PDF form: {str(e)}")
        raise HTTPException(status_code=500, detail=f"PDF filling failed: {str(e)}")


@router.post("/generate-qa-pdf")
async def generate_qa_pdf(
    questions_file: UploadFile = File(...),
    answers_data: str = Form(...)
):
    """
    Generate a PDF with questions and answers filled in
    
    Args:
        questions_file: PDF file containing questions
        answers_data: JSON string containing matched Q&A pairs
        
    Returns:
        PDF file with answers filled in
    """
    try:
        # Validate inputs
        if not questions_file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Parse answers data
        try:
            qa_data = json.loads(answers_data)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON format for answers")
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            content = await questions_file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Analyze the PDF form structure
            form_structure = await form_analyzer.analyze_pdf_form(temp_file_path)
            
            # Extract matched Q&A pairs
            matched_qa = qa_data.get("matched_qa", [])
            
            # Map questions to positions
            positions = coordinate_mapper.map_answers_to_positions(form_structure, matched_qa)
            
            # Optimize layout
            optimized_positions = coordinate_mapper.optimize_layout(positions, form_structure)
            
            # Convert to AnswerData objects
            answer_objects = []
            for qa_pair in matched_qa:
                question_id = qa_pair.get("question_number", f"q_{len(answer_objects)}")
                answer_obj = AnswerData(
                    question_id=str(question_id),
                    answer_text=qa_pair.get("answer", ""),
                    confidence=qa_pair.get("match_confidence", 1.0),
                    source_text=qa_pair.get("question", "")
                )
                answer_objects.append(answer_obj)
            
            # Create output filename
            base_name = Path(questions_file.filename).stem
            output_filename = f"{base_name}_completed.pdf"
            
            # Create temporary output file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as output_file:
                output_path = output_file.name
            
            # Fill the PDF
            filled_pdf_path = await pdf_filler.fill_pdf_with_answers(
                temp_file_path, form_structure, answer_objects, output_path
            )
            
            # Return the filled PDF
            return FileResponse(
                path=filled_pdf_path,
                filename=output_filename,
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename={output_filename}"}
            )
            
        finally:
            # Clean up temporary input file
            Path(temp_file_path).unlink(missing_ok=True)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating Q&A PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Q&A PDF generation failed: {str(e)}")


@router.post("/create-answer-summary")
async def create_answer_summary(answers_data: str = Form(...)):
    """
    Create a summary PDF with all questions and answers
    
    Args:
        answers_data: JSON string containing Q&A pairs
        
    Returns:
        Summary PDF file
    """
    try:
        # Parse answers data
        try:
            qa_data = json.loads(answers_data)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON format for answers")
        
        # Extract matched Q&A pairs
        matched_qa = qa_data.get("matched_qa", [])
        
        # Convert to AnswerData objects
        answer_objects = []
        for qa_pair in matched_qa:
            answer_obj = AnswerData(
                question_id=str(qa_pair.get("question_number", len(answer_objects) + 1)),
                answer_text=qa_pair.get("answer", ""),
                confidence=qa_pair.get("match_confidence", 1.0),
                source_text=qa_pair.get("question", "")
            )
            answer_objects.append(answer_obj)
        
        # Create temporary output file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as output_file:
            output_path = output_file.name
        
        # Create summary PDF
        summary_path = pdf_filler.create_answer_summary_pdf(answer_objects, output_path)
        
        # Return the summary PDF
        return FileResponse(
            path=summary_path,
            filename="qa_summary.pdf",
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=qa_summary.pdf"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating answer summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Answer summary creation failed: {str(e)}")


@router.get("/preview-layout")
async def preview_layout(
    file: UploadFile = File(...),
    answers_data: str = Form(...)
):
    """
    Preview where answers will be placed on the PDF
    
    Args:
        file: PDF file to analyze
        answers_data: JSON string containing answers
        
    Returns:
        Layout preview information
    """
    try:
        # Parse answers data
        try:
            qa_data = json.loads(answers_data)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON format for answers")
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Analyze the PDF form structure
            form_structure = await form_analyzer.analyze_pdf_form(temp_file_path)
            
            # Extract matched Q&A pairs
            matched_qa = qa_data.get("matched_qa", [])
            
            # Map questions to positions
            positions = coordinate_mapper.map_answers_to_positions(form_structure, matched_qa)
            
            # Optimize layout
            optimized_positions = coordinate_mapper.optimize_layout(positions, form_structure)
            
            # Create preview
            preview = coordinate_mapper.create_position_preview(optimized_positions, form_structure)
            
            return {
                "status": "success",
                "filename": file.filename,
                "form_analysis": {
                    "total_pages": form_structure.total_pages,
                    "total_fields": len(form_structure.form_fields),
                    "has_fillable_fields": form_structure.has_fillable_fields
                },
                "layout_preview": preview
            }
            
        finally:
            # Clean up temporary file
            Path(temp_file_path).unlink(missing_ok=True)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating layout preview: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Layout preview failed: {str(e)}")
