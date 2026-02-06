from google.cloud import firestore
from typing import Optional, List
from datetime import datetime
import logging
import time

from app.models.feature_request import (
    CreateFeatureRequestRequest,
    FeatureRequestResponse,
    FeatureRequestListResponse,
    VoteType,
)
from app.models.user import User

logger = logging.getLogger(__name__)

FEATURE_REQUESTS_COLLECTION = "feature_requests"


class FeatureRequestService:
    """Service for managing feature requests and votes in Firestore"""

    def __init__(self, db: firestore.Client):
        self.db = db
        self.collection = db.collection(FEATURE_REQUESTS_COLLECTION)

    def _doc_to_response(self, doc_id: str, data: dict) -> FeatureRequestResponse:
        created_at = data.get("created_at", datetime.utcnow())
        updated_at = data.get("updated_at", datetime.utcnow())

        if hasattr(created_at, "to_datetime"):
            created_at = created_at.to_datetime()
        if hasattr(updated_at, "to_datetime"):
            updated_at = updated_at.to_datetime()

        return FeatureRequestResponse(
            id=doc_id,
            title=data.get("title", ""),
            description=data.get("description", ""),
            created_by=data.get("created_by", ""),
            created_by_email=data.get("created_by_email"),
            upvotes=int(data.get("upvotes", 0)),
            downvotes=int(data.get("downvotes", 0)),
            score=int(data.get("score", 0)),
            created_at=created_at,
            updated_at=updated_at,
        )

    async def create_feature_request(
        self, request: CreateFeatureRequestRequest, user: User
    ) -> FeatureRequestResponse:
        now = datetime.utcnow()

        data = {
            "title": request.title.strip(),
            "description": request.description.strip(),
            "created_by": user.id or "",
            "created_by_email": user.email,
            "upvotes": 0,
            "downvotes": 0,
            "score": 0,
            "created_at": now,
            "updated_at": now,
        }

        _, doc_ref = self.collection.add(data)
        logger.info(f"Created feature request with ID: {doc_ref.id}")

        return self._doc_to_response(doc_ref.id, data)

    async def get_feature_request(
        self, feature_request_id: str
    ) -> Optional[FeatureRequestResponse]:
        doc_ref = self.collection.document(feature_request_id)
        doc = doc_ref.get()

        if not doc.exists:
            return None

        return self._doc_to_response(doc.id, doc.to_dict())

    async def list_feature_requests(
        self,
        sort: str = "new",
        limit: int = 100,
    ) -> FeatureRequestListResponse:
        query = self.collection

        if sort == "top":
            query = query.order_by("score", direction=firestore.Query.DESCENDING)
            query = query.order_by("created_at", direction=firestore.Query.DESCENDING)
        else:
            query = query.order_by("created_at", direction=firestore.Query.DESCENDING)

        query = query.limit(limit)

        docs = query.stream()
        feature_requests: List[FeatureRequestResponse] = []

        for doc in docs:
            feature_requests.append(self._doc_to_response(doc.id, doc.to_dict()))

        return FeatureRequestListResponse(
            feature_requests=feature_requests, total=len(feature_requests)
        )

    async def vote_feature_request(
        self, feature_request_id: str, user: User, vote: VoteType
    ) -> Optional[FeatureRequestResponse]:
        start = time.perf_counter()
        doc_ref = self.collection.document(feature_request_id)
        vote_ref = doc_ref.collection("votes").document(user.id or "")
        now = datetime.utcnow()

        if not user.id:
            return None

        vote_value = 1 if vote == VoteType.UP else -1

        transaction = self.db.transaction()
        logger.info(
            "vote_feature_request: begin transaction feature_request_id=%s user_id=%s vote=%s",
            feature_request_id,
            user.id,
            vote.value,
        )

        @firestore.transactional
        def update_vote(transaction: firestore.Transaction):
            doc_snapshot = doc_ref.get(transaction=transaction)
            if not doc_snapshot.exists:
                return None

            data = doc_snapshot.to_dict() or {}
            upvotes = int(data.get("upvotes", 0))
            downvotes = int(data.get("downvotes", 0))
            score = int(data.get("score", 0))

            vote_snapshot = vote_ref.get(transaction=transaction)
            previous_vote = None
            if vote_snapshot.exists:
                previous_vote = int(vote_snapshot.to_dict().get("vote", 0))

            if previous_vote == vote_value:
                # Toggle off: remove existing vote
                if previous_vote == 1:
                    upvotes = max(0, upvotes - 1)
                    score = score - 1
                elif previous_vote == -1:
                    downvotes = max(0, downvotes - 1)
                    score = score + 1

                transaction.delete(vote_ref)
                transaction.update(
                    doc_ref,
                    {
                        "upvotes": upvotes,
                        "downvotes": downvotes,
                        "score": score,
                        "updated_at": now,
                    },
                )

                updated = data.copy()
                updated.update(
                    {
                        "upvotes": upvotes,
                        "downvotes": downvotes,
                        "score": score,
                        "updated_at": now,
                    }
                )
                return updated

            # Remove previous vote
            if previous_vote == 1:
                upvotes = max(0, upvotes - 1)
                score = score - 1
            elif previous_vote == -1:
                downvotes = max(0, downvotes - 1)
                score = score + 1

            # Apply new vote
            if vote_value == 1:
                upvotes += 1
                score += 1
            else:
                downvotes += 1
                score -= 1

            transaction.set(
                vote_ref,
                {"vote": vote_value, "updated_at": now, "created_at": now},
                merge=True,
            )
            transaction.update(
                doc_ref,
                {
                    "upvotes": upvotes,
                    "downvotes": downvotes,
                    "score": score,
                    "updated_at": now,
                },
            )

            updated = data.copy()
            updated.update(
                {
                    "upvotes": upvotes,
                    "downvotes": downvotes,
                    "score": score,
                    "updated_at": now,
                }
            )
            return updated

        txn_start = time.perf_counter()
        updated_data = update_vote(transaction)
        txn_ms = (time.perf_counter() - txn_start) * 1000
        logger.info(
            "vote_feature_request: transaction done feature_request_id=%s user_id=%s ms=%.2f",
            feature_request_id,
            user.id,
            txn_ms,
        )
        if updated_data is None:
            total_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "vote_feature_request: not found feature_request_id=%s user_id=%s total_ms=%.2f",
                feature_request_id,
                user.id,
                total_ms,
            )
            return None

        response = self._doc_to_response(feature_request_id, updated_data)
        total_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "vote_feature_request: completed feature_request_id=%s user_id=%s total_ms=%.2f",
            feature_request_id,
            user.id,
            total_ms,
        )
        return response
