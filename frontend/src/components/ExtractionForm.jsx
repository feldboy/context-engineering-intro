import React, { useState, useEffect } from 'react';

const ExtractionForm = ({ 
  fields = [],
  schema = {},
  verificationStatus = {},
  currentFieldName = null,
  notes = {},
  onFieldClick = () => {},
  onFieldValueChange = () => {},
  onFieldVerify = () => {},
  onFieldFlag = () => {},
  onNotesUpdate = () => {}
}) => {
  const [editingField, setEditingField] = useState(null);
  const [tempValues, setTempValues] = useState({});

  // Initialize temp values
  useEffect(() => {
    const initialValues = {};
    fields.forEach(field => {
      initialValues[field.name] = field.value || '';
    });
    setTempValues(initialValues);
  }, [fields]);

  // Get field schema information
  const getFieldSchema = (fieldName) => {
    return schema.fields?.find(f => f.name === fieldName) || {};
  };

  // Handle field editing
  const handleStartEdit = (fieldName) => {
    setEditingField(fieldName);
    setTempValues(prev => ({
      ...prev,
      [fieldName]: fields.find(f => f.name === fieldName)?.value || ''
    }));
  };

  const handleSaveEdit = (fieldName) => {
    const newValue = tempValues[fieldName];
    onFieldValueChange(fieldName, newValue);
    setEditingField(null);
  };

  const handleCancelEdit = (fieldName) => {
    setTempValues(prev => ({
      ...prev,
      [fieldName]: fields.find(f => f.name === fieldName)?.value || ''
    }));
    setEditingField(null);
  };

  // Handle input changes
  const handleInputChange = (fieldName, value) => {
    setTempValues(prev => ({
      ...prev,
      [fieldName]: value
    }));
  };

  // Render field input based on type
  const renderFieldInput = (field, fieldSchema) => {
    const isEditing = editingField === field.name;
    const value = isEditing ? tempValues[field.name] : field.value;
    
    if (!isEditing) {
      return React.createElement('div', { 
        className: 'field-value-display',
        onClick: () => handleStartEdit(field.name)
      },
        React.createElement('span', { className: 'field-value' }, value || 'No value'),
        React.createElement('button', { 
          className: 'btn btn-sm btn-edit',
          onClick: (e) => {
            e.stopPropagation();
            handleStartEdit(field.name);
          }
        }, 'Edit')
      );
    }

    const commonProps = {
      value: value,
      onChange: (e) => handleInputChange(field.name, e.target.value),
      className: 'form-control'
    };

    switch (fieldSchema.type) {
      case 'number':
        return React.createElement('div', { className: 'field-input-group' },
          React.createElement('input', {
            ...commonProps,
            type: 'number',
            step: 'any'
          }),
          React.createElement('div', { className: 'input-actions' },
            React.createElement('button', { 
              className: 'btn btn-sm btn-success',
              onClick: () => handleSaveEdit(field.name)
            }, 'Save'),
            React.createElement('button', { 
              className: 'btn btn-sm btn-secondary',
              onClick: () => handleCancelEdit(field.name)
            }, 'Cancel')
          )
        );
      
      case 'date':
        return React.createElement('div', { className: 'field-input-group' },
          React.createElement('input', {
            ...commonProps,
            type: 'date'
          }),
          React.createElement('div', { className: 'input-actions' },
            React.createElement('button', { 
              className: 'btn btn-sm btn-success',
              onClick: () => handleSaveEdit(field.name)
            }, 'Save'),
            React.createElement('button', { 
              className: 'btn btn-sm btn-secondary',
              onClick: () => handleCancelEdit(field.name)
            }, 'Cancel')
          )
        );
      
      case 'boolean':
        return React.createElement('div', { className: 'field-input-group' },
          React.createElement('select', {
            ...commonProps,
            value: value === true ? 'true' : value === false ? 'false' : '',
            onChange: (e) => handleInputChange(field.name, e.target.value === 'true')
          },
            React.createElement('option', { value: '' }, 'Select...'),
            React.createElement('option', { value: 'true' }, 'Yes'),
            React.createElement('option', { value: 'false' }, 'No')
          ),
          React.createElement('div', { className: 'input-actions' },
            React.createElement('button', { 
              className: 'btn btn-sm btn-success',
              onClick: () => handleSaveEdit(field.name)
            }, 'Save'),
            React.createElement('button', { 
              className: 'btn btn-sm btn-secondary',
              onClick: () => handleCancelEdit(field.name)
            }, 'Cancel')
          )
        );
      
      default:
        return React.createElement('div', { className: 'field-input-group' },
          React.createElement('textarea', {
            ...commonProps,
            rows: 3
          }),
          React.createElement('div', { className: 'input-actions' },
            React.createElement('button', { 
              className: 'btn btn-sm btn-success',
              onClick: () => handleSaveEdit(field.name)
            }, 'Save'),
            React.createElement('button', { 
              className: 'btn btn-sm btn-secondary',
              onClick: () => handleCancelEdit(field.name)
            }, 'Cancel')
          )
        );
    }
  };

  // Render confidence indicator
  const renderConfidenceIndicator = (confidence) => {
    let className = 'confidence-indicator ';
    let label = '';
    
    if (confidence >= 0.8) {
      className += 'confidence-high';
      label = 'High';
    } else if (confidence >= 0.6) {
      className += 'confidence-medium';
      label = 'Medium';
    } else {
      className += 'confidence-low';
      label = 'Low';
    }
    
    return React.createElement('div', { className },
      React.createElement('span', { className: 'confidence-label' }, label),
      React.createElement('span', { className: 'confidence-value' }, `${Math.round(confidence * 100)}%`)
    );
  };

  // Render field status
  const renderFieldStatus = (fieldName) => {
    const status = verificationStatus[fieldName] || {};
    
    return React.createElement('div', { className: 'field-status' },
      React.createElement('div', { className: 'status-actions' },
        React.createElement('button', {
          className: `btn btn-sm ${status.verified ? 'btn-success' : 'btn-outline-success'}`,
          onClick: () => onFieldVerify(fieldName, !status.verified)
        }, status.verified ? 'Verified' : 'Verify'),
        React.createElement('button', {
          className: `btn btn-sm ${status.needsReview ? 'btn-warning' : 'btn-outline-warning'}`,
          onClick: () => onFieldFlag(fieldName, !status.needsReview)
        }, status.needsReview ? 'Flagged' : 'Flag')
      )
    );
  };

  // Render notes section
  const renderNotes = (fieldName) => {
    const note = notes[fieldName] || '';
    
    return React.createElement('div', { className: 'field-notes' },
      React.createElement('label', { className: 'notes-label' }, 'Notes:'),
      React.createElement('textarea', {
        className: 'form-control notes-input',
        value: note,
        onChange: (e) => onNotesUpdate(fieldName, e.target.value),
        placeholder: 'Add notes about this field...',
        rows: 2
      })
    );
  };

  return React.createElement('div', { className: 'extraction-form' },
    React.createElement('div', { className: 'form-header' },
      React.createElement('h4', null, 'Extracted Fields'),
      React.createElement('p', { className: 'form-description' }, 
        'Review and verify the extracted data. Click on field names to highlight them in the document.'
      )
    ),
    
    React.createElement('div', { className: 'fields-container' },
      fields.map(field => {
        const fieldSchema = getFieldSchema(field.name);
        const status = verificationStatus[field.name] || {};
        const isSelected = currentFieldName === field.name;
        
        return React.createElement('div', { 
          key: field.name,
          className: `field-item ${isSelected ? 'selected' : ''} ${status.needsReview ? 'needs-review' : ''}`
        },
          React.createElement('div', { className: 'field-header' },
            React.createElement('h5', { 
              className: 'field-name',
              onClick: () => onFieldClick(field.name)
            }, field.name),
            renderConfidenceIndicator(field.confidence),
            renderFieldStatus(field.name)
          ),
          
          React.createElement('div', { className: 'field-description' },
            fieldSchema.description || 'No description available'
          ),
          
          React.createElement('div', { className: 'field-content' },
            React.createElement('div', { className: 'field-input-section' },
              React.createElement('label', { className: 'field-label' }, 'Value:'),
              renderFieldInput(field, fieldSchema)
            ),
            
            field.source_text && React.createElement('div', { className: 'field-source' },
              React.createElement('label', { className: 'field-label' }, 'Source Text:'),
              React.createElement('div', { className: 'source-text' }, field.source_text)
            ),
            
            renderNotes(field.name)
          ),
          
          field.manually_edited && React.createElement('div', { className: 'field-badges' },
            React.createElement('span', { className: 'badge badge-info' }, 'Manually Edited')
          )
        );
      })
    ),
    
    fields.length === 0 && React.createElement('div', { className: 'no-fields' },
      React.createElement('p', null, 'No fields to display.')
    )
  );
};

export default ExtractionForm;
