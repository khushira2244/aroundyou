from fastapi import APIRouter, Depends
from app.api.dependencies import identity,session
router=APIRouter()
@router.get("/me")
def me(user=Depends(identity),db=Depends(session)):
    from app.access.accounts import identity_for
    return {"data":{"user":{"id":user.id,"display_name":user.display_name},"identity":identity_for(db,user)},"meta":{}}
