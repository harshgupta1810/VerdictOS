import pytest
from fastapi import Request, HTTPException
from unittest.mock import AsyncMock, MagicMock
from src.api.middleware.validation import validate_deal_state

@pytest.mark.asyncio
async def test_validate_deal_state_missing_id() -> None:
    request = MagicMock(spec=Request)
    request.path_params = {}
    db = AsyncMock()
    with pytest.raises(HTTPException) as exc:
        await validate_deal_state(request, db)
    assert exc.value.status_code == 400

@pytest.mark.asyncio
async def test_validate_deal_state_not_found() -> None:
    request = MagicMock(spec=Request)
    request.path_params = {"id": "123"}
    db = AsyncMock()
    db.get.return_value = None
    with pytest.raises(HTTPException) as exc:
        await validate_deal_state(request, db)
    assert exc.value.status_code == 404

@pytest.mark.asyncio
async def test_validate_deal_state_success() -> None:
    request = MagicMock(spec=Request)
    request.path_params = {"id": "123"}
    request.url.path = "/api/v1/deals/123"
    db = AsyncMock()
    deal = MagicMock()
    db.get.return_value = deal
    result = await validate_deal_state(request, db)
    assert result == deal

@pytest.mark.asyncio
async def test_validate_deal_state_escalation_path() -> None:
    request = MagicMock(spec=Request)
    request.path_params = {"id": "123"}
    request.url.path = "/api/v1/deals/123/escalations/resolve"
    db = AsyncMock()
    deal = MagicMock()
    deal.status = "complete"
    db.get.return_value = deal
    result = await validate_deal_state(request, db)
    assert result == deal

@pytest.mark.asyncio
async def test_validate_deal_state_escalation_path_invalid() -> None:
    request = MagicMock(spec=Request)
    request.path_params = {"id": "123"}
    request.url.path = "/api/v1/deals/123/escalations/resolve"
    db = AsyncMock()
    deal = MagicMock()
    deal.status = "ingesting"
    db.get.return_value = deal
    result = await validate_deal_state(request, db)
    assert result == deal
