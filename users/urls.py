from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'', views.UserViewSet)   # 注册视图集，生成 /api/users/users/ 这样的URL
router.register(r'feedbacks', views.FeedbackViewSet)


urlpatterns = [
    path('feedbacks/', views.FeedbackViewSet.as_view({'get': 'list', 'post': 'create'}), name='feedback-list'),
    path('feedbacks/<int:pk>/', views.FeedbackViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='feedback-detail'),
    path('', include(router.urls)),
]