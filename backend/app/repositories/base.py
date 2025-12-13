"""
Base Repository

Generic async repository with common CRUD operations.
"""

from typing import Generic, TypeVar, Type, Optional, List, Any, Dict
from uuid import UUID

from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import Base


ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository with common CRUD operations"""
    
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        """
        Initialize repository
        
        Args:
            model: SQLAlchemy model class
            db: Database session
        """
        self.model = model
        self.db = db
    
    async def get_by_id(
        self, 
        id: UUID, 
        relationships: Optional[List[str]] = None
    ) -> Optional[ModelType]:
        """
        Get a record by ID
        
        Args:
            id: Record ID
            relationships: List of relationship names to eager load
            
        Returns:
            Model instance or None
        """
        query = select(self.model).where(self.model.id == id)
        
        if relationships:
            for rel in relationships:
                query = query.options(selectinload(getattr(self.model, rel)))
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        relationships: Optional[List[str]] = None,
        order_by: Optional[str] = None
    ) -> List[ModelType]:
        """
        Get all records with pagination and filtering
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Dictionary of field:value filters
            relationships: List of relationship names to eager load
            order_by: Field name to order by
            
        Returns:
            List of model instances
        """
        query = select(self.model)
        
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.where(getattr(self.model, field) == value)
        
        if relationships:
            for rel in relationships:
                query = query.options(selectinload(getattr(self.model, rel)))
        
        if order_by and hasattr(self.model, order_by):
            query = query.order_by(getattr(self.model, order_by))
        
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count records with optional filtering
        
        Args:
            filters: Dictionary of field:value filters
            
        Returns:
            Total count
        """
        query = select(func.count(self.model.id))
        
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.where(getattr(self.model, field) == value)
        
        result = await self.db.execute(query)
        return result.scalar_one()
    
    async def create(self, obj_in: Dict[str, Any]) -> ModelType:
        """
        Create a new record
        
        Args:
            obj_in: Dictionary of field values
            
        Returns:
            Created model instance
        """
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj
    
    async def update(
        self, 
        id: UUID, 
        obj_in: Dict[str, Any]
    ) -> Optional[ModelType]:
        """
        Update a record
        
        Args:
            id: Record ID
            obj_in: Dictionary of field values to update
            
        Returns:
            Updated model instance or None
        """
        # Remove None values
        update_data = {k: v for k, v in obj_in.items() if v is not None}
        
        if not update_data:
            return await self.get_by_id(id)
        
        query = (
            update(self.model)
            .where(self.model.id == id)
            .values(**update_data)
            .returning(self.model)
        )
        
        result = await self.db.execute(query)
        await self.db.commit()
        
        updated_obj = result.scalar_one_or_none()
        if updated_obj:
            await self.db.refresh(updated_obj)
        
        return updated_obj
    
    async def delete(self, id: UUID) -> bool:
        """
        Delete a record
        
        Args:
            id: Record ID
            
        Returns:
            True if deleted, False if not found
        """
        query = delete(self.model).where(self.model.id == id)
        result = await self.db.execute(query)
        await self.db.commit()
        
        return result.rowcount > 0
    
    async def exists(self, id: UUID) -> bool:
        """
        Check if a record exists
        
        Args:
            id: Record ID
            
        Returns:
            True if exists, False otherwise
        """
        query = select(func.count(self.model.id)).where(self.model.id == id)
        result = await self.db.execute(query)
        count = result.scalar_one()
        return count > 0
    
    async def get_by_field(
        self, 
        field: str, 
        value: Any
    ) -> Optional[ModelType]:
        """
        Get a record by a specific field value
        
        Args:
            field: Field name
            value: Field value
            
        Returns:
            Model instance or None
        """
        if not hasattr(self.model, field):
            return None
        
        query = select(self.model).where(getattr(self.model, field) == value)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def bulk_create(self, objects: List[Dict[str, Any]]) -> List[ModelType]:
        """
        Create multiple records in bulk
        
        Args:
            objects: List of dictionaries with field values
            
        Returns:
            List of created model instances
        """
        db_objects = [self.model(**obj) for obj in objects]
        self.db.add_all(db_objects)
        await self.db.commit()
        
        for obj in db_objects:
            await self.db.refresh(obj)
        
        return db_objects
