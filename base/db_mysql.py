from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import json
import decimal
# sqlalchemy.orm.state.InstanceState
from sqlalchemy.orm.state import InstanceState


def obj_json_default(obj):
    if type(obj) is decimal.Decimal:
        return float(obj)
    if isinstance(obj, InstanceState):
        return None
    dic = obj.__dict__.copy()
    del dic['_sa_instance_state']
    return dic


def obj_to_json(obj):
    return json.dumps(obj, default=obj_json_default)


def init_db(connection_url: str):
    engine = create_engine(connection_url, json_serializer=obj_to_json)
    return sessionmaker(bind=engine)
