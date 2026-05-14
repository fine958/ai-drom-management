from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import auto_generate_report

router = DefaultRouter()
router.register(r'inspects', views.DormInspectViewSet)   # 对应 /api/dorm/inspects/
router.register(r'powers', views.PowerInspectViewSet)     # 对应 /api/dorm/powers/

urlpatterns = [
    path('', include(router.urls)),
    # 添加导出视图的路由
    path('export/inspects/', views.ExportDormInspectView.as_view(), name='export-inspects'),
    path('ai-detect/', views.AIDetectView.as_view(), name='ai-detect'),
    path('ai-report/', views.ai_generate_report, name='ai_generate_report'),
    path('ai-weekly-report/', views.ai_weekly_report, name='ai_weekly_report'),
    path('ai-qa/', views.ai_qa, name='ai_qa'),
    path('warnings/trigger/', views.trigger_warning_scan, name='trigger_warning'),
    path('warnings/', views.warning_list, name='warning_list'),
    path('warnings/<int:warning_id>/', views.warning_detail, name='warning_detail'),
    path('warnings/<int:warning_id>/mark-handled/', views.mark_warning_handled, name='mark_warning_handled'),
    path('translate/', views.ai_translate, name='ai_translate'),
    path('auto-report/', views.auto_generate_report, name='auto_report'),
    path('report/<str:task_id>/', views.get_report_result, name='get_report_result'),
]