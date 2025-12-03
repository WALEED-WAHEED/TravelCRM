from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """
    Standard pagination class with 10 items per page
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class LargeResultsSetPagination(PageNumberPagination):
    """
    Pagination class for larger result sets with 25 items per page
    """
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


class SmallResultsSetPagination(PageNumberPagination):
    """
    Pagination class for smaller result sets with 5 items per page
    """
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 50

