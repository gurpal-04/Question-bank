from google.cloud import firestore
from fastapi import HTTPException, status
from typing import List, Optional
from datetime import datetime

from app.models.assessment import (
    ResultResponse,
    ResultsListResponse,
    QuestionWithAnswer,
)


class ResultService:
    def __init__(self, db: firestore.Client):
        self.db = db

    async def get_result(self, result_id: str) -> ResultResponse:
        """
        Get a specific assessment result by its ID with enriched question details.
        """
        result_ref = self.db.collection("assessment_results").document(result_id)
        result_doc = result_ref.get()

        if not result_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Result with id {result_id} not found",
            )

        result_data = result_doc.to_dict()
        created_at = result_data.get("created_at", datetime.utcnow())

        # Handle Firestore Timestamp conversion
        if hasattr(created_at, "timestamp") and hasattr(created_at, "to_datetime"):
            created_at = created_at.to_datetime()
        elif not isinstance(created_at, datetime):
            created_at = datetime.utcnow()

        # Fetch associated assessment to get question details
        assessment_id = result_data.get("assessment_id", "")
        user_answers = result_data.get("user_answers", {})
        correct_questions = result_data.get("correct_questions", [])

        enriched_questions = []

        if assessment_id:
            try:
                assessment_ref = self.db.collection("assessments").document(
                    assessment_id
                )
                assessment_doc = assessment_ref.get()

                if assessment_doc.exists:
                    assessment_data = assessment_doc.to_dict()
                    questions = assessment_data.get("questions", [])

                    # Enrich each question with user's answer and correctness
                    for question in questions:
                        question_id = question.get("id")
                        if question_id:
                            user_answer = user_answers.get(question_id)
                            is_correct = question_id in correct_questions

                            enriched_questions.append(
                                QuestionWithAnswer(
                                    id=question_id,
                                    question=question.get("question", ""),
                                    options=question.get("options", []),
                                    correct_answer=question.get("correct_answer", ""),
                                    explanation=question.get("explanation", ""),
                                    difficulty=question.get("difficulty", ""),
                                    metadata=question.get("metadata", {}),
                                    user_answer=user_answer,
                                    is_correct=is_correct,
                                )
                            )
            except Exception as e:
                # Log error but don't fail the request
                print(f"Error fetching assessment {assessment_id}: {e}")

        return ResultResponse(
            id=result_doc.id,
            assessment_id=assessment_id,
            score=result_data.get("score", 0.0),
            max_score=result_data.get("max_score", 0.0),
            feedback=result_data.get("feedback"),
            weak_topics=result_data.get("weak_topics", []),
            resources=result_data.get("resources", []),
            correct_questions=correct_questions,
            incorrect_questions=result_data.get("incorrect_questions", []),
            user_answers=user_answers,
            questions=enriched_questions,
            created_at=created_at,
        )

    async def get_user_results(self, user_id: str) -> ResultsListResponse:
        """
        Get all assessment results for the user with enriched question details.
        """
        try:
            # Query results for the user
            results_ref = self.db.collection("assessment_results")
            query = results_ref.where(
                field_path="user_id", op_string="==", value=user_id
            )

            docs = query.stream()

            results = []
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

                # Fetch associated assessment to get question details
                assessment_id = data.get("assessment_id", "")
                user_answers = data.get("user_answers", {})
                correct_questions = data.get("correct_questions", [])

                enriched_questions = []

                if assessment_id:
                    try:
                        assessment_ref = self.db.collection("assessments").document(
                            assessment_id
                        )
                        assessment_doc = assessment_ref.get()

                        if assessment_doc.exists:
                            assessment_data = assessment_doc.to_dict()
                            questions = assessment_data.get("questions", [])

                            # Enrich each question with user's answer and correctness
                            for question in questions:
                                question_id = question.get("id")
                                if question_id:
                                    user_answer = user_answers.get(question_id)
                                    is_correct = question_id in correct_questions

                                    enriched_questions.append(
                                        QuestionWithAnswer(
                                            id=question_id,
                                            question=question.get("question", ""),
                                            options=question.get("options", []),
                                            correct_answer=question.get(
                                                "correct_answer", ""
                                            ),
                                            explanation=question.get("explanation", ""),
                                            difficulty=question.get("difficulty", ""),
                                            metadata=question.get("metadata", {}),
                                            user_answer=user_answer,
                                            is_correct=is_correct,
                                        )
                                    )
                    except Exception as e:
                        # Log error but don't fail the request
                        print(f"Error fetching assessment {assessment_id}: {e}")

                results.append(
                    ResultResponse(
                        id=doc.id,
                        assessment_id=assessment_id,
                        score=data.get("score", 0.0),
                        max_score=data.get("max_score", 0.0),
                        feedback=data.get("feedback"),
                        weak_topics=data.get("weak_topics", []),
                        resources=data.get("resources", []),
                        correct_questions=correct_questions,
                        incorrect_questions=data.get("incorrect_questions", []),
                        user_answers=user_answers,
                        questions=enriched_questions,
                        created_at=created_at,
                    )
                )

            # Sort by created_at descending (newest first)
            results.sort(key=lambda x: x.created_at, reverse=True)

            return ResultsListResponse(results=results)

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fetching results: {str(e)}",
            )
