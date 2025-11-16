from fastapi import APIRouter, Depends, HTTPException, status
from google.cloud import firestore
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
import inspect
import uuid

from google.genai import types

from app.core.database import get_db
from app.models.assessment import Assessment, AssessmentResult
from app.services.ai_agents.generator_agent.agent import generator_runner, generator_agent
from app.services.ai_agents.feedback_agent.feedback_agent import feedback_runner, feedback_agent


router = APIRouter()

# Request/Response Models
class GenerateAssessmentRequest(BaseModel):
    topic: str = Field(..., description="Topic for the assessment (e.g., React, Python)")
    level: str = Field(..., description="Difficulty level: Beginner, Intermediate, or Advanced")


class QuestionResponse(BaseModel):
    question: str
    options: List[str]
    correct_answer: str
    explanation: str
    difficulty: str
    metadata: Dict[str, Any]


class GenerateAssessmentResponse(BaseModel):
    assessment_id: str
    topic: str
    level: str
    questions: List[QuestionResponse]
    created_at: datetime


class SubmitAssessmentRequest(BaseModel):
    assessment_id: str = Field(..., description="ID of the assessment")
    user_answers: Dict[int, str] = Field(
        ..., 
        description="Dictionary mapping question index to user's answer"
    )


class SubmitAssessmentResponse(BaseModel):
    score: float
    max_score: float
    feedback: str
    correct_questions: List[int]
    incorrect_questions: List[int]
    result_id: str


class ResultResponse(BaseModel):
    id: str
    assessment_id: str
    score: float
    max_score: float
    feedback: Optional[str]
    correct_questions: List[int]
    incorrect_questions: List[int]
    created_at: datetime


class ResultsListResponse(BaseModel):
    results: List[ResultResponse]


async def run_agent(runner, agent, prompt: str):
    """
    Helper function to run an ADK agent using Runner.
    Creates a unique session for each request and extracts the final response.
    """
    try:
        import logging
        logger = logging.getLogger(__name__)
        
        # Generate unique session ID for this request
        session_id = f"session_{uuid.uuid4().hex[:8]}"
        user_id = "api_user"
        
        # Create session before running
        await runner.session_service.create_session(
            app_name=runner.app_name,
            user_id=user_id,
            session_id=session_id
        )
        
        # Create user message using types.Content (ADK format)
        user_msg = types.Content(
            role="user",
            parts=[types.Part(text=prompt)]
        )
        
        # Run the agent and collect final response
        final_text = None
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=user_msg
        ):
            if event.is_final_response():
                if event.content and event.content.parts:
                    final_text = event.content.parts[0].text
        
        if final_text is None:
            raise ValueError("No final response received from agent")
        
        # If agent has output_key, try to get structured output from session state
        if hasattr(agent, 'output_key') and agent.output_key:
            try:
                current_session = await runner.session_service.get_session(
                    app_name=runner.app_name,
                    user_id=user_id,
                    session_id=session_id
                )
                if current_session and current_session.state:
                    stored_output = current_session.state.get(agent.output_key)
                    if stored_output:
                        # Try to parse as JSON (output_schema returns JSON string)
                        try:
                            import json
                            return json.loads(stored_output)
                        except:
                            return stored_output
            except Exception as e:
                logger.warning(f"Could not get stored output from session: {e}")
        
        # Return the text response (might be JSON string if output_schema is used)
        return final_text
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error running agent: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calling agent: {str(e)}"
        )


@router.post("/generate", response_model=GenerateAssessmentResponse, status_code=status.HTTP_201_CREATED)
async def generate_assessment(
    request: GenerateAssessmentRequest,
    db: firestore.Client = Depends(get_db)
):
    """
    Generate a new assessment with questions based on topic and level.
    """
    try:
        # Call the generator agent
        prompt = f"Generate assessment questions for topic: {request.topic}, level: {request.level}"
        response = await run_agent(generator_runner, generator_agent, prompt)

        # Extract questions - response is already a dict from run_agent (parsed JSON)
        questions = response.get('questions', [])
        
        if not questions:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No questions generated"
            )
        
        # Save to Firestore (questions are already dicts, ready to save)
        assessment_data = {
            "topic": request.topic,
            "level": request.level,
            "questions": questions,
            "created_at": datetime.utcnow()
        }
        
        _, doc_ref = db.collection("assessments").add(assessment_data)
        assessment_id = doc_ref.id
        
        # Convert to response format
        questions_response = [QuestionResponse(**q) for q in questions]
        
        return GenerateAssessmentResponse(
            assessment_id=assessment_id,
            topic=request.topic,
            level=request.level,
            questions=questions_response,
            created_at=assessment_data["created_at"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating assessment: {str(e)}"
        )


@router.post("/submit", response_model=SubmitAssessmentResponse, status_code=status.HTTP_201_CREATED)
async def submit_assessment(
    request: SubmitAssessmentRequest,
    db: firestore.Client = Depends(get_db)
):
    """
    Submit answers for an assessment and get results with feedback.
    """
    # Fetch the assessment from Firestore
    assessment_ref = db.collection("assessments").document(request.assessment_id)
    assessment_doc = assessment_ref.get()
    
    if not assessment_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment with id {request.assessment_id} not found"
        )
    
    assessment_data = assessment_doc.to_dict()
    questions = assessment_data.get("questions", [])
    
    if not questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assessment has no questions"
        )
    
    # Evaluate answers (no AI)
    correct_questions = []
    incorrect_questions = []
    score = 0.0
    max_score = float(len(questions))
    
    for idx, question in enumerate(questions):
        user_answer = request.user_answers.get(idx)
        correct_answer = question.get("correct_answer")
        
        if user_answer == correct_answer:
            correct_questions.append(idx)
            score += 1.0
        else:
            incorrect_questions.append(idx)
    
    # Prepare context for feedback agent
    correct_questions_data = [questions[i] for i in correct_questions]
    incorrect_questions_data = [questions[i] for i in incorrect_questions]
    
    feedback_prompt = f"""
    Assessment Topic: {assessment_data.get('topic', 'Unknown')}
    Difficulty Level: {assessment_data.get('level', 'Unknown')}
    Score: {score}/{max_score} ({score/max_score*100:.1f}%)
    
    Correct Answers ({len(correct_questions)}):
    {[q.get('question', '')[:100] for q in correct_questions_data]}
    
    Incorrect Answers ({len(incorrect_questions)}):
    {[q.get('question', '')[:100] for q in incorrect_questions_data]}
    
    Please provide personalized feedback for this performance.
    """
    
    # Call feedback agent
    try:
        feedback_response = await run_agent(feedback_runner, feedback_agent, feedback_prompt)
        # Handle different response structures
        # If response is a dict (from JSON parsing), extract feedback
        if isinstance(feedback_response, dict):
            feedback_text = feedback_response.get('feedback', '')
        elif hasattr(feedback_response, 'feedback'):
            feedback_text = feedback_response.feedback
        elif isinstance(feedback_response, str):
            # Try to parse as JSON
            try:
                import json
                parsed = json.loads(feedback_response)
                feedback_text = parsed.get('feedback', feedback_response)
            except:
                feedback_text = feedback_response
        else:
            feedback_text = str(feedback_response) if feedback_response else ""
    except Exception as e:
        # If feedback generation fails, provide a basic feedback
        feedback_text = f"You scored {score}/{max_score}. Keep practicing to improve!"
    
    # Save result to Firestore
    result_data = {
        "assessment_id": request.assessment_id,
        "user_answers": request.user_answers,
        "score": score,
        "max_score": max_score,
        "correct_questions": correct_questions,
        "incorrect_questions": incorrect_questions,
        "feedback": feedback_text,
        "created_at": datetime.utcnow()
    }
    
    results_ref = db.collection("assessment_results")
    # add() returns a tuple (timestamp, DocumentReference)
    _, result_doc_ref = results_ref.add(result_data)
    result_id = result_doc_ref.id
    
    return SubmitAssessmentResponse(
        score=score,
        max_score=max_score,
        feedback=feedback_text,
        correct_questions=correct_questions,
        incorrect_questions=incorrect_questions,
        result_id=result_id
    )


@router.get("/{assessment_id}/results", response_model=ResultsListResponse)
async def get_assessment_results(
    assessment_id: str,
    db: firestore.Client = Depends(get_db)
):
    """
    Get all results for a specific assessment.
    """
    # Verify assessment exists
    assessment_ref = db.collection("assessments").document(assessment_id)
    assessment_doc = assessment_ref.get()
    
    if not assessment_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment with id {assessment_id} not found"
        )
    
    # Fetch all results for this assessment
    # Note: Firestore requires an index for order_by with where clauses
    # For simplicity, we'll fetch and sort in memory
    results_query = (
        db.collection("assessment_results")
        .where("assessment_id", "==", assessment_id)
    )
    
    results_docs = list(results_query.stream())
    # Sort by created_at descending
    def get_created_at(doc):
        doc_data = doc.to_dict()
        created_at = doc_data.get("created_at", datetime.min)
        # Firestore Timestamp is automatically converted to datetime by to_dict()
        if hasattr(created_at, 'timestamp'):
            return created_at.to_datetime()
        return created_at if isinstance(created_at, datetime) else datetime.min
    results_docs.sort(key=get_created_at, reverse=True)
    
    results_response = []
    for doc in results_docs:
        result_data = doc.to_dict()
        created_at = result_data.get("created_at", datetime.utcnow())
        # Handle Firestore Timestamp conversion
        if hasattr(created_at, 'timestamp'):
            created_at = created_at.to_datetime()
        elif not isinstance(created_at, datetime):
            created_at = datetime.utcnow()
        results_response.append(
            ResultResponse(
                id=doc.id,
                assessment_id=result_data.get("assessment_id", ""),
                score=result_data.get("score", 0.0),
                max_score=result_data.get("max_score", 0.0),
                feedback=result_data.get("feedback"),
                correct_questions=result_data.get("correct_questions", []),
                incorrect_questions=result_data.get("incorrect_questions", []),
                created_at=created_at
            )
        )
    
    return ResultsListResponse(results=results_response)
