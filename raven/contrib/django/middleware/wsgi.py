"""
raven.contrib.django.middleware.wsgi
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2010-2012 by the Sentry Team, see AUTHORS for more details.
:license: BSD, see LICENSE for more details.
"""
from __future__ import absolute_import

from raven.middleware import Sentry

import warnings

warnings.warn('raven.contrib.django is deprecated. Use raven_django instead.', DeprecationWarning)


class Sentry(Sentry):
    """
    Identical to the default WSGI middleware except that
    the client comes dynamically via ``get_client

    >>> from raven.contrib.django.middleware.wsgi import Sentry
    >>> application = Sentry(application)
    """
    def __init__(self, application):
        self.application = application

    @property
    def client(self):
        from raven.contrib.django.models import client
        return client
