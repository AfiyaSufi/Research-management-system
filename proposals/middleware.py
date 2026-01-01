from django.utils.cache import add_never_cache_headers


class DisableClientSideCachingMiddleware:
    """Middleware to disable client-side caching for API responses"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Disable caching for API endpoints and external form views
        if request.path.startswith('/api/') or request.path.startswith('/external/'):
            add_never_cache_headers(response)
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        
        return response
