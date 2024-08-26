from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str

class UserCreate(BaseModel):
    user_name: str
    email: str
    password: str

class UserInDB(UserCreate):
    hashed_password: str