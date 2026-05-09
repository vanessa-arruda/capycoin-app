from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from core.auth import hash_password, verify_password, create_access_token, get_current_parent
from models import Parent, Child, Household
from schemas.auth import LoginRequest, TokenResponse
from schemas.parent import ParentCreate, ParentRead
from schemas.child import ChildCreate, ChildRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register/parent", response_model=ParentRead, status_code=201)
def register_parent(payload: ParentCreate, db: Session = Depends(get_db)):
    if db.query(Parent).filter(Parent.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    household = Household(name=f"{payload.name}'s household")
    db.add(household)
    db.flush()
    parent = Parent(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        household_id=household.id,
    )
    db.add(parent)
    db.commit()
    db.refresh(parent)
    return parent


@router.post("/register/child", response_model=ChildRead, status_code=201)
def register_child(
    payload: ChildCreate,
    db: Session = Depends(get_db),
    current_parent: Parent = Depends(get_current_parent),
):
    if db.query(Child).filter(Child.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    child = Child(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        parent_id=current_parent.id,
        household_id=current_parent.household_id,
    )
    db.add(child)
    db.commit()
    db.refresh(child)
    return child


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    parent = db.query(Parent).filter(Parent.email == payload.email).first()
    if parent and verify_password(payload.password, parent.password_hash):
        token = create_access_token({"sub": str(parent.id), "role": "parent"})
        return TokenResponse(access_token=token, role="parent")

    child = db.query(Child).filter(Child.email == payload.email).first()
    if child and verify_password(payload.password, child.password_hash):
        token = create_access_token({"sub": str(child.id), "role": "child"})
        return TokenResponse(access_token=token, role="child")

    raise HTTPException(status_code=401, detail="Invalid credentials")
