from google.cloud import firestore
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import logging
from google.genai import types
from fastapi import HTTPException, status
import asyncio

from app.models.assessment import (
    GenerateAssessmentRequest,
    GenerateAssessmentResponse,
    SubmitAssessmentRequest,
    SubmitAssessmentResponse,
    AssessmentListResponse,
    AssessmentSummary,
)
from app.models.questions import QuestionResponse
from app.services.ai_agents.generator_agent.agent import (
    generator_runner,
    generator_agent,
)
from app.services.ai_agents.feedback_agent.feedback_agent import (
    feedback_runner,
    feedback_agent,
)

logger = logging.getLogger(__name__)


class AssessmentService:
    def __init__(self, db: firestore.Client):
        self.db = db

    async def run_agent(self, runner, agent, prompt: str):
        """
        Helper function to run an ADK agent using Runner.
        Creates a unique session for each request and extracts the final response.
        """
        try:
            # Generate unique session ID for this request
            session_id = f"session_{uuid.uuid4().hex[:8]}"
            user_id = "api_user"

            # Create session before running
            await runner.session_service.create_session(
                app_name=runner.app_name, user_id=user_id, session_id=session_id
            )

            # Create user message using types.Content (ADK format)
            user_msg = types.Content(role="user", parts=[types.Part(text=prompt)])

            # Run the agent and collect final response
            final_text = None
            async for event in runner.run_async(
                user_id=user_id, session_id=session_id, new_message=user_msg
            ):
                if event.is_final_response():
                    if event.content and event.content.parts:
                        final_text = event.content.parts[0].text

            if final_text is None:
                raise ValueError("No final response received from agent")

            # If agent has output_key, try to get structured output from session state
            if hasattr(agent, "output_key") and agent.output_key:
                try:
                    current_session = await runner.session_service.get_session(
                        app_name=runner.app_name, user_id=user_id, session_id=session_id
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
            logger.error(f"Error running agent: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error calling agent: {str(e)}",
            )

    async def generate_assessment(
        self, request: GenerateAssessmentRequest, user_id: str
    ) -> GenerateAssessmentResponse:
        """
        Generate a new assessment with questions based on topic and level.
        """
        try:
            # Call the generator agent
            prompt = f"Generate assessment questions for topic: {request.topic}, level: {request.level}"
            response = await self.run_agent(generator_runner, generator_agent, prompt)

            # Extract questions - response is already a dict from run_agent (parsed JSON)
            questions = response.get("questions", [])

            if not questions:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="No questions generated",
                )

            # Assign unique IDs to each question
            for question in questions:
                if "id" not in question or not question["id"]:
                    question["id"] = str(uuid.uuid4())

            # Save to Firestore (questions are already dicts, ready to save)
            assessment_data = {
                "user_id": user_id,
                "topic": request.topic,
                "level": request.level,
                "questions": questions,
                "created_at": datetime.utcnow(),
            }

            _, doc_ref = self.db.collection("assessments").add(assessment_data)
            assessment_id = doc_ref.id

            # Convert to response format
            questions_response = [QuestionResponse(**q) for q in questions]

            return GenerateAssessmentResponse(
                assessment_id=assessment_id,
                topic=request.topic,
                level=request.level,
                questions=questions_response,
                created_at=assessment_data["created_at"],
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error generating assessment: {str(e)}",
            )

    async def submit_assessment(
        self, request: SubmitAssessmentRequest, user_id: str
    ) -> SubmitAssessmentResponse:
        """
        Submit answers for an assessment and get results with feedback.
        """
        # Fetch the assessment from Firestore
        assessment_ref = self.db.collection("assessments").document(
            request.assessment_id
        )
        assessment_doc = assessment_ref.get()

        if not assessment_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assessment with id {request.assessment_id} not found",
            )

        assessment_data = assessment_doc.to_dict()
        questions = assessment_data.get("questions", [])

        if not questions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assessment has no questions",
            )

        # Evaluate answers (no AI)
        correct_questions = []
        incorrect_questions = []
        score = 0.0
        max_score = float(len(questions))

        for question in questions:
            question_id = question.get("id")
            if not question_id:
                # Skip questions without IDs (shouldn't happen with new system)
                continue

            user_answer = request.user_answers.get(question_id)
            correct_answer = question.get("correct_answer")

            if user_answer == correct_answer:
                correct_questions.append(question_id)
                score += 1.0
            elif user_answer is not None:
                # Only count as incorrect if user provided an answer
                incorrect_questions.append(question_id)

        # Prepare context for feedback agent
        # Create a mapping of question IDs to questions for easy lookup
        questions_by_id = {q.get("id"): q for q in questions if q.get("id")}
        correct_questions_data = [
            questions_by_id[qid] for qid in correct_questions if qid in questions_by_id
        ]
        incorrect_questions_data = [
            questions_by_id[qid]
            for qid in incorrect_questions
            if qid in questions_by_id
        ]

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
            feedback_response = await self.run_agent(
                feedback_runner, feedback_agent, feedback_prompt
            )
            # Handle different response structures
            # If response is a dict (from JSON parsing), extract feedback
            if isinstance(feedback_response, dict):
                feedback_text = feedback_response.get("feedback", "")
                weak_topics = feedback_response.get("weak_topics", [])
                # We ignore resources from feedback agent as we'll fetch from RAG
            elif hasattr(feedback_response, "feedback"):
                feedback_text = feedback_response.feedback
                weak_topics = getattr(feedback_response, "weak_topics", [])
            elif isinstance(feedback_response, str):
                # Try to parse as JSON
                try:
                    import json

                    parsed = json.loads(feedback_response)
                    feedback_text = parsed.get("feedback", feedback_response)
                    weak_topics = parsed.get("weak_topics", [])
                except:
                    feedback_text = feedback_response
                    weak_topics = []
            else:
                feedback_text = str(feedback_response) if feedback_response else ""
                weak_topics = []

            # Fetch resources from RAG based on weak topics
            resources = []
            if weak_topics:
                try:
                    # 1. Normalize topics
                    from app.services.ai_agents.topic_normalizer.agent import (
                        topic_normalizer_runner,
                        topic_normalizer_agent,
                    )

                    normalization_prompt = f"Normalize these topics: {weak_topics}"
                    normalization_response = await self.run_agent(
                        topic_normalizer_runner,
                        topic_normalizer_agent,
                        normalization_prompt,
                    )

                    search_queries = []
                    if isinstance(normalization_response, dict):
                        normalized_list = normalization_response.get(
                            "normalized_topics", []
                        )
                        search_queries = [
                            item.get("normalized")
                            for item in normalized_list
                            if item.get("normalized")
                        ]
                    elif hasattr(normalization_response, "normalized_topics"):
                        search_queries = [
                            item.normalized
                            for item in normalization_response.normalized_topics
                        ]

                    # Fallback to raw topics if normalization fails or returns empty
                    if not search_queries:
                        search_queries = weak_topics

                    # 2. Search for resources
                    from app.services.ingestion_service import IngestionService

                    ingestion_service = IngestionService(self.db)
                    found_resource_ids = set()

                    for query in search_queries:
                        # Fetch top 2 resources per topic
                        search_results = await ingestion_service.search_resources(
                            query=query, n_results=2
                        )

                        for result in search_results:
                            res_id = result.get("id")
                            if res_id and res_id not in found_resource_ids:
                                found_resource_ids.add(res_id)
                                metadata = result.get("metadata", {})
                                resources.append(
                                    {
                                        "title": metadata.get("title", ""),
                                        "type": metadata.get("type", "article"),
                                        "url": metadata.get("url", ""),
                                        "description": metadata.get("summary", "")
                                        or f"Learn more about {query}",
                                    }
                                )

                except Exception as e:
                    logger.error(f"Error fetching RAG resources: {e}")
                    # Don't fail the whole request, just proceed with empty resources

        except Exception as e:
            # If feedback generation fails, provide a basic feedback
            logger.error(f"Error generating feedback: {e}")
            feedback_text = (
                f"You scored {score}/{max_score}. Keep practicing to improve!"
            )
            weak_topics = []
            resources = []

        # Save result to Firestore
        result_data = {
            "user_id": user_id,
            "assessment_id": request.assessment_id,
            "user_answers": request.user_answers,
            "score": score,
            "max_score": max_score,
            "correct_questions": correct_questions,
            "incorrect_questions": incorrect_questions,
            "feedback": feedback_text,
            "weak_topics": weak_topics,
            "resources": resources,
            "created_at": datetime.utcnow(),
        }

        results_ref = self.db.collection("assessment_results")
        # add() returns a tuple (timestamp, DocumentReference)
        _, result_doc_ref = results_ref.add(result_data)
        result_id = result_doc_ref.id

        # Update assessment with result_id
        try:
            assessment_ref.update({"result_id": result_id})
        except Exception as e:
            logger.error(
                f"Failed to update assessment {request.assessment_id} with result_id: {e}"
            )
            # We don't fail the request if this update fails, as the result is already created

        return SubmitAssessmentResponse(
            score=score,
            max_score=max_score,
            feedback=feedback_text,
            weak_topics=weak_topics,
            resources=resources,
            correct_questions=correct_questions,
            incorrect_questions=incorrect_questions,
            result_id=result_id,
        )

    async def get_user_assessments(self, user_id: str) -> AssessmentListResponse:
        """
        Get all assessments created by the user.
        """
        try:
            # Query assessments for the user
            assessments_ref = self.db.collection("assessments")
            query = assessments_ref.where(
                field_path="user_id", op_string="==", value=user_id
            )

            docs = query.stream()

            assessments = []
            for doc in docs:
                data = doc.to_dict()
                created_at = data.get("created_at", datetime.utcnow())

                # Handle Firestore Timestamp conversion
                if hasattr(created_at, "timestamp") and hasattr(
                    created_at, "to_datetime"
                ):
                    created_at = created_at.to_datetime()
                elif not isinstance(created_at, datetime):
                    created_at = datetime.utcnow()

                questions = data.get("questions", [])

                assessments.append(
                    AssessmentSummary(
                        id=doc.id,
                        topic=data.get("topic", "Unknown"),
                        level=data.get("level", "Unknown"),
                        created_at=created_at,
                        questions_count=len(questions),
                        result_id=data.get("result_id"),
                    )
                )

            # Sort by created_at descending (newest first)
            assessments.sort(key=lambda x: x.created_at, reverse=True)

            return AssessmentListResponse(assessments=assessments)

        except Exception as e:
            logger.error(f"Error fetching user assessments: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fetching assessments: {str(e)}",
            )

    async def get_assessment(
        self, assessment_id: str, user_id: str
    ) -> GenerateAssessmentResponse:
        """
        Get a specific assessment by ID.
        Verifies that the assessment belongs to the user.
        """
        try:
            doc_ref = self.db.collection("assessments").document(assessment_id)
            doc = doc_ref.get()

            if not doc.exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Assessment with id {assessment_id} not found",
                )

            data = doc.to_dict()

            # Verify ownership
            if data.get("user_id") != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to access this assessment",
                )

            created_at = data.get("created_at", datetime.utcnow())
            if hasattr(created_at, "to_datetime"):
                created_at = created_at.to_datetime()

            questions = data.get("questions", [])
            questions_response = [QuestionResponse(**q) for q in questions]

            return GenerateAssessmentResponse(
                assessment_id=doc.id,
                topic=data.get("topic", "Unknown"),
                level=data.get("level", "Unknown"),
                questions=questions_response,
                created_at=created_at,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"Error fetching assessment {assessment_id}: {e}", exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fetching assessment: {str(e)}",
            )
