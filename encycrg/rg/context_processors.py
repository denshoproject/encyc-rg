from datetime import datetime
import os

from django.conf import settings


def sitewide(request):
    """Variables that need to be inserted into all templates.
    """
    return {
        'request': request,
        'debug': settings.DEBUG,
        'time': datetime.now().isoformat(),
        'pid': os.getpid(),
        'host': os.uname()[1],
        'git_commit': settings.GIT_COMMIT[:10],
        'git_branch': settings.GIT_BRANCH,
        'version': settings.VERSION,
        'packages': settings.PACKAGES,
        'docstore_host': settings.DOCSTORE_HOST,
        'encycrg_cluster': settings.DOCSTORE_CLUSTER,
        'base_template': settings.BASE_TEMPLATE,
        'MEDIA_URL_LOCAL_NETLOC': settings.MEDIA_URL_LOCAL_NETLOC,
        'MEDIA_URL_LOCAL_IP': settings.MEDIA_URL_LOCAL_IP,
        'static_url': settings.STATIC_URL,
        'google_analytics_id': settings.GOOGLE_ANALYTICS_ID,
        'site_msg_text': settings.SITE_MSG_TEXT,
    }
