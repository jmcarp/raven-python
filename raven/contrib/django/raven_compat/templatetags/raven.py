"""
raven.contrib.django.raven_compat.templatetags.raven
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2010-2013 by the Sentry Team, see AUTHORS for more details.
:license: BSD, see LICENSE for more details.
"""

from __future__ import absolute_import

from raven.contrib.django.templatetags.raven import *  # NOQA

import warnings

warnings.warn('raven.contrib.django.templatetags is deprecated. Use raven_django instead.', DeprecationWarning)
