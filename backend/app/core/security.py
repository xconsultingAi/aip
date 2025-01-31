import requests
from jose import jwt, JWTError
from fastapi import HTTPException, status
from app.core.config import settings
from fastapi import Depends, HTTPException, status
from datetime import datetime, timedelta
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

http_bearer = HTTPBearer()

#MJ: Clerk Secured Public Key URL
CLERK_JWKS_URL = settings.CLERK_JWKS_URL

#MJ: Fetch Clerk JWKS Key and Algorithm
def get_clerk_jwks() -> dict:
    
    #TODO: Add proper error handling
    headers = {
        "Authorization": f"Bearer {settings.CLERK_SECRET_KEY}"
    }
    response = requests.get(CLERK_JWKS_URL, headers=headers)
    if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to fetch Clerk JWKS",
            )
    return response.json() 


#MJ: Verify Clerk Token
def verify_clerk_token(credentials: HTTPAuthorizationCredentials) -> dict:

    #MJ: For Testing Only
    if settings.PRODUCTION == False:
        return create_test_payload()

    #TODO: Add proper error handling

    #Token from Credentials passed from caller (e.g. Get_current_user())
    token = credentials.credentials

    #Get Clerk JWKS Data
    jwks_data = get_clerk_jwks()    
    
    #Extract the algorithm and the key
    algorithm = jwks_data["keys"][0]["alg"]
    rsa_key = jwks_data["keys"][0]
    
    options = {
        algorithm: algorithm
    }

    #MJ: Decoding the token with the rsa key
    try:
        payload = jwt.decode(
            token,
            key=rsa_key,  
            options=options
            
        )
        return payload  # If successful, return the decoded payload

    #MJ: Default Error - Need to optimize this    
    except JWTError:   
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

def create_test_payload():
    payload = {
        "sub": "user_id_123",
        "email": "test@example.com",
        "iat": datetime.now(),
        "exp": datetime.now() + timedelta(hours=1),
        "iss": "clerk"
    }
    return payload