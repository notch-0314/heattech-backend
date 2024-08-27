import requests
from datetime import datetime, timedelta
from openai import OpenAI
import os
from models import CopingMaster, User, CopingMessage, DailyMessage
from sqlalchemy import and_, func
from sqlalchemy.orm import Session
from db.db_config import SessionLocal
from dotenv import load_dotenv
import random

# .envファイルから環境変数を読み込む
load_dotenv()

# 環境変数からAPIキーを取得
OURA_API_KEY_1 = os.getenv('OURA_API_KEY_1')
OURA_API_KEY_2 = os.getenv('OURA_API_KEY_2')
GPT_API_KEY = os.getenv('GPT_API_KEY')

# 日付に関する定義
yesterday_date = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')
today_date = datetime.today().strftime('%Y-%m-%d')
today = datetime.today().strftime('%Y-%m-%d')
current_day = datetime.today().weekday()  # 月曜日=0, 日曜日=6

# time_valuesを取得
if current_day in [0, 1, 2, 3, 4]:  # 平日
    time_values = (10, 60, 180)
else:  # 休日
    time_values = (60, 180, 200)

# SQLAlchemyのDB接続
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 指定したコーピングをコーピングマスタから取得する関数
def fetch_coping_master(db: Session, score_id: int, time_value: int):
    return db.query(CopingMaster).filter(
        CopingMaster.type_name == '焦燥',
        CopingMaster.score_id == score_id,
        CopingMaster.time == time_value
    ).all()

# OuraAPIから昨日と今日のスコアを取得する関数
def fetch_daily_readiness(api_key: str):
    url = 'https://api.ouraring.com/v2/usercollection/daily_readiness'
    params = {
        'start_date': yesterday_date,
        'end_date': today_date
    }
    headers = {
        'Authorization': f'Bearer {api_key}'
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        print(f"Failed to fetch data from API, status code: {response.status_code}")
        return 0, 0

    data = response.json()
    if not data['data']:
        print("No data found for today")
        return 0, 0

    # データからスコアを抽出
    scores = {entry['day']: entry['score'] for entry in data['data']}
    return scores.get(yesterday_date, 0), scores.get(today_date, 0)


# ユーザーによってOuraAPIキーを変える関数
def select_api_key(user):
    if user.oura_id == 1:
        return OURA_API_KEY_1
    elif user.oura_id == 2:
        return OURA_API_KEY_2
    else:
        print(f"Invalid user type for user {user.user_name}")
        return None

# 今日のスコアからscore_idを取得する関数
def calculate_score_id(todays_score):
    if 0 <= todays_score <= 59:
        return 1
    elif 60 <= todays_score <= 69:
        return 2
    elif 70 <= todays_score <= 84:
        return 3
    elif 85 <= todays_score <= 100:
        return 4
    else:
        return None

# スコアに合わせてランダムにプロンプトを取得する関数
def get_assistant_content(score_id):
    if score_id == 1:
        messages = [
            "今は一度立ち止まる時です。体調が非常に心配です。残業で心身が限界に近づきつつあります。どうか無理をせず、今すぐ休息を取って、自分を大切にしてください。",
            "体調が非常に心配です。長時間の残業が続いていませんか？これ以上無理をすると、健康に大きな影響が出るかもしれません。まずは少し休んで、心と体を労わってください。",
            "かなり疲れが溜まっており、放置すると危険な状況です。今すぐしっかりと休息を取って、体をいたわってあげてください。あなたの健康が第一です。"
        ]
    elif score_id == 2:
        messages = [
            "少し体調が悪化していますね。残業が続いていませんか？このままではもっと辛くなるかもしれません。早めに休息を取って、心身をリフレッシュしてくださいね。",
            "体調が気になります。長時間働きすぎていませんか？今、少しでも休むことで、これ以上の疲れを防げます。どうかご自身を大事にしてください。",
            "最近、体調が少し崩れているようです。残業が続いているので、今すぐにでも休息を取って、心と体をリセットしましょう。"
        ]
    elif score_id == 3:
        messages = [
            "健康状態は良好ですね。ただ、残業が続くと疲労が溜まってしまうこともあります。健康を保つためにも、定期的にリフレッシュする時間を持つことをおすすめします。",
            "今の調子はとても良いですが、無理をしないよう気をつけてくださいね。疲れる前に休息を取り、この良い状態を保っていきましょう。",
            "あなたの健康は今とても良好ですが、疲れが溜まらないように、時々リフレッシュして体調を整えてください。"
        ]
    elif score_id == 4:
        messages = [
            "今のあなたはとても良い状態です。この調子で、無理をせずに適度な休息を取りながらバランスよく過ごしていきましょうね。",
            "健康状態がとても良いですね。でも、無理をしないように、定期的にリフレッシュして今の素晴らしい状態を保ってください。",
            "あなたの状態はとても良いです。このまま無理をせず、適度な休息を取りながら過ごして、良い状態を維持してくださいね。"
        ]
    
    return random.choice(messages)

# 取得したtime_valueの数だけcoping_masterからコーピングレコードを取得する関数
def fetch_all_coping_lists(db: Session, score_id: int, time_values):
    coping_lists = []
    for time_value in time_values:
        result = fetch_coping_master(db, score_id, time_value)
        if result:
            random_record = random.choice(result)  # ランダムに1行を選択
            coping_lists.append(random_record)
    return coping_lists

# GPTを利用する関数
def generate_gpt_response(coping_lists):
    advice_lists = []
    client = OpenAI(api_key=GPT_API_KEY)
    for index, record in enumerate(coping_lists):
        try:
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "あなたは残業が異常に多いビジネスマンに休憩の方法をアドバイスする、経験豊富なアドバイザーです。彼らは責任感が強く、休むことに対して罪悪感を感じる傾向があります。"},
                    {"role": "user", "content": "以下の休憩方法を50字以内で紹介してください。"},
                    {"role": "user", "content": f"{record.rest_type}"}
                ],
                model="gpt-4-turbo",
            )
            advice = chat_completion.choices[0].message.content.strip()
            advice_lists.append(advice)
            print(f"Advice for coping item {index + 1}: {advice}")

        except Exception as e:
            print(f"Error processing coping item {index + 1}: {e}")

    return advice_lists

# coping_messageを保存する関数
def save_coping_message(db, user_id, assistant_text, message_text):
    new_coping_message = CopingMessage(
        user_id=user_id,
        assistant_text=assistant_text,
        coping_message_text=message_text,
        satisfaction_score="とても良い",
        heart_rate_before=0,
        heart_rate_after=0
    )
    db.add(new_coping_message)
    db.commit()

# coping_messageを取り出す関数
def get_coping_results(db, user_id, today_date):
    return db.query(CopingMessage).filter(
        CopingMessage.user_id == user_id,
        func.date(CopingMessage.create_datetime) == today_date,
        CopingMessage.satisfaction_score.isnot(None)
    ).all()

# daily_messageを生成する関数
def generate_daily_message_text(coping_results, todays_score, yesterdays_score):
    def get_score_comment(score):
        if 0 <= score <= 59:
            return '疲労が蓄積しています。あなたは十分に頑張っています。今は無理せず、心と体を休める時間を大切にしてください。自分を労わることも大切ですよ。'
        elif 60 <= score <= 69:
            return '少し疲れが出てきていますね。ペースを落とし、安心して休息を取りましょう。焦らずに、あなたのペースで進めば大丈夫です。'
        elif 70 <= score <= 84:
            return '体調は安定しています。少しリラックスして、無理せずに、休息も大切にしてください。'
        elif 85 <= score <= 100:
            return '体調がとても良い状態です。この良い状態を維持するために、適度に休息を取りながら、日々を過ごしましょう。'
        else:
            return 'スコアが不正です。'

    # 当日スコアがNoneの場合
    if todays_score is None:
        return '当日スコアがないため比較できません'
    
    # coping_resultsがある場合
    if coping_results:
        if todays_score > yesterdays_score:
            return f'昨日よりもスコアが良くなっていますね。{get_score_comment(todays_score)}'
        elif todays_score == yesterdays_score:
            return f'スコアは昨日と同じです。{get_score_comment(todays_score)}'
        else:
            return f'昨日よりスコアが少し下がっていますが、焦らずにいきましょう。{get_score_comment(todays_score)}'
    
    # coping_resultsがない場合
    else:
        if todays_score > yesterdays_score:
            return f'昨日よりもスコアが良くなっていますね。{get_score_comment(todays_score)}'
        elif todays_score == yesterdays_score:
            return f'スコアは昨日と同じです。{get_score_comment(todays_score)}'
        else:
            return f'昨日よりスコアが少し下がっています。{get_score_comment(todays_score)}'

# daily_messageを保存する関数
def save_daily_message(db, user_id, daily_message_text, yesterdays_score, todays_score):
    new_daily_message = DailyMessage(
        user_id=user_id,
        daily_message_text=daily_message_text,
        previous_days_score=yesterdays_score,
        todays_days_score=todays_score
    )
    db.add(new_daily_message)
    db.commit()

def main():

    # データベースセッションの作成
    db_gen = get_db()
    db = next(db_gen)

    # すべてのユーザーを取得
    users = db.query(User).all()

    for user in users:
        # APIキーの選択
        api_key = select_api_key(user)
        if api_key is None:
            continue

        # APIからスコアを取得
        yesterdays_score, todays_score = fetch_daily_readiness(api_key)
        if todays_score is None:
            continue

        # スコアIDの計算
        score_id = calculate_score_id(todays_score)
        if score_id is None:
            print(f"{user.user_name}のスコアIDはありません")
            continue

        # scoreとscore_idを出力
        print(f"User: {user.user_name}")
        print(f"Score: {todays_score}")
        print(f"Score ID: {score_id}")

        # コーピングマスタに照合
        coping_lists = fetch_all_coping_lists(db, score_id, time_values)

        # assistant_messageを生成
        assistant_message = get_assistant_content(score_id)

        # GPTにアクセス
        advice_lists = generate_gpt_response(coping_lists)

        # advice_listごとに保存
        for advice_list in advice_lists:
            save_coping_message(db, user.user_id, assistant_message, advice_list)
            print(advice_list)
            print("-" * 50)

        # クエリの実行
        coping_results = get_coping_results(db, user.user_id, today_date)

        # 取得したコーピングメッセージの表示
        for coping in coping_results:
            print(f'当てはまるcoping_messageは{coping.coping_message_text, coping.satisfaction_score}')

        # daily_messageの生成
        daily_message_text = generate_daily_message_text(coping_results, todays_score, yesterdays_score)

        # daily_messagesテーブルにdaily_messageを格納
        save_daily_message(db, user.user_id, daily_message_text, yesterdays_score, todays_score)

    # セッションのクローズ
    db_gen.close()

if __name__ == "__main__":
    main()







