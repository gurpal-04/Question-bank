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
    CreateFeatureRequestCommentRequest,
    FeatureRequestCommentResponse,
    FeatureRequestCommentListResponse,
)
from app.models.user import User

logger = logging.getLogger(__name__)

FEATURE_REQUESTS_COLLECTION = "feature_requests"


class FeatureRequestService:
    """Service for managing feature requests and votes in Firestore"""

    def __init__(self, db: firestore.Client):
        self.db = db
        self.collection = db.collection(FEATURE_REQUESTS_COLLECTION)

    def _doc_to_response(
        self,
        doc_id: str,
        data: dict,
        user_vote: Optional[VoteType] = None,
    ) -> FeatureRequestResponse:
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
            comments_count=int(data.get("comments_count", 0)),
            user_vote=user_vote,
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
            "comments_count": 0,
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

    async def get_feature_request_with_user_vote(
        self, feature_request_id: str, user: User
    ) -> Optional[FeatureRequestResponse]:
        doc_ref = self.collection.document(feature_request_id)
        doc = doc_ref.get()

        if not doc.exists:
            return None

        user_vote = None
        if user.id:
            vote_doc = doc_ref.collection("votes").document(user.id).get()
            if vote_doc.exists:
                vote_value = int(vote_doc.to_dict().get("vote", 0))
                if vote_value == 1:
                    user_vote = VoteType.UP
                elif vote_value == -1:
                    user_vote = VoteType.DOWN

        return self._doc_to_response(doc.id, doc.to_dict(), user_vote=user_vote)

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

    async def list_feature_requests_with_user_vote(
        self,
        user: User,
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

        docs = list(query.stream())
        feature_requests: List[FeatureRequestResponse] = []

        if user.id and docs:
            vote_doc_refs = [
                self.collection.document(doc.id)
                .collection("votes")
                .document(user.id)
                for doc in docs
            ]
            vote_docs = list(self.db.get_all(vote_doc_refs))
            vote_map = {}
            for vote_doc in vote_docs:
                if not vote_doc.exists:
                    continue
                # Resolve feature_request_id from vote document reference
                # vote_doc.reference.parent is 'votes' collection; parent.parent is feature request doc
                fr_ref = vote_doc.reference.parent.parent
                if fr_ref is None:
                    continue
                vote_value = int(vote_doc.to_dict().get("vote", 0))
                if vote_value == 1:
                    vote_map[fr_ref.id] = VoteType.UP
                elif vote_value == -1:
                    vote_map[fr_ref.id] = VoteType.DOWN

            for doc in docs:
                feature_requests.append(
                    self._doc_to_response(
                        doc.id, doc.to_dict(), user_vote=vote_map.get(doc.id)
                    )
                )
        else:
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

        # Determine current user vote after transaction (to update UI state)
        user_vote = None
        vote_doc = vote_ref.get()
        if vote_doc.exists:
            vote_value = int(vote_doc.to_dict().get("vote", 0))
            if vote_value == 1:
                user_vote = VoteType.UP
            elif vote_value == -1:
                user_vote = VoteType.DOWN

        response = self._doc_to_response(
            feature_request_id, updated_data, user_vote=user_vote
        )
        total_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "vote_feature_request: completed feature_request_id=%s user_id=%s total_ms=%.2f",
            feature_request_id,
            user.id,
            total_ms,
        )
        return response

    async def add_comment(
        self,
        feature_request_id: str,
        request: CreateFeatureRequestCommentRequest,
        user: User,
    ) -> Optional[FeatureRequestCommentResponse]:
        if not user.id:
            return None

        doc_ref = self.collection.document(feature_request_id)
        doc = doc_ref.get()
        if not doc.exists:
            return None

        now = datetime.utcnow()
        data = {
            "feature_request_id": feature_request_id,
            "text": request.text.strip(),
            "created_by": user.id,
            "created_by_email": user.email,
            "created_at": now,
        }

        comment_ref = doc_ref.collection("comments").document()
        transaction = self.db.transaction()

        @firestore.transactional
        def add_comment_txn(transaction: firestore.Transaction):
            snapshot = doc_ref.get(transaction=transaction)
            if not snapshot.exists:
                return None

            current_count = int(snapshot.to_dict().get("comments_count", 0))
            transaction.set(comment_ref, data)
            transaction.update(
                doc_ref,
                {
                    "comments_count": current_count + 1,
                    "updated_at": now,
                },
            )
            return True

        ok = add_comment_txn(transaction)
        if not ok:
            return None

        logger.info(
            "Created feature request comment: feature_request_id=%s comment_id=%s user_id=%s",
            feature_request_id,
            comment_ref.id,
            user.id,
        )

        return FeatureRequestCommentResponse(id=comment_ref.id, **data)

    async def list_comments(
        self,
        feature_request_id: str,
        limit: int = 100,
    ) -> Optional[FeatureRequestCommentListResponse]:
        doc_ref = self.collection.document(feature_request_id)
        doc = doc_ref.get()
        if not doc.exists:
            return None

        query = (
            doc_ref.collection("comments")
            .order_by("created_at", direction=firestore.Query.ASCENDING)
            .limit(limit)
        )

        docs = query.stream()
        comments: List[FeatureRequestCommentResponse] = []

        for doc in docs:
            data = doc.to_dict()
            created_at = data.get("created_at", datetime.utcnow())
            if hasattr(created_at, "to_datetime"):
                created_at = created_at.to_datetime()

            comments.append(
                FeatureRequestCommentResponse(
                    id=doc.id,
                    feature_request_id=data.get(
                        "feature_request_id", feature_request_id
                    ),
                    text=data.get("text", ""),
                    created_by=data.get("created_by", ""),
                    created_by_email=data.get("created_by_email"),
                    created_at=created_at,
                )
            )

        return FeatureRequestCommentListResponse(
            comments=comments, total=len(comments)
        )
