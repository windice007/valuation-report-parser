from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import MYSQL_CONNECTION
import json
import decimal


def obj_json_default(obj):
    if type(obj) is decimal.Decimal:
        return float(obj)
    return obj.__dict__


def obj_to_json(obj):
    return json.dumps(obj, default=obj_json_default)


def init_db():
    engine = create_engine(MYSQL_CONNECTION, json_serializer=obj_to_json)
    return sessionmaker(bind=engine)


DBSession = init_db()
