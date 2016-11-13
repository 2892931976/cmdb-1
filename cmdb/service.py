import datetime
import socket
import struct
from dateutil.parser import parse
from sqlalchemy import or_, func, distinct, select
from .models import db, Schema, Field, FieldHistory, Relationship, Entity, Value, ValueHistory


def is_datetime(origin):
    if isinstance(origin, datetime.datetime):
        return origin
    if isinstance(origin, str):
        try:
            return True, parse(origin).timestamp()
        except:
            return False, None
    if isinstance(origin, (int, float)):
        try:
            return True, datetime.datetime.fromtimestamp(origin).timestamp()
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
    def remove_field(field_id):
        field = Field.query.filter(Field.id == field_id).first_or_404()
        if not SchemaService.field_deletable(field):
            raise Exception()
        field.deleted = True
        fh = FieldHistory(name=field.name,
                          schema_id=field.schema_id,
                          display=field.display,
                          type=field.type,
                          required=field.required,
                          multi=field.multi,
                          unique=field.unique,
                          default=field.default,
                          deleted=True,
                          field=field,
                          timestamp=datetime.datetime.now())
        try:
            db.session.add(field)
            db.session.add(fh)
            db.session.commit(field)
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def change_field(field_id, data):
        try:
            field = Field.query.filter(Field.id == field_id).first_or_404()
            field.name = data['name']
            field.display = data.get('display', data['name'])
            if data.get('default') is not None:
                ok, ret = type_validate_map[field.type](data.get('default'))
                if ok:
                    data['default'] = ret
                else:
                    raise TypeError()
            field.default = data.get('default')
            if field.unique is False:
                if data.get('unique', False) is True:
                    c1 = Value.query.filter(Value.field_id == field.id).count()
                    c2 = db.session.query(func.count(distinct(Value.value))).filter(Value.field_id == field.id)
                    if c1 != c2:
                        raise Exception()
                field.unique = data.get('unique', False)
            if field.required is False:
                if data.get('required', False) is True:
                    if field.multi:
                        for entity in Entity.query.filter(Entity.schema_id == field.schema_id).all():
                            if Value.query.filter(Value.entity_id == entity.id).first() is None:
                                raise Exception()
                    else:
                        c1 = Entity.query.filter(Entity.schema_id == field.schema_id).count()
                        c2 = Value.query.filter(Value.field_id == field.id).count()
                        if c1 != c2:
                            raise Exception
                field.required = data.get('required', False)
            if field.multi is True:
                if data.get('multi', False) is False:
                    stmt = select([Value.entity_id, func.count(Value.id)])\
                        .select_from(Value).group_by(Value.entity_id)\
                        .having(func.count(Value.id) > 0)
                    if len(db._engine.connect().execute(stmt).fetch_all()) > 0:
                        raise Exception()
                field.multi = data.get('multi', False)
            db.session.add(field)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def field_deletable(field):
        return Relationship.query\
            .filter(or_(Relationship.source_id == field.id, Relationship.target_id == field.id))\
            .first() is None