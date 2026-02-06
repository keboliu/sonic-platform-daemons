"""
Mock swsscommon.swsscommon module
"""


class FieldValuePairs(list):
    """Mock FieldValuePairs class"""

    def __init__(self, pairs=None):
        if pairs:
            super(FieldValuePairs, self).__init__(pairs)
        else:
            super(FieldValuePairs, self).__init__()


class Table:
    """Mock Table class"""

    def __init__(self, db, table_name):
        self.db = db
        self.table_name = table_name
        self._data = {}

    def set(self, key, fvs):
        self._data[key] = dict(fvs)

    def get(self, key):
        if key in self._data:
            return True, list(self._data[key].items())
        return False, []

    def _del(self, key):
        if key in self._data:
            del self._data[key]

    def getKeys(self):
        return list(self._data.keys())
