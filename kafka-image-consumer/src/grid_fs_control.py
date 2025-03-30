import gridfs
from pymongo import MongoClient
from bson import ObjectId


class GridFSControl:
    def __init__(self, host: str, port: int, db: str, collection: str, user: str, pwd: str):
        self.db_url = f'mongodb://{user}:{pwd}@{host}:{port}'
        client = MongoClient(self.db_url)
        db = client[db]
        self.grid_fs = gridfs.GridFS(db, collection=collection)

    def upload(self, file_data: bytes, file_meta_data: dict):
        file_id = self.grid_fs.put(file_data, **file_meta_data)
        return str(file_id)

    def download(self, file_id: str) -> tuple[str, bytes]:
        file = self.grid_fs.get(ObjectId(file_id))
        return file.filename, file.read()

    def get_list(self):
        cursor = self.grid_fs.find()
        return cursor.to_list()
