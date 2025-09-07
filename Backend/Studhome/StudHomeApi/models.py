from datetime import timedelta, timezone
import datetime
import uuid
from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser
from phonenumber_field.modelfields import PhoneNumberField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import JSONField 
from decimal import Decimal

class User(AbstractUser):
    username = models.CharField(max_length=150, unique=True)
    user_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = PhoneNumberField()
    email = models.EmailField(unique=True)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'phone_number']

    def __str__(self):
        return self.username

    class Meta:
        indexes = [models.Index(fields=['username', 'email'])]
        ordering = ['username']

class House(models.Model):
    house_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    house_name = models.CharField(max_length=50)
    ROOM_TYPES = (
        ('single', 'Single Room'),
        ('double', 'Double Room'),
        ('apartment', 'Apartment'),
    )
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES)
    availability = models.BooleanField(default=True)
    is_reserved = models.BooleanField(default=False)
    remove = models.BooleanField(default=False)
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    lat = models.FloatField(validators=[MinValueValidator(-90), MaxValueValidator(90)])
    lng = models.FloatField(validators=[MinValueValidator(-180), MaxValueValidator(180)])
    date_added = models.DateTimeField(auto_now_add=True)
    media = JSONField(default=list, blank=True) 

    def __str__(self):
        return self.house_name

    class Meta:
        indexes = [models.Index(fields=['house_name', 'room_type'])]
        ordering = ['date_added']

class Transaction(models.Model):
    transaction_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='transactions')
    house = models.ForeignKey('House', on_delete=models.CASCADE, related_name='transactions')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    TRANSACTION_TYPES = (
        ('reserve', 'Reserve a house'),
        ('tour', 'Book a tour'),
    )
    transaction_type = models.CharField(max_length=25, choices=TRANSACTION_TYPES)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_reference = models.CharField(max_length=100, null=True, blank=True)
    payment_status = models.CharField(max_length=20, default='PENDING')

    def __str__(self):
        return f"{self.user.username} - {self.house.house_name} - {self.amount_paid}"

    class Meta:
        indexes = [models.Index(fields=['payment_date'])]
        ordering = ['-payment_date']

class Reservation(models.Model):
    reservation_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='reservations')
    house = models.ForeignKey('House', on_delete=models.CASCADE, related_name='reservations')
    reservation_date = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.expiry_date:
            self.expiry_date = timezone.now() + datetime.timedelta(days=7)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Reservation for {self.house.house_name} by {self.user.username}"

    class Meta:
        indexes = [models.Index(fields=['reservation_date', 'expiry_date'])]
        ordering = ['-reservation_date']

class SavedHome(models.Model):
    saved_home_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='saved_homes')
    house = models.ForeignKey('House', on_delete=models.CASCADE, related_name='saved_by')
    saved_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} saved {self.house.house_name}"

    class Meta:
        indexes = [models.Index(fields=['user', 'house'])]
        ordering = ['-saved_at']
        unique_together = ['user', 'house']