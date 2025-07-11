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

      const questionsUploadResponse = await fetch('/api/documents/upload', {
        method: 'POST',
        body: questionsFormData
      });

      if (!questionsUploadResponse.ok) {
        throw new Error('Failed to upload questions document');
      }

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

      const answersUploadResponse = await fetch('/api/documents/upload', {
        method: 'POST',
        body: answersFormData
      });

      if (!answersUploadResponse.ok) {
        throw new Error('Failed to upload answers document');
      }

      // Now match questions with answers
      const matchingResponse = await fetch('/api/documents/match-qa', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          questions_document: questionsFile.name,
          answers_document: answersFile.name
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
          </div>
        )}
      </main>
    </div>
  );
};

export default App;
