"""
Coordinate Mapper - Maps questions to answer positions with intelligent positioning
"""
import fitz  # PyMuPDF
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from .pdf_form_analyzer import FormField, PDFFormStructure
import logging

logger = logging.getLogger(__name__)


@dataclass
class AnswerPosition:
    """Represents where an answer should be placed"""
    x: float
    y: float
    width: float
    height: float
    page_number: int
    alignment: str = "left"  # left, center, right
    font_size: int = 10
    max_lines: int = 3


class CoordinateMapper:
    """
    Maps questions to optimal answer positions on PDF pages
    """
    
    def __init__(self):
        self.default_answer_width = 200
        self.default_answer_height = 20
        self.line_spacing = 15
        self.margin = 5
        
    def map_answers_to_positions(
        self,
        form_structure: PDFFormStructure,
        question_answer_pairs: List[Dict]
    ) -> Dict[str, AnswerPosition]:
        """
        Map questions to optimal answer positions
        
        Args:
            form_structure: Structure of the PDF form
            question_answer_pairs: List of question-answer pairs
            
        Returns:
            Dictionary mapping question IDs to answer positions
        """
        position_map = {}
        
        try:
            # Create a mapping of questions to form fields
            question_to_field = self._match_questions_to_fields(
                form_structure.form_fields, question_answer_pairs
            )
            
            # Calculate positions for each question
            for qa_pair in question_answer_pairs:
                question_id = qa_pair.get("question_id", f"q_{len(position_map)}")
                question_text = qa_pair.get("question", "")
                answer_text = qa_pair.get("answer", "")
                
                # Find the best position for this answer
                if question_id in question_to_field:
                    field = question_to_field[question_id]
                    position = self._calculate_position_from_field(field, answer_text)
                else:
                    # Fallback: try to find position based on question text
                    position = self._find_position_by_text_analysis(
                        form_structure, question_text, answer_text
                    )
                
                if position:
                    position_map[question_id] = position
                    
        except Exception as e:
            logger.error(f"Error mapping answers to positions: {str(e)}")
            
        return position_map
    
    def _match_questions_to_fields(
        self,
        form_fields: List[FormField],
        question_answer_pairs: List[Dict]
    ) -> Dict[str, FormField]:
        """Match questions to form fields based on text similarity"""
        question_to_field = {}
        
        for qa_pair in question_answer_pairs:
            question_id = qa_pair.get("question_id", "")
            question_text = qa_pair.get("question", "").lower()
            
            best_field = None
            best_score = 0
            
            for field in form_fields:
                # Calculate similarity score
                score = self._calculate_text_similarity(question_text, field.question_text.lower())
                
                if score > best_score and score > 0.5:  # Threshold for matching
                    best_score = score
                    best_field = field
            
            if best_field:
                question_to_field[question_id] = best_field
                
        return question_to_field
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings"""
        # Simple word overlap similarity
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
            
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _calculate_position_from_field(self, field: FormField, answer_text: str) -> AnswerPosition:
        """Calculate answer position based on form field"""
        if field.answer_area:
            x, y, width, height = field.answer_area
        else:
            # Use field position as fallback
            x, y, width, height = field.position
            
        # Adjust dimensions based on answer length
        answer_length = len(answer_text)
        lines_needed = max(1, answer_length // 50)  # Rough estimate
        
        # Adjust height for multi-line answers
        if lines_needed > 1:
            height = max(height, lines_needed * self.line_spacing)
            
        return AnswerPosition(
            x=x,
            y=y,
            width=width,
            height=height,
            page_number=field.page_number,
            font_size=self._calculate_optimal_font_size(answer_text, width, height),
            max_lines=lines_needed
        )
    
    def _find_position_by_text_analysis(
        self,
        form_structure: PDFFormStructure,
        question_text: str,
        answer_text: str
    ) -> Optional[AnswerPosition]:
        """Find answer position by analyzing text layout"""
        # This is a fallback method when no form fields are found
        # Place answers at the bottom of the first page
        
        if not form_structure.page_dimensions:
            return None
            
        page_width, page_height = form_structure.page_dimensions.get(1, (612, 792))
        
        # Place answer in the lower portion of the page
        answer_width = min(self.default_answer_width, page_width - 100)
        answer_height = self.default_answer_height
        
        # Calculate lines needed
        lines_needed = max(1, len(answer_text) // 50)
        answer_height = lines_needed * self.line_spacing
        
        return AnswerPosition(
            x=50,  # Left margin
            y=page_height - 200,  # Upper portion
            width=answer_width,
            height=answer_height,
            page_number=1,
            font_size=self._calculate_optimal_font_size(answer_text, answer_width, answer_height),
            max_lines=lines_needed
        )
    
    def _calculate_optimal_font_size(self, text: str, width: float, height: float) -> int:
        """Calculate optimal font size for the given text and area"""
        # Simple font size calculation
        text_length = len(text)
        available_area = width * height
        
        # Base font size
        base_size = 10
        
        # Adjust based on text length and available area
        if text_length > 100:
            base_size = max(8, base_size - 2)
        elif text_length < 20:
            base_size = min(12, base_size + 2)
            
        # Adjust based on available area
        if available_area < 1000:
            base_size = max(6, base_size - 2)
        elif available_area > 5000:
            base_size = min(14, base_size + 2)
            
        return base_size
    
    def optimize_layout(
        self,
        positions: Dict[str, AnswerPosition],
        form_structure: PDFFormStructure
    ) -> Dict[str, AnswerPosition]:
        """Optimize the layout to avoid overlapping answers"""
        optimized_positions = {}
        
        # Group positions by page
        positions_by_page = {}
        for question_id, position in positions.items():
            page = position.page_number
            if page not in positions_by_page:
                positions_by_page[page] = []
            positions_by_page[page].append((question_id, position))
        
        # Optimize each page
        for page_num, page_positions in positions_by_page.items():
            # Sort by y-position (top to bottom)
            page_positions.sort(key=lambda x: x[1].y)
            
            # Check for overlaps and adjust
            for i, (question_id, position) in enumerate(page_positions):
                adjusted_position = self._avoid_overlaps(position, page_positions[:i])
                optimized_positions[question_id] = adjusted_position
        
        return optimized_positions
    
    def _avoid_overlaps(
        self,
        position: AnswerPosition,
        existing_positions: List[Tuple[str, AnswerPosition]]
    ) -> AnswerPosition:
        """Adjust position to avoid overlapping with existing positions"""
        current_y = position.y
        
        for _, existing_pos in existing_positions:
            # Check if positions overlap
            if self._positions_overlap(position, existing_pos):
                # Move current position below the existing one
                current_y = existing_pos.y - position.height - 10
        
        # Create new position with adjusted y
        return AnswerPosition(
            x=position.x,
            y=current_y,
            width=position.width,
            height=position.height,
            page_number=position.page_number,
            alignment=position.alignment,
            font_size=position.font_size,
            max_lines=position.max_lines
        )
    
    def _positions_overlap(self, pos1: AnswerPosition, pos2: AnswerPosition) -> bool:
        """Check if two positions overlap"""
        if pos1.page_number != pos2.page_number:
            return False
            
        # Check rectangle overlap
        return not (pos1.x + pos1.width < pos2.x or 
                   pos2.x + pos2.width < pos1.x or 
                   pos1.y + pos1.height < pos2.y or 
                   pos2.y + pos2.height < pos1.y)
    
    def create_position_preview(
        self,
        positions: Dict[str, AnswerPosition],
        form_structure: PDFFormStructure
    ) -> Dict:
        """Create a preview of where answers will be placed"""
        preview = {
            "total_positions": len(positions),
            "positions_by_page": {},
            "layout_warnings": []
        }
        
        for question_id, position in positions.items():
            page = position.page_number
            if page not in preview["positions_by_page"]:
                preview["positions_by_page"][page] = []
                
            preview["positions_by_page"][page].append({
                "question_id": question_id,
                "x": position.x,
                "y": position.y,
                "width": position.width,
                "height": position.height,
                "font_size": position.font_size
            })
            
            # Check for potential issues
            page_dims = form_structure.page_dimensions.get(page, (612, 792))
            if position.x + position.width > page_dims[0]:
                preview["layout_warnings"].append(
                    f"Answer for {question_id} extends beyond page width"
                )
            if position.y + position.height > page_dims[1]:
                preview["layout_warnings"].append(
                    f"Answer for {question_id} extends beyond page height"
                )
        
        return preview
