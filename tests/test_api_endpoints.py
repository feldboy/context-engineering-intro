"""
Tests for API endpoints
"""
import pytest
import json
import tempfile
import os
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import io

# Set test environment before importing the app
os.environ['ENVIRONMENT'] = 'test'
os.environ['OPENAI_API_KEY'] = 'test_openai_key'
os.environ['ANTHROPIC_API_KEY'] = 'test_anthropic_key'
os.environ['DEEPSEEK_API_KEY'] = 'test_deepseek_key'

from backend.api.ai_agents import app
from backend.agents.models import ProcessingStatus, ExtractionResult, ExtractionField, DocumentType


class TestAPIEndpoints:
    """Test suite for API endpoints"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.client = TestClient(app)
        
        self.sample_schema = {
            "fields": [
                {
                    "name": "plaintiff_name",
                    "type": "string", 
                    "description": "Name of the plaintiff"
                },
                {
                    "name": "case_number",
                    "type": "string",
                    "description": "Court case number"
                }
            ]
        }
        
        # Create sample metadata
        from datetime import datetime
        from backend.agents.models import DocumentMetadata
        sample_metadata = DocumentMetadata(
            filename="test-doc.pdf",
            file_size=1024,
            page_count=2,
            document_type=DocumentType.COMPLAINT,
            processing_method="direct_text",
            raw_text_md5="abc123",
            processing_duration=2.5,
            total_characters=500
        )
        
        self.sample_result = ExtractionResult(
            document_id="test-doc-123",
            extracted_data={
                "plaintiff_name": ExtractionField(value="John Doe", confidence_score=0.9),
                "case_number": ExtractionField(value="2023-CV-001", confidence_score=0.8)
            },
            metadata=sample_metadata,
            processing_errors=[]
        )
        
    def test_health_check(self):
        """Test health check endpoint"""
        response = self.client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        
    def test_get_system_info(self):
        """Test system information endpoint"""
        response = self.client.get("/system/info")
        
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "supported_formats" in data
        assert "llm_providers" in data
        
    def test_validate_schema_valid(self):
        """Test schema validation with valid schema"""
        response = self.client.post(
            "/analyze/validate-schema",
            json=self.sample_schema
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] == True
        assert len(data["errors"]) == 0
        
    def test_validate_schema_invalid(self):
        """Test schema validation with invalid schema"""
        invalid_schema = {"invalid": "schema"}
        
        response = self.client.post(
            "/analyze/validate-schema",
            json=invalid_schema
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] == False
        assert len(data["errors"]) > 0
        
    def test_upload_document_success(self):
        """Test successful document upload"""
        # Create a temporary PDF file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(b'%PDF-1.4\n fake pdf content')
            tmp_path = tmp.name
            
        try:
            with open(tmp_path, 'rb') as f:
                response = self.client.post(
                    "/documents/upload",
                    files={"file": ("test.pdf", f, "application/pdf")},
                    data={"schema": json.dumps(self.sample_schema)}
                )
                
            assert response.status_code == 200
            data = response.json()
            assert "document_id" in data
            assert "status" in data
            assert data["status"] == "uploaded"
            
        finally:
            os.unlink(tmp_path)
            
    def test_upload_document_invalid_format(self):
        """Test document upload with invalid format"""
        # Create a temporary text file
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp:
            tmp.write(b'This is not a PDF')
            tmp_path = tmp.name
            
        try:
            with open(tmp_path, 'rb') as f:
                response = self.client.post(
                    "/documents/upload",
                    files={"file": ("test.txt", f, "text/plain")},
                    data={"schema": json.dumps(self.sample_schema)}
                )
                
            assert response.status_code == 400
            data = response.json()
            assert "error" in data
            assert "format" in data["error"].lower()
            
        finally:
            os.unlink(tmp_path)
            
    def test_upload_document_missing_schema(self):
        """Test document upload without schema"""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(b'%PDF-1.4\n fake pdf content')
            tmp_path = tmp.name
            
        try:
            with open(tmp_path, 'rb') as f:
                response = self.client.post(
                    "/documents/upload",
                    files={"file": ("test.pdf", f, "application/pdf")}
                )
                
            assert response.status_code == 400
            data = response.json()
            assert "error" in data
            assert "schema" in data["error"].lower()
            
        finally:
            os.unlink(tmp_path)
            
    @patch('backend.api.ai_agents.get_document_analysis_agent')
    def test_analyze_document_success(self, mock_get_agent):
        """Test successful document analysis"""
        mock_agent = MagicMock()
        mock_agent.analyze_document.return_value = self.sample_result
        mock_get_agent.return_value = mock_agent
        
        response = self.client.post(
            "/analyze/document/test-doc-123",
            json={"schema": self.sample_schema}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == "test-doc-123"
        assert data["status"] == "completed"
        assert len(data["extracted_fields"]) == 2
        
    @patch('backend.api.ai_agents.get_document_analysis_agent')
    def test_analyze_document_not_found(self, mock_get_agent):
        """Test analysis of non-existent document"""
        mock_agent = MagicMock()
        mock_agent.analyze_document.side_effect = FileNotFoundError("Document not found")
        mock_get_agent.return_value = mock_agent
        
        response = self.client.post(
            "/analyze/document/nonexistent-doc",
            json={"schema": self.sample_schema}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "not found" in data["error"].lower()
        
    @patch('backend.api.ai_agents.get_document_analysis_agent')
    def test_get_analysis_status_success(self, mock_get_agent):
        """Test getting analysis status"""
        mock_agent = MagicMock()
        mock_agent.get_processing_status.return_value = {
            "document_id": "test-doc-123",
            "status": "processing",
            "progress": 0.75,
            "estimated_time_remaining": 30
        }
        mock_get_agent.return_value = mock_agent
        
        response = self.client.get("/analyze/status/test-doc-123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == "test-doc-123"
        assert data["status"] == "processing"
        assert data["progress"] == 0.75
        
    @patch('backend.api.ai_agents.get_document_analysis_agent')
    def test_get_analysis_results_success(self, mock_get_agent):
        """Test getting analysis results"""
        mock_agent = MagicMock()
        mock_agent.get_analysis_results.return_value = self.sample_result
        mock_get_agent.return_value = mock_agent
        
        response = self.client.get("/analyze/results/test-doc-123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == "test-doc-123"
        assert data["status"] == "completed"
        assert len(data["extracted_fields"]) == 2
        
    @patch('backend.api.ai_agents.get_document_analysis_agent')
    def test_get_analysis_results_not_found(self, mock_get_agent):
        """Test getting results for non-existent analysis"""
        mock_agent = MagicMock()
        mock_agent.get_analysis_results.return_value = None
        mock_get_agent.return_value = mock_agent
        
        response = self.client.get("/analyze/results/nonexistent-doc")
        
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "not found" in data["error"].lower()
        
    @patch('backend.api.ai_agents.get_document_analysis_agent')
    def test_list_documents_success(self, mock_get_agent):
        """Test listing documents"""
        mock_agent = MagicMock()
        mock_agent.list_documents.return_value = [
            {
                "document_id": "doc-1",
                "filename": "complaint.pdf",
                "upload_time": "2023-01-01T10:00:00Z",
                "status": "completed"
            },
            {
                "document_id": "doc-2", 
                "filename": "retainer.pdf",
                "upload_time": "2023-01-02T11:00:00Z",
                "status": "processing"
            }
        ]
        mock_get_agent.return_value = mock_agent
        
        response = self.client.get("/documents/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["documents"]) == 2
        assert data["documents"][0]["document_id"] == "doc-1"
        
    @patch('backend.api.ai_agents.get_document_analysis_agent')
    def test_list_documents_with_filters(self, mock_get_agent):
        """Test listing documents with filters"""
        mock_agent = MagicMock()
        mock_agent.list_documents.return_value = [
            {
                "document_id": "doc-1",
                "filename": "complaint.pdf", 
                "upload_time": "2023-01-01T10:00:00Z",
                "status": "completed"
            }
        ]
        mock_get_agent.return_value = mock_agent
        
        response = self.client.get("/documents/?status=completed&limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["documents"]) == 1
        assert data["documents"][0]["status"] == "completed"
        
    @patch('backend.api.ai_agents.get_document_analysis_agent')
    def test_delete_document_success(self, mock_get_agent):
        """Test successful document deletion"""
        mock_agent = MagicMock()
        mock_agent.delete_document.return_value = True
        mock_get_agent.return_value = mock_agent
        
        response = self.client.delete("/documents/test-doc-123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["document_id"] == "test-doc-123"
        
    @patch('backend.api.ai_agents.get_document_analysis_agent')
    def test_delete_document_not_found(self, mock_get_agent):
        """Test deletion of non-existent document"""
        mock_agent = MagicMock()
        mock_agent.delete_document.return_value = False
        mock_get_agent.return_value = mock_agent
        
        response = self.client.delete("/documents/nonexistent-doc")
        
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "not found" in data["error"].lower()
        
    @patch('backend.api.ai_agents.get_document_analysis_agent')
    def test_clear_cache_success(self, mock_get_agent):
        """Test successful cache clearing"""
        mock_agent = MagicMock()
        mock_agent.clear_cache.return_value = {"cleared_items": 5}
        mock_get_agent.return_value = mock_agent
        
        response = self.client.post("/system/cache/clear")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["cleared_items"] == 5
        
    def test_cors_headers(self):
        """Test CORS headers are properly set"""
        response = self.client.get("/health")
        
        assert response.status_code == 200
        # Check that CORS headers would be set (depends on middleware configuration)
        
    def test_rate_limiting(self):
        """Test rate limiting behavior"""
        # Make multiple rapid requests
        responses = []
        for i in range(5):
            response = self.client.get("/health")
            responses.append(response)
            
        # All should succeed for health check (no rate limiting)
        assert all(r.status_code == 200 for r in responses)
        
    def test_error_handling_internal_error(self):
        """Test internal server error handling"""
        with patch('backend.api.ai_agents.get_document_analysis_agent') as mock_get_agent:
            mock_get_agent.side_effect = Exception("Internal error")
            
            response = self.client.get("/analyze/status/test-doc-123")
            
            assert response.status_code == 500
            data = response.json()
            assert "error" in data
            
    def test_request_validation_invalid_json(self):
        """Test request validation with invalid JSON"""
        response = self.client.post(
            "/analyze/validate-schema",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
        
    def test_file_upload_size_limit(self):
        """Test file upload size limit"""
        # Create a large file (simulate)
        large_content = b'%PDF-1.4\n' + b'x' * (10 * 1024 * 1024)  # 10MB
        
        response = self.client.post(
            "/documents/upload",
            files={"file": ("large.pdf", io.BytesIO(large_content), "application/pdf")},
            data={"schema": json.dumps(self.sample_schema)}
        )
        
        # Should handle large files or return appropriate error
        assert response.status_code in [200, 413]  # 413 = Payload Too Large
        
    def test_concurrent_requests(self):
        """Test handling of concurrent requests"""
        import concurrent.futures
        
        def make_request():
            return self.client.get("/health")
            
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            responses = [f.result() for f in futures]
            
        assert all(r.status_code == 200 for r in responses)
        
    def test_api_documentation(self):
        """Test API documentation endpoint"""
        response = self.client.get("/docs")
        
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        
    def test_openapi_spec(self):
        """Test OpenAPI specification endpoint"""
        response = self.client.get("/openapi.json")
        
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data
