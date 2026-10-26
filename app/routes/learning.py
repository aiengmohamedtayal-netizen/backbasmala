import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import db
from ..deps import current_user

router = APIRouter(prefix="/learning", tags=["learning"])


class ProgressIn(BaseModel):
    skill_id: int
    status: Literal["todo", "in_progress", "done"]


@router.patch("/progress")
def set_progress(body: ProgressIn, user: dict = Depends(current_user)):
    row = db.latest_analysis(user["id"])
    if row is None:
        raise HTTPException(status_code=404, detail="No analysis yet.")
    roadmap_ids = {item["skill_id"] for item in json.loads(row["result_json"])["roadmap"]}
    if body.skill_id not in roadmap_ids:
        raise HTTPException(status_code=404, detail="That skill is not in your roadmap.")
    db.set_progress(user["id"], body.skill_id, body.status)
    return {"ok": True}
