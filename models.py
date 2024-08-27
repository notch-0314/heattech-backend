from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from db.db_config import Base
from datetime import datetime
import pytz

# 日本時間取得
def jst_now():
    return datetime.now(pytz.timezone('Asia/Tokyo'))

# テーブルの定義
class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_name = Column(String(225), unique=True, index=True)
    email = Column(String(225), unique=True, index=True)
    password = Column(String(225))
    oura_id = Column(Integer)
    type_id = Column(Integer)
    occupation_id = Column(String(225))
    overtime_id = Column(Integer)
    create_datetime = Column(DateTime, default=jst_now)
    update_datetime = Column(DateTime, default=jst_now, onupdate=jst_now)

    # リレーションシップの定義
    coping_messages = relationship("CopingMessage", back_populates="user")
    daily_messages = relationship("DailyMessage", back_populates="user")

class CopingMessage(Base):
    __tablename__ = "coping_messages"

    coping_message_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    assistant_text = Column(Text)
    coping_message_text = Column(Text)
    satisfaction_score = Column(String)
    heart_rate_before = Column(Integer)
    heart_rate_after = Column(Integer)
    create_datetime = Column(DateTime, default=jst_now)
    update_datetime = Column(DateTime, default=jst_now, onupdate=jst_now)

    # リレーションシップの定義
    user = relationship("User", back_populates="coping_messages")

class CopingMaster(Base):
    __tablename__ = "coping_master"

    coping_master_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    type_no = Column(Integer)
    type_name = Column(String(225))
    score_id = Column(Integer)
    time = Column(Integer)
    tone = Column(String(225))
    rest_type = Column(String(225))
    how_to_rest = Column(String(225))
    create_datetime = Column(DateTime, default=jst_now)
    update_datetime = Column(DateTime, default=jst_now, onupdate=jst_now)

class DailyMessage(Base):
    __tablename__ = "daily_messages"

    daily_message_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    daily_message_text = Column(Text)
    previous_days_score = Column(Integer)
    todays_days_score = Column(Integer)
    create_datetime = Column(DateTime, default=jst_now)
    update_datetime = Column(DateTime, default=jst_now, onupdate=jst_now)

    # リレーションシップの定義
    user = relationship("User", back_populates="daily_messages")