import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from careerly_core import CVError, UnknownRole, analyze_file
from careerly_core.matcher import roles
from careerly_core.parser import MAX_BYTES

from .. import db, views
from ..deps import current_user

router = APIRouter(tags=["cv"])


@router.get("/roles")
def list_roles():
    """Target roles the user can pick on the upload page (public)."""
    return {"roles": list(roles())}


# Plain `def` (not async): parsing a PDF is CPU work, FastAPI runs it in a worker thread.
@router.post("/cv/upload")
def upload_cv(
    file: UploadFile = File(...),
    target_role: str = Form(""),   # empty -> we pick the closest role from the CV
    user: dict = Depends(current_user),
):
    role = target_role.strip()
    data = file.file.read(MAX_BYTES + 1)  # +1 so an oversize file is detected, not silently cut
    try:
        result = analyze_file(data, file.filename or "", target_role=role or None)
    except (CVError, UnknownRole) as e:
        raise HTTPException(status_code=422, detail=str(e))

    payload = views.to_api(result)
    # the DB column is still called job_description; it now stores the target role name
    db.save_analysis(user["id"], result["targetRole"] or "", json.dumps(payload))
    return views.with_progress(payload, db.get_progress(user["id"]))


@router.get("/analysis/latest")
def latest_analysis(user: dict = Depends(current_user)):
    row = db.latest_analysis(user["id"])
    if row is None:
        raise HTTPException(status_code=404, detail="No analysis yet.")
    return views.with_progress(json.loads(row["result_json"]), db.get_progress(user["id"]))
