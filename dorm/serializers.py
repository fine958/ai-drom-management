from rest_framework import serializers
from .models import DormInspect, PowerInspect

class DormInspectSerializer(serializers.ModelSerializer):
    inspector_name = serializers.CharField(source='inspector.username', read_only=True)  # 额外显示检查人姓名

    class Meta:
        model = DormInspect
        fields = '__all__'   # 包含所有字段
        read_only_fields = ['inspector', 'inspect_time']

class PowerInspectSerializer(serializers.ModelSerializer):
    inspector_name = serializers.CharField(source='inspector.username', read_only=True)

    class Meta:
        model = PowerInspect
        fields = '__all__'
        read_only_fields = ['inspector', 'inspect_time']