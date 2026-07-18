import os

env_name = os.environ.get('DJANGO_ENV', 'dev')

if env_name == 'prod':
    from .prod import *
else:
    from .dev import *
