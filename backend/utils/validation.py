import re
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, ValidationError
import logging
from ..agents.models import ExtractionField, ExtractionSchema

logger = logging.getLogger(__name__)


class ValidationUtils:
    """Utility functions for data validation."""
    
    @staticmethod
    def validate_extraction_schema(schema: Dict[str, Any]) -> bool:
        """
        Validate extraction schema structure.
        
        Args:
            schema: Schema to validate
            
        Returns:
            True if schema is valid
        """
        if not isinstance(schema, dict):
            return False
        
        # Check that schema is not empty
        if not schema:
            return False
        
        # Basic validation - ensure all values are valid types
        for key, value in schema.items():
            if not isinstance(key, str) or not key.strip():
                return False
        
        return True
    
    @staticmethod
    def sanitize_extracted_value(value: Any) -> Any:
        """
        Sanitize extracted values.
        
        Args:
            value: Value to sanitize
            
        Returns:
            Sanitized value
        """
        if value is None:
            return None
        
        if isinstance(value, str):
            # Remove extra whitespace
            value = value.strip()
            
            # Remove common OCR artifacts for short strings
            if len(value) < 50:
                # Common OCR substitutions
                ocr_fixes = {
                    '|': 'I',
                    '0': 'O',  # Only for very short strings that might be names
                    '1': 'l',  # Only in specific contexts
                }
                
                # Apply fixes cautiously
                for old, new in ocr_fixes.items():
                    if old in value and len(value) < 20:
                        value = value.replace(old, new)
            
            # Remove extra spaces
            value = re.sub(r'\s+', ' ', value)
        
        elif isinstance(value, list):
            # Sanitize list items
            value = [ValidationUtils.sanitize_extracted_value(item) for item in value]
            # Remove None values
            value = [item for item in value if item is not None]
        
        return value
    
    @staticmethod
    def validate_confidence_score(score: float) -> bool:
        """
        Validate confidence score is within valid range.
        
        Args:
            score: Confidence score
            
        Returns:
            True if valid
        """
        return 0.0 <= score <= 1.0
    
    @staticmethod
    def validate_case_number(case_number: str) -> bool:
        """
        Validate case number format.
        
        Args:
            case_number: Case number to validate
            
        Returns:
            True if format appears valid
        """
        if not case_number or not isinstance(case_number, str):
            return False
        
        case_number = case_number.strip()
        
        # Common case number patterns
        patterns = [
            r'^[A-Z]{2,4}-\d{4}-\d{3,6}$',  # CV-2024-123456
            r'^\d{2}-[A-Z]{2}-\d{4,6}$',   # 24-CV-123456
            r'^\d{4}[A-Z]{2,4}\d{3,6}$',   # 2024CV123456
            r'^[A-Z]+\d{2,4}-\d{3,6}$',    # CIV24-123456
        ]
        
        for pattern in patterns:
            if re.match(pattern, case_number.upper()):
                return True
        
        return False
    
    @staticmethod
    def validate_party_name(name: str) -> bool:
        """
        Validate party name format.
        
        Args:
            name: Party name to validate
            
        Returns:
            True if format appears valid
        """
        if not name or not isinstance(name, str):
            return False
        
        name = name.strip()
        
        # Should contain at least one letter
        if not re.search(r'[a-zA-Z]', name):
            return False
        
        # Should not be too short or too long
        if len(name) < 2 or len(name) > 200:
            return False
        
        # Should not contain excessive numbers (likely OCR error)
        digit_ratio = len(re.findall(r'\d', name)) / len(name)
        if digit_ratio > 0.5:
            return False
        
        return True
    
    @staticmethod
    def validate_date_format(date_str: str) -> bool:
        """
        Validate date format.
        
        Args:
            date_str: Date string to validate
            
        Returns:
            True if format appears valid
        """
        if not date_str or not isinstance(date_str, str):
            return False
        
        # Common date patterns
        patterns = [
            r'^\d{4}-\d{2}-\d{2}$',     # 2024-04-15
            r'^\d{2}/\d{2}/\d{4}$',     # 04/15/2024
            r'^\d{1,2}/\d{1,2}/\d{4}$', # 4/15/2024
            r'^[A-Za-z]+ \d{1,2}, \d{4}$', # April 15, 2024
        ]
        
        for pattern in patterns:
            if re.match(pattern, date_str.strip()):
                return True
        
        return False
    
    @staticmethod
    def validate_extraction_field(field: ExtractionField) -> List[str]:
        """
        Validate an extraction field and return list of issues.
        
        Args:
            field: ExtractionField to validate
            
        Returns:
            List of validation issues (empty if valid)
        """
        issues = []
        
        # Validate confidence score
        if not ValidationUtils.validate_confidence_score(field.confidence_score):
            issues.append(f"Invalid confidence score: {field.confidence_score}")
        
        # If value is present, validate it
        if field.value is not None:
            # Check if source_text is provided when value is present
            if not field.source_text:
                issues.append("Source text missing for non-null value")
            
            # Validate specific field types based on common patterns
            if isinstance(field.value, str):
                value_str = field.value.strip()
                
                # Check for obvious OCR errors
                if re.search(r'[^\w\s\-.,():/;]', value_str):
                    issues.append("Value contains unusual characters (possible OCR error)")
                
                # Check for excessive whitespace
                if '  ' in value_str:
                    issues.append("Value contains excessive whitespace")
        
        return issues
    
    @staticmethod
    def validate_extraction_results(
        results: Dict[str, ExtractionField],
        schema: ExtractionSchema
    ) -> Dict[str, List[str]]:
        """
        Validate extraction results against schema.
        
        Args:
            results: Extraction results
            schema: Original schema
            
        Returns:
            Dictionary of field names to validation issues
        """
        validation_report = {}
        
        # Check each field in the schema
        for field_name in schema.fields.keys():
            if field_name in results:
                field_issues = ValidationUtils.validate_extraction_field(results[field_name])
                if field_issues:
                    validation_report[field_name] = field_issues
            else:
                validation_report[field_name] = ["Field missing from results"]
        
        return validation_report
    
    @staticmethod
    def auto_correct_common_errors(value: str) -> str:
        """
        Auto-correct common OCR errors.
        
        Args:
            value: Value to correct
            
        Returns:
            Corrected value
        """
        if not isinstance(value, str):
            return value
        
        # Common OCR corrections
        corrections = {
            # Letter/number confusions
            r'\b0(?=[A-Za-z])': 'O',  # 0 at start of words -> O
            r'(?<=[A-Za-z])0\b': 'O',  # 0 at end of words -> O
            r'\b1(?=[A-Za-z])': 'I',  # 1 at start of words -> I
            r'(?<=[A-Za-z])1\b': 'l',  # 1 at end of words -> l
            
            # Common legal document fixes
            r'\bP1aintiff\b': 'Plaintiff',
            r'\bDefendant\b': 'Defendant',
            r'\bCourt\b': 'Court',
            r'\bCase\b': 'Case',
        }
        
        corrected = value
        for pattern, replacement in corrections.items():
            corrected = re.sub(pattern, replacement, corrected)
        
        return corrected
