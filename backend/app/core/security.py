import requests
from jose import jwt, jwk, JWTError
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)


#MJ: Clerk Secured Public Key URL
http_bearer = HTTPBearer()

#SH: Clerk configuration
CLERK_JWKS_URL = settings.CLERK_JWKS_URL
CLERK_ISSUER = "https://maximum-cardinal-66.clerk.accounts.dev"
#MJ: Fetch Clerk JWKS Key and Algorithm
def get_clerk_jwks() -> dict:
    #TODO: Add proper error handling
    """Fetch Clerk's JWKS without authentication"""
    try:
        response = requests.get(CLERK_JWKS_URL, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Clerk JWKS fetch failed: {str(e)}"
        )

def get_public_key(token: str, jwks_data: dict):
    """Select correct key using kid from token header"""
    try:
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        
        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing key ID in token header"
            )
            
        for key in jwks_data.get("keys", []):
            if key.get("kid") == kid:
                return jwk.construct(key)
                
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No matching key found in JWKS"
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token header: {str(e)}"
        )
#MJ: Verify Clerk Token
def verify_clerk_token(credentials: HTTPAuthorizationCredentials) -> dict:
    #MJ: For Testing Only
    """Full JWT verification with proper error handling"""
    token = credentials.credentials
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token"
        )
    
    try:
        # Get JWKS data
        jwks_data = get_clerk_jwks()
        
        # Get correct public key
        public_key = get_public_key(token, jwks_data)
        
        # Decode and validate token
        payload = jwt.decode(
            token,
            key=public_key,
            algorithms=["RS256"],
            issuer=CLERK_ISSUER,
            options={
                "verify_signature": True,
                "verify_aud": False,
                "verify_iss": True,
                "verify_exp": True,
                "leeway": 30
            }
        )
        
        # Log the token payload for debugging
        logging.info(f"Token Payload: {payload}")
        
        # Check for required claims
        if "sub" not in payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing 'sub' claim"
            )
        
        # Extract user information safely
        user_id = payload.get("user_id")
        username = payload.get("username")
        email = payload.get("email")
        
        return {
            "sub": payload.get("sub"),
            "user_id": user_id,
            "username": username,
            "email": email
        }
#MJ: Default Error - Need to optimize this            
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except jwt.JWTClaimsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid claims: {str(e)}"
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication error: {str(e)}"
        )