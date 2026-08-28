from fastapi import Query


def pagination_params(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> tuple[int, int]:
    return page, page_size


def paginated_query(query, page: int, page_size: int):
    total = query.order_by(None).count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def paginated_items(items, page: int, page_size: int):
    total = len(items)
    start = (page - 1) * page_size
    return {
        "items": items[start:start + page_size],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
