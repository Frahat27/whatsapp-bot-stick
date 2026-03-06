"""
Repositorio base CRUD genérico para SQLAlchemy async.
"""

from typing import Any, Optional, Sequence, Type, TypeVar

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository:
    """Repositorio genérico con operaciones CRUD básicas."""

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get_by_id(self, id: int) -> Optional[ModelType]:
        """Buscar por ID primario."""
        return await self.session.get(self.model, id)

    async def get_one(self, **filters) -> Optional[ModelType]:
        """Buscar un registro por filtros."""
        stmt = select(self.model).filter_by(**filters)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_many(
        self,
        limit: int = 100,
        offset: int = 0,
        order_by: Optional[Any] = None,
        **filters,
    ) -> Sequence[ModelType]:
        """Buscar múltiples registros con filtros, paginación y orden."""
        stmt = select(self.model).filter_by(**filters).offset(offset).limit(limit)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(self, **data) -> ModelType:
        """Crear un nuevo registro."""
        instance = self.model(**data)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def update_by_id(self, id: int, **data) -> Optional[ModelType]:
        """Actualizar un registro por ID."""
        instance = await self.get_by_id(id)
        if instance is None:
            return None
        for key, value in data.items():
            setattr(instance, key, value)
        await self.session.flush()
        return instance

    async def delete_by_id(self, id: int) -> bool:
        """Eliminar un registro por ID."""
        instance = await self.get_by_id(id)
        if instance is None:
            return False
        await self.session.delete(instance)
        await self.session.flush()
        return True
