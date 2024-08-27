import requests
import json
import pandas as pd
import mysql.connector
from openai import OpenAI
import os
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from schemas import Token, UserCreate, UserInDB
from starlette.status import HTTP_401_UNAUTHORIZED
from sqlalchemy.orm import Session
from sqlalchemy import text, create_engine, func
from models import CopingMessage, User, DailyMessage
from typing import List, Optional
from db.db_init import initialize_database
from db.db_config import SessionLocal
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pytz

app = FastAPI()

'''
# CORSミドルウェアを追加
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ここには許可するオリジンを指定します。全て許可する場合は["*"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
'''


initialize_database()

# SQLAlchemyのDB接続
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# シークレットキーの設定
SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# .envファイルから環境変数を読み込む
load_dotenv()

# 環境変数からAPIキーを取得
OURA_API_KEY_1 = os.getenv('OURA_API_KEY_1')
OURA_API_KEY_2 = os.getenv('OURA_API_KEY_2')
GPT_API_KEY = os.getenv('GPT_API_KEY')

# 日付に関する定義
yesterday_date = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')
today_date = datetime.today().strftime('%Y-%m-%d')

# パスワードのハッシュ化のための設定
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# OAuth2の設定
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# ユーザーによってOuraAPIキーを変える関数
def select_api_key(user):
    if user.oura_id == 1:
        return OURA_API_KEY_1
    elif user.oura_id == 2:
        return OURA_API_KEY_2
    else:
        print(f"Invalid user type for user {user.user_name}")
        return None

# パスワードの検証
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# パスワードのハッシュ化
def get_password_hash(password):
    return pwd_context.hash(password)

# アクセストークンの作成
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# ユーザーを取得する関数
def get_user(db: Session, username: str):
    return db.query(User).filter(User.user_name == username).first()

# ユーザーの認証
def authenticate_user(db: Session, username: str, password: str):
    user = get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user.password):
        return False
    return user

# トークンのデコード
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(db, username=username)
    if user is None:
        raise credentials_exception
    return user

# coping_messageを取得する関数
def fetch_coping_message(db: Session, user_id: int):
    result = db.query(CopingMessage).filter(
        CopingMessage.user_id == user_id,
        func.date(CopingMessage.create_datetime) == today_date
    ).all()

    # 最後の3つのメッセージのみを取得
    last_three_messages = result[-3:]

    return [message.__dict__ for message in last_three_messages]

# daily_messageを取得する関数
def fetch_daily_message(db: Session, user_id: int):
    result = db.query(DailyMessage).filter(
        DailyMessage.user_id == user_id,
        func.date(DailyMessage.create_datetime) == today_date
    ).first()
    return result

def fetch_contributer(api_key: str):

    url = 'https://api.ouraring.com/v2/usercollection/daily_readiness'
    params = {
        'start_date': today_date,
        'end_date': today_date
    }
    headers = {
        'Authorization': f'Bearer {api_key}'
    }
    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        print(f"Failed to fetch data from API, status code: {response.status_code}")
        return None

    data = response.json()

    if not data['data']:
        print("No data found for today")
        return None

    print(data)

    return data

# 最新の心拍数を取得する関数
def fetch_heart_rate(api_key: int):
    url = 'https://api.ouraring.com/v2/usercollection/heartrate'
    params = {}
    headers = {
        'Authorization': f'Bearer {api_key}'
    }
    response = requests.request('GET', url, headers=headers, params=params)
    data = response.json()
    print(data)
    latest_bpm = data['data'][-1]['bpm'] if 'data' in data and len(data['data']) > 0 else None
    print(latest_bpm)
    return(latest_bpm)

# 心拍数をheart_rate_beforeに登録する関数
def update_heart_rate_before(db: Session, coping_message_id: int, heart_rate_before: int):
    coping_message = db.query(CopingMessage).filter(CopingMessage.coping_message_id == coping_message_id).first()
    if coping_message:
        coping_message.heart_rate_before = heart_rate_before
        db.commit()
    else:
        raise HTTPException(status_code=404, detail="Coping message not found")

# 満足度を登録する関数
def update_satisfaction_score(db: Session, coping_message_id: int, satisfaction_score: str):
    coping_message = db.query(CopingMessage).filter(CopingMessage.coping_message_id == coping_message_id).first()
    if coping_message:
        coping_message.satisfaction_score = satisfaction_score
        db.commit()
    else:
        raise HTTPException(status_code=404, detail="Coping message not found")

# 心拍数をheart_rate_afterに登録する関数
def update_heart_rate_after(db: Session, coping_message_id: int, heart_rate_after: int):
    coping_message = db.query(CopingMessage).filter(CopingMessage.coping_message_id == coping_message_id).first()
    if coping_message:
        coping_message.heart_rate_after = heart_rate_after
        db.commit()
    else:
        raise HTTPException(status_code=404, detail="Coping message not found")

# 特定のcoping_message_idのheart_rate_beforeを取得する関数
def get_heart_rate_before(db: Session, coping_message_id: int):
    coping_message = db.query(CopingMessage).filter(CopingMessage.coping_message_id == coping_message_id).first()
    if coping_message:
        return coping_message.heart_rate_before
    else:
        raise HTTPException(status_code=404, detail="Coping message not found")

# ログインAPI
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.user_name}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# ユーザーの登録API
@app.post("/register")
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = User(
        user_name=user.user_name,
        email=user.email,
        password=get_password_hash(user.password),
        type_id=0,  # 仮の値
        occupation_id="unknown",  # 仮の値
        overtime_id=0,  # 仮の値
        create_datetime=datetime.now(pytz.timezone('Asia/Tokyo')),
        update_datetime=datetime.now(pytz.timezone('Asia/Tokyo'))
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# レコメンドページ情報取得API
@app.get('/coping_message')
async def get_coping_message(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    messages = fetch_coping_message(db, current_user.user_id)
    return {
        "user_name": current_user.user_name,
        "assistant_text": messages[0]["assistant_text"],
        "coping_messages": [{"coping_message_id": message["coping_message_id"],
                            "coping_message_text": message["coping_message_text"]
                            } for message in messages]
    }

# コンディションページ情報取得API
@app.get('/condition')
async def get_condition_info(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    message = fetch_daily_message(db, current_user.user_id) # daily_messageを取得
    api_key = select_api_key(current_user) # OuraのAPIキーを取得
    contributer = fetch_contributer(api_key) # Ouraのスコアを取得
    contributer_data = contributer['data'][0] if contributer['data'] else {} # Ouraスコアの中でcontributerデータを抽出
    return {
        "user_name": current_user.user_name,
        "daily_message_text": message.daily_message_text,
        "previous_days_score": message.previous_days_score,
        "todays_days_score": message.todays_days_score,
        "activity_balance": contributer_data.get('contributors', {}).get('activity_balance'),
        "body_temperature": contributer_data.get('contributors', {}).get('body_temperature'),
        "hrv_balance": contributer_data.get('contributors', {}).get('hrv_balance'),
        "previous_day_activity": contributer_data.get('contributors', {}).get('previous_day_activity'),
        "previous_night": contributer_data.get('contributors', {}).get('previous_night'),
        "recovery_index": contributer_data.get('contributors', {}).get('recovery_index'),
        "resting_heart_rate": contributer_data.get('contributors', {}).get('resting_heart_rate'),
        "sleep_balance": contributer_data.get('contributors', {}).get('sleep_balance'),
        "day": contributer_data.get('day')
    }

# コーピング実施前の心拍数取得API。coping_message_idをリクエストに含める必要あり
@app.post('/coping_start')
async def coping_start(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # リクエストからcoping_message_idを取得
    data = await request.json()
    coping_message_id = data.get('coping_message_id')
    if not coping_message_id:
        raise HTTPException(status_code=400, detail="coping_message_id is required")
    
    # 心拍数取得
    api_key = select_api_key(current_user) # OuraのAPIキーを取得
    latest_heart_rate = fetch_heart_rate(api_key)
    if latest_heart_rate is None:
        raise HTTPException(status_code=404, detail='心拍数が見つかりません')
    
    # 心拍数をcoping_messageに登録
    update_heart_rate_before(db, coping_message_id, latest_heart_rate)
    return{
            "message": "心拍数を登録しました",
            "heart_rate_before": latest_heart_rate
        }

#コーピング実施後の満足度登録/心拍数取得/メッセージ表示API。coping_message_id、satisfaction_scoreをリクエストに含める必要あり
@app.post('/coping_finish')
async def coping_finish(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # リクエストからcoping_message_idを取得
    data = await request.json()
    coping_message_id = data.get('coping_message_id')
    if not coping_message_id:
        raise HTTPException(status_code=400, detail="coping_message_idが必要です")

    # リクエストからsatisfaction_scoreを取得
    satisfaction_score = data.get('satisfaction_score')
    if not satisfaction_score:
        raise HTTPException(status_code=400, detail="satisfaction_scoreが必要です")

    # 心拍数取得
    api_key = select_api_key(current_user) # OuraのAPIキーを取得
    latest_heart_rate = fetch_heart_rate(api_key)
    if latest_heart_rate is None:
        raise HTTPException(status_code=404, detail='心拍数が見つかりません')
    
    # satisfaction_scoreを登録
    update_satisfaction_score(db, coping_message_id, satisfaction_score)
    
    # 心拍数を登録
    update_heart_rate_after(db, coping_message_id, latest_heart_rate)

    # heart_rate_beforeをテーブルから取得
    heart_rate_before = get_heart_rate_before(db, coping_message_id)

    # heart_rate_beforeとheart_rate_afterを比較して、メッセージを作成
    if latest_heart_rate < heart_rate_before:
        message = '休息により心拍数が下がり、リラックス傾向が高まりました。この調子で、定期的に休憩を取りましょう！'
    else:
        message = '休息前と比べて、心拍数が変わっていない、または少し心拍数が上がっているようです。休息が十分でない可能性があるので、他の休息も取り入れてみると良いかもしれません。'

    return {
        'message': message,
        'heart_rate_before': heart_rate_before,
        'latest_heart_rate': latest_heart_rate,
        'satisfaction_score': satisfaction_score
    }