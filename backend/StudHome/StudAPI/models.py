import uuid 
from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.

class Login(models.Model):
    Userid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    Username = models.CharField(max_length=150 , blank=False , null=False)
    password = models.CharField(max_length=128 , blank=False , null=False)
    Email = models.EmailField(max_length=200 , blank=False , null=False) 

class Token(models.Model):
    token = models.CharField(max_length=255, blank=False, null=False)
    user = models.ForeignKey(Login, on_delete=models.CASCADE)

    def __str__(self):
        return self.token

    def save(self, *args, **kwargs):
        self.token = make_password(self.tokencjh)
        super().save(*args, **kwargs)
