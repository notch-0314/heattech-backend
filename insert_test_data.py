from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import Session
from datetime import datetime
import pytz
from passlib.context import CryptContext
from db.db_config import Base, engine, SessionLocal  # db_configからインポート
from models import User  # models.pyからインポート

# 日本時間（JST）を取得する関数
def jst_now():
    return datetime.now(pytz.timezone('Asia/Tokyo'))

# パスワードのハッシュ化のための設定
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# テーブルの再作成
Base.metadata.drop_all(bind=engine, tables=[Base.metadata.tables['users']])
Base.metadata.create_all(bind=engine, tables=[Base.metadata.tables['users']])

# テストデータの作成
test_data = [
    User(
        user_name="高橋晃",
        email="new_test1@example.com",
        password=pwd_context.hash("password1"),
        oura_id=1,
        type_id=1,
        occupation_id="1",
        overtime_id=20
    ),
    User(
        user_name="山下里佳",
        email="new_test2@example.com",
        password=pwd_context.hash("password2"),
        oura_id=2,
        type_id=2,
        occupation_id="2",
        overtime_id=20
    ),
    User(
        user_name="井上充",
        email="new_test3@example.com",
        password=pwd_context.hash("password2"),
        oura_id=1,
        type_id=2,
        occupation_id="2",
        overtime_id=20
    ),
    User(
        user_name="渡辺知実",
        email="new_test4@example.com",
        password=pwd_context.hash("password2"),
        oura_id=1,
        type_id=2,
        occupation_id="2",
        overtime_id=20
    ),
    User(
        user_name="林淳",
        email="new_test5@example.com",
        password=pwd_context.hash("password2"),
        oura_id=2,
        type_id=2,
        occupation_id="2",
        overtime_id=20
    )
]

# データベースにテストデータを挿入する関数
def insert_test_data(session: Session, data):
    # 既存のデータを削除
    session.query(User).delete()
    session.commit()

    for record in data:
        session.add(record)
    session.commit()

# メインプログラム
if __name__ == "__main__":
    # データベースセッションの作成
    db = SessionLocal()

    # テストデータの挿入
    insert_test_data(db, test_data)

    # セッションのクローズ
    db.close()
