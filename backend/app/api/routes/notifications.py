from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.notifications import NotificationResponse, UnreadCountResponse
from app.services.notifications import list_notifications, mark_notification_read, unread_count

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationResponse])
def get_notifications(
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_notifications(db, user, limit, offset)


@router.get("/unread-count", response_model=UnreadCountResponse)
def get_unread_count(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"unread_count": unread_count(db, user)}


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
def mark_read(notification_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notification = mark_notification_read(db, user, notification_id)
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found.")
    return notification
