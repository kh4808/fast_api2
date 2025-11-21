from datetime import datetime
from sqlalchemy.orm import Session
from typing import Optional
from server.models import LevelTestLog, User

def get_user_by_login_id(db: Session, login_id: str):
    return db.query(User).filter(User.login_id == login_id).first()

def get_last_log(db: Session, user_id: int):
    return (
        db.query(LevelTestLog)
        .filter(LevelTestLog.user_id == user_id)
        .order_by(LevelTestLog.created_at.desc())
        .first()
    )

def get_recent_logs(db: Session, user_id: int, level_test_num: Optional[int] = None, limit: int = 10):
    """
    특정 유저의 레벨 테스트 로그를 가져옵니다.
    - level_test_num이 있으면: 해당 level_test_num의 최근 로그
    - level_test_num이 없으면: 모든 level_test_num의 최근 로그
    """
    if level_test_num is not None:
        logs = (
            db.query(LevelTestLog)
            .filter(LevelTestLog.user_id == user_id,
                    LevelTestLog.level_test_num == level_test_num)
            .order_by(LevelTestLog.created_at.desc())
            .limit(limit)
            .all()
        )
    else:
        logs = (
            db.query(LevelTestLog)
            .filter(LevelTestLog.user_id == user_id)
            .order_by(LevelTestLog.created_at.desc())
            .limit(limit)
            .all()
        )
    logs.reverse()
    return logs

def get_all_logs_by_level(db: Session, user_id: int, level_test_num: int):
    return (
        db.query(LevelTestLog)
        .filter(LevelTestLog.user_id == user_id,
                LevelTestLog.level_test_num == level_test_num)
        .order_by(LevelTestLog.created_at.asc())
        .all()
    )

def save_level_test_log(db: Session, user_id: int, user_question: str, ai_response: str,
                        level_test_num: int, dialog_num: int):
    new_log = LevelTestLog(
        user_id=user_id,
        user_question=user_question,
        ai_response=ai_response,
        level_test_num=level_test_num,
        diolog_num=dialog_num,
        created_at=datetime.utcnow()
    )
    db.add(new_log)
    db.commit()
    db.refresh(new_log)
    return new_log
