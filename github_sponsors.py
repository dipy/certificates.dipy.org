import os
import httpx
from dotenv import load_dotenv
from typing import Dict, Any, Optional

load_dotenv()

GITHUB_SPONSORS_TOKEN = os.getenv("GITHUB_SPONSORS_TOKEN")
GITHUB_API_URL = "https://api.github.com"


async def get_github_user_info(github_id: str) -> Optional[Dict[str, Any]]:
    """
    Get GitHub user information by ID.
    """
    if not GITHUB_SPONSORS_TOKEN:
        print("Warning: GitHub token not configured, skipping GitHub user lookup")
        return None

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GITHUB_API_URL}/user/{github_id}",
                headers={
                    "Authorization": f"token {GITHUB_SPONSORS_TOKEN}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to get GitHub user info: {response.status_code}")
                return None
    except Exception as e:
        print(f"Error fetching GitHub user info: {e}")
        return None


async def mark_github_user_as_sponsor(github_id: str, plan_type: str = "individual") -> Dict[str, Any]:
    """
    Mark a GitHub user as a sponsor in your system after FlexPay payment completion.
    
    This function:
    1. Gets the user's GitHub profile info
    2. Marks them as a sponsor in your internal system
    3. Returns sponsor information for tracking
    
    Note: This doesn't use GitHub's Sponsors API (which has limitations),
    but instead tracks sponsors internally with their GitHub info.
    """
    try:
        # Get GitHub user information
        user_info = await get_github_user_info(github_id)
        
        if user_info:
            # Create sponsor record with GitHub info
            sponsor_data = {
                "github_id": github_id,
                "github_username": user_info.get("login"),
                "github_avatar_url": user_info.get("avatar_url"),
                "github_profile_url": user_info.get("html_url"),
                "full_name": user_info.get("name"),
                "plan_type": plan_type,
                "sponsor_since": "now",  # You can add timestamp logic
                "status": "active"
            }
            
            print(f"✅ Marked GitHub user {user_info.get('login')} as sponsor ({plan_type} plan)")
            
            return {
                "id": github_id,  # Use GitHub ID as sponsor ID
                "github_username": user_info.get("login"),
                "plan_type": plan_type,
                "status": "marked_as_sponsor",
                "sponsor_data": sponsor_data
            }
        else:
            # Fallback if GitHub info can't be fetched
            return {
                "id": github_id,
                "github_username": f"user_{github_id}",
                "plan_type": plan_type,
                "status": "marked_as_sponsor_no_github_info",
                "sponsor_data": {
                    "github_id": github_id,
                    "plan_type": plan_type,
                    "status": "active"
                }
            }
            
    except Exception as e:
        print(f"Error marking user as sponsor: {e}")
        return {
            "id": github_id,
            "error": str(e),
            "status": "failed"
        }


async def get_sponsor_badge_url(github_username: str) -> str:
    """
    Generate a sponsor badge URL for the user.
    You can customize this to point to your own badge system.
    """
    # Example: Return a custom badge URL
    return f"https://your-domain.com/badges/sponsor/{github_username}.svg"


async def update_user_sponsor_status(github_id: str, is_sponsor: bool, plan_type: str = None) -> Dict[str, Any]:
    """
    Update a user's sponsor status in your system.
    """
    try:
        user_info = await get_github_user_info(github_id)
        
        if user_info:
            status_data = {
                "github_id": github_id,
                "github_username": user_info.get("login"),
                "is_sponsor": is_sponsor,
                "plan_type": plan_type or "unknown",
                "updated_at": "now"
            }
            
            print(f"Updated sponsor status for {user_info.get('login')}: {is_sponsor}")
            return status_data
        else:
            return {
                "github_id": github_id,
                "is_sponsor": is_sponsor,
                "error": "Could not fetch GitHub user info"
            }
            
    except Exception as e:
        return {
            "github_id": github_id,
            "error": str(e)
        }