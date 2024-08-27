from .db_config import engine, Base

def initialize_database():
    # テーブルを作成
    Base.metadata.create_all(bind=engine)
    print("Database and tables initialized successfully")
