"""Miner control and telemetry API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_current_user_id
from app.engine.miner_worker import miner_service
from app.schemas.miner import MinerControlRequest, MinerStatusResponse

router = APIRouter(prefix="/api/miner", tags=["Miner Engine"])


@router.get("/status", response_model=MinerStatusResponse)
async def get_miner_status(user_id: str = Depends(get_current_user_id)):
    """Fetch current real-time mining state, drop progress, and active channel."""
    return miner_service.get_status()


@router.post("/control")
async def control_miner(
    body: MinerControlRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Control miner lifecycle actions: start, stop, pause, resume, force_check."""
    action = body.action.lower()

    if action == "start":
        await miner_service.start()
        await miner_service.check_and_mine()
    elif action == "stop":
        await miner_service.stop()
    elif action == "pause":
        await miner_service.pause()
    elif action == "resume":
        await miner_service.resume()
    elif action == "force_check":
        await miner_service.check_and_mine()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown action '{body.action}'. Supported: start, stop, pause, resume, force_check",
        )

    return {
        "action": action,
        "status": miner_service.get_status(),
        "message": f"Miner action '{action}' executed successfully.",
    }
