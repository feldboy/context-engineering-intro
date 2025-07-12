# 📁 Project Structure

```
context-engineering-intro/
├── 📂 backend/                    # Python backend application
│   ├── agents/                    # AI agents and models
│   ├── api/                      # FastAPI endpoints
│   ├── config/                   # Configuration management
│   ├── tools/                    # Document processing tools
│   └── utils/                    # Utility functions
├── 📂 frontend/                   # React frontend application
│   ├── src/                      # Source code
│   │   ├── components/           # React components
│   │   ├── styles/               # CSS styles
│   │   ├── App.jsx               # Main document analysis app
│   │   └── QAApp.js              # Q&A matching app
│   ├── public/                   # Static assets
│   └── package.json              # Dependencies
├── 📂 docs/                      # Documentation
│   ├── USAGE_GUIDE.md            # Comprehensive usage guide
│   ├── CLAUDE.md                 # Development guidelines
│   └── INITIAL.md                # Initial project overview
├── 📂 demos/                     # Demo applications
│   ├── demo_real_analysis.py     # Real document analysis demo
│   ├── demo_usage.py             # Usage demonstration
│   └── web_api_demo.py           # Web API demo
├── 📂 examples/                  # Code examples
│   ├── python_api_example.py     # Python API usage
│   └── usage_example.py          # Basic usage examples
├── 📂 scripts/                   # Utility scripts
│   ├── setup.sh                  # Automated setup script
│   └── create_sample_qa_pdfs.py  # Sample PDF generator
├── 📂 tests/                     # Test suite
│   ├── test_application.py       # Application tests
│   ├── test_real_usage.py        # Real usage tests
│   └── [other test files]        # Component tests
├── 📂 uploads/                   # Sample upload files
├── 📂 storage/                   # Document storage
│   └── samples/                  # Sample documents
├── 📂 PRPs/                      # Project Requirements & Patterns
├── main.py                       # FastAPI application entry point
├── requirements.txt              # Python dependencies
├── docker-compose.yml            # Docker composition
└── README.md                     # This file
```

## 📋 Key Directories

- **`backend/`**: Core Python application with AI agents, API endpoints, and document processing tools
- **`frontend/`**: React-based user interface for document analysis and verification
- **`docs/`**: Comprehensive documentation including usage guides and development guidelines
- **`demos/`**: Working demonstrations of the system's capabilities
- **`examples/`**: Code examples showing how to use the API
- **`scripts/`**: Utility scripts for setup, sample generation, and maintenance
- **`tests/`**: Complete test suite for all components
- **`uploads/`**: Sample files for testing and demonstration
- **`storage/`**: Document storage with organized sample files

## 🗂️ File Organization

All files are now properly organized into logical directories:

- ✅ **Documentation** → `docs/`
- ✅ **Demos** → `demos/`
- ✅ **Examples** → `examples/`
- ✅ **Scripts** → `scripts/`
- ✅ **Tests** → `tests/`
- ✅ **Samples** → `uploads/` and `storage/samples/`
- ✅ **Frontend** → `frontend/src/`
- ✅ **Backend** → `backend/`
