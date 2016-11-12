import datetime
import socket
import struct
from dateutil.parser import parse
from sqlalchemy import or_
from .models import db, Schema, Field, FieldHistory, Relationship, Entity, Value, ValueHistory


def is_datetime(origin):
    if isinstance(origin, datetime.datetime):
        return origin
    if isinstance(origin, str):
        try:
            return True, parse(origin)
        except:
            return False, None
    if isinstance(origin, (int, float)):
        try:
            return True, datetime.datetime.fromtimestamp(origin)
        except:
            return False, None
    return False


def is_ip(origin):
    if isinstance(origin, str):
        try:
            return True, struct.unpack('>I', socket.inet_aton(str))
        except:
            return False, None
    if isinstance(origin, int):
        try:
            socket.inet_ntoa(struct.pack('>I', origin))
            return True, origin
        except:
            return False, None


type_validate_map = {
    Field.TYPE_INT: lambda x: (isinstance(x, int), x),
    Field.TYPE_FLOAT: lambda x: (isinstance(x, float), x),
    Field.TYPE_STRING: lambda x: (isinstance(x, str), x),
    Field.TYPE_DATETIME: is_datetime,
    Field.TYPE_IP: is_ip
}


class SchemaService:
    @staticmethod
    def create(data):
        try:
            schema = Schema(name=data['name'], display=data.get('display', data['name']))
            db.session.add(schema)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def remove(schema_id):
        try:
            schema = Schema.query.filter(id == schema_id).first()
            if schema is None:
                return
            for field in schema.fields:
                if not SchemaService.field_deletable(field):
                    raise Exception('field {} not deletable')
            schema.deleted = True
            db.session.add(schema)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def add_field(schema_id, data):
        type = getattr(Field, 'TYPE_{}'.format(data.get('type').upper()), 'TYPE_STRING')
        try:
            schema = Schema.query.filter(Schema.id == schema_id).first_or_404()
            if data.get('default') is not None:
                ok, ret = type_validate_map[type](data.get('default'))
                if ok:
                    data['default'] = ret
                else:
                    raise TypeError()
            if data.get('required', False) and Entity.query.filter(Entity.schema_id == schema_id).count() > 0:
                if data.get('unique', False):
                    raise Exception()
                if data.get('default') is None:
                    raise Exception()

            field = Field(name=data['name'],
                          schema=schema,
                          display=data.get('display', data['name']),
                          type=type,
                          required=data.get('required', False),
                          multi=data.get('multi', False),
                          unique=data.get('unique', False),
                          default=data.get('default'))
            db.session.add(field)
            fh = FieldHistory(name=data['name'],
                              schema=schema,
                              display=data.get('display', data['name']),
                              type=type,
                              required=data.get('required', False),
                              multi=data.get('multi', False),
                              unique=data.get('unique', False),
                              default=data.get('default'),
                              field=field,
                              timestamp=datetime.datetime.now())
            db.session.add(fh)
            if field.required:
                for entity in Entity.query.filter(Entity.schema_id == schema_id).all():
                    value = Value(entity_id=entity.id, field=field, value=data['default'])
                    db.session.add(value)
                    vh = ValueHistory(entity_id=entity.id, field=field, value=data['default'],
                                      timestamp=datetime.datetime.now())
                    db.session.add(vh)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e


    @staticmethod
    def remove_field(schema_id, data):
        pass

    @staticmethod
    def change_field(schema_id, field_id, data):
        pass

    @staticmethod
    def field_deletable(field):
        return Relationship.query\
            .filter(or_(Relationship.source_id == field.id, Relationship.target_id == field.id))\
            .first() is None
