from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'issues', views.ClockIssueViewSet)      # /api/attendance/issues/
router.register(r'records', views.ClockRecordViewSet)    # /api/attendance/records/
router.register(r'leaves', views.LeaveViewSet)           # /api/attendance/leaves/
router.register(r'registrations', views.RecordViewSet)
router.register(r'auto-settings', views.AutoClockSettingViewSet)
router.register(r'notifications', views.NotificationViewSet,basename='notifications')
router.register(r'user-notifications', views.UserNotificationViewSet,basename='user-notification')
router.register(r'templates', views.NotificationTemplateViewSet,basename='notification-template')
router.register(r'messages', views.MessageViewSet)

urlpatterns = [
    path('', include(router.urls)),
]