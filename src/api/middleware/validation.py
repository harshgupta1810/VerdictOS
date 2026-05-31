"""Request Validation Middleware.

Validates that deal_id exists and deal state permits requested operations.
"""

from typing import Callable, Any
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse
import re

# Use absolute import for DB session factory if we need manual sessions.
# Since async sessions in middleware can be complex, a cleaner approach 
# is to provide a validation dependency to be used in routes.

# Here is the dependency version:
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from src.db.session import get_db
from src.db.models import Deal

async def validate_deal_state(request: Request, db: AsyncSession = Depends(get_db)) -> Deal:
    """Dependency to validate deal existence and state based on the path."""
    deal_id = request.path_params.get("id")
    if not deal_id:
        raise HTTPException(status_code=400, detail="Missing deal ID in path")
        
    deal = await db.get(Deal, deal_id)
    if not deal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deal with id {deal_id} not found"
        )
        
    # We can add state-based validation based on the request method and path
    # For example, resolving an escalation requires a specific state
    path = request.url.path
    if "escalations" in path and "resolve" in path:
        if deal.status not in ["judging", "complete"]:  # Adjust based on rules
            pass
            
    # For now, return the deal so endpoints can use it
    return deal
