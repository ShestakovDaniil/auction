from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app.security import verify_csrf

router = APIRouter()


@router.post("/logout", tags=["web"])
def logout(request: Request, csrf_token: str = Form(...)):
    verify_csrf(request, csrf_token)
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("access_token", path="/", samesite="strict")
    return response
