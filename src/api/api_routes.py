from typing import Any, List
from ninja import NinjaAPI

api = NinjaAPI()

@api.get("/categories", response=Any)
def categories(request: Any) -> List[Any]:
    return "Hello from categories"

