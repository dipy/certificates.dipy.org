# Authentication Setup for DIPY Sponsor System

This document explains how to set up authentication for the sponsor system.

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```bash
# Database Configuration
DATABASE_URL=sqlite+aiosqlite:///./sponsors.db

# Security
SECRET_KEY=your-secret-key-change-in-production

# GitHub OAuth (for GitHub login)
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret

# Google OAuth (for Google login)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Linkedin Oauth (For linkedin login)
LINKEDIN_CLIENT_ID=your-linkedin-client-id
LINKEDIN_CLIENT_SECRET=your-linkedin-client-secret

# Base URL for the application
BASE_URL=http://localhost:8000

# GitHub Webhook Secret (existing)
GITHUB_WEBHOOK_SECRET=your-github-webhook-secret

# FlexPay Configuration (for payment processing)
FLEXPAY_URL=https://api.flexpay.com
FLEXPAY_CLIENT_ID=your-flexpay-client-id
FLEXPAY_CLIENT_SECRET=your-flexpay-client-secret

# GitHub Sponsors API (for marking users as sponsors)
GITHUB_SPONSORS_TOKEN=your-github-sponsors-token
```

## Setting up OAuth Applications

### GitHub OAuth

1. Go to GitHub Settings > Developer settings > OAuth Apps
2. Create a new OAuth App
3. Set the Authorization callback URL to: `http://localhost:8000/services/auth/github/callback`
4. Copy the Client ID and Client Secret to your `.env` file

### Google OAuth

1. Go to Google Cloud Console
2. Create a new project or select existing one
3. Enable the Google+ API
4. Go to Credentials > Create Credentials > OAuth 2.0 Client IDs
5. Set the Authorized redirect URIs to: `http://localhost:8000/services/auth/google/callback`
6. Copy the Client ID and Client Secret to your `.env` file

### Linkedin OAuth

1. Go to LinkedIn Developers: https://developer.linkedin.com/
2. Click Create App and fill in the required details (App name, company, etc.)
3. In your app settings, go to Auth tab.
4. Set the OAuth 2.0 Redirect URLs to: http://localhost:8000/services/auth/linkedin/callback
5. Under Products, add the following permissions:
    - r_liteprofile
    - r_emailaddress
6. Copy the Client ID and Client Secret from the LinkedIn app dashboard to your `.env` file


## Setting up GITHUB SPONSORS TOKEN

1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Give it a name like "DIPY Sponsor Management"
4. Select scopes:
   - read:user (to read user profile information)
   - user:email (to read user email addresses)
5. Click "Generate token"
6. Copy the token (you won't see it again!)

## Installation

1. Install the new dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python main.py
```

## Features Implemented

### Authentication
- ✅ GitHub OAuth login
- ✅ Google OAuth login
- ✅ Linkedin OAuth login
- ✅ JWT token management
- ✅ User session management

### Database
- ✅ SQLite database with SQLAlchemy
- ✅ User model with multiple auth methods
- ✅ Sponsorship model for tracking payments
- ✅ Automatic database initialization

### Frontend
- ✅ Updated sponsors page with pricing
- ✅ Login modal with multiple options
- ✅ User dashboard showing sponsorships
- ✅ Token-based authentication flow

## Next Steps

1. **FlexPay Integration**: Implement payment processing with FlexPay API
2. **GitHub Sponsors Integration**: Mark users as sponsors on GitHub after payment
3. **Invoice Generation**: Create and store invoice URLs
4. **Email Notifications**: Send confirmation emails after successful payments

## API Endpoints

### Authentication
- `GET /services/auth/github/login` - Start GitHub OAuth flow
- `GET /services/auth/github/callback` - GitHub OAuth callback
- `GET /services/auth/google/login` - Start Google OAuth flow
- `GET /services/auth/google/callback` - Google OAuth callback
- `POST /services/auth/email/register` - Email registration
- `POST /services/auth/email/login` - Email login
- `GET /services/auth/me` - Get current user info
- `GET /services/auth/logout` - Logout

### Sponsors
- `GET /services/sponsors/` - Sponsors page
- `GET /services/sponsors/my-sponsorships` - Get user's sponsorships

## Testing

1. Start the server: `python main.py`
2. Visit: `http://localhost:8000/services/sponsors`
3. Try the different login methods
4. Check that user data is stored in the database