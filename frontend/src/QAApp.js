import React, { useState } from 'react';
import './App.css';

const App = () => {
  const [questionsFile, setQuestionsFile] = useState(null);
  const [answersFile, setAnswersFile] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  const handleQuestionsUpload = (event) => {
    const file = event.target.files[0];
    if (file && file.type === 'application/pdf') {
      setQuestionsFile(file);
      setError(null);
    } else {
      setError('Please upload a PDF file for questions');
    }
  };

  const handleAnswersUpload = (event) => {
    const file = event.target.files[0];
    if (file && file.type === 'application/pdf') {
      setAnswersFile(file);
      setError(null);
    } else {
      setError('Please upload a PDF file for answers');
    }
  };

  const processDocuments = async () => {
    if (!questionsFile || !answersFile) {
      setError('Please upload both questions and answers PDFs');
      return;
    }

    setIsProcessing(true);
    setError(null);
    setResults(null);

    try {
      // First, upload and analyze the questions document
      const questionsFormData = new FormData();
      questionsFormData.append('file', questionsFile);
      questionsFormData.append('extraction_schema', JSON.stringify({
        schema_name: "questions_extraction",
        fields: {
          "questions": {
            "type": "array",
            "description": "List of all questions found in the document"
          },
          "question_numbers": {
            "type": "array", 
            "description": "Question numbers or identifiers"
          },
          "question_topics": {
            "type": "array",
            "description": "Topics or subjects of each question"
          }
        }
      }));

      const questionsUploadResponse = await fetch('http://localhost:8000/api/documents/upload', {
        method: 'POST',
        body: questionsFormData
      });

      if (!questionsUploadResponse.ok) {
        throw new Error('Failed to upload questions document');
      }

      const questionsUploadData = await questionsUploadResponse.json();

      // Upload and analyze the answers document
      const answersFormData = new FormData();
      answersFormData.append('file', answersFile);
      answersFormData.append('extraction_schema', JSON.stringify({
        schema_name: "answers_extraction",
        fields: {
          "answers": {
            "type": "array",
            "description": "List of all answers found in the document"
          },
          "answer_numbers": {
            "type": "array",
            "description": "Answer numbers or identifiers"
          },
          "answer_content": {
            "type": "array",
            "description": "Full content of each answer"
          }
        }
      }));

      const answersUploadResponse = await fetch('http://localhost:8000/api/documents/upload', {
        method: 'POST',
        body: answersFormData
      });

      if (!answersUploadResponse.ok) {
        throw new Error('Failed to upload answers document');
      }

      const answersUploadData = await answersUploadResponse.json();

      // Now match questions with answers using the document IDs
      const matchingResponse = await fetch('http://localhost:8000/api/documents/match-qa', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          questions_document: questionsUploadData.document_id,
          answers_document: answersUploadData.document_id
        })
      });

      if (!matchingResponse.ok) {
        throw new Error('Failed to match questions and answers');
      }

      const matchingResults = await matchingResponse.json();
      setResults(matchingResults);

    } catch (err) {
      setError(err.message);
    } finally {
      setIsProcessing(false);
    }
  };

  const downloadFilledPDF = async () => {
    if (!results || !results.can_generate_pdf) {
      setError('No results available for PDF generation');
      return;
    }

    try {
      setIsProcessing(true);
      
      // Generate PDF with answers filled in
      const formData = new FormData();
      formData.append('questions_file', questionsFile);
      formData.append('answers_data', JSON.stringify(results));
      
      const response = await fetch('http://localhost:8000/api/pdf/generate-qa-pdf', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error('Failed to generate PDF');
      }

      // Download the PDF
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${questionsFile.name.replace('.pdf', '')}_completed.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

    } catch (err) {
      setError(`PDF generation failed: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const downloadSummaryPDF = async () => {
    if (!results) {
      setError('No results available for summary generation');
      return;
    }

    try {
      setIsProcessing(true);
      
      const response = await fetch('http://localhost:8000/api/pdf/create-answer-summary', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: `answers_data=${encodeURIComponent(JSON.stringify(results))}`
      });

      if (!response.ok) {
        throw new Error('Failed to generate summary PDF');
      }

      // Download the summary PDF
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'qa_summary.pdf';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

    } catch (err) {
      setError(`Summary PDF generation failed: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>🤖 AI Question-Answer Matcher</h1>
        <p>Upload PDFs with questions and answers, and let AI match them together!</p>
      </header>

      <main className="App-main">
        <div className="upload-section">
          <div className="upload-box">
            <h3>📋 Questions Document</h3>
            <div className="file-upload">
              <input
                type="file"
                accept=".pdf"
                onChange={handleQuestionsUpload}
                id="questions-upload"
                className="file-input"
              />
              <label htmlFor="questions-upload" className="file-label">
                {questionsFile ? questionsFile.name : 'Choose Questions PDF'}
              </label>
            </div>
            {questionsFile && (
              <div className="file-info">
                ✅ {questionsFile.name} ({(questionsFile.size / 1024 / 1024).toFixed(2)} MB)
              </div>
            )}
          </div>

          <div className="upload-box">
            <h3>📝 Answers Document</h3>
            <div className="file-upload">
              <input
                type="file"
                accept=".pdf"
                onChange={handleAnswersUpload}
                id="answers-upload"
                className="file-input"
              />
              <label htmlFor="answers-upload" className="file-label">
                {answersFile ? answersFile.name : 'Choose Answers PDF'}
              </label>
            </div>
            {answersFile && (
              <div className="file-info">
                ✅ {answersFile.name} ({(answersFile.size / 1024 / 1024).toFixed(2)} MB)
              </div>
            )}
          </div>
        </div>

        <div className="action-section">
          <button
            onClick={processDocuments}
            disabled={!questionsFile || !answersFile || isProcessing}
            className="process-button"
          >
            {isProcessing ? '🔄 Processing...' : '🚀 Match Questions & Answers'}
          </button>
        </div>

        {error && (
          <div className="error-message">
            ❌ {error}
          </div>
        )}

        {isProcessing && (
          <div className="processing-status">
            <div className="spinner"></div>
            <p>🤖 AI is analyzing your documents and matching questions with answers...</p>
            <div className="progress-steps">
              <div className="step">📋 Extracting questions...</div>
              <div className="step">📝 Extracting answers...</div>
              <div className="step">🔗 Matching content...</div>
            </div>
          </div>
        )}

        {results && (
          <div className="results-section">
            <h2>🎯 Matched Questions & Answers</h2>
            <div className="results-stats">
              <div className="stat">
                <span className="stat-number">{results.total_questions || 0}</span>
                <span className="stat-label">Questions Found</span>
              </div>
              <div className="stat">
                <span className="stat-number">{results.total_answers || 0}</span>
                <span className="stat-label">Answers Found</span>
              </div>
              <div className="stat">
                <span className="stat-number">{results.matched_pairs || 0}</span>
                <span className="stat-label">Successful Matches</span>
              </div>
            </div>

            <div className="qa-pairs">
              {results.matched_qa && results.matched_qa.map((pair, index) => (
                <div key={index} className="qa-pair">
                  <div className="question-section">
                    <h4>❓ Question {pair.question_number || index + 1}</h4>
                    <p className="question-text">{pair.question}</p>
                    <div className="confidence">
                      Confidence: {(pair.question_confidence * 100).toFixed(1)}%
                    </div>
                  </div>
                  
                  <div className="answer-section">
                    <h4>✅ Answer</h4>
                    <p className="answer-text">{pair.answer}</p>
                    <div className="confidence">
                      Match Confidence: {(pair.match_confidence * 100).toFixed(1)}%
                    </div>
                  </div>

                  {pair.match_confidence < 0.8 && (
                    <div className="review-needed">
                      ⚠️ This match may need human review
                    </div>
                  )}
                </div>
              ))}
            </div>

            {results.unmatched_questions && results.unmatched_questions.length > 0 && (
              <div className="unmatched-section">
                <h3>❓ Unmatched Questions</h3>
                {results.unmatched_questions.map((question, index) => (
                  <div key={index} className="unmatched-item">
                    <p>{question}</p>
                  </div>
                ))}
              </div>
            )}

            {results.unmatched_answers && results.unmatched_answers.length > 0 && (
              <div className="unmatched-section">
                <h3>📝 Unmatched Answers</h3>
                {results.unmatched_answers.map((answer, index) => (
                  <div key={index} className="unmatched-item">
                    <p>{answer}</p>
                  </div>
                ))}
              </div>
            )}

            <div className="download-section">
              <h3>📥 Download Options</h3>
              <button
                onClick={downloadFilledPDF}
                disabled={!results || !results.can_generate_pdf || isProcessing}
                className="download-button"
              >
                {isProcessing ? '🔄 Generating PDF...' : '📄 Download Filled PDF'}
              </button>
              <button
                onClick={downloadSummaryPDF}
                disabled={!results || isProcessing}
                className="download-button"
              >
                {isProcessing ? '🔄 Generating Summary PDF...' : '📊 Download Summary PDF'}
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default App;
