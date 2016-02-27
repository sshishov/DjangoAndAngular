from .injector import inject_settings


inject_settings(
    'django_and_angular.settings.defaults',
    locals()
)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '$6(x*g_2g9l_*g8peb-@anl5^*8q!1w)k&e&2!i)t6$s8kia94'
