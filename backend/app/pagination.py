"""?page=1&pageSize=20 query parameters, shared by every list endpoint."""

import math

from fastapi import Query

from .schemas import PageMeta


class PageParams:
    def __init__(self, page: int = Query(1, ge=1),
                 page_size: int = Query(20, ge=1, le=100, alias="pageSize")):
        self.page = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    def meta(self, total_count: int) -> PageMeta:
        return PageMeta(page=self.page, page_size=self.page_size, total_count=total_count,
                        total_pages=math.ceil(total_count / self.page_size))
