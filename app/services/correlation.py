import threading
import uuid


class CorrelationContext:
    _local = threading.local()

    @classmethod
    def new_request_id(cls):
        rid = uuid.uuid4().hex[:12]
        cls.set_request_id(rid)
        return rid

    @classmethod
    def new_execution_id(cls):
        eid = uuid.uuid4().hex[:12]
        cls.set_execution_id(eid)
        return eid

    @classmethod
    def set_request_id(cls, request_id):
        cls._local.request_id = request_id

    @classmethod
    def get_request_id(cls):
        return getattr(cls._local, 'request_id', None)

    @classmethod
    def set_execution_id(cls, execution_id):
        cls._local.execution_id = execution_id

    @classmethod
    def get_execution_id(cls):
        return getattr(cls._local, 'execution_id', None)

    @classmethod
    def clear(cls):
        for attr in ('request_id', 'execution_id'):
            if hasattr(cls._local, attr):
                delattr(cls._local, attr)
