from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import os
from dotenv import load_dotenv

from database import get_db
from models import User
from auth import (
    create_access_token,
    verify_token,
    get_github_access_token,
    get_github_user_info,
    get_google_access_token,
    get_google_user_info,
    get_linkedin_access_token,
    get_linkedin_user_info
)

load_dotenv()

auth_router = APIRouter(prefix="/auth", tags=["authentication"])

# OAuth URLs
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")


@auth_router.get("/github/login")
async def github_login():
    """Redirect to GitHub OAuth"""
    if not GITHUB_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GitHub OAuth not configured"
        )

    github_auth_url = (
        f"https://github.com/login/oauth/authorize?"
        f"client_id={GITHUB_CLIENT_ID}&"
        f"scope=user user:email"
    )
    return RedirectResponse(url=github_auth_url)


@auth_router.get("/github/callback")
async def github_callback(
    code: str,
    db: AsyncSession = Depends(get_db)
):
    """Handle GitHub OAuth callback"""
    try:
        # Exchange code for access token
        access_token = await get_github_access_token(code)

        # Get user info from GitHub
        user_info = await get_github_user_info(access_token)

        # Check if user exists
        result = await db.execute(
            select(User).where(User.github_id == str(user_info["id"]))
        )
        user = result.scalar_one_or_none()

        if not user:
            # Handle missing email - GitHub doesn't always provide email
            email = user_info.get("email")
            if not email:
                # Generate a placeholder email or use username
                username = user_info.get("login", "github_user")
                email = f"{username}@github.user"
                print(
                    f"Warning: No email from GitHub for user {username}, "
                    f"using placeholder: {email}"
                )

            # Create new user
            user = User(
                email=email,
                username=user_info.get("login"),
                full_name=user_info.get("name"),
                github_id=str(user_info["id"]),
                github_username=user_info.get("login"),
                avatar_url=user_info.get("avatar_url")
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

        # Create access token
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )

        # Redirect to sponsors page with token
        return RedirectResponse(
            url=f"{BASE_URL}/services/sponsors?token={access_token}"
        )

    except Exception as e:
        print(f"Error in github_callback: {e}")
        return RedirectResponse(
            url=f"{BASE_URL}/services/sponsors?error=github_auth_failed"
        )


@auth_router.get("/google/login")
async def google_login():
    """Redirect to Google OAuth"""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth not configured"
        )

    redirect_uri = f"{BASE_URL}/services/auth/google/callback"
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope=openid email profile"
    )
    return RedirectResponse(url=google_auth_url)


@auth_router.get("/google/callback")
async def google_callback(
    code: str,
    db: AsyncSession = Depends(get_db)
):
    """Handle Google OAuth callback"""
    try:
        redirect_uri = f"{BASE_URL}/services/auth/google/callback"

        # Exchange code for access token
        access_token = await get_google_access_token(code, redirect_uri)

        # Get user info from Google
        user_info = await get_google_user_info(access_token)

        # Check if user exists
        result = await db.execute(
            select(User).where(User.google_id == user_info["id"])
        )
        user = result.scalar_one_or_none()

        if not user:
            # Create new user
            user = User(
                email=user_info.get("email", ""),
                username=user_info.get("email").split("@")[0],
                full_name=user_info.get("name"),
                google_id=user_info["id"],
                avatar_url=user_info.get("picture")
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

        # Create access token
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )

        # Redirect to sponsors page with token
        return RedirectResponse(
            url=f"{BASE_URL}/services/sponsors?token={access_token}"
        )

    except Exception:
        return RedirectResponse(
            url=f"{BASE_URL}/services/sponsors?error=google_auth_failed"
        )


@auth_router.get("/linkedin/login")
async def linkedin_login():
    """Redirect to LinkedIn OAuth"""
    if not LINKEDIN_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="LinkedIn OAuth not configured"
        )

    redirect_uri = f"{BASE_URL}/services/auth/linkedin/callback"
    linkedin_auth_url = (
        f"https://www.linkedin.com/oauth/v2/authorization?"
        f"client_id={LINKEDIN_CLIENT_ID}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope=r_liteprofile r_emailaddress"
    )
    return RedirectResponse(url=linkedin_auth_url)


@auth_router.get("/linkedin/callback")
async def linkedin_callback(
    code: str,
    db: AsyncSession = Depends(get_db)
):
    """Handle LinkedIn OAuth callback"""
    try:
        redirect_uri = f"{BASE_URL}/services/auth/linkedin/callback"

        # Exchange code for access token
        access_token = await get_linkedin_access_token(code, redirect_uri)

        # Get user info from LinkedIn
        user_info = await get_linkedin_user_info(access_token)

        # Check if user exists
        result = await db.execute(
            select(User).where(User.linkedin_id == user_info["id"])
        )
        user = result.scalar_one_or_none()

        if not user:
            # Create new user
            user = User(
                email=user_info.get("email", ""),
                username=(
                    user_info.get("email", "").split("@")[0]
                    if user_info.get("email") else None
                ),
                full_name=user_info.get("name"),
                linkedin_id=user_info["id"],
                linkedin_username=user_info.get("username"),
                avatar_url=user_info.get("picture")
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

        # Create access token
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )

        # Redirect to sponsors page with token
        return RedirectResponse(
            url=f"{BASE_URL}/services/sponsors?token={access_token}"
        )

    except Exception as e:
        print(f"Error in linkedin_callback: {e}")
        return RedirectResponse(
            url=f"{BASE_URL}/services/sponsors?error=linkedin_auth_failed"
        )


@auth_router.get("/me")
async def get_current_user(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """Get current user information"""
    try:
        payload = verify_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "auth_method": user.auth_method,
            "avatar_url": user.avatar_url
        }

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


@auth_router.get("/logout")
async def logout():
    """Logout endpoint - client should clear token"""
    return {"message": "Logged out successfully"}