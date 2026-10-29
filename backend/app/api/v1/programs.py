"""Programs API: CRUD, list/search, archive (HF-FR-001..004)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, or_, select

from ...core.audit import AuditService
from ...core.errors import ApiError, ErrorCode
from ...db.models import Program, User
from ...schemas.programs import ProgramCreate, ProgramOut, ProgramUpdate
from ..deps import get_current_user, get_db, parse_uuid, require_csrf
from ._common import ListParams, Page, paginate
from ...services import programs as programs_service

router = APIRouter(prefix="/programs", tags=["programs"])


def _out(db, program: Program) -> ProgramOut:
    return ProgramOut(
        id=program.id,
        name=program.name,
        platform=program.platform,
        url=program.url,
        description=program.description,
        notes_md=program.notes_md,
        policy_source_url=program.policy_source_url,
        last_policy_review=program.last_policy_review,
        archived_at=program.archived_at,
        current_policy_version=programs_service.latest_policy_version(db, program.id),
        created_at=program.created_at,
        updated_at=program.updated_at,
    )


@router.get("")
def list_programs(
    params: ListParams = Depends(),
    include_archived: bool = False,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
) -> Page[ProgramOut]:
    stmt = select(Program)
    if not include_archived:
        stmt = stmt.where(Program.archived_at.is_(None))
    if params.q:
        like = f"%{params.q}%"
        stmt = stmt.where(or_(Program.name.ilike(like), Program.url.ilike(like)))
    if params.sort == "name":
        order = Program.name.asc()
    else:
        order = Program.created_at.desc()
    rows, total = paginate(db, stmt, params.page, params.page_size, order)
    return Page(items=[_out(db, p) for p in rows], total=total, page=params.page, page_size=params.page_size)


@router.post("")
def create_program(
    body: ProgramCreate,
    request: Request,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> ProgramOut:
    program = Program(
        name=body.name,
        platform=body.platform,
        url=body.url,
        description=body.description,
        notes_md=body.notes_md,
        policy_source_url=body.policy_source_url,
        last_policy_review=body.last_policy_review,
    )
    db.add(program)
    db.flush()
    AuditService.record(
        db, "program.created", "program", program.id, after={"name": program.name},
        actor_id=user.id, ip=request.client.host if request.client else None,
    )
    db.commit()
    return _out(db, program)


@router.get("/{program_id}")
def get_program_detail(
    program_id: str,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProgramOut:
    program = programs_service.get_program(db, parse_uuid(program_id))
    return _out(db, program)


@router.patch("/{program_id}")
def update_program(
    program_id: str,
    body: ProgramUpdate,
    request: Request,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> ProgramOut:
    program = programs_service.get_program(db, parse_uuid(program_id))
    changes = body.model_dump(exclude_unset=True)
    archived = changes.pop("archived", None)
    for key, value in changes.items():
        setattr(program, key, value)
    if archived is True and program.archived_at is None:
        program.archived_at = datetime.now(timezone.utc)
    elif archived is False:
        program.archived_at = None
    AuditService.record(
        db, "program.updated", "program", program.id,
        actor_id=user.id, ip=request.client.host if request.client else None,
    )
    db.commit()
    return _out(db, program)


@router.delete("/{program_id}")
def archive_program(
    program_id: str,
    request: Request,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> dict:
    program = programs_service.get_program(db, parse_uuid(program_id))
    program.archived_at = datetime.now(timezone.utc)
    AuditService.record(db, "program.archived", "program", program.id, actor_id=user.id)
    db.commit()
    return {"status": "ok"}
