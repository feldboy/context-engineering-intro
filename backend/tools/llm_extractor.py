import json
import asyncio
from typing import Dict, List, Any, Optional, Union
from enum import Enum
import logging
import httpx
from ..config.settings import settings
from ..agents.models import ExtractionField

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"


class LLMExtractor:
    """
    LLM-based data extraction with multi-provider support.
    """
    
    def __init__(self, preferred_provider: Optional[str] = None):
        self.preferred_provider = preferred_provider or "openai"
        self.available_providers = settings.available_llm_providers
        
        if not self.available_providers:
            raise ValueError("No LLM providers configured. Please set API keys in environment.")
        
        # Initialize HTTP client
        self.client = httpx.AsyncClient(timeout=30.0)
        
        # Provider configurations
        self.provider_configs = {
            "openai": {
                "api_base": "https://api.openai.com/v1",
                "model": "gpt-4",
                "headers": {"Authorization": f"Bearer {settings.openai_api_key}"}
            },
            "anthropic": {
                "api_base": "https://api.anthropic.com/v1",
                "model": "claude-3-sonnet-20240229",
                "headers": {"x-api-key": settings.anthropic_api_key}
            },
            "deepseek": {
                "api_base": "https://api.deepseek.com/v1",
                "model": "deepseek-chat",
                "headers": {"Authorization": f"Bearer {settings.deepseek_api_key}"}
            }
        }
    
    async def extract_structured_data(
        self, 
        text: str, 
        schema: Dict[str, Any], 
        provider: Optional[str] = None
    ) -> Dict[str, ExtractionField]:
        """
        Extract structured data from text using LLM with confidence scoring.
        
        Args:
            text: Text to extract data from
            schema: JSON schema for extraction
            provider: LLM provider to use
            
        Returns:
            Dictionary of extracted fields
        """
        provider = provider or self.preferred_provider
        
        if provider not in self.available_providers:
            raise ValueError(f"Provider {provider} not available. Available: {self.available_providers}")
        
        # PATTERN: Role-based prompting for legal documents
        system_prompt = """You are an expert paralegal specializing in personal injury cases. 
Your task is to extract specific information from legal documents with extreme accuracy.

CRITICAL RULES:
1. Extract information ONLY from the provided text
2. Do not infer or add information not explicitly stated
3. For each field, provide the exact source text that justifies the extraction
4. Assign confidence scores from 0.0 to 1.0 based on text clarity
5. If information is not found, return null values with 0.0 confidence
6. Be extremely conservative - better to return null than guess"""
        
        # PATTERN: Structured prompt with schema and instructions
        user_prompt = f"""
Extract the following information from this legal document text:

TARGET SCHEMA:
{json.dumps(schema, indent=2)}

DOCUMENT TEXT:
{text}

Return a JSON object where each field contains:
- value: The extracted value (null if not found)
- source_text: The exact text that supports this extraction
- confidence_score: A score from 0.0 to 1.0 indicating confidence

Example format:
{{
    "case_number": {{
        "value": "CIV-2024-1138",
        "source_text": "Case Number: CIV-2024-1138",
        "confidence_score": 0.99
    }},
    "plaintiff_name": {{
        "value": "Jane Doe",
        "source_text": "Jane Doe, an individual, Plaintiff",
        "confidence_score": 0.95
    }}
}}

IMPORTANT: Only extract information that is explicitly stated in the text. Do not infer or guess.
"""
        
        try:
            # Get provider-specific response
            if provider == "openai":
                response = await self._call_openai(system_prompt, user_prompt)
            elif provider == "anthropic":
                response = await self._call_anthropic(system_prompt, user_prompt)
            elif provider == "deepseek":
                response = await self._call_deepseek(system_prompt, user_prompt)
            else:
                raise ValueError(f"Unsupported provider: {provider}")
            
            # Parse and validate response
            extracted_data = self._parse_llm_response(response, schema)
            
            logger.info("LLM extraction completed successfully with provider: %s", provider)
            return extracted_data
            
        except Exception as e:
            logger.error("Error in LLM extraction with provider %s: %s", provider, str(e))
            # Try fallback provider if available
            if len(self.available_providers) > 1:
                fallback_provider = next(
                    (p for p in self.available_providers if p != provider), 
                    None
                )
                if fallback_provider:
                    logger.info("Trying fallback provider: %s", fallback_provider)
                    return await self.extract_structured_data(text, schema, fallback_provider)
            
            raise ValueError(f"LLM extraction failed: {str(e)}")
    
    async def _call_openai(self, system_prompt: str, user_prompt: str) -> str:
        """Call OpenAI API."""
        config = self.provider_configs["openai"]
        
        payload = {
            "model": config["model"],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,  # Low temperature for consistent extraction
            "max_tokens": 2000
        }
        
        response = await self.client.post(
            f"{config['api_base']}/chat/completions",
            headers=config["headers"],
            json=payload
        )
        
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    
    async def _call_anthropic(self, system_prompt: str, user_prompt: str) -> str:
        """Call Anthropic API."""
        config = self.provider_configs["anthropic"]
        
        payload = {
            "model": config["model"],
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 2000
        }
        
        response = await self.client.post(
            f"{config['api_base']}/messages",
            headers={
                **config["headers"],
                "content-type": "application/json",
                "anthropic-version": "2023-06-01"
            },
            json=payload
        )
        
        response.raise_for_status()
        result = response.json()
        return result["content"][0]["text"]
    
    async def _call_deepseek(self, system_prompt: str, user_prompt: str) -> str:
        """Call DeepSeek API."""
        config = self.provider_configs["deepseek"]
        
        payload = {
            "model": config["model"],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 2000,
            "response_format": {"type": "json_object"}
        }
        
        response = await self.client.post(
            f"{config['api_base']}/chat/completions",
            headers=config["headers"],
            json=payload
        )
        
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    
    def _parse_llm_response(self, response: str, schema: Dict[str, Any]) -> Dict[str, ExtractionField]:
        """
        Parse and validate LLM response.
        
        Args:
            response: JSON response from LLM
            schema: Expected schema
            
        Returns:
            Dictionary of ExtractionField objects
        """
        try:
            # Parse JSON response
            data = json.loads(response)
            
            # Convert to ExtractionField objects
            extraction_fields = {}
            
            for field_name in schema.keys():
                if field_name in data:
                    field_data = data[field_name]
                    
                    # Validate field structure
                    if isinstance(field_data, dict):
                        extraction_fields[field_name] = ExtractionField(
                            value=field_data.get("value"),
                            source_text=field_data.get("source_text"),
                            confidence_score=field_data.get("confidence_score", 0.0)
                        )
                    else:
                        # Handle simple value format
                        extraction_fields[field_name] = ExtractionField(
                            value=field_data,
                            source_text=None,
                            confidence_score=0.5  # Default confidence for simple values
                        )
                else:
                    # Field not found in response
                    extraction_fields[field_name] = ExtractionField(
                        value=None,
                        source_text=None,
                        confidence_score=0.0
                    )
            
            return extraction_fields
            
        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM response as JSON: %s", str(e))
            raise ValueError(f"Invalid JSON response from LLM: {str(e)}")
    
    async def extract(self, text: str, schema: Dict[str, Any]) -> Dict[str, ExtractionField]:
        """
        Main extraction method (simplified interface).
        
        Args:
            text: Text to extract from
            schema: Extraction schema
            
        Returns:
            Dictionary of extracted fields
        """
        return await self.extract_structured_data(text, schema)
    
    def synthesize_chunk_results(self, chunk_results: List[Dict[str, ExtractionField]]) -> Dict[str, ExtractionField]:
        """
        Synthesize results from multiple chunks, choosing the best extraction for each field.
        
        Args:
            chunk_results: List of extraction results from different chunks
            
        Returns:
            Synthesized extraction results
        """
        if not chunk_results:
            return {}
        
        # Get all field names
        all_fields = set()
        for result in chunk_results:
            all_fields.update(result.keys())
        
        synthesized = {}
        
        for field_name in all_fields:
            # Collect all extractions for this field
            field_extractions = []
            
            for result in chunk_results:
                if field_name in result and result[field_name].value is not None:
                    field_extractions.append(result[field_name])
            
            if field_extractions:
                # Choose the extraction with highest confidence
                best_extraction = max(field_extractions, key=lambda x: x.confidence_score)
                synthesized[field_name] = best_extraction
            else:
                # No valid extractions found
                synthesized[field_name] = ExtractionField(
                    value=None,
                    source_text=None,
                    confidence_score=0.0
                )
        
        return synthesized
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
