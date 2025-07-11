"""
PDF Fill Service - Fill PDF forms with answers and generate downloadable PDFs
"""
import fitz  # PyMuPDF
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import black
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import tempfile
import logging
from dataclasses import dataclass
from .pdf_form_analyzer import PDFFormStructure, FormField

logger = logging.getLogger(__name__)


@dataclass
class AnswerData:
    """Represents an answer to be filled in a form"""
    question_id: str
    answer_text: str
    confidence: float = 1.0
    source_text: str = ""


class PDFFillerService:
    """
    Service for filling PDF forms with answers
    """
    
    def __init__(self):
        self.default_font_size = 10
        self.default_font = "Helvetica"
        self.margin = 5
        
    async def fill_pdf_with_answers(
        self,
        original_pdf_path: str,
        form_structure: PDFFormStructure,
        answers: List[AnswerData],
        output_path: Optional[str] = None
    ) -> str:
        """
        Fill a PDF form with answers and return the path to the filled PDF
        
        Args:
            original_pdf_path: Path to the original PDF
            form_structure: Structure of the PDF form
            answers: List of answers to fill in
            output_path: Optional output path, if not provided, a temp file will be created
            
        Returns:
            Path to the filled PDF
        """
        try:
            # Create output path if not provided
            if output_path is None:
                temp_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
                output_path = temp_file.name
                temp_file.close()
            
            # Create answer mapping
            answer_map = {answer.question_id: answer for answer in answers}
            
            # Choose filling method based on form type
            if form_structure.has_fillable_fields:
                filled_path = await self._fill_fillable_pdf(
                    original_pdf_path, form_structure, answer_map, output_path
                )
            else:
                filled_path = await self._fill_text_based_pdf(
                    original_pdf_path, form_structure, answer_map, output_path
                )
            
            logger.info(f"Successfully filled PDF: {filled_path}")
            return filled_path
            
        except Exception as e:
            logger.error(f"Error filling PDF: {str(e)}")
            raise ValueError(f"PDF filling failed: {str(e)}")
    
    async def _fill_fillable_pdf(
        self,
        original_pdf_path: str,
        form_structure: PDFFormStructure,
        answer_map: Dict[str, AnswerData],
        output_path: str
    ) -> str:
        """Fill a PDF with actual fillable form fields"""
        try:
            # Open the original PDF
            with fitz.open(original_pdf_path) as doc:
                # Iterate through pages and fill fields
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    
                    # Fill form fields on this page
                    for field in page.widgets():
                        if field.field_type == fitz.PDF_WIDGET_TYPE_TEXT:
                            # Find corresponding answer
                            field_id = f"field_{page_num}_{field.field_name or 'unknown'}"
                            
                            if field_id in answer_map:
                                answer = answer_map[field_id]
                                # Set field value
                                field.field_value = answer.answer_text
                                field.update()
                
                # Save the filled PDF
                doc.save(output_path)
                
            return output_path
            
        except Exception as e:
            logger.error(f"Error filling fillable PDF: {str(e)}")
            raise
    
    async def _fill_text_based_pdf(
        self,
        original_pdf_path: str,
        form_structure: PDFFormStructure,
        answer_map: Dict[str, AnswerData],
        output_path: str
    ) -> str:
        """Fill a PDF by overlaying text on top of the original"""
        try:
            # Create a temporary PDF with just the answers
            overlay_path = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False).name
            
            # Create the overlay PDF with answers
            await self._create_answer_overlay(form_structure, answer_map, overlay_path)
            
            # Merge the overlay with the original PDF
            await self._merge_pdfs(original_pdf_path, overlay_path, output_path)
            
            # Clean up temporary file
            Path(overlay_path).unlink(missing_ok=True)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error filling text-based PDF: {str(e)}")
            raise
    
    async def _create_answer_overlay(
        self,
        form_structure: PDFFormStructure,
        answer_map: Dict[str, AnswerData],
        overlay_path: str
    ) -> None:
        """Create a PDF overlay with just the answers"""
        try:
            # Get the dimensions of the first page for the canvas
            first_page_dims = form_structure.page_dimensions.get(1, (612, 792))  # Default letter size
            
            # Create the overlay PDF
            c = canvas.Canvas(overlay_path, pagesize=first_page_dims)
            
            current_page = 1
            
            # Process each form field
            for field in form_structure.form_fields:
                if field.field_id in answer_map:
                    answer = answer_map[field.field_id]
                    
                    # Check if we need to start a new page
                    if field.page_number != current_page:
                        c.showPage()
                        current_page = field.page_number
                        
                        # Set page size for the new page
                        page_dims = form_structure.page_dimensions.get(current_page, first_page_dims)
                        c.setPageSize(page_dims)
                    
                    # Add the answer text
                    await self._add_answer_to_canvas(c, field, answer, first_page_dims)
            
            # Save the overlay PDF
            c.save()
            
        except Exception as e:
            logger.error(f"Error creating answer overlay: {str(e)}")
            raise
    
    async def _add_answer_to_canvas(
        self,
        canvas_obj: canvas.Canvas,
        field: FormField,
        answer: AnswerData,
        page_dims: Tuple[float, float]
    ) -> None:
        """Add an answer to the canvas at the specified position"""
        try:
            if not field.answer_area:
                return
                
            x, y, width, height = field.answer_area
            
            # Convert coordinates (PDF coordinates start from bottom-left)
            page_height = page_dims[1]
            canvas_y = page_height - y - height
            
            # Set font and color
            canvas_obj.setFont(self.default_font, self.default_font_size)
            canvas_obj.setFillColor(black)
            
            # Format and fit text
            formatted_text = self._format_text_for_area(answer.answer_text, width, height)
            
            # Draw the text
            if isinstance(formatted_text, list):
                # Multi-line text
                for i, line in enumerate(formatted_text):
                    line_y = canvas_y - (i * (self.default_font_size + 2))
                    if line_y > 0:  # Don't draw outside the page
                        canvas_obj.drawString(x + self.margin, line_y, line)
            else:
                # Single line text
                canvas_obj.drawString(x + self.margin, canvas_y, formatted_text)
                
            # Add confidence indicator for low confidence answers
            if answer.confidence < 0.8:
                self._add_confidence_indicator(canvas_obj, x, canvas_y, answer.confidence)
                
        except Exception as e:
            logger.error(f"Error adding answer to canvas: {str(e)}")
            # Don't raise, just log and continue
    
    def _format_text_for_area(self, text: str, width: float, height: float) -> List[str]:
        """Format text to fit within the specified area"""
        # Simple text wrapping - this could be enhanced
        max_chars_per_line = max(1, int(width / 6))  # Rough estimate
        max_lines = max(1, int(height / (self.default_font_size + 2)))
        
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + " " + word if current_line else word
            if len(test_line) <= max_chars_per_line:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
                
                if len(lines) >= max_lines:
                    break
        
        if current_line and len(lines) < max_lines:
            lines.append(current_line)
        
        return lines[:max_lines]
    
    def _add_confidence_indicator(self, canvas_obj: canvas.Canvas, x: float, y: float, confidence: float) -> None:
        """Add a visual indicator for low confidence answers"""
        # Add a small warning symbol
        canvas_obj.setFillColor(black)
        canvas_obj.setFont("Helvetica", 8)
        canvas_obj.drawString(x - 15, y, f"[{confidence:.1f}]")
    
    async def _merge_pdfs(self, original_path: str, overlay_path: str, output_path: str) -> None:
        """Merge the original PDF with the overlay PDF"""
        try:
            # Open both PDFs
            with fitz.open(original_path) as original_doc:
                with fitz.open(overlay_path) as overlay_doc:
                    # Create a new document
                    merged_doc = fitz.open()
                    
                    # Process each page
                    for page_num in range(len(original_doc)):
                        # Get the original page
                        original_page = original_doc[page_num]
                        
                        # Create a new page in the merged document
                        merged_page = merged_doc.new_page(width=original_page.rect.width, 
                                                        height=original_page.rect.height)
                        
                        # Insert the original page content
                        merged_page.show_pdf_page(original_page.rect, original_doc, page_num)
                        
                        # Insert the overlay content if it exists
                        if page_num < len(overlay_doc):
                            overlay_page = overlay_doc[page_num]
                            merged_page.show_pdf_page(overlay_page.rect, overlay_doc, page_num)
                    
                    # Save the merged PDF
                    merged_doc.save(output_path)
                    merged_doc.close()
                    
        except Exception as e:
            logger.error(f"Error merging PDFs: {str(e)}")
            raise
    
    def create_answer_summary_pdf(self, answers: List[AnswerData], output_path: str) -> str:
        """Create a summary PDF with all questions and answers"""
        try:
            c = canvas.Canvas(output_path, pagesize=letter)
            width, height = letter
            
            # Title
            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, height - 50, "Question & Answer Summary")
            
            y_position = height - 100
            
            for i, answer in enumerate(answers, 1):
                # Check if we need a new page
                if y_position < 100:
                    c.showPage()
                    y_position = height - 50
                
                # Question
                c.setFont("Helvetica-Bold", 12)
                c.drawString(50, y_position, f"Q{i}:")
                y_position -= 20
                
                # Answer
                c.setFont("Helvetica", 10)
                answer_lines = self._format_text_for_area(answer.answer_text, width - 100, 60)
                for line in answer_lines:
                    c.drawString(70, y_position, line)
                    y_position -= 15
                
                # Confidence
                c.setFont("Helvetica", 8)
                c.drawString(50, y_position, f"Confidence: {answer.confidence:.2f}")
                y_position -= 30
            
            c.save()
            return output_path
            
        except Exception as e:
            logger.error(f"Error creating answer summary PDF: {str(e)}")
            raise
