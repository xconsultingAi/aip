import logging
import requests
from jose import jwt, jwk, JWTError
from fastapi import HTTPException, status
from fastapi.security import  HTTPBearer,HTTPAuthorizationCredentials
from fastapi import WebSocketException
from app.core.config import settings

#MJ: Clerk Secured Public Key URL
http_bearer = HTTPBearer()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#SH: Clerk configuration
CLERK_JWKS_URL = settings.CLERK_JW
CLERK_ISSUER = settings.CLERK_ISSUE
#MJ: Fetch Clerk JWKS Key and Algorithm
issuer = settings.CLERK_ISSUER

def get_clerk_jwks() -> dict:
    #TODO: Add proper error handling
    """Fetch Clerk's JWKS without authentication"""
    logger.info("try to fetching Clerk JWKS")

    try:
        logger.info(f"Clerk JWKS URL: {CLERK_JWKS_URL}")
        response = requests.get(CLERK_JWKS_URL, timeout=10)
        logger.info(f"HTTP response status: {response.status_code}")

        response.raise_for_status()

        jwks = response.json()
        logger.info("JWKS successfully fetched")
        return jwks

    except requests.RequestException as e:
        logger.error(f"Clerk JWKS fetch failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Clerk JWKS fetch failed: {str(e)}"
        )

def get_public_key(token: str, jwks_data: dict):
    
    #Sh: Select correct key using 'kid' from token header.
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

def get_public_key_ws(token: str):
    
    #SH: Select correct key using 'kid' from token header for WebSocket.
    jwks_data = get_clerk_jwks()
    return get_public_key(token, jwks_data)

#MJ: Verify Clerk Token
def verify_clerk_token(credentials: HTTPAuthorizationCredentials) -> dict:
        #MJ: For Testing Only
    """Full JWT verification with proper error handling"""
    
    #SH: Full JWT verification with proper error handling.
    token = credentials.credentials
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token"
        )
    
    try:
        #Sh: Get JWKS data
        jwks_data = get_clerk_jwks()
        
        #Sh: Get correct public key

        public_key = get_public_key(token, jwks_data)

        #Sh: Decode and validate token
        payload = jwt.decode(
            token,
            key=public_key,
            algorithms=["RS256"],
            issuer=issuer,
            options={
                "verify_signature": True,
                "verify_aud": False,
                "verify_iss": True,
                "verify_exp": True,
                "leeway": 30
            }
        )
        
        #Sh: Log the token payload for debugging
        logging.info(f"Token Payload: {payload}")
        
        #Sh: Check for required claims
        if "sub" not in payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing 'sub' claim"
            )
        
        return payload

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
        
#SH: websocket Token verification
def verify_websocket_token(token: str) -> dict:
    try:
        logger.debug(f"Token received: {token[:15]}...")  # Log first 15 characters of the token

        # Verify token structure
        if not token.startswith("eyJ") or token.count(".") != 2:
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Invalid token format"
            )

        # Fetch the JWKS data to get the public keys
        jwks_data = get_clerk_jwks()
        logger.debug(f"JWKS keys: {[k['kid'] for k in jwks_data.get('keys', [])][:2]}")  # Log first two JWKS keys

        # Decode the header from the token
        unverified_header = jwt.get_unverified_header(token)
        logger.debug(f"Token header: {unverified_header}")

        #Sh: Public key extraction logic
        public_key = get_public_key(token, jwks_data)
        logger.debug("Public key retrieved successfully")

        #SH: Decode and verify the JWT token with audience
        payload = jwt.decode(
            token,
            key=public_key,
            algorithms=["RS256"],
            issuer=settings.CLERK_ISSUER,
            audience=settings.CLERK_PUBLISHABLE_KEY,
            options={"verify_iss": True, "verify_aud": True, "verify_exp": True}
        )
        logger.debug(f"Token payload decoded: {payload}")

        # Check essential claims
        required_claims = {"sub", "exp", "iat", "nbf"}
        if not required_claims.issubset(payload.keys()):
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Missing required token claims"
            )

        return payload

    except jwt.ExpiredSignatureError:
        logger.error("WebSocket token has expired")
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Token expired"
        )
    except jwt.JWTClaimsError as e:
        logger.error(f"WebSocket token claims are invalid: {str(e)}")
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason=f"Invalid token claims: {str(e)}"
        )
    except JWTError as e:
        logger.error(f"Invalid WebSocket token: {str(e)}")
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason=f"Invalid token: {str(e)}"
        )
    except Exception as e:
        logger.error(f"WebSocket token verification failed: {str(e)}")
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid token"
        )

