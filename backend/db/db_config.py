import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# SSL証明書のパス
base_path = os.path.dirname(os.path.abspath(__file__))
ssl_cert_path = os.path.join(base_path, 'DigiCertGlobalRootG2.crt.pem')

# MySQLの接続URLにSSLオプションを追加
DATABASE_URL = (
    "mysql+mysqlconnector://tech0gen7student:vY7JZNfU"
    "@tech0-db-step4-studentrdb-2.mysql.database.azure.com/heattech_app"
    "?ssl_ca={}".format(ssl_cert_path)
)

# SQLAlchemyエンジンの作成
engine = create_engine(DATABASE_URL, echo=True)

# セッションの作成
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ベースクラスの宣言
Base = declarative_base()


