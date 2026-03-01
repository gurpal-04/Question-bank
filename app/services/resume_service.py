from google.cloud import firestore
from fastapi import HTTPException, status
from typing import List, Optional
from datetime import datetime
import uuid

from app.models.resume import Resume, ResumeProfile, ResumeCreate, ResumeResponse
from app.services.ai_agents.resume_parser.agent import resume_parser_runner


class ResumeService:
    def __init__(self, db: firestore.Client):
        self.db = db
        self.collection = "resumes"

    async def parse_and_save_resume(
        self, user_id: str, resume_in: ResumeCreate
    ) -> ResumeResponse:
        """
        Parses raw resume text using ResumeParserAgent and saves it to Firestore.
        """
        try:
            # 1. Parse resume text using AI Agent
            prompt = f"Please parse the following resume text:\n\n{resume_in.raw_text}"

            from app.services.ai_agents.runner_utils import run_agent_with_runner
            from app.services.ai_agents.resume_parser.agent import (
                resume_parser_runner,
                resume_parser_agent,
            )

            # run_agent_with_runner returns the parsed JSON dict if output_key is set
            parsed_data = await run_agent_with_runner(
                resume_parser_runner, resume_parser_agent, prompt
            )

            if not parsed_data:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="AI failed to parse the resume text.",
                )

            # The agent returns the object directly if output_schema is provided
            # and runner_utils handles the JSON parsing.
            try:
                parsed_profile = ResumeProfile(**parsed_data)
            except Exception as e:
                print(f"Schema validation error: {e}")
                # Fallback or re-raise
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Parsed data does not match ResumeProfile schema: {e}",
                )

            # 2. Create Resume model
            resume_id = str(uuid.uuid4())
            resume = Resume(
                id=resume_id,
                user_id=user_id,
                raw_text=resume_in.raw_text,
                parsed_profile=parsed_profile,
                created_at=datetime.utcnow(),
            )

            # 3. Save to Firestore
            resume_data = resume.dict()
            if "id" in resume_data:
                del resume_data[
                    "id"
                ]  # Let Firestore doc ID be the source of truth if needed, but we use resume_id

            self.db.collection(self.collection).document(resume_id).set(resume_data)

            return ResumeResponse(
                id=resume_id,
                user_id=user_id,
                parsed_profile=parsed_profile,
                created_at=resume.created_at,
            )

        except Exception as e:
            print(f"Error in parse_and_save_resume: {e}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process resume: {str(e)}",
            )

    async def get_user_resumes(self, user_id: str) -> List[ResumeResponse]:
        """
        Retrieves all resumes for a specific user.
        """
        try:
            resumes_ref = self.db.collection(self.collection)
            query = resumes_ref.where("user_id", "==", user_id)
            docs = query.stream()

            resumes = []
            for doc in docs:
                data = doc.to_dict()

                # Handle Firestore Timestamp
                created_at = data.get("created_at")
                if hasattr(created_at, "to_datetime"):
                    created_at = created_at.to_datetime()
                elif not isinstance(created_at, datetime):
                    created_at = datetime.utcnow()

                resumes.append(
                    ResumeResponse(
                        id=doc.id,
                        user_id=data.get("user_id"),
                        parsed_profile=ResumeProfile(**data.get("parsed_profile", {})),
                        created_at=created_at,
                    )
                )

            # Sort by created_at descending
            resumes.sort(key=lambda x: x.created_at, reverse=True)
            return resumes

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fetching resumes: {str(e)}",
            )

    async def get_resume(self, resume_id: str) -> ResumeResponse:
        """
        Retrieves a specific resume by its ID.
        """
        doc_ref = self.db.collection(self.collection).document(resume_id)
        doc = doc_ref.get()

        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Resume with id {resume_id} not found",
            )

        data = doc.to_dict()
        created_at = data.get("created_at")
        if hasattr(created_at, "to_datetime"):
            created_at = created_at.to_datetime()

        return ResumeResponse(
            id=doc.id,
            user_id=data.get("user_id"),
            parsed_profile=ResumeProfile(**data.get("parsed_profile", {})),
            created_at=created_at,
        )

    async def delete_resume(self, resume_id: str, user_id: str):
        """
        Deletes a resume, ensuring the user owns it.
        """
        doc_ref = self.db.collection(self.collection).document(resume_id)
        doc = doc_ref.get()

        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Resume with id {resume_id} not found",
            )

        data = doc.to_dict()
        if data.get("user_id") != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this resume",
            )

        doc_ref.delete()
        return {"status": "success", "message": "Resume deleted successfully"}
