from rest_framework import serializers
from .models import House, Reservation, Transaction, User, SavedHome
from django.utils import timezone
from decimal import Decimal

class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = ['reservation_id', 'user', 'house', 'reservation_date', 'expiry_date', 'is_active']

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['transaction_id', 'user', 'house', 'amount_paid', 'transaction_type', 'payment_date', 'payment_reference', 'payment_status']

class HouseSerializer(serializers.ModelSerializer):
    reservation_status = serializers.SerializerMethodField()
    media = serializers.JSONField()
    is_saved = serializers.SerializerMethodField()

    class Meta:
        model = House
        fields = ['house_id', 'house_name', 'room_type', 'price', 'description', 'availability', 'is_reserved', 'lat', 'lng', 'date_added', 'media', 'reservation_status', 'is_saved']

    def get_reservation_status(self, obj):
        request = self.context.get('request')
        reservation = Reservation.objects.filter(
            house=obj,
            is_active=True,
            expiry_date__gt=timezone.now()
        ).first()
        return {
            'is_reserved': obj.is_reserved,
            'reserved_by_user': reservation and request and reservation.user == request.user,
            'expiry_date': reservation.expiry_date if reservation else None
        }

    def get_is_saved(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return SavedHome.objects.filter(user=request.user, house=obj).exists()
        return False

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than zero.")
        return value

    def validate_media(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Media must be a list.")
        image_count = sum(1 for item in value if item.get('media_type') == 'image')
        model_count = sum(1 for item in value if item.get('media_type') == '3d_model')
        if image_count > 6:
            raise serializers.ValidationError("Maximum of 6 images allowed per house.")
        if model_count > 1:
            raise serializers.ValidationError("Only one 3D model allowed per house.")
        for item in value:
            if not isinstance(item, dict) or not all(key in item for key in ['media_type', 'file_url', 'caption', 'uploaded_at']):
                raise serializers.ValidationError("Each media item must have media_type, file_url, caption, and uploaded_at.")
            if item['media_type'] not in ['image', '3d_model']:
                raise serializers.ValidationError("Media type must be 'image' or '3d_model'.")
        return value

class SavedHomeSerializer(serializers.ModelSerializer):
    house = HouseSerializer(read_only=True)

    class Meta:
        model = SavedHome
        fields = ['saved_home_id', 'user', 'house', 'saved_at']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['user_id', 'username', 'email', 'phone_number']