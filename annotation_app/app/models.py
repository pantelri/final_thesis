import enum

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base


class ElementType(enum.Enum):
    sentence = "sentence"
    table = "table"


class LengthJudgment(enum.Enum):
    ok = "ok"
    too_short = "too_short"
    too_long = "too_long"


class ApplicableType(enum.Enum):
    yes = "yes"
    no = "no"
    unsure = "unsure"


class FulfilledType(enum.Enum):
    yes = "yes"
    partially = "partially"
    no = "no"


class Annotator(Base):
    __tablename__ = "annotators"

    id = Column(Integer, primary_key=True)
    code_hash = Column(Text, unique=True, nullable=False)
    label = Column(Text)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default="NOW()")
    consent_given_at = Column(DateTime(timezone=True))

    annotations = relationship("Annotation", back_populates="annotator")


class Obligation(Base):
    __tablename__ = "obligations"

    id = Column(String(20), primary_key=True)
    legal_basis = Column(Text)
    title_de = Column(Text, nullable=False)
    category = Column(Text)
    verification_criterion = Column(Text)
    applicability_type = Column(Text)
    applicability_trigger = Column(Text)


class Company(Base):
    __tablename__ = "companies"

    id = Column(String(50), primary_key=True)
    name = Column(Text, nullable=False)
    pdf_path = Column(Text)


class AnnotationItem(Base):
    __tablename__ = "annotation_items"

    id = Column(Integer, primary_key=True)
    company_id = Column(String(50), ForeignKey("companies.id"), nullable=False)
    obligation_id = Column(String(20), ForeignKey("obligations.id"), nullable=False)
    passage_text = Column(Text, nullable=False)
    passage_start = Column(Integer)
    passage_end = Column(Integer)
    in_overlap_set = Column(Boolean, default=False, nullable=False)
    stratum = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default="NOW()")

    company = relationship("Company")
    obligation = relationship("Obligation")
    sentences = relationship(
        "PassageSentence", back_populates="item", cascade="all, delete-orphan",
        order_by="PassageSentence.idx",
    )
    annotations = relationship("Annotation", back_populates="item")


class PassageSentence(Base):
    __tablename__ = "passage_sentences"

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey("annotation_items.id", ondelete="CASCADE"), nullable=False)
    idx = Column(Integer, nullable=False)
    element_type = Column(Enum(ElementType, name="element_type"), nullable=False, default=ElementType.sentence)
    text = Column(Text, nullable=False)
    char_start = Column(Integer)
    char_end = Column(Integer)

    item = relationship("AnnotationItem", back_populates="sentences")


class Annotation(Base):
    __tablename__ = "annotations"

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey("annotation_items.id"), nullable=False)
    annotator_id = Column(Integer, ForeignKey("annotators.id"), nullable=False)
    is_relevant = Column(Boolean)
    length_judgment = Column(Enum(LengthJudgment, name="length_judg_type"))
    is_applicable = Column(Enum(ApplicableType, name="applicable_type"))
    is_fulfilled = Column(Enum(FulfilledType, name="fulfilled_type"))
    justification_ok = Column(Boolean)   # nullable, never rendered
    comment = Column(Text)
    missing_info = Column(Text)          # free text: what the annotator felt was missing (too_short)
    submitted_at = Column(DateTime(timezone=True))
    reviewed_at = Column(DateTime(timezone=True))  # set once revisited via /review; clears the re-review flag

    __table_args__ = (UniqueConstraint("item_id", "annotator_id"),)

    item = relationship("AnnotationItem", back_populates="annotations")
    annotator = relationship("Annotator", back_populates="annotations")
    irrelevant_elements = relationship(
        "IrrelevantElement", back_populates="annotation", cascade="all, delete-orphan"
    )
    suggested_passages = relationship(
        "SuggestedPassage", back_populates="annotation", cascade="all, delete-orphan"
    )


class IrrelevantElement(Base):
    __tablename__ = "irrelevant_elements"

    id = Column(Integer, primary_key=True)
    annotation_id = Column(Integer, ForeignKey("annotations.id", ondelete="CASCADE"), nullable=False)
    sentence_idx = Column(Integer, nullable=False)

    __table_args__ = (UniqueConstraint("annotation_id", "sentence_idx"),)

    annotation = relationship("Annotation", back_populates="irrelevant_elements")


class SuggestedPassage(Base):
    """Alternative passage chosen by the annotator from LLM suggestions (too_short flow)."""
    __tablename__ = "suggested_passages"

    id = Column(Integer, primary_key=True)
    annotation_id = Column(
        Integer, ForeignKey("annotations.id", ondelete="CASCADE"), nullable=False
    )
    passage_text = Column(Text, nullable=False)
    source_ref = Column(Text)            # optional locator from the LLM (heading/page)
    created_at = Column(DateTime(timezone=True), server_default="NOW()")

    annotation = relationship("Annotation", back_populates="suggested_passages")


class AssignmentLog(Base):
    __tablename__ = "assignment_log"

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey("annotation_items.id"), nullable=False)
    annotator_id = Column(Integer, ForeignKey("annotators.id"), nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default="NOW()")
