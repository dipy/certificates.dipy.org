from dotenv import load_dotenv
import pathlib
import uvicorn
import re  # Import regex module
from fastapi import FastAPI, Request, Form, HTTPException, Header, APIRouter
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional
import urllib.parse
from rapidfuzz import fuzz
import hmac
import hashlib
import json
import subprocess
import os


# Load environment variables from the .env file
load_dotenv()

# --- Configuration ---
CERTIFICATES_DIR = pathlib.Path("certificates")
STATIC_DIR = pathlib.Path("static")
TEMPLATES_DIR = pathlib.Path("templates")
SUPPORTED_YEARS = list(range(2023, 2026))  # Years 2023, 2024, 2025
LINKEDIN_CERT_URL = (
    "https://www.linkedin.com/profile/add?startTask=CERTIFICATION_NAME"
)
ORGANIZATION_ID = "18898741"  # DIPY LinkedIn Organization ID
ISSUE_MONTH = "5"      # Default Issue Month - Still used for LinkedIn link

# GitHub webhook settings
GITHUB_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")
UPDATE_LAB_SCRIPT_PATH = pathlib.Path("update_lab_website.sh")
UPDATE_WORKSHOP_SCRIPT_PATH = pathlib.Path("update_workshop.sh")

# Create directories if they don't exist
CERTIFICATES_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)

# --- FastAPI App Setup ---
app = FastAPI(title="DIPY Services server")

# Create routers for different services
# Prefixes here will be combined with the prefix in app.include_router
certificates_router = APIRouter(prefix="/certificates", tags=["certificates"])
webhooks_router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def root_url_for(request: Request, name: str, **params):
    return str(request.url_for(name, **params))


# Setup Jinja2 templates
templates = Jinja2Templates(directory=TEMPLATES_DIR)
templates.env.globals["root_url_for"] = root_url_for


# --- Helper Functions ---
def find_certificate(
    search_name: str, search_year: str, min_score_threshold: int = 70
) -> Optional[pathlib.Path]:
    """
    Find the certificate PDF file with the best matching name recursively
    within a specific year folder.

    Performs a case-insensitive search within the CERTIFICATES_DIR/{search_year}
    directory and its subdirectories for PDF files. Calculates a similarity
    score between the search_name and the filename stem (the part before .pdf)
    using fuzzy matching. Returns the path of the file with the highest
    score above a minimum threshold.

    Parameters
    ----------
    search_name : str
        The name to search for (case-insensitive).
    search_year : str
        The specific year subfolder to search within (must be 4 digits).
    min_score_threshold : int, optional
        The minimum similarity score (0-100) required for a match
        to be considered valid. Default is 70.

    Returns
    -------
    Optional[pathlib.Path]
        The Path object of the best matching certificate file above the
        threshold, or None if no suitable match is found.
    """
    # Validate inputs
    if not search_name or not search_year:
        return None
    if not re.fullmatch(r'\d{4}', search_year):
        print(f"Warning: Invalid year format received: {search_year}")
        return None

    year_dir = CERTIFICATES_DIR / search_year
    if not year_dir.is_dir():
        print(
            f"Warning: Certificate directory for year '{search_year}' "
            f"not found at {year_dir}"
        )
        return None

    search_lower = search_name.lower()
    best_match_path = None
    highest_score = -1

    try:
        # Use rglob to search recursively within the specific year directory
        for item in year_dir.rglob("*.pdf"):
            if item.is_file():
                stem_lower = item.stem.lower()
                # Calculate partial ratio similarity score
                score = fuzz.partial_ratio(search_lower, stem_lower)

                # Check if this score is the best so far
                if score > highest_score:
                    highest_score = score
                    best_match_path = item

    except FileNotFoundError:
        # This specific error shouldn't happen due to the is_dir check above,
        # but added for robustness.
        print(f"Error: Unexpected FileNotFoundError while searching in {year_dir}")
        return None

    # Return the best match only if it meets the minimum score threshold
    if highest_score >= min_score_threshold:
        print(
            f"Best match found: '{best_match_path.name}' in year {search_year}"
            f" with score {highest_score} for query '{search_name}'"
        )
        return best_match_path
    else:
        print(
            f"No match found in year {search_year} above threshold "
            f"{min_score_threshold} for query '{search_name}'. "
            f"Highest score: {highest_score}"
        )
        return None


# --- Certificate Routes ---
@certificates_router.get("/healthcheck")
def certificates_healthcheck():
    return {"message": "Hello from FastAPI Certificates Service!"}


@certificates_router.get("/", response_class=HTMLResponse)
async def get_certificates_homepage(request: Request):  # Renamed for clarity
    """
    Serve the homepage for certificates.
    """
    context = {
        "request": request,
        "title": "DIPY Certificates",
        "supported_years": SUPPORTED_YEARS
    }
    return templates.TemplateResponse("index.html", context)


@certificates_router.post("/search", name="search_certificates_page",
                          response_class=HTMLResponse)
async def search_certificates_page(  # Renamed for clarity
    request: Request,
    search_query: str = Form(..., max_length=100),
    search_year: str = Form(..., max_length=4)
):
    """
    Handle the certificate search request from the homepage.

    Searches for a certificate matching the query within the specified year.
    Returns an HTML snippet containing either the certificate details (with
    download/view/LinkedIn links) or a 'not found' message. This response
    is designed to be inserted into the DOM by HTMX.

    Parameters
    ----------
    request : Request
        The incoming request object.
    search_query : str
        The name entered in the search bar, obtained from form data.
    search_year : str
        The year selected in the dropdown, obtained from form data.

    Returns
    -------
    HTMLResponse
        An HTML snippet with the search results.
    """
    print(f"Searching for '{search_query}' in year '{search_year}'")  # Debug print
    certificate_path = find_certificate(search_query, search_year)
    certificate_name = certificate_path.stem if certificate_path else None
    linkedin_url = None

    if certificate_name:
        # Generate absolute URL for the certificate view page on this server
        try:
            cert_page_url = request.url_for(
                'view_certificate_page', year=search_year, name_stem=certificate_name
            )
        except Exception as e:
            print(f"Error generating URL for view_certificate_page: {e}")
            cert_page_url = ""  # Handle error case

        # Prepare parameters for LinkedIn URL
        params = {
            "name": certificate_name,
            "organizationId": ORGANIZATION_ID,
            "issueYear": search_year,  # Use selected year
            "issueMonth": ISSUE_MONTH,  # Use configured default month
            # Ensure certUrl is a string and fits within line limits
            "certUrl": str(cert_page_url)
        }
        # URL-encode parameters
        encoded_params = urllib.parse.urlencode(params)
        linkedin_url = f"{LINKEDIN_CERT_URL}&{encoded_params}"

    # Pass search_year to the template for link generation
    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "certificate_name": certificate_name,
            "linkedin_url": linkedin_url,
            "not_found": certificate_path is None,
            "query": search_query,   # Keep original query for display
            "year": search_year,      # Pass year for download/view links
            "router_prefix": certificates_router.prefix  # Pass router prefix
        },
    )


@certificates_router.get(
    "/download/{year}/{name_stem}.pdf", name="download_certificate_file"
)
async def download_certificate_file(year: str, name_stem: str):  # Renamed
    """
    Serve a specific certificate file for download, ensuring year match.

    This route re-validates the path by calling find_certificate with the
    provided year and name stem.

    Parameters
    ----------
    year : str
        The year directory containing the certificate.
    name_stem : str
        The stem (filename without extension) of the certificate.

    Returns
    -------
    FileResponse
        The PDF file response for downloading.

    Raises
    ------
    HTTPException
        404 Not Found if the certificate file doesn't exist within that year.
    """
    # Re-run find_certificate for validation. Use a high threshold for exact match.
    # Note: We search using the *stem* as the query here.
    certificate_path = find_certificate(
        search_name=name_stem, search_year=year, min_score_threshold=95
    )

    if not certificate_path or certificate_path.stem != name_stem:
        # Extra check to ensure the found stem matches the requested stem exactly
        raise HTTPException(
            status_code=404, detail="Certificate not found or name mismatch"
        )

    return FileResponse(
        path=certificate_path,
        filename=certificate_path.name,
        media_type='application/pdf',
        content_disposition_type="attachment"
    )


@certificates_router.get("/view/{year}/{name_stem}.pdf", name="view_certificate_page")
async def view_certificate_page(year: str, name_stem: str):
    """
    Serve a specific certificate file for viewing, ensuring year match.

    This route re-validates the path by calling find_certificate with the
    provided year and name stem.

    Parameters
    ----------
    year : str
        The year directory containing the certificate.
    name_stem : str
        The stem (filename without extension) of the certificate.

    Returns
    -------
    FileResponse
        The PDF file response for inline viewing.

    Raises
    ------
    HTTPException
        404 Not Found if the certificate file doesn't exist within that year.
    """
    # Re-run find_certificate for validation. Use a high threshold for exact match.
    # Note: We search using the *stem* as the query here.
    certificate_path = find_certificate(
        search_name=name_stem, search_year=year, min_score_threshold=95
    )

    if not certificate_path or certificate_path.stem != name_stem:
        # Extra check to ensure the found stem matches the requested stem exactly
        raise HTTPException(
            status_code=404, detail="Certificate not found or name mismatch"
        )

    return FileResponse(
        path=certificate_path,
        filename=certificate_path.name,
        media_type='application/pdf',
        content_disposition_type="inline"  # Suggest viewing in browser
    )


# --- Webhook Helper Functions ---
async def _run_update_script(script_path: pathlib.Path, webhook_name: str):
    try:
        result = subprocess.run(
            ["stdbuf", "-oL", str(script_path.absolute())],
            # capture_output=True,
            # text=True,
            check=True
        )
        print(f"Update script output ({script_path.name})")  # : {result.stdout}")
        return JSONResponse(
            content={
                "status": "success",
                "message": f"{webhook_name} updated successfully"
            }
        )
    except subprocess.CalledProcessError as e:
        print(f"Error running update script ({script_path.name}): {e.stderr}")
        return JSONResponse(
            content={
                "status": "error",
                "message": f"Script error for {webhook_name}: {e.stderr}"
            },
            status_code=500
        )


async def _verify_github_signature_and_parse(
    request: Request, x_hub_signature_256: Optional[str]
):
    payload_bytes = await request.body()
    if GITHUB_SECRET:
        if not x_hub_signature_256:
            raise HTTPException(
                status_code=401, detail="Missing X-Hub-Signature-256 header")
        signature = hmac.new(
            GITHUB_SECRET.encode(),
            msg=payload_bytes,
            digestmod=hashlib.sha256
        ).hexdigest()
        expected_signature = f"sha256={signature}"
        if not hmac.compare_digest(expected_signature, x_hub_signature_256):
            raise HTTPException(status_code=401, detail="Invalid signature")
    try:
        payload = json.loads(payload_bytes)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    return payload


async def _process_github_event(
    request: Request,
    payload: dict,
    script_path: pathlib.Path,
    webhook_name: str
):
    event_type = request.headers.get("X-GitHub-Event")
    action = payload.get("action")

    if event_type == "ping":
        # Respond to GitHub ping event for webhook setup/test
        return JSONResponse(
            content={
                "status": "ok",
                "message": f"Ping event received for {webhook_name}",
                "zen": payload.get("zen", "")
            }
        )

    if event_type == "pull_request" and action == "closed":
        if payload.get("pull_request", {}).get("merged"):
            base_branch = payload.get("pull_request", {}).get("base", {}).get("ref")
            if base_branch in ["main", "master"]:
                return await _run_update_script(script_path, webhook_name)
    elif event_type == "push":
        ref = payload.get("ref")
        if ref in ["refs/heads/main", "refs/heads/master"]:
            return await _run_update_script(script_path, webhook_name)

    return JSONResponse(
        content={
            "status": "ignored",
            "message":
                f"Event {event_type} (action: {action}) ignored for {webhook_name}"
        }
    )


# --- Webhook Endpoints ---
@webhooks_router.get("/healthcheck")
def webhook_healthcheck():
    return {"message": "Hello from FastAPI Webhook Service!"}


@webhooks_router.post("/lab", response_class=JSONResponse)
async def github_webhook_lab(
    request: Request, x_hub_signature_256: Optional[str] = Header(None)
):
    payload = await _verify_github_signature_and_parse(request, x_hub_signature_256)
    return await _process_github_event(
        request, payload, UPDATE_LAB_SCRIPT_PATH, "Lab Website"
    )


@webhooks_router.post("/workshop", response_class=JSONResponse)
async def github_webhook_workshop(
    request: Request, x_hub_signature_256: Optional[str] = Header(None)
):
    payload = await _verify_github_signature_and_parse(request, x_hub_signature_256)
    return await _process_github_event(
        request, payload, UPDATE_WORKSHOP_SCRIPT_PATH, "Workshop Website"
    )

# Include the routers in the main app
# All routes in certificates_router will be prefixed with /services
# e.g. /services/certificates/home
app.include_router(certificates_router, prefix="/services")
# All routes in webhooks_router will be prefixed with /services
# e.g. /services/webhooks/lab
app.include_router(webhooks_router, prefix="/services")


@app.get("/services", response_class=HTMLResponse)
async def services_status(request: Request):
    """
    Return a static status page listing all available services (API routers).
    """
    return templates.TemplateResponse("services_status.html", {"request": request})


@app.get("/")
def root_redirect():
    return RedirectResponse(url="/services")


# Mount static files for certificates
app.mount(
    "/services/certificates/static",
    StaticFiles(directory=STATIC_DIR),
    name="certificates_static"
)

# --- Main Execution ---
if __name__ == "__main__":
    print(f"Starting server. Certificates expected in: {CERTIFICATES_DIR.resolve()}")
    print(f"Static files served from: {STATIC_DIR.resolve()}")
    print(f"Templates loaded from: {TEMPLATES_DIR.resolve()}")
    if not CERTIFICATES_DIR.exists():
        print(
            f"Warning: Certificate directory '{CERTIFICATES_DIR}' not found. "
            "Please create it and add PDF certificates."
        )
    elif not any(CERTIFICATES_DIR.iterdir()):
        print(f"Warning: Certificate directory '{CERTIFICATES_DIR}' is empty.")

    uvicorn.run(
        "main:app", host="0.0.0.0", port=8000, reload=False
    )
