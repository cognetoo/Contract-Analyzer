from datetime import datetime
from typing import List, Optional,Any

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, JSON, Integer, ForeignKey, Text

from api.db import Base

class Contract(Base):
    __tablename__ = "contracts"

    contract_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)

    # persist paths so API can reload after restart
    pdf_path: Mapped[str] = mapped_column(String, nullable=False)
    index_path: Mapped[str] = mapped_column(String, nullable=False)

    num_clauses: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # relationship to clauses
    clauses: Mapped[List["Clause"]] = relationship(
        "Clause",
        back_populates="contract",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class Clause(Base):
    __tablename__ = "clauses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    contract_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("contracts.contract_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    clause_id: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    clause_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    contract: Mapped["Contract"] = relationship("Contract", back_populates="clauses")


class ContractResult(Base):
    __tablename__ = "contract_results"

    contract_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    last_result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ContractRun(Base):
    __tablename__ = "contract_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contract_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("contracts.contract_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    # helpful metadata for UI
    query: Mapped[str] = mapped_column(Text, nullable=False)
    plan: Mapped[dict] = mapped_column(JSON, nullable=False)
    result: Mapped[dict] = mapped_column(JSON, nullable=False)
    perf_ms: Mapped[dict] = mapped_column(JSON, nullable=False) 