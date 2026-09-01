from __future__ import annotations
from uuid import UUID
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.database import Base

class ToolModel(Base):
    __tablename__ = "tools"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    skill_id: Mapped[str] = mapped_column(String, ForeignKey("skills.id"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    required_permission: Mapped[str] = mapped_column(String, nullable=False)
    
    skill: Mapped["SkillModel"] = relationship("SkillModel", back_populates="tools")

class SkillPermission(Base):
    __tablename__ = "skill_permissions"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    skill_id: Mapped[str] = mapped_column(String, ForeignKey("skills.id"))
    permission: Mapped[str] = mapped_column(String, nullable=False)
    
    skill: Mapped["SkillModel"] = relationship("SkillModel", back_populates="permissions")

class SkillModel(Base):
    __tablename__ = "skills"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[str] = mapped_column(String, nullable=False)
    trust_level: Mapped[str] = mapped_column(String, nullable=False)
    
    tools: Mapped[list["ToolModel"]] = relationship("ToolModel", back_populates="skill")
    permissions: Mapped[list["SkillPermission"]] = relationship("SkillPermission", back_populates="skill")
