from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

# Security settings
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing (keeping for potential future use)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth settings
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_github_user_info(access_token: str) -> Dict[str, Any]:
    """Get GitHub user information using access token"""
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"token {access_token}"}
        response = await client.get("https://api.github.com/user", headers=headers)

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not validate GitHub credentials"
            )

        return response.json()


async def get_github_access_token(code: str) -> str:
    """Exchange GitHub authorization code for access token"""
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GitHub OAuth not configured"
        )

    async with httpx.AsyncClient() as client:
        data = {
            "client_id": GITHUB_CLIENT_ID,
            "client_secret": GITHUB_CLIENT_SECRET,
            "code": code
        }
        response = await client.post(
            "https://github.com/login/oauth/access_token",
            data=data,
            headers={"Accept": "application/json"}
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not get GitHub access token"
            )

        token_data = response.json()
        if "error" in token_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"GitHub OAuth error: {token_data['error']}"
            )

        return token_data["access_token"]


async def get_google_user_info(access_token: str) -> Dict[str, Any]:
    """Get Google user information using access token"""
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers=headers
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not validate Google credentials"
            )

        return response.json()


async def get_google_access_token(code: str, redirect_uri: str) -> str:
    """Exchange Google authorization code for access token"""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth not configured"
        )

    async with httpx.AsyncClient() as client:
        data = {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri
        }
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data=data
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not get Google access token"
            )

        token_data = response.json()
        if "error" in token_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Google OAuth error: {token_data['error']}"
            )

        return token_data["access_token"]


async def get_linkedin_user_info(access_token: str) -> Dict[str, Any]:
    """Get LinkedIn user information and email using access token"""
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {access_token}"}
        # Fetch profile
        profile_resp = await client.get(
            "https://api.linkedin.com/v2/me",
            headers=headers
        )
        if profile_resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not validate LinkedIn credentials"
            )
        profile = profile_resp.json()

        # Fetch email
        email_url = (
            "https://api.linkedin.com/v2/emailAddress"
            "?q=members&projection=(elements*(handle~))"
        )
        email_resp = await client.get(
            email_url,
            headers=headers
        )
        if email_resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not fetch LinkedIn email"
            )
        email_data = email_resp.json()
        email = None
        elements = email_data.get("elements", [])
        if elements and "handle~" in elements[0]:
            email = elements[0]["handle~"].get("emailAddress")

        # Compose user info
        user_info = {
            "id": profile.get("id"),
            "name": (
                profile.get("localizedFirstName", "")
                + " "
                + profile.get("localizedLastName", "")
            ),
            "email": email,
            # LinkedIn does not provide avatar by default
            "avatar_url": None
        }
        return user_info


async def get_linkedin_access_token(code: str, redirect_uri: str) -> str:
    """Exchange LinkedIn authorization code for access token"""
    if not LINKEDIN_CLIENT_ID or not LINKEDIN_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="LinkedIn OAuth not configured"
        )

    async with httpx.AsyncClient() as client:
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": LINKEDIN_CLIENT_ID,
            "client_secret": LINKEDIN_CLIENT_SECRET
        }
        response = await client.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            data=data
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not get LinkedIn access token"
            )

        token_data = response.json()
        if "error" in token_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"LinkedIn OAuth error: {token_data['error']}"
            )

        return token_data["access_token"]