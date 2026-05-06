"""API категорий."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.deps import CurrentUser, DbSession
from app.models.category import CategoryKind
from app.schemas.finance import CategoryCreate, CategoryPublic, CategoryUpdate
from app.services.categories import CategoryService

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryPublic])
async def list_categories(
    user: CurrentUser, db: DbSession, kind: CategoryKind | None = None
) -> list[CategoryPublic]:
    svc = CategoryService(db)
    cats = await svc.list(user.id, kind=kind)
    return [CategoryPublic.model_validate(c) for c in cats]


@router.post("", response_model=CategoryPublic, status_code=status.HTTP_201_CREATED)
async def create_category(
    user: CurrentUser, db: DbSession, data: CategoryCreate
) -> CategoryPublic:
    svc = CategoryService(db)
    cat = await svc.create(user.id, data)
    await db.commit()
    return CategoryPublic.model_validate(cat)


@router.patch("/{cat_id}", response_model=CategoryPublic)
async def update_category(
    user: CurrentUser, db: DbSession, cat_id: int, data: CategoryUpdate
) -> CategoryPublic:
    svc = CategoryService(db)
    cat = await svc.update(user.id, cat_id, data)
    if not cat:
        raise HTTPException(status_code=404, detail="категория не найдена")
    await db.commit()
    return CategoryPublic.model_validate(cat)


@router.delete("/{cat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(user: CurrentUser, db: DbSession, cat_id: int) -> None:
    svc = CategoryService(db)
    if not await svc.delete(user.id, cat_id):
        raise HTTPException(status_code=404, detail="категория не найдена")
    await db.commit()
