#!/usr/bin/env python
# flake8: noqa

import os
import sys

if __name__ == "__main__":
    level = os.environ.get('LEVEL') or 'development'
    os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                          'django_and_angular.settings.{0}'.format(level))

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
