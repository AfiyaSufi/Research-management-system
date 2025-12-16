from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProposalViewSet, NoticeViewSet,
    EvaluatorFormView, CommitteeFormView, RectorFormView
)

router = DefaultRouter()
router.register(r'proposals', ProposalViewSet, basename='proposal')
router.register(r'notices', NoticeViewSet, basename='notice')

urlpatterns = [
    path('', include(router.urls)),
]

# External form URLs (no auth required - token based)
external_urlpatterns = [
    path('external/evaluate/<uuid:token>/', EvaluatorFormView.as_view(), name='evaluator-form'),
    path('external/committee/<uuid:token>/', CommitteeFormView.as_view(), name='committee-form'),
    path('external/rector/<uuid:token>/', RectorFormView.as_view(), name='rector-form'),
]
