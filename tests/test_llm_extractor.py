"""
Tests for LLM extractor functionality
"""
import pytest
import json
import os
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

# Set test environment
os.environ['ENVIRONMENT'] = 'test'
os.environ['OPENAI_API_KEY'] = 'test_openai_key'
os.environ['ANTHROPIC_API_KEY'] = 'test_anthropic_key'
os.environ['DEEPSEEK_API_KEY'] = 'test_deepseek_key'

from backend.tools.llm_extractor import LLMExtractor
from backend.agents.models import ProcessingStatus, ExtractionResult, ExtractionField
from backend.agents.providers import LLMProvider


class TestLLMExtractor:
    """Test suite for LLM extractor"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.extractor = LLMExtractor()
        self.sample_text = """
        COMPLAINT FOR DAMAGES
        
        Plaintiff: John Doe
        Defendant: ABC Corporation
        Case Number: 2023-CV-001
        Date Filed: January 15, 2023
        
        FACTS:
        On December 1, 2022, plaintiff was injured in a car accident 
        caused by defendant's negligence. Medical expenses totaled $15,000.
        """
        
        self.sample_schema = {
            "fields": [
                {
                    "name": "plaintiff_name",
                    "type": "string",
                    "description": "Name of the plaintiff"
                },
                {
                    "name": "defendant_name", 
                    "type": "string",
                    "description": "Name of the defendant"
                },
                {
                    "name": "case_number",
                    "type": "string",
                    "description": "Court case number"
                },
                {
                    "name": "medical_expenses",
                    "type": "number",
                    "description": "Total medical expenses amount"
                }
            ]
        }
        
    def test_init_default_provider(self):
        """Test LLM extractor initialization with default provider"""
        extractor = LLMExtractor()
        assert extractor.provider == LLMProvider.OPENAI
        assert extractor.model is not None
        
    def test_init_custom_provider(self):
        """Test LLM extractor initialization with custom provider"""
        extractor = LLMExtractor(provider=LLMProvider.ANTHROPIC)
        assert extractor.provider == LLMProvider.ANTHROPIC
        
    def test_prepare_prompt_basic(self):
        """Test basic prompt preparation"""
        prompt = self.extractor.prepare_prompt(
            text=self.sample_text,
            schema=self.sample_schema
        )
        
        assert "John Doe" in prompt
        assert "plaintiff_name" in prompt
        assert "Extract the following information" in prompt
        
    def test_prepare_prompt_with_context(self):
        """Test prompt preparation with additional context"""
        context = {"document_type": "complaint", "jurisdiction": "California"}
        
        prompt = self.extractor.prepare_prompt(
            text=self.sample_text,
            schema=self.sample_schema,
            context=context
        )
        
        assert "complaint" in prompt.lower()
        assert "California" in prompt
        
    def test_validate_schema_valid(self):
        """Test schema validation with valid schema"""
        is_valid, errors = self.extractor.validate_schema(self.sample_schema)
        
        assert is_valid == True
        assert len(errors) == 0
        
    def test_validate_schema_invalid_missing_fields(self):
        """Test schema validation with missing fields"""
        invalid_schema = {"invalid": "schema"}
        
        is_valid, errors = self.extractor.validate_schema(invalid_schema)
        
        assert is_valid == False
        assert len(errors) > 0
        assert "fields" in errors[0].lower()
        
    def test_validate_schema_invalid_field_structure(self):
        """Test schema validation with invalid field structure"""
        invalid_schema = {
            "fields": [
                {"name": "test_field"}  # Missing required properties
            ]
        }
        
        is_valid, errors = self.extractor.validate_schema(invalid_schema)
        
        assert is_valid == False
        assert len(errors) > 0
        
    @patch('backend.tools.llm_extractor.openai.ChatCompletion.create')
    def test_call_openai_success(self, mock_openai):
        """Test successful OpenAI API call"""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='{"plaintiff_name": "John Doe"}'))
        ]
        mock_openai.return_value = mock_response
        
        result = self.extractor.call_openai("test prompt")
        
        assert result == '{"plaintiff_name": "John Doe"}'
        mock_openai.assert_called_once()
        
    @patch('backend.tools.llm_extractor.openai.ChatCompletion.create')
    def test_call_openai_failure(self, mock_openai):
        """Test OpenAI API call failure handling"""
        mock_openai.side_effect = Exception("API Error")
        
        result = self.extractor.call_openai("test prompt")
        
        assert result is None
        
    @patch('backend.tools.llm_extractor.anthropic.Anthropic')
    def test_call_anthropic_success(self, mock_anthropic_class):
        """Test successful Anthropic API call"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"plaintiff_name": "John Doe"}')]
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client
        
        extractor = LLMExtractor(provider=LLMProvider.ANTHROPIC)
        result = extractor.call_anthropic("test prompt")
        
        assert result == '{"plaintiff_name": "John Doe"}'
        
    def test_parse_llm_response_valid_json(self):
        """Test parsing valid JSON response"""
        response = '{"plaintiff_name": "John Doe", "case_number": "2023-CV-001"}'
        
        parsed = self.extractor.parse_llm_response(response)
        
        assert isinstance(parsed, dict)
        assert parsed["plaintiff_name"] == "John Doe"
        assert parsed["case_number"] == "2023-CV-001"
        
    def test_parse_llm_response_invalid_json(self):
        """Test parsing invalid JSON response"""
        response = "This is not valid JSON"
        
        parsed = self.extractor.parse_llm_response(response)
        
        assert parsed is None
        
    def test_parse_llm_response_json_with_extra_text(self):
        """Test parsing JSON response with extra text"""
        response = '''Here is the extracted data:
        {"plaintiff_name": "John Doe", "case_number": "2023-CV-001"}
        Additional notes here.'''
        
        parsed = self.extractor.parse_llm_response(response)
        
        assert isinstance(parsed, dict)
        assert parsed["plaintiff_name"] == "John Doe"
        
    def test_calculate_field_confidence_high(self):
        """Test confidence calculation for high-confidence field"""
        field_data = {
            "value": "John Doe",
            "source_text": "Plaintiff: John Doe",
            "reasoning": "Clear plaintiff identification"
        }
        
        confidence = self.extractor.calculate_field_confidence(field_data, self.sample_text)
        
        assert confidence >= 0.8
        
    def test_calculate_field_confidence_low(self):
        """Test confidence calculation for low-confidence field"""
        field_data = {
            "value": "Unknown",
            "source_text": "",
            "reasoning": "Could not determine"
        }
        
        confidence = self.extractor.calculate_field_confidence(field_data, self.sample_text)
        
        assert confidence < 0.5
        
    def test_post_process_extraction_valid(self):
        """Test post-processing of valid extraction"""
        raw_extraction = {
            "plaintiff_name": "John Doe",
            "defendant_name": "ABC Corporation",
            "case_number": "2023-CV-001",
            "medical_expenses": 15000
        }
        
        processed = self.extractor.post_process_extraction(
            raw_extraction, self.sample_schema, self.sample_text
        )
        
        assert isinstance(processed, list)
        assert len(processed) == 4
        assert all(isinstance(field, ExtractionField) for field in processed)
        
    def test_post_process_extraction_missing_fields(self):
        """Test post-processing with missing schema fields"""
        raw_extraction = {
            "plaintiff_name": "John Doe",
            # Missing other required fields
        }
        
        processed = self.extractor.post_process_extraction(
            raw_extraction, self.sample_schema, self.sample_text
        )
        
        # Should still create fields for missing data
        assert len(processed) == 4
        plaintiff_field = next(f for f in processed if f.name == "plaintiff_name")
        assert plaintiff_field.value == "John Doe"
        
    def test_extract_from_text_success(self):
        """Test successful text extraction"""
        with patch.object(self.extractor, 'call_openai') as mock_call:
            mock_call.return_value = json.dumps({
                "plaintiff_name": "John Doe",
                "defendant_name": "ABC Corporation",
                "case_number": "2023-CV-001",
                "medical_expenses": 15000
            })
            
            result = self.extractor.extract_from_text(
                text=self.sample_text,
                schema=self.sample_schema
            )
            
            assert isinstance(result, ExtractionResult)
            assert result.status == ProcessingStatus.COMPLETED
            assert len(result.extracted_fields) == 4
            
    def test_extract_from_text_api_failure(self):
        """Test extraction with API failure"""
        with patch.object(self.extractor, 'call_openai') as mock_call:
            mock_call.return_value = None
            
            result = self.extractor.extract_from_text(
                text=self.sample_text,
                schema=self.sample_schema
            )
            
            assert isinstance(result, ExtractionResult)
            assert result.status == ProcessingStatus.FAILED
            
    def test_extract_from_text_invalid_schema(self):
        """Test extraction with invalid schema"""
        invalid_schema = {"invalid": "schema"}
        
        result = self.extractor.extract_from_text(
            text=self.sample_text,
            schema=invalid_schema
        )
        
        assert isinstance(result, ExtractionResult)
        assert result.status == ProcessingStatus.FAILED
        assert "schema" in result.error_message.lower()
        
    def test_extract_from_chunks_multiple(self):
        """Test extraction from multiple text chunks"""
        chunks = [
            "Plaintiff: John Doe, Case: 2023-CV-001",
            "Defendant: ABC Corporation", 
            "Medical expenses: $15,000"
        ]
        
        with patch.object(self.extractor, 'extract_from_text') as mock_extract:
            mock_results = [
                ExtractionResult(
                    extracted_fields=[
                        ExtractionField(name="plaintiff_name", value="John Doe", confidence=0.9),
                        ExtractionField(name="case_number", value="2023-CV-001", confidence=0.8)
                    ],
                    status=ProcessingStatus.COMPLETED
                ),
                ExtractionResult(
                    extracted_fields=[
                        ExtractionField(name="defendant_name", value="ABC Corporation", confidence=0.9)
                    ],
                    status=ProcessingStatus.COMPLETED
                ),
                ExtractionResult(
                    extracted_fields=[
                        ExtractionField(name="medical_expenses", value=15000, confidence=0.7)
                    ],
                    status=ProcessingStatus.COMPLETED
                )
            ]
            mock_extract.side_effect = mock_results
            
            result = self.extractor.extract_from_chunks(
                chunks=chunks,
                schema=self.sample_schema
            )
            
            assert isinstance(result, ExtractionResult)
            assert result.status == ProcessingStatus.COMPLETED
            assert len(result.extracted_fields) == 4  # All schema fields
            
    def test_merge_chunk_results(self):
        """Test merging results from multiple chunks"""
        results = [
            ExtractionResult(
                extracted_fields=[
                    ExtractionField(name="plaintiff_name", value="John Doe", confidence=0.9),
                    ExtractionField(name="case_number", value="2023-CV-001", confidence=0.8)
                ],
                status=ProcessingStatus.COMPLETED
            ),
            ExtractionResult(
                extracted_fields=[
                    ExtractionField(name="defendant_name", value="ABC Corporation", confidence=0.9),
                    ExtractionField(name="case_number", value="2023-CV-001", confidence=0.7)  # Duplicate
                ],
                status=ProcessingStatus.COMPLETED
            )
        ]
        
        merged = self.extractor.merge_chunk_results(results, self.sample_schema)
        
        assert isinstance(merged, ExtractionResult)
        assert merged.status == ProcessingStatus.COMPLETED
        
        # Should have unique fields with best confidence
        case_number_field = next(f for f in merged.extracted_fields if f.name == "case_number")
        assert case_number_field.confidence == 0.8  # Higher confidence wins
        
    def test_get_supported_providers(self):
        """Test getting supported LLM providers"""
        providers = self.extractor.get_supported_providers()
        
        assert isinstance(providers, list)
        assert LLMProvider.OPENAI in providers
        assert LLMProvider.ANTHROPIC in providers
        
    def test_estimate_token_usage(self):
        """Test token usage estimation"""
        tokens = self.extractor.estimate_token_usage(self.sample_text, self.sample_schema)
        
        assert isinstance(tokens, int)
        assert tokens > 0
        
    def test_get_extraction_statistics(self):
        """Test extraction statistics generation"""
        result = ExtractionResult(
            extracted_fields=[
                ExtractionField(name="field1", value="value1", confidence=0.9),
                ExtractionField(name="field2", value="value2", confidence=0.7),
                ExtractionField(name="field3", value="", confidence=0.3)
            ],
            status=ProcessingStatus.COMPLETED
        )
        
        stats = self.extractor.get_extraction_statistics(result)
        
        assert isinstance(stats, dict)
        assert "total_fields" in stats
        assert "extracted_fields" in stats
        assert "average_confidence" in stats
        assert "low_confidence_fields" in stats
        
        assert stats["total_fields"] == 3
        assert stats["extracted_fields"] == 2  # Non-empty values
        assert stats["average_confidence"] == pytest.approx(0.63, rel=1e-2)
