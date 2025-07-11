import React, { useState, useEffect } from 'react';
import DocumentViewer from './DocumentViewer.jsx';
import ExtractionForm from './ExtractionForm.jsx';

const VerificationUI = ({ 
  documentUrl, 
  extractionResult, 
  schema,
  onFieldUpdate = () => {},
  onVerificationComplete = () => {},
  onFlagForReview = () => {}
}) => {
  const [currentFieldName, setCurrentFieldName] = useState(null);
  const [highlights, setHighlights] = useState([]);
  const [verificationStatus, setVerificationStatus] = useState({});
  const [showLowConfidenceOnly, setShowLowConfidenceOnly] = useState(false);
  const [notes, setNotes] = useState({});

  // Initialize verification status and highlights
  useEffect(() => {
    if (!extractionResult || !extractionResult.extracted_fields) return;

    const initialStatus = {};
    const initialHighlights = [];

    extractionResult.extracted_fields.forEach(field => {
      initialStatus[field.name] = {
        verified: false,
        needsReview: field.confidence < 0.7,
        confidence: field.confidence
      };

      // Create highlights for fields with source text
      if (field.source_text && field.source_location) {
        initialHighlights.push({
          fieldName: field.name,
          text: field.source_text,
          page: field.source_location.page || 1,
          x: field.source_location.x || 0,
          y: field.source_location.y || 0,
          width: field.source_location.width || 100,
          height: field.source_location.height || 20,
          color: field.confidence < 0.7 ? 'rgba(255, 0, 0, 0.3)' : 'rgba(0, 255, 0, 0.3)'
        });
      }
    });

    setVerificationStatus(initialStatus);
    setHighlights(initialHighlights);
  }, [extractionResult]);

  // Handle field selection
  const handleFieldClick = (fieldName) => {
    setCurrentFieldName(fieldName);
    
    // Scroll to the field's source location in the document
    const highlight = highlights.find(h => h.fieldName === fieldName);
    if (highlight) {
      // Document viewer will handle highlighting the selected field
    }
  };

  // Handle text selection from document
  const handleTextSelect = (selectionData) => {
    if (currentFieldName) {
      // Update the field's source text based on selection
      const updatedField = {
        ...extractionResult.extracted_fields.find(f => f.name === currentFieldName),
        source_text: selectionData.text,
        source_location: {
          page: selectionData.page,
          x: selectionData.x,
          y: selectionData.y,
          width: selectionData.width,
          height: selectionData.height
        }
      };

      onFieldUpdate(currentFieldName, updatedField);
      
      // Update highlights
      const newHighlights = highlights.map(h => 
        h.fieldName === currentFieldName 
          ? { ...h, ...selectionData, text: selectionData.text }
          : h
      );
      setHighlights(newHighlights);
    }
  };

  // Handle field value changes
  const handleFieldValueChange = (fieldName, newValue) => {
    const field = extractionResult.extracted_fields.find(f => f.name === fieldName);
    if (field) {
      const updatedField = {
        ...field,
        value: newValue,
        manually_edited: true
      };
      onFieldUpdate(fieldName, updatedField);
    }
  };

  // Handle field verification
  const handleFieldVerify = (fieldName, isVerified) => {
    setVerificationStatus(prev => ({
      ...prev,
      [fieldName]: {
        ...prev[fieldName],
        verified: isVerified,
        needsReview: isVerified ? false : prev[fieldName].needsReview
      }
    }));
  };

  // Handle field flagging for review
  const handleFieldFlag = (fieldName, flagged) => {
    setVerificationStatus(prev => ({
      ...prev,
      [fieldName]: {
        ...prev[fieldName],
        needsReview: flagged
      }
    }));
    
    onFlagForReview(fieldName, flagged);
  };

  // Handle notes update
  const handleNotesUpdate = (fieldName, note) => {
    setNotes(prev => ({
      ...prev,
      [fieldName]: note
    }));
  };

  // Complete verification
  const handleCompleteVerification = () => {
    const verifiedFields = extractionResult.extracted_fields.map(field => ({
      ...field,
      verification_status: verificationStatus[field.name],
      notes: notes[field.name] || ''
    }));

    onVerificationComplete({
      ...extractionResult,
      extracted_fields: verifiedFields,
      verification_completed: true,
      verification_timestamp: new Date().toISOString()
    });
  };

  // Filter fields based on confidence
  const filteredFields = extractionResult?.extracted_fields?.filter(field => {
    if (!showLowConfidenceOnly) return true;
    return field.confidence < 0.7;
  }) || [];

  // Get verification stats
  const getVerificationStats = () => {
    const total = extractionResult?.extracted_fields?.length || 0;
    const verified = Object.values(verificationStatus).filter(s => s.verified).length;
    const needsReview = Object.values(verificationStatus).filter(s => s.needsReview).length;
    
    return { total, verified, needsReview };
  };

  const stats = getVerificationStats();

  return React.createElement('div', { className: 'verification-ui' },
    // Header with stats
    React.createElement('div', { className: 'verification-header' },
      React.createElement('div', { className: 'verification-stats' },
        React.createElement('span', { className: 'stat-item' }, 
          `Total Fields: ${stats.total}`
        ),
        React.createElement('span', { className: 'stat-item' }, 
          `Verified: ${stats.verified}`
        ),
        React.createElement('span', { className: 'stat-item stat-warning' }, 
          `Needs Review: ${stats.needsReview}`
        )
      ),
      React.createElement('div', { className: 'verification-controls' },
        React.createElement('label', { className: 'checkbox-label' },
          React.createElement('input', {
            type: 'checkbox',
            checked: showLowConfidenceOnly,
            onChange: (e) => setShowLowConfidenceOnly(e.target.checked)
          }),
          'Show Low Confidence Only'
        ),
        React.createElement('button', {
          className: 'btn btn-primary',
          onClick: handleCompleteVerification,
          disabled: stats.needsReview > 0
        }, 'Complete Verification')
      )
    ),

    // Main content area
    React.createElement('div', { className: 'verification-content' },
      // Document viewer
      React.createElement('div', { className: 'document-panel' },
        React.createElement('h3', null, 'Document'),
        React.createElement(DocumentViewer, {
          documentUrl: documentUrl,
          highlights: highlights,
          onTextSelect: handleTextSelect,
          selectedFieldName: currentFieldName
        })
      ),

      // Extraction form
      React.createElement('div', { className: 'extraction-panel' },
        React.createElement('h3', null, 'Extracted Data'),
        React.createElement(ExtractionForm, {
          fields: filteredFields,
          schema: schema,
          verificationStatus: verificationStatus,
          currentFieldName: currentFieldName,
          notes: notes,
          onFieldClick: handleFieldClick,
          onFieldValueChange: handleFieldValueChange,
          onFieldVerify: handleFieldVerify,
          onFieldFlag: handleFieldFlag,
          onNotesUpdate: handleNotesUpdate
        })
      )
    ),

    // Instructions panel
    React.createElement('div', { className: 'instructions-panel' },
      React.createElement('h4', null, 'Instructions'),
      React.createElement('ul', null,
        React.createElement('li', null, 'Click on a field in the form to highlight it in the document'),
        React.createElement('li', null, 'Select text in the document to update field source location'),
        React.createElement('li', null, 'Edit field values directly in the form'),
        React.createElement('li', null, 'Mark fields as verified when confident in the extraction'),
        React.createElement('li', null, 'Flag fields for review if they need additional attention'),
        React.createElement('li', null, 'Add notes to explain any changes or concerns')
      )
    )
  );
};

export default VerificationUI;
