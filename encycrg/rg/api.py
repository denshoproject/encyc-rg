# -*- coding: utf-8 -*-

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(['GET'])
def index(request, format=None):
    """INDEX DOCS HERE
    """
    return Response({
        'hello': 'world',
    })
