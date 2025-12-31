A FastAPI-based assessment platform that uses AI agents to generate, evaluate, and provide feedback on technical assessments. The system supports interview context generation, question generation, answer evaluation, and personalized learning resources.

## Features

- **AI-Powered Assessment Generation**: Generate technical assessments with questions tailored to specific topics and difficulty levels
- **Interview Context Generation**: Create stable interview contexts based on role, experience level, and difficulty
- **Automated Evaluation**: Submit answers and receive AI-generated feedback with scoring
- **Vector Search**: ChromaDB integration for semantic search and resource recommendations
- **User Management**: Support for both authenticated users and guest sessions
- **Learning Resources**: Get personalized learning resources based on assessment performance
- **Topic Normalization**: Normalize and standardize technical topics for consistent assessment generation

## Tech Stack

- **Framework**: FastAPI
- **Database**: Google Cloud Firestore
- **Vector Store**: ChromaDB
- **AI/ML**: Google ADK (Agent Development Kit), Gemini models
- **Authentication**: JWT (JSON Web Tokens)
- **Embeddings**: Sentence Transformers
- **Deployment**: Docker support

## Prerequisites

- Python 3.11+
- Google Cloud account with Firestore enabled
- Google Cloud service account credentials
- (Optional) Docker for containerized deployment

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd Question-bank
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up Google Cloud credentials

You have two options:

**Option A: Local development (JSON file)**

1. Download your Google Cloud service account JSON key
2. Save it as `api-key.json` in the project root

**Option B: Environment variable (for deployment)**
Set the `GOOGLE_APPLICATION_CREDENTIALS_JSON` environment variable with your service account JSON content.

### 5. Configure environment variables

Create a `.env` file in the project root (optional, for local development):

```env
PORT=8080
GOOGLE_APPLICATION_CREDENTIALS_JSON=<your-json-credentials>
# Add other environment variables as needed
```

### 6. ChromaDB Setup

**No additional setup required!** ChromaDB runs as an embedded database (PersistentClient) and is automatically initialized when the application starts. The `chroma_data/` directory will be created automatically in the project root to store vector embeddings. No separate ChromaDB server needs to be started.

## Running the Application

### Development mode

```bash
python -m app.main
```

Or using uvicorn directly:

```bash
uvicorn app.main:app --reload --port 8080
```

The API will be available at `http://localhost:8080`

### Production mode

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

### Using Docker

```bash
docker build -t question-bank-api .
docker run -p 8080:8080 question-bank-api
```

## API Documentation

Once the server is running, access the interactive API documentation:

- **Swagger UI**: `http://localhost:8080/docs`
- **ReDoc**: `http://localhost:8080/redoc`
- **OpenAPI JSON**: `http://localhost:8080/openapi.json`

## Project Structure

```
Question-bank/
├── app/
│   ├── api/
│   │   └── v1/              # API route handlers
│   │       ├── assessments.py
│   │       ├── auth.py
│   │       ├── interview_context.py
│   │       ├── resources.py
│   │       ├── results.py
│   │       └── users.py
│   ├── core/                # Core configuration and utilities
│   │   ├── config.py
│   │   ├── database.py      # Firestore client setup
│   │   ├── dependencies.py
│   │   ├── evaluation_bars.py
│   │   └── security.py      # JWT authentication
│   ├── models/              # Pydantic models
│   │   ├── assessment.py
│   │   ├── feedback.py
│   │   ├── interview_context.py
│   │   ├── questions.py
│   │   ├── resource.py
│   │   └── user.py
│   ├── services/            # Business logic
│   │   ├── ai_agents/       # AI agent implementations
│   │   │   ├── evaluator_agent/
│   │   │   ├── feedback_agent/
│   │   │   ├── generator_agent/
│   │   │   ├── interview_context_agent/
│   │   │   ├── summary_agent/
│   │   │   └── topic_normalizer/
│   │   ├── assessment_service.py
│   │   ├── auth_service.py
│   │   ├── embedding_service.py
│   │   ├── ingestion_service.py
│   │   ├── resource_service.py
│   │   ├── result_service.py
│   │   ├── user_service.py
│   │   └── vector_store.py
│   ├── prompts/             # AI prompt templates
│   ├── utils/               # Utility functions
│   └── main.py              # FastAPI application entry point
├── chroma_data/             # ChromaDB data directory
├── tests/                   # Test files
├── Dockerfile
├── requirements.txt
└── README.md
```

## AI Agents

The system uses multiple specialized AI agents:

1. **Generator Agent**: Generates assessment questions based on topics and difficulty
2. **Evaluator Agent**: Evaluates submitted answers and provides scores
3. **Feedback Agent**: Generates detailed feedback on assessment performance
4. **Interview Context Agent**: Creates stable interview contexts for consistent evaluation
5. **Summary Agent**: Generates summaries of assessment results
6. **Topic Normalizer**: Normalizes and standardizes technical topics

## Development

### Code Style

The project follows Python best practices and uses:

- Pydantic for data validation
- Type hints throughout
- FastAPI dependency injection
- Async/await for I/O operations

### Adding New Features

1. Define models in `app/models/`
2. Create service logic in `app/services/`
3. Add API routes in `app/api/v1/`
4. Register routes in `app/main.py`

## Environment Variables

- `PORT`: Server port (default: 8080)
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to Google Cloud credentials JSON file
- `GOOGLE_APPLICATION_CREDENTIALS_JSON`: JSON string of Google Cloud credentials (alternative to file)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

For issues and questions, please open an issue in the repository.
