from datetime import datetime
import os

from django.conf import settings


def sitewide(request):
    """Variables that need to be inserted into all templates.
    """
    docstore_hosts = '%s:%s' % (
        settings.DOCSTORE_HOSTS[0]['host'],
        settings.DOCSTORE_HOSTS[0]['port'],
    )
    return {
        'request': request,
        'pid': os.getpid(),
        'host': os.uname()[1],
        'time': datetime.now(),
        'git_commit': settings.GIT_COMMIT[:10],
        'git_branch': settings.GIT_BRANCH,
        'version': settings.VERSION,
        'docstore_hosts': docstore_hosts,
        'docstore_index': settings.DOCSTORE_INDEX,
    }
