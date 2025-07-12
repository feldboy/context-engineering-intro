import React, { useState, useEffect } from 'react';
import VerificationUI from './components/VerificationUI.jsx';
import './styles/verification.css';

const App = () => {
  const [documents, setDocuments] = useState([]);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [extractionResult, setExtractionResult] = useState(null);
  const [schema, setSchema] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Load documents on component mount
  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/documents/');
      const data = await response.json();
      setDocuments(data.documents || []);
    } catch (err) {
      setError(`Failed to load documents: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDocumentSelect = async (documentId) => {
    try {
      setLoading(true);
      setError(null);
      
      // Get extraction results
      const resultResponse = await fetch(`/api/analyze/results/${documentId}`);
      const resultData = await resultResponse.json();
      
      if (resultResponse.ok) {
        setExtractionResult(resultData);
        setSelectedDocument(documentId);
        
        // Get schema (assuming it's stored with the document)
        if (resultData.schema) {
          setSchema(resultData.schema);
        }
      } else {
        setError(resultData.error || 'Failed to load extraction results');
      }
    } catch (err) {
      setError(`Failed to load document: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleFieldUpdate = async (fieldName, updatedField) => {
    try {
      // Update the extraction result locally
      setExtractionResult(prev => ({
        ...prev,
        extracted_fields: prev.extracted_fields.map(field =>
          field.name === fieldName ? updatedField : field
        )
      }));
      
      // Send update to backend
      const response = await fetch(`/api/analyze/results/${selectedDocument}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          field_name: fieldName,
          updated_field: updatedField
        })
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to update field');
      }
    } catch (err) {
      setError(`Failed to update field: ${err.message}`);
    }
  };

  const handleVerificationComplete = async (verifiedResult) => {
    try {
      setLoading(true);
      
      const response = await fetch(`/api/analyze/results/${selectedDocument}/verify`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(verifiedResult)
      });
      
      if (response.ok) {
        // Update local state
        setExtractionResult(verifiedResult);
        
        // Show success message
        alert('Verification completed successfully!');
        
        // Refresh documents list
        loadDocuments();
      } else {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to complete verification');
      }
    } catch (err) {
      setError(`Failed to complete verification: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleFlagForReview = async (fieldName, flagged) => {
    try {
      const response = await fetch(`/api/analyze/results/${selectedDocument}/flag`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          field_name: fieldName,
          flagged: flagged
        })
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to flag field');
      }
    } catch (err) {
      setError(`Failed to flag field: ${err.message}`);
    }
  };

  const handleFileUpload = async (file, extractionSchema) => {
    try {
      setLoading(true);
      setError(null);
      
      const formData = new FormData();
      formData.append('file', file);
      formData.append('schema', JSON.stringify(extractionSchema));
      
      const response = await fetch('/api/documents/upload', {
        method: 'POST',
        body: formData
      });
      
      const data = await response.json();
      
      if (response.ok) {
        // Start analysis
        await analyzeDocument(data.document_id, extractionSchema);
        
        // Refresh documents list
        loadDocuments();
      } else {
        throw new Error(data.error || 'Failed to upload file');
      }
    } catch (err) {
      setError(`Failed to upload file: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const analyzeDocument = async (documentId, extractionSchema) => {
    try {
      const response = await fetch(`/api/analyze/document/${documentId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          schema: extractionSchema
        })
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to analyze document');
      }
      
      // Poll for completion
      pollAnalysisStatus(documentId);
    } catch (err) {
      setError(`Failed to analyze document: ${err.message}`);
    }
  };

  const pollAnalysisStatus = async (documentId) => {
    const maxAttempts = 30;
    let attempts = 0;
    
    const poll = async () => {
      try {
        const response = await fetch(`/api/analyze/status/${documentId}`);
        const data = await response.json();
        
        if (response.ok && data.status === 'completed') {
          // Analysis completed, load results
          handleDocumentSelect(documentId);
          return;
        }
        
        if (data.status === 'failed') {
          throw new Error(data.error || 'Analysis failed');
        }
        
        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 2000); // Poll every 2 seconds
        } else {
          throw new Error('Analysis timed out');
        }
      } catch (err) {
        setError(`Analysis failed: ${err.message}`);
      }
    };
    
    poll();
  };

  return React.createElement('div', { className: 'app' },
    React.createElement('div', { className: 'app-header' },
      React.createElement('h1', null, 'Document Analysis Agent'),
      React.createElement('p', null, 'AI-powered legal document analysis and verification')
    ),
    
    error && React.createElement('div', { className: 'error-banner' },
      React.createElement('span', null, error),
      React.createElement('button', { 
        onClick: () => setError(null),
        className: 'error-close'
      }, '×')
    ),
    
    loading && React.createElement('div', { className: 'loading-overlay' },
      React.createElement('div', { className: 'loading-spinner' }, 'Processing...')
    ),
    
    !selectedDocument ? 
      React.createElement(DocumentSelector, {
        documents: documents,
        onDocumentSelect: handleDocumentSelect,
        onFileUpload: handleFileUpload,
        loading: loading
      }) :
      React.createElement(VerificationUI, {
        documentUrl: `/api/documents/${selectedDocument}/file`,
        extractionResult: extractionResult,
        schema: schema,
        onFieldUpdate: handleFieldUpdate,
        onVerificationComplete: handleVerificationComplete,
        onFlagForReview: handleFlagForReview
      })
  );
};

// Document selector component
const DocumentSelector = ({ documents, onDocumentSelect, onFileUpload, loading }) => {
  const [selectedSchema, setSelectedSchema] = useState('');
  const [uploadFile, setUploadFile] = useState(null);

  const predefinedSchemas = {
    'complaint': {
      name: 'Legal Complaint',
      fields: [
        { name: 'plaintiff_name', type: 'string', description: 'Plaintiff name' },
        { name: 'defendant_name', type: 'string', description: 'Defendant name' },
        { name: 'case_number', type: 'string', description: 'Case number' },
        { name: 'court_name', type: 'string', description: 'Court name' },
        { name: 'medical_expenses', type: 'number', description: 'Medical expenses' }
      ]
    },
    'retainer': {
      name: 'Retainer Agreement',
      fields: [
        { name: 'client_name', type: 'string', description: 'Client name' },
        { name: 'attorney_name', type: 'string', description: 'Attorney name' },
        { name: 'law_firm_name', type: 'string', description: 'Law firm name' },
        { name: 'contingency_fee_percentage', type: 'number', description: 'Contingency fee %' }
      ]
    }
  };

  const handleUpload = () => {
    if (!uploadFile || !selectedSchema) return;
    
    const schema = predefinedSchemas[selectedSchema];
    if (schema) {
      onFileUpload(uploadFile, schema);
    }
  };

  return React.createElement('div', { className: 'document-selector' },
    React.createElement('div', { className: 'upload-section' },
      React.createElement('h2', null, 'Upload New Document'),
      React.createElement('div', { className: 'upload-form' },
        React.createElement('input', {
          type: 'file',
          accept: '.pdf',
          onChange: (e) => setUploadFile(e.target.files[0]),
          disabled: loading
        }),
        React.createElement('select', {
          value: selectedSchema,
          onChange: (e) => setSelectedSchema(e.target.value),
          disabled: loading
        },
          React.createElement('option', { value: '' }, 'Select document type...'),
          Object.entries(predefinedSchemas).map(([key, schema]) =>
            React.createElement('option', { key, value: key }, schema.name)
          )
        ),
        React.createElement('button', {
          onClick: handleUpload,
          disabled: !uploadFile || !selectedSchema || loading,
          className: 'btn btn-primary'
        }, 'Upload & Analyze')
      )
    ),
    
    React.createElement('div', { className: 'existing-documents' },
      React.createElement('h2', null, 'Existing Documents'),
      documents.length === 0 ? 
        React.createElement('p', null, 'No documents available.') :
        React.createElement('div', { className: 'documents-grid' },
          documents.map(doc => 
            React.createElement('div', { 
              key: doc.document_id,
              className: 'document-card',
              onClick: () => onDocumentSelect(doc.document_id)
            },
              React.createElement('h3', null, doc.filename),
              React.createElement('p', null, `Status: ${doc.status}`),
              React.createElement('p', null, `Uploaded: ${new Date(doc.upload_time).toLocaleDateString()}`)
            )
          )
        )
    )
  );
};

export default App;
