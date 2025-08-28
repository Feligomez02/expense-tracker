from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
import json

router = APIRouter()

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
CLIENT_SECRETS_FILE = "credentials.json"

# URL de callback (donde Google devolverá el code)
REDIRECT_URI = "http://127.0.0.1:8000/auth/callback"

@router.get("/login")
def login():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    auth_url, _ = flow.authorization_url(prompt='consent')
    return RedirectResponse(auth_url)

@router.get("/callback")
def callback(code: str):
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    flow.fetch_token(code=code)
    credentials = flow.credentials

    token_data = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes
    }

    with open("token.json", "w") as token_file:
        json.dump(token_data, token_file)


    # Guardá el access_token y refresh_token en tu DB o archivo seguro
    return {
        "access_token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "expiry": str(credentials.expiry),
        "msg": "Tokens guardados en token.json."

    }
