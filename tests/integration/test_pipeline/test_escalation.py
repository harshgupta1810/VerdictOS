"""Integration tests for Escalation SLA monitoring."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

from src.db.models import Deal, Escalation
from src.workers.tasks import enforce_escalation_sla

@pytest.mark.asyncio
async def test_escalation_sla_drops_timed_out_deals():
    with patch("src.workers.tasks.AsyncSessionLocal") as mock_db_session, \
         patch("src.workers.tasks.emit_pipeline_event") as mock_emit:
         
        mock_session = AsyncMock()
        mock_db_session.return_value.__aenter__.return_value = mock_session
        
        # Setup an expired escalation
        esc = Escalation(
            escalation_id="esc_1",
            deal_id="deal_expired",
            finding_id="finding_1",
            status="pending",
            created_at=datetime.utcnow() - timedelta(hours=25)
        )
        
        # Setup a deal associated with the expired escalation
        deal_expired = Deal(
            deal_id="deal_expired",
            client_id="client1",
            status="debating"
        )
        
        from unittest.mock import MagicMock
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [esc]
        mock_session.execute.return_value = mock_result
        
        mock_session.get.return_value = deal_expired
        
        # Run the SLA job
        dropped_deals = await enforce_escalation_sla(timeout_hours=24)
        
        # Verify the deal is dropped
        assert "deal_expired" in dropped_deals
        assert deal_expired.status == "error"
        assert esc.status == "timed_out"
        mock_emit.assert_called_once_with("deal_expired", "error", {"message": "Escalation SLA timeout."})
        mock_session.commit.assert_called_once()
