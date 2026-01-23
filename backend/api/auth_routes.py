"""
Authentication Routes for Frontend Integration
Create this file: backend/api/auth_routes.py
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
import uuid

from database import get_db, User

router = APIRouter()


# ===== Request/Response Models =====

class SignupRequest(BaseModel):
    fullName: str
    email: EmailStr
    phone: str
    password: str
    confirmPassword: str

class LoginRequest(BaseModel):
    email: str
    password: str

class AuthResponse(BaseModel):
    user_id: str
    email: str
    message: str
    
    class Config:
        from_attributes = True


# ===== Routes =====

@router.post("/auth/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED, tags=["Authentication"])
def signup(request: SignupRequest, db: Session = Depends(get_db)):
    """
    Create new user account - matches frontend SignupPage
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    
    # TODO: In production, hash password with bcrypt
    # Example: from passlib.hash import bcrypt
    # hashed = bcrypt.hash(request.password)
    new_user = User(
        user_id=user_id,
        email=request.email,
        hashed_password=request.password  # Store hashed in production!
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    print(f"✅ New user created: {request.email}")
    
    return {
        "user_id": new_user.user_id,
        "email": new_user.email,
        "message": "Account created successfully"
    }


@router.post("/auth/login", response_model=AuthResponse, tags=["Authentication"])
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Login user - matches frontend LoginPage
    """
    # Find user
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # TODO: In production, verify hashed password with bcrypt
    # Example: bcrypt.verify(request.password, user.hashed_password)
    if user.hashed_password != request.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    print(f"✅ User logged in: {request.email}")
    
    return {
        "user_id": user.user_id,
        "email": user.email,
        "message": "Login successful"
    }