from django.urls import path
from . import views
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [

    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

   
    path('user/register/', views.UserRegisterAPIView.as_view(), name='user_register'),
    path('user/profile/', views.UserProfileAPIView.as_view(), name='user_profile'),
    path('user/reservations/', views.UserReservationsAPIView.as_view(), name='user_reservations'),
    path('user/transactions/', views.UserTransactionsAPIView.as_view(), name='user_transactions'),
    path('user/saved-homes/', views.UserSavedHomesAPIView.as_view(), name='user_saved_homes'),
 path('user/change-password/', views.ChangePasswordAPIView.as_view(), name='change_password'),

    path('houses/', views.HouseListAPIView.as_view(), name='house_list'),
    path('house/create/', views.HouseCreateAPIView.as_view(), name='house_create'),
    path('house/<uuid:house_id>/', views.HouseDetailAPIView.as_view(), name='house_detail'),
    path('house/<uuid:house_id>/update/', views.HouseUpdateDeleteAPIView.as_view(), name='house_update_delete'),
    path('house/<uuid:house_id>/media/', views.HouseMediaUploadAPIView.as_view(), name='house_media_upload'),
    path('house/<uuid:house_id>/reserve/', views.ReserveHouseAPIView.as_view(), name='reserve_house'),
    path('house/<uuid:house_id>/tour/', views.BookTourAPIView.as_view(), name='book_tour'),
    path('house/<uuid:house_id>/save/', views.SaveHouseAPIView.as_view(), name='save_house'),
    path('house/<uuid:house_id>/unsave/', views.UnsaveHouseAPIView.as_view(), name='unsave_house'),

 
    path('transaction/create/', views.TransactionCreateAPIView.as_view(), name='transaction_create'),
    path('house/<uuid:house_id>/initiate-payment/', views.InitiatePaymentAPIView.as_view(), name='initiate_payment'),
    path('payment/verify/<str:reference>/', views.VerifyPaymentAPIView.as_view(), name='verify_payment'),


    path('payment/webhook/', views.PaymentWebhookAPIView.as_view(), name='payment_webhook'),
]
