import React, { useState, useEffect, useRef } from 'react';
import * as pdfjsLib from 'pdfjs-dist';
import 'pdfjs-dist/build/pdf.worker.entry';

const DocumentViewer = ({ 
  documentUrl, 
  highlights = [], 
  onTextSelect = () => {}, 
  onPageChange = () => {},
  selectedFieldName = null 
}) => {
  const [pdfDocument, setPdfDocument] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [scale, setScale] = useState(1.0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const canvasRef = useRef(null);
  const textLayerRef = useRef(null);

  // Load PDF document
  useEffect(() => {
    if (!documentUrl) return;

    const loadPDF = async () => {
      setLoading(true);
      setError(null);
      try {
        const pdf = await pdfjsLib.getDocument(documentUrl).promise;
        setPdfDocument(pdf);
        setTotalPages(pdf.numPages);
        setCurrentPage(1);
      } catch (err) {
        setError(`Failed to load PDF: ${err.message}`);
      } finally {
        setLoading(false);
      }
    };

    loadPDF();
  }, [documentUrl]);

  // Render current page
  useEffect(() => {
    if (!pdfDocument || !canvasRef.current) return;

    const renderPage = async () => {
      try {
        const page = await pdfDocument.getPage(currentPage);
        const viewport = page.getViewport({ scale });
        
        const canvas = canvasRef.current;
        const context = canvas.getContext('2d');
        
        canvas.height = viewport.height;
        canvas.width = viewport.width;

        const renderContext = {
          canvasContext: context,
          viewport: viewport
        };

        await page.render(renderContext).promise;
        
        // Render text layer for selection
        await renderTextLayer(page, viewport);
        
        // Apply highlights
        applyHighlights(page, viewport);
        
      } catch (err) {
        setError(`Failed to render page: ${err.message}`);
      }
    };

    renderPage();
  }, [pdfDocument, currentPage, scale]);

  // Render text layer for text selection
  const renderTextLayer = async (page, viewport) => {
    if (!textLayerRef.current) return;

    const textContent = await page.getTextContent();
    const textLayer = textLayerRef.current;
    
    // Clear previous text layer
    textLayer.innerHTML = '';
    textLayer.style.height = `${viewport.height}px`;
    textLayer.style.width = `${viewport.width}px`;

    // Create text layer using PDF.js utilities
    const textLayerFactory = new pdfjsLib.TextLayerBuilder({
      textLayerDiv: textLayer,
      pageIndex: currentPage - 1,
      viewport: viewport
    });

    textLayerFactory.setTextContent(textContent);
    textLayerFactory.render();
  };

  // Apply highlights to the document
  const applyHighlights = (page, viewport) => {
    if (!highlights.length) return;

    const highlightLayer = document.getElementById('highlight-layer');
    if (!highlightLayer) return;

    // Clear previous highlights
    highlightLayer.innerHTML = '';
    highlightLayer.style.height = `${viewport.height}px`;
    highlightLayer.style.width = `${viewport.width}px`;

    highlights.forEach(highlight => {
      if (highlight.page === currentPage) {
        const highlightDiv = document.createElement('div');
        highlightDiv.className = `highlight ${highlight.fieldName === selectedFieldName ? 'selected' : ''}`;
        highlightDiv.style.position = 'absolute';
        highlightDiv.style.left = `${highlight.x * scale}px`;
        highlightDiv.style.top = `${highlight.y * scale}px`;
        highlightDiv.style.width = `${highlight.width * scale}px`;
        highlightDiv.style.height = `${highlight.height * scale}px`;
        highlightDiv.style.backgroundColor = highlight.color || 'rgba(255, 255, 0, 0.3)';
        highlightDiv.style.border = highlight.fieldName === selectedFieldName ? '2px solid #007bff' : 'none';
        highlightDiv.title = `${highlight.fieldName}: ${highlight.text}`;
        
        highlightDiv.addEventListener('click', () => {
          onTextSelect(highlight);
        });
        
        highlightLayer.appendChild(highlightDiv);
      }
    });
  };

  // Handle text selection
  const handleTextSelection = () => {
    const selection = window.getSelection();
    if (selection.rangeCount === 0) return;

    const range = selection.getRangeAt(0);
    const selectedText = range.toString().trim();
    
    if (selectedText) {
      const rect = range.getBoundingClientRect();
      const canvasRect = canvasRef.current.getBoundingClientRect();
      
      const selectionData = {
        text: selectedText,
        page: currentPage,
        x: (rect.left - canvasRect.left) / scale,
        y: (rect.top - canvasRect.top) / scale,
        width: rect.width / scale,
        height: rect.height / scale
      };
      
      onTextSelect(selectionData);
    }
  };

  // Navigation handlers
  const goToPreviousPage = () => {
    if (currentPage > 1) {
      const newPage = currentPage - 1;
      setCurrentPage(newPage);
      onPageChange(newPage);
    }
  };

  const goToNextPage = () => {
    if (currentPage < totalPages) {
      const newPage = currentPage + 1;
      setCurrentPage(newPage);
      onPageChange(newPage);
    }
  };

  const goToPage = (pageNumber) => {
    if (pageNumber >= 1 && pageNumber <= totalPages) {
      setCurrentPage(pageNumber);
      onPageChange(pageNumber);
    }
  };

  // Zoom handlers
  const zoomIn = () => {
    setScale(prev => Math.min(prev * 1.2, 3.0));
  };

  const zoomOut = () => {
    setScale(prev => Math.max(prev / 1.2, 0.5));
  };

  const resetZoom = () => {
    setScale(1.0);
  };

  if (loading) {
    return React.createElement('div', { className: 'document-viewer loading' },
      React.createElement('div', { className: 'loading-spinner' }, 'Loading document...')
    );
  }

  if (error) {
    return React.createElement('div', { className: 'document-viewer error' },
      React.createElement('div', { className: 'error-message' }, error)
    );
  }

  return React.createElement('div', { className: 'document-viewer' },
    // Toolbar
    React.createElement('div', { className: 'document-toolbar' },
      React.createElement('div', { className: 'navigation-controls' },
        React.createElement('button', { 
          onClick: goToPreviousPage, 
          disabled: currentPage <= 1,
          className: 'btn btn-sm'
        }, 'Previous'),
        React.createElement('span', { className: 'page-info' },
          'Page ',
          React.createElement('input', { 
            type: 'number', 
            value: currentPage, 
            onChange: (e) => goToPage(parseInt(e.target.value)),
            min: '1', 
            max: totalPages,
            className: 'page-input'
          }),
          ` of ${totalPages}`
        ),
        React.createElement('button', { 
          onClick: goToNextPage, 
          disabled: currentPage >= totalPages,
          className: 'btn btn-sm'
        }, 'Next')
      ),
      React.createElement('div', { className: 'zoom-controls' },
        React.createElement('button', { onClick: zoomOut, className: 'btn btn-sm' }, 'Zoom Out'),
        React.createElement('span', { className: 'zoom-level' }, `${Math.round(scale * 100)}%`),
        React.createElement('button', { onClick: zoomIn, className: 'btn btn-sm' }, 'Zoom In'),
        React.createElement('button', { onClick: resetZoom, className: 'btn btn-sm' }, 'Reset')
      )
    ),
    // Document container
    React.createElement('div', { className: 'document-container' },
      React.createElement('div', { className: 'document-page', style: { position: 'relative' } },
        React.createElement('canvas', { 
          ref: canvasRef,
          className: 'pdf-canvas'
        }),
        React.createElement('div', { 
          ref: textLayerRef,
          className: 'text-layer',
          style: {
            position: 'absolute',
            left: 0,
            top: 0,
            right: 0,
            bottom: 0,
            overflow: 'hidden',
            opacity: 0.2,
            lineHeight: 1.0,
            pointerEvents: 'auto'
          },
          onMouseUp: handleTextSelection
        }),
        React.createElement('div', { 
          id: 'highlight-layer',
          className: 'highlight-layer',
          style: {
            position: 'absolute',
            left: 0,
            top: 0,
            right: 0,
            bottom: 0,
            pointerEvents: 'auto'
          }
        })
      )
    )
  );
};

export default DocumentViewer;
