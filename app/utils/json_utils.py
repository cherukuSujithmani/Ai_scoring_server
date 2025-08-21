# app/utils/json_utils.py
import json
import decimal
import datetime


class EnhancedJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder to handle Decimal, datetime, and other types.
    Ensures all objects are JSON serializable.
    """

    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            # Convert Decimal to float (safe for scores, amounts)
            return float(obj)
        if isinstance(obj, (datetime.datetime, datetime.date)):
            # Format dates as ISO strings
            return obj.isoformat()
        return super().default(obj)


def json_dumps(data: dict, **kwargs) -> str:
    """
    Serialize Python objects into JSON string with custom encoder.
    """
    return json.dumps(data, cls=EnhancedJSONEncoder, ensure_ascii=False, **kwargs)


def json_loads(data: str) -> dict:
    """
    Deserialize JSON string into Python dict.
    """
    return json.loads(data)
