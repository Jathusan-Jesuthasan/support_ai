from datetime import datetime, timezone
from typing import Annotated, Any, Dict, Optional, Type, TypeVar
from uuid import UUID
# pyrefly: ignore [missing-import]
from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, GetCoreSchemaHandler
from pydantic_core import core_schema

# Generic TypeVar representing subclasses of MongoDocument
T = TypeVar("T", bound="MongoDocument")


# =====================================================================
# MongoDB ObjectId custom validation type for Pydantic V2
# =====================================================================


class _ObjectIdAnnotation:
    """
    Pydantic V2 custom type validator allowing seamless serialization and
    validation of MongoDB BSON ObjectId keys.
    """

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        def validate(value: Any) -> ObjectId:
            if isinstance(value, ObjectId):
                return value
            if isinstance(value, str):
                try:
                    return ObjectId(value)
                except Exception:
                    raise ValueError(f"Invalid hexadecimal ObjectId: {value}")
            raise ValueError(f"Expected ObjectId or string, got {type(value)}")

        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.with_info_plain_validator_function(
                lambda v, info: validate(v)
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(str),

        )


# Exposed custom annotation type for MongoDB ObjectId fields
PyObjectId = Annotated[ObjectId, _ObjectIdAnnotation]


# =====================================================================
# Database Reusable Model Definitions
# =====================================================================


class EmbeddedModel(BaseModel):
    """
    Base model for nested/embedded documents in MongoDB.
    Excludes ObjectIds, UUID keys, and top-level audit fields.
    """

    model_config = ConfigDict(
        validate_assignment=True,
        use_enum_values=True,
        extra="forbid",
    )


class AuditFields(BaseModel):
    """
    Metadata mixin tracking entity creation and updates.
    """

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the document was initially created",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the document was last updated",
    )
    created_by: Optional[UUID] = Field(
        None, description="The user_id UUID of the creator entity"
    )
    updated_by: Optional[UUID] = Field(
        None, description="The user_id UUID of the last modifying entity"
    )

    def update_audit(self, modifier_id: Optional[UUID] = None) -> None:
        """
        Updates the modification timestamp and logs the modifier ID.
        """
        self.updated_at = datetime.now(timezone.utc)
        if modifier_id:
            self.updated_by = modifier_id


class SoftDeleteFields(BaseModel):
    """
    Metadata mixin supporting logical data deletion.
    """

    is_deleted: bool = Field(
        False, description="Flag indicating if the document has been logically soft-deleted"
    )
    deleted_at: Optional[datetime] = Field(
        None, description="UTC timestamp indicating when the document was soft-deleted"
    )

    def soft_delete(self, modifier_id: Optional[UUID] = None) -> None:
        """
        Flags the record as soft-deleted and updates corresponding audit tracks.
        """
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)
        if hasattr(self, "update_audit"):
            # Update audit field timestamp during deletion operation
            getattr(self, "update_audit")(modifier_id)


class MongoDocument(BaseModel):
    """
    Base properties for root MongoDB documents.
    Maps internal ObjectIds and exposes helper serialization methods.
    """

    id: Optional[PyObjectId] = Field(
        default=None,
        alias="_id",
        description="Internal MongoDB primary key (BSON ObjectId)",
    )

    # Configure Pydantic validation rules:
    # - populate_by_name: Allows creating models using 'id' or '_id'
    # - arbitrary_types_allowed: Allows validation of non-Pydantic types (e.g. ObjectId)
    # - validate_assignment: Performs schema checks on in-code value adjustments
    # - use_enum_values: Serializes Enums directly to their backing string value
    # - extra: Forbids input schema pollution by rejecting undeclared attributes
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=True,
        extra="forbid",
    )

    def to_mongo(self, exclude_none: bool = False) -> Dict[str, Any]:
        """
        Serializes the model into a dictionary suitable for Motor write operations.
        Ensures Pydantic aliases (like _id) are correctly populated.
        """
        data = self.model_dump(by_alias=True, exclude_none=exclude_none)

        # Remove _id key if None so MongoDB auto-generates ObjectId on inserts
        if "_id" in data and data["_id"] is None:
            data.pop("_id")

        return data

    @classmethod
    def from_mongo(cls: Type[T], data: Dict[str, Any]) -> Optional[T]:
        """
        Instantiates the Pydantic model from raw MongoDB BSON query results.
        """
        if not data:
            return None
        return cls(**data)


class BaseEntity(MongoDocument, AuditFields, SoftDeleteFields):
    """
    Core template parent model for all primary database entities.
    Combines MongoDB mappings, audit tags, and soft-delete capabilities.
    Excludes generic UUID fields to allow concrete entities to declare specific names.
    """

    version: Optional[int] = Field(
        default=1,
        description="Document version identifier for optimistic concurrency controls",
    )
