# Context processors for searchapp

from StreamingCommunity.upload.version import __version__


def version_context(request):
    """Add version to template context."""
    return {
        'app_version': __version__,
    }