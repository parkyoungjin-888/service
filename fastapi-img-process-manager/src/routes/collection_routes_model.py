from pydantic import BaseModel


class DocId(BaseModel):
    doc_id: str


class DocIdList(BaseModel):
    doc_id_list: list[str]


class DocListResponse(BaseModel):
    doc_list: list[dict]
    total_count: int


class DocUpdateRequest(BaseModel):
    doc_id_list: list[str]
    set: dict


class CountResponse(BaseModel):
    count: int
