from fastapi import APIRouter, Depends

from kigaprio.utils import validate_token

router = APIRouter()


@router.get(
    "/protected-data",
    status_code=200,
    summary="Test protection via token",
    description="A test function to check that token protection is working",
)
async def protected_data(token: str = Depends(validate_token)):
    _ = token  # dummy to prevent unused variable warning
    # Here your protected logic

    return {"message": "This data is protected and you are authenticated."}
