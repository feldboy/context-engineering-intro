from fastapi import Depends
from ..agents.document_analysis_agent import DocumentAnalysisAgent
from ..config.settings import settings
import logging

logger = logging.getLogger(__name__)

# Global agent instance
_agent_instance = None


def get_document_analysis_agent() -> DocumentAnalysisAgent:
    """
    Dependency to get the document analysis agent instance.
    
    Returns:
        DocumentAnalysisAgent instance
    """
    global _agent_instance
    
    if _agent_instance is None:
        _agent_instance = DocumentAnalysisAgent()
        logger.info("Created new DocumentAnalysisAgent instance")
    
    return _agent_instance


def get_settings():
    """
    Dependency to get application settings.
    
    Returns:
        Application settings
    """
    return settings
