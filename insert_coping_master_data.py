from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import Session
from datetime import datetime
import pytz
import pandas as pd
from passlib.context import CryptContext
from db.db_config import Base, engine, SessionLocal  # db_configからインポート


# 日本時間（JST）を取得する関数
def jst_now():
    return datetime.now(pytz.timezone('Asia/Tokyo'))

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

# テーブルの作成
Base.metadata.create_all(bind=engine)

# CSVファイルからデータを読み込む関数
def load_csv_to_db(csv_file_path, session: Session):
    # CSVファイルを読み込む
    data = pd.read_csv(csv_file_path)
    
    # 既存のデータを削除する
    session.query(CopingMaster).delete()
    session.commit()
    
    # データをCopingMasterインスタンスに変換
    for index, row in data.iterrows():
        record = CopingMaster(
            type_no=row['type_no'],
            type_name=row['type_name'],
            score_id=row['score_id'],
            time=row['time'],
            tone=row['tone'],
            rest_type=row['rest_type'],
            how_to_rest=row['how_to_rest']
        )
        session.add(record)
    
    session.commit()

# メインプログラム
if __name__ == "__main__":
    # データベースセッションの作成
    db = SessionLocal()

    # CSVファイルからデータを読み込んで挿入
    csv_file_path = './coping_master.csv'   # CSVファイルのパスを設定
    load_csv_to_db(csv_file_path, db)

    # セッションのクローズ
    db.close()
