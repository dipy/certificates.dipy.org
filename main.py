import pathlib
import uvicorn
import re  # Import regex module
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional
import urllib.parse
from rapidfuzz import fuzz

# --- Configuration ---
CERTIFICATES_DIR = pathlib.Path("certificates")
STATIC_DIR = pathlib.Path("static")
TEMPLATES_DIR = pathlib.Path("templates")
SUPPORTED_YEARS = list(range(2023, 2026))  # Years 2023, 2024, 2025
LINKEDIN_CERT_URL = (
    "https://www.linkedin.com/profile/add?startTask=CERTIFICATION_NAME"
)
ORGANIZATION_ID = "18898741"  # DIPY LinkedIn Organization ID
# ISSUE_YEAR = "2023"  # Default Issue Year - No longer needed
ISSUE_MONTH = "5"      # Default Issue Month - Still used for LinkedIn link

# Create directories if they don't exist (optional, good practice)
CERTIFICATES_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)

# --- FastAPI App Setup ---
app = FastAPI(title="DIPY Certificate Server", root_path="/certificates")

# Mount static files directory
app.mount("/certificates/static", StaticFiles(directory=STATIC_DIR), name="static")


def root_url_for(request: Request, name: str, **params):
    # return request.scope["root_path"] + str(request.url_for(name, **params))
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


# --- Routes ---

@app.get("/certificates/")
def read_cert():
    return {"message": "Hello from FastAPI!"}


@app.get("/", response_class=HTMLResponse)
async def get_homepage(request: Request):
    """
    Serve the homepage.

    Renders the main index.html template which includes the
    welcome message, logo, and search bar.

    Parameters
    ----------
    request : Request
        The incoming request object.

    Returns
    -------
    HTMLResponse
        The rendered HTML page.
    """
    context = {
        "request": request,
        "title": "DIPY Certificates",
        "supported_years": SUPPORTED_YEARS
    }
    return templates.TemplateResponse("index.html", context)


@app.post("/search", name="search", response_class=HTMLResponse)
async def search_certificates(
    request: Request,
    search_query: str = Form(..., max_length=100),  # Added max_length
    search_year: str = Form(..., max_length=4)      # Added max_length
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
            # Use the name stem and the validated search_year for the URL
            cert_page_url = request.url_for(
                'view_certificate', year=search_year, name_stem=certificate_name
            )
        except Exception as e:
            print(f"Error generating URL for view_certificate: {e}")
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
            "year": search_year      # Pass year for download/view links
        },
    )


@app.get("/download/{year}/{name_stem}.pdf", name="download_certificate")
async def download_certificate(year: str, name_stem: str):
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
        content_disposition_type="attachment"  # Suggest download
    )


@app.get("/view/{year}/{name_stem}.pdf", name="view_certificate")
async def view_certificate(year: str, name_stem: str):
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


# --- Main Execution ---
if __name__ == "__main__":
    # IMPORTANT: Disable reload=True in production environments!
    print(f"Starting server. Certificates expected in: {CERTIFICATES_DIR.resolve()}")
    print(f"Static files served from: {STATIC_DIR.resolve()}")
    print(f"Templates loaded from: {TEMPLATES_DIR.resolve()}")
    # Make sure certificate dir exists
    if not CERTIFICATES_DIR.exists():
        print(
            f"Warning: Certificate directory '{CERTIFICATES_DIR}' not found. "
            "Please create it and add PDF certificates."
        )
    elif not any(CERTIFICATES_DIR.iterdir()):
        print(f"Warning: Certificate directory '{CERTIFICATES_DIR}' is empty.")

    uvicorn.run(
        "main:app", host="0.0.0.0", port=8000, reload=False
    )  # Set reload=False for production
