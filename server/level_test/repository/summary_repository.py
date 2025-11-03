from datetime import datetime
from sqlalchemy.orm import Session
from server.models import LevelTestSummary

def get_summaries_by_level(db: Session, user_id: int, level_test_num: int):
    return (
        db.query(LevelTestSummary)
        .filter(LevelTestSummary.user_id == user_id,
                LevelTestSummary.level_test_num == level_test_num)
        .order_by(LevelTestSummary.summary_num.asc())
        .all()
    )

def get_last_summary(db: Session, user_id: int, level_test_num: int):
    return (
        db.query(LevelTestSummary)
        .filter(LevelTestSummary.user_id == user_id,
                LevelTestSummary.level_test_num == level_test_num)
        .order_by(LevelTestSummary.summary_num.desc())
        .first()
    )

def save_summary(db: Session, user_id: int, level_test_num: int,
                 summary_num: int, summary_text: str):
    from server.models import LevelTestSummary
    new_summary = LevelTestSummary(
        user_id=user_id,
        level_test_num=level_test_num,
        summary_num=summary_num,
        summary_text=summary_text,
        created_at=datetime.utcnow()
    )
    db.add(new_summary)
    db.commit()
    db.refresh(new_summary)
    return new_summary
