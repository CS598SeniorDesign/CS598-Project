from __future__ import annotations

from rest_framework.pagination import PageNumberPagination


class OptionalPageNumberPagination(PageNumberPagination):
    """
    Page-number pagination that only applies when the client asks for it with ``?page=`` or ``?page_size=``.

    Without either parameter the full list is returned as a plain JSON array, as before pagination existed, so
    existing clients keep working while new ones opt in. Paginated responses have DRF's usual shape:
    ``{"count", "next", "previous", "results"}``.
    """

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200

    def paginate_queryset(self, queryset, request, view=None):
        """
        Paginate only when the request names a page or page size.

        :param queryset: The filtered queryset.
        :param request: The request.
        :param view: The view.
        :returns: The current page's items, or None to return the whole list unpaginated.
        """
        params = request.query_params
        if self.page_query_param not in params and self.page_size_query_param not in params:
            return None
        return super().paginate_queryset(queryset, request, view)
