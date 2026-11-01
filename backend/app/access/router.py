from fastapi import APIRouter, Depends
from app.api.dependencies import identity
router=APIRouter()
@router.get("/me")
def me(user=Depends(identity)):
    return {"data":{"user":{"id":user.id,"display_name":user.display_name}},"meta":{}}
