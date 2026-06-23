from rest_framework import serializers
from .models import WithdrawalRequest


class WithdrawalHistorySerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    amount = serializers.DecimalField(source='net_amount', max_digits=10, decimal_places=2)

    class Meta:
        model = WithdrawalRequest
        fields = [
            'id', 'amount', 'bank_name', 'account_number', 'account_name',
            'status', 'status_display', 'admin_note', 'created_at'
        ]