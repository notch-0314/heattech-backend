import requests

# ログインAPIのURL
login_url = "http://127.0.0.1:8000/token"

# ログインに使用するデータ
login_data = {
    "username": "田中太郎",  # ユーザー名
    "password": "password1"  # パスワード
}

# FastAPIのOAuth2PasswordRequestFormに対応するデータ形式
login_form_data = {
    "grant_type": "",
    "username": login_data["username"],
    "password": login_data["password"],
    "scope": "",
    "client_id": "",
    "client_secret": ""
}

# ヘッダー情報
headers = {
    'Content-Type': 'application/x-www-form-urlencoded'
}

# ログインリクエストを送信
response = requests.post(login_url, data=login_form_data, headers=headers)

# 結果を表示
print(f"Status code: {response.status_code}")
print("Response text:", response.text)

try:
    print(response.json())
except requests.exceptions.JSONDecodeError:
    print("Failed to decode JSON response")
