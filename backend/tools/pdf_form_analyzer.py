"""
PDF Form Analyzer - Extract form fields and question positions from PDF documents
"""
import fitz  # PyMuPDF
import re
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FormField:
    """Represents a form field in a PDF"""
    field_id: str
    question_text: str
    position: Tuple[float, float, float, float]  # (x, y, width, height)
    page_number: int
    field_type: str = "text"  # text, checkbox, radio, etc.
    answer_area: Optional[Tuple[float, float, float, float]] = None


@dataclass
class PDFFormStructure:
    """Represents the structure of a PDF form"""
    form_fields: List[FormField]
    total_pages: int
    page_dimensions: Dict[int, Tuple[float, float]]  # page -> (width, height)
    has_fillable_fields: bool = False


class PDFFormAnalyzer:
    """
    Analyzes PDF documents to extract form structure and question positions
    """
    
    def __init__(self):
        self.question_patterns = [
            r"Question\s*\d+[:\.]?\s*",
            r"Q\d+[:\.]?\s*",
            r"\d+[:\.]?\s*",
            r"[A-Z]\)\s*",
            r"\([a-z]\)\s*"
        ]
        
    async def analyze_pdf_form(self, pdf_path: str) -> PDFFormStructure:
        """
        Analyze a PDF to extract form structure and question positions
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            PDFFormStructure with form fields and positions
        """
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
            
        try:
            with fitz.open(str(pdf_path)) as doc:
                form_fields = []
                page_dimensions = {}
                
                # First, check for fillable form fields
                fillable_fields = self._extract_fillable_fields(doc)
                
                # Then, analyze text-based questions
                text_based_fields = self._extract_text_based_questions(doc)
                
                # Combine all fields
                all_fields = fillable_fields + text_based_fields
                
                # Get page dimensions
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    page_dimensions[page_num + 1] = (page.rect.width, page.rect.height)
                
                return PDFFormStructure(
                    form_fields=all_fields,
                    total_pages=len(doc),
                    page_dimensions=page_dimensions,
                    has_fillable_fields=len(fillable_fields) > 0
                )
                
        except Exception as e:
            logger.error(f"Error analyzing PDF form: {str(e)}")
            raise ValueError(f"PDF form analysis failed: {str(e)}")
    
    def _extract_fillable_fields(self, doc: fitz.Document) -> List[FormField]:
        """Extract fillable form fields from PDF"""
        fields = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Get form fields on this page
            for field in page.widgets():
                if field.field_type == fitz.PDF_WIDGET_TYPE_TEXT:
                    # Extract question text (look for text near the field)
                    question_text = self._find_question_text_near_field(page, field.rect)
                    
                    form_field = FormField(
                        field_id=f"field_{page_num}_{field.field_name or len(fields)}",
                        question_text=question_text,
                        position=(field.rect.x0, field.rect.y0, field.rect.width, field.rect.height),
                        page_number=page_num + 1,
                        field_type="fillable_text",
                        answer_area=(field.rect.x0, field.rect.y0, field.rect.width, field.rect.height)
                    )
                    fields.append(form_field)
                    
        return fields
    
    def _extract_text_based_questions(self, doc: fitz.Document) -> List[FormField]:
        """Extract text-based questions from PDF"""
        fields = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Get text blocks from the page
            text_blocks = page.get_text("dict")
            
            for block in text_blocks["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = span["text"].strip()
                            
                            # Check if this looks like a question
                            if self._is_question_text(text):
                                # Calculate answer area (area below/after the question)
                                answer_area = self._calculate_answer_area(span, page.rect)
                                
                                form_field = FormField(
                                    field_id=f"question_{page_num}_{len(fields)}",
                                    question_text=text,
                                    position=(span["bbox"][0], span["bbox"][1], 
                                             span["bbox"][2] - span["bbox"][0], 
                                             span["bbox"][3] - span["bbox"][1]),
                                    page_number=page_num + 1,
                                    field_type="text_question",
                                    answer_area=answer_area
                                )
                                fields.append(form_field)
        
        return fields
    
    def _is_question_text(self, text: str) -> bool:
        """Check if text looks like a question"""
        # Check for question patterns
        for pattern in self.question_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        # Check for question marks
        if "?" in text:
            return True
            
        # Check for common question words
        question_words = ["what", "when", "where", "who", "why", "how", "which", "is", "are", "do", "does", "did"]
        text_lower = text.lower()
        
        for word in question_words:
            if text_lower.startswith(word) and len(text) > 10:
                return True
                
        return False
    
    def _find_question_text_near_field(self, page: fitz.Page, field_rect: fitz.Rect) -> str:
        """Find question text near a fillable field"""
        # Look for text in the area around the field
        search_rect = fitz.Rect(
            field_rect.x0 - 200,  # Look left
            field_rect.y0 - 50,   # Look up
            field_rect.x1 + 50,   # Look right
            field_rect.y1 + 50    # Look down
        )
        
        # Extract text in the search area
        text_instances = page.get_text("words", clip=search_rect)
        
        if text_instances:
            # Combine words into text
            words = [instance[4] for instance in text_instances]
            question_text = " ".join(words)
            
            # Clean up the text
            question_text = re.sub(r'\s+', ' ', question_text).strip()
            
            return question_text
        
        return "Unknown question"
    
    def _calculate_answer_area(self, question_span: Dict, page_rect: fitz.Rect) -> Tuple[float, float, float, float]:
        """Calculate the area where the answer should be placed"""
        # Get question position
        q_x0, q_y0, q_x1, q_y1 = question_span["bbox"]
        
        # Calculate answer area (typically below or to the right of the question)
        answer_width = min(200, page_rect.width - q_x1 - 20)  # Leave margin
        answer_height = 20  # Standard text height
        
        # Position answer area
        if q_x1 + answer_width < page_rect.width - 20:
            # Place to the right of the question
            answer_x = q_x1 + 10
            answer_y = q_y0
        else:
            # Place below the question
            answer_x = q_x0
            answer_y = q_y1 + 5
        
        return (answer_x, answer_y, answer_width, answer_height)
    
    def get_form_summary(self, form_structure: PDFFormStructure) -> Dict:
        """Get a summary of the form structure"""
        return {
            "total_pages": form_structure.total_pages,
            "total_fields": len(form_structure.form_fields),
            "has_fillable_fields": form_structure.has_fillable_fields,
            "fields_by_page": {
                page: len([f for f in form_structure.form_fields if f.page_number == page])
                for page in range(1, form_structure.total_pages + 1)
            },
            "field_types": {
                field_type: len([f for f in form_structure.form_fields if f.field_type == field_type])
                for field_type in set(f.field_type for f in form_structure.form_fields)
            }
        }
