from m.extensions.sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Boolean, BLOB, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy import UniqueConstraint


db = SQLAlchemy(config_prefix='database')


class Schema(db.Model):
    __tablename__ = 'schema'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(45), unique=True, nullable=False)
    display = Column(String(45), unique=True, nullable=False)
    deleted = Column(Boolean, default=False, nullable=False)

    fields = relationship('Field', back_populates='schema', foreign_keys='[Field.schema_id]')


class Field(db.Model):
    __tablename__ = 'field'

    TYPE_INT = 0
    TYPE_FLOAT = 1
    TYPE_STRING = 2
    TYPE_DATETIME = 3
    TYPE_IP = 4

    id = Column(Integer, primary_key=True, autoincrement=True)
    schema_id = Column(Integer, ForeignKey('schema.id'), nullable=False)
    name = Column(String(45), unique=True, nullable=False)
    display = Column(String(45), unique=True, nullable=False)
    type = Column(Integer, nullable=False, default=TYPE_STRING)
    required = Column(Boolean, nullable=False, default=True)
    multi = Column(Boolean, nullable=False, default=False)
    unique = Column(Boolean, nullable=False, default=False)
    default = Column(BLOB, nullable=True)
    deleted = Column(Boolean, nullable=False, default=False)

    schema = relationship('Schema', back_populates='fields', foreign_keys=[schema_id])
    histories = relationship('FieldHistory', back_populates='field', foreign_keys=['FieldHistory.field_id'])

    __table_args__ = (UniqueConstraint(schema_id, name, name='uq_field_schema_name'),
                      UniqueConstraint(schema_id, display, name='uq_field_schema_display'))


class FieldHistory(db.Model):
    __tablename__ = 'field_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    schema_id = Column(Integer, ForeignKey('schema.id'), nullable=False)
    name = Column(String(45), unique=True, nullable=False)
    display = Column(String(45), unique=True, nullable=False)
    type = Column(Integer, nullable=False, default=Field.TYPE_STRING)
    required = Column(Boolean, nullable=False, default=True)
    multi = Column(Boolean, nullable=False, default=False)
    unique = Column(Boolean, nullable=False, default=False)
    default = Column(BLOB, nullable=True)
    deleted = Column(Boolean, nullable=False, default=False)

    field_id = Column(Integer, ForeignKey('field.id'), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)

    field = relationship('Field', back_populates='histories', foreign_keys=[field_id])


class Relationship(db.Model):
    __tablename__ = 'relationship'

    source_id = Column(Integer, ForeignKey('field.id'), primary_key=True)
    target_id = Column(Integer, ForeignKey('field.id'), primary_key=True)


class Entity(db.Model):
    __tablename__ = 'entity'

    id = Column(Integer, primary_key=True, autoincrement=True)
    schema_id = Column(Integer, ForeignKey('schema.id'), nullable=False)

    schema = relationship('Schema', foreign_keys=[schema_id])
    values = relationship('Value', foreign_keys='[Value.entity_id]')


class Value(db.Model):
    __tablename__ = 'value'

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_id = Column(Integer, ForeignKey('entity.id'), nullable=False)
    field_id = Column(Integer, ForeignKey('field.id'), nullable=False)
    value = Column(BLOB, nullable=False, index=True)

    field = relationship('Field', foreign_keys=[field_id])


class ValueHistory(db.Model):
    __tablename__ = 'value_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_id = Column(Integer, ForeignKey('entity.id'), nullable=False)
    field_id = Column(Integer, ForeignKey('field.id'), nullable=False)
    value = Column(BLOB, nullable=False, index=True)

    deleted = Column(Boolean, nullable=False, default=False)
    timestamp = Column(DateTime, nullable=False, index=True)
