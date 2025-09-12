from rest_framework import serializers
from .models import House, Transaction, Reservation, User, SavedHome
from django.db.models import Q

class HouseSerializer(serializers.ModelSerializer):
    reservation_status = serializers.SerializerMethodField()

    class Meta:
        model = House
        fields = ['house_id', 'house_name', 'room_type', 'lat', 'lng', 'media', 'is_reserved', 'price', 'description', 'reservation_status']

    def get_reservation_status(self, obj):
        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None
        reservation = Reservation.objects.filter(house=obj, is_active=True).first()
        return {
            'is_reserved': reservation is not None,
            'reserved_by_user': reservation is not None and user is not None and reservation.user == user
        }

class TransactionSerializer(serializers.ModelSerializer):
    house = HouseSerializer(read_only=True)

    class Meta:
        model = Transaction
        fields = ['transaction_id', 'house', 'transaction_type', 'amount_paid', 'payment_date', 'payment_status', 'payment_reference']

class ReservationSerializer(serializers.ModelSerializer):
    house = HouseSerializer(read_only=True)

    class Meta:
        model = Reservation
        fields = ['reservation_id', 'house', 'is_active', 'expiry_date']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['user_id', 'username', 'email', 'phone_number']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

class SavedHomeSerializer(serializers.ModelSerializer):
    house = HouseSerializer(read_only=True)

    class Meta:
        model = SavedHome
        fields = ['house']