import os
import httpx
import base64
import urllib.parse
from dotenv import load_dotenv
from typing import Dict, Any

load_dotenv()

FLEXPAY_URL = os.getenv("FLEXPAY_URL", "https://api.flexpay.com")
FLEXPAY_CLIENT_ID = os.getenv("FLEXPAY_CLIENT_ID")
FLEXPAY_CLIENT_SECRET = os.getenv("FLEXPAY_CLIENT_SECRET")


async def get_flexpay_bearer_token() -> str:
    """
    Get a bearer token using OAuth2 client credentials flow.
    """
    if not FLEXPAY_CLIENT_ID or not FLEXPAY_CLIENT_SECRET:
        raise RuntimeError("FlexPay credentials not configured.")

    # Step 1: Encode Client ID and Client Secret
    encoded_client_id = urllib.parse.quote(FLEXPAY_CLIENT_ID)
    encoded_client_secret = urllib.parse.quote(FLEXPAY_CLIENT_SECRET)

    # Concatenate and base64 encode
    credentials = f"{encoded_client_id}:{encoded_client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    # Step 2: Obtain bearer token
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{FLEXPAY_URL}/oauth/token",
            headers={
                "Authorization": f"Basic {encoded_credentials}",
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"
            },
            data={"grant_type": "client_credentials"}
        )

        if response.status_code != 200:
            raise RuntimeError(f"Failed to get bearer token: {response.status_code}")

        token_data = response.json()
        if token_data.get("token_type", "").lower() != "bearer":
            raise RuntimeError("Invalid token type received")

        return token_data["access_token"]


async def create_flexpay_session(
    amount: float,
    currency: str,
    user_email: str,
    plan_type: str,
    user_id: int,
    success_url: str,
    cancel_url: str
) -> Dict[str, Any]:
    """
    Create a FlexPay payment session and return the session info (including redirect URL).
    """
    # Get bearer token
    bearer_token = await get_flexpay_bearer_token()

    payload = {
        "Operator": user_email,
        "PatronType": "Anonymous",
        "PatronIdentifier":  str(user_id),
        "ReturnURL": success_url,
        "PageTitle": "DIPY SPONSOR PAYMENT OPTIONS",
        "Amount": "{:.2f}".format(amount),
        "Payments": {
            "CreditCardProcessing": {
                "PaymentScreenText": "Please enter your Credit Card information.",
                "ClientTransactionNumber": "feff9047-f190-40e3-b93e-42b53323833d",
                "Comment": "test comment",
                "ReceiptText": "text for receipt"
            }
        },
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{FLEXPAY_URL}/api/v1/payment",
            json=payload,
            headers={"Authorization": f"Bearer {bearer_token}"}
        )
        response.raise_for_status()
        return response.json()


async def verify_flexpay_payment(payment_id: str) -> Dict[str, Any]:
    """
    Verify the status of a FlexPay payment by its ID.
    """
    # Get bearer token
    bearer_token = await get_flexpay_bearer_token()

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{FLEXPAY_URL}/api/v1/transaction/request/status/{payment_id}",
            headers={"Authorization": f"Bearer {bearer_token}"}
        )
        response.raise_for_status()
        return response.json()


async def execute_flexpay_payment(transaction_request_id: str) -> Dict[str, Any]:
    """
    Execute a FlexPay payment after authorization using the TransactionRequestId.
    """
    bearer_token = await get_flexpay_bearer_token()
    
    payload = {
        "TransactionRequestId": transaction_request_id,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{FLEXPAY_URL}/api/v1/execute",
            json=payload,
            headers={"Authorization": f"Bearer {bearer_token}"}
        )
        response.raise_for_status()
        return response.json()