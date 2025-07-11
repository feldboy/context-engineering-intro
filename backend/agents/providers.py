from typing import Dict, Any, Optional
from enum import Enum
import logging
from ..config.settings import settings

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"


class LLMProviderConfig:
    """Configuration for LLM providers."""
    
    def __init__(self):
        self.providers = {
            LLMProvider.OPENAI: {
                "api_base": "https://api.openai.com/v1",
                "model": "gpt-4",
                "api_key": settings.openai_api_key,
                "headers": {"Authorization": f"Bearer {settings.openai_api_key}"},
                "supports_json_mode": True
            },
            LLMProvider.ANTHROPIC: {
                "api_base": "https://api.anthropic.com/v1",
                "model": "claude-3-sonnet-20240229",
                "api_key": settings.anthropic_api_key,
                "headers": {
                    "x-api-key": settings.anthropic_api_key,
                    "content-type": "application/json",
                    "anthropic-version": "2023-06-01"
                },
                "supports_json_mode": False
            },
            LLMProvider.DEEPSEEK: {
                "api_base": "https://api.deepseek.com/v1",
                "model": "deepseek-chat",
                "api_key": settings.deepseek_api_key,
                "headers": {"Authorization": f"Bearer {settings.deepseek_api_key}"},
                "supports_json_mode": True
            }
        }
    
    def get_provider_config(self, provider: LLMProvider) -> Dict[str, Any]:
        """
        Get configuration for a specific provider.
        
        Args:
            provider: LLM provider
            
        Returns:
            Provider configuration
        """
        if provider not in self.providers:
            raise ValueError(f"Unsupported provider: {provider}")
        
        config = self.providers[provider]
        
        if not config["api_key"]:
            raise ValueError(f"API key not configured for provider: {provider}")
        
        return config
    
    def get_available_providers(self) -> list[LLMProvider]:
        """
        Get list of available providers (those with API keys configured).
        
        Returns:
            List of available providers
        """
        available = []
        
        for provider, config in self.providers.items():
            if config["api_key"]:
                available.append(provider)
        
        return available
    
    def get_best_provider(self, prefer_json_mode: bool = True) -> Optional[LLMProvider]:
        """
        Get the best available provider based on preferences.
        
        Args:
            prefer_json_mode: Whether to prefer providers that support JSON mode
            
        Returns:
            Best available provider or None
        """
        available = self.get_available_providers()
        
        if not available:
            return None
        
        # If preferring JSON mode, filter by that capability
        if prefer_json_mode:
            json_capable = [
                p for p in available 
                if self.providers[p]["supports_json_mode"]
            ]
            if json_capable:
                available = json_capable
        
        # Priority order: OpenAI, Anthropic, DeepSeek
        priority_order = [LLMProvider.OPENAI, LLMProvider.ANTHROPIC, LLMProvider.DEEPSEEK]
        
        for provider in priority_order:
            if provider in available:
                return provider
        
        # Return first available if no priority match
        return available[0]
    
    def validate_configuration(self) -> Dict[str, Any]:
        """
        Validate provider configurations.
        
        Returns:
            Validation report
        """
        report = {
            "valid_providers": [],
            "invalid_providers": [],
            "missing_keys": [],
            "total_available": 0
        }
        
        for provider, config in self.providers.items():
            if config["api_key"]:
                report["valid_providers"].append(provider.value)
                report["total_available"] += 1
            else:
                report["invalid_providers"].append(provider.value)
                report["missing_keys"].append(f"{provider.value.upper()}_API_KEY")
        
        return report


# Global provider configuration instance
provider_config = LLMProviderConfig()
