from datetime import timedelta
import requests
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.mail import send_mail
import cloudinary.uploader
from campay.sdk import Client as CamPayClient
from .models import House, Transaction, Reservation, User, SavedHome
from .serializers import HouseSerializer, TransactionSerializer, ReservationSerializer, UserSerializer, SavedHomeSerializer
from rest_framework_simplejwt.tokens import RefreshToken  # Added for token generation
import logging

logger = logging.getLogger(__name__)

campay = CamPayClient({
    "app_username": settings.CAMPAY_USERNAME,
    "app_password": settings.CAMPAY_PASSWORD,
    "environment": "DEV"
})

class UserRegisterAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)  # Generate tokens
            response_data = {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
            logger.info(f"User registration response: {response_data}")  # Debug log
            return Response(response_data, status=status.HTTP_201_CREATED)
        logger.error(f"Registration errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def put(self, request):
        user = request.user
        username = request.data.get('username')
        phone_number = request.data.get('phone_number')
        
        if not username or not username.strip():
            return Response({'error': 'Username is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if User.objects.filter(username=username).exclude(user_id=user.user_id).exists():
            return Response({'error': 'Username already exists'}, status=status.HTTP_400_BAD_REQUEST)
        
        user.username = username.strip()
        if phone_number:
            user.phone_number = phone_number.strip()
        
        try:
            user.save()
            serializer = UserSerializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': 'Failed to update profile'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class HouseDetailAPIView(APIView):
    def get(self, request, house_id):
        house = get_object_or_404(House, house_id=house_id)
        serializer = HouseSerializer(house, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

class BookTourAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, house_id):
        house = get_object_or_404(House, house_id=house_id)
        transaction = Transaction.objects.filter(
            user=request.user,
            house=house,
            transaction_type='tour',
            payment_status='SUCCESSFUL'
        ).first()
        if not transaction:
            return Response({"error": "No successful payment found for tour"}, status=status.HTTP_400_BAD_REQUEST)
        serializer = TransactionSerializer(transaction)
        return Response(serializer.data, status=status.HTTP_200_OK)

class HouseListAPIView(APIView):
    def get(self, request):
        room_type = request.query_params.get('room_type')
        houses = House.objects.filter(remove=False)
        if room_type and room_type in ['single', 'double', 'apartment']:
            houses = houses.filter(room_type=room_type)
        serializer = HouseSerializer(houses, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

class HouseCreateAPIView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        data = request.data.copy()
        data['media'] = []
        serializer = HouseSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            house = serializer.save()
            return self.handle_media_upload(request, house)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def handle_media_upload(self, request, house):
        files = request.FILES.getlist('media')
        captions = request.data.getlist('caption', [])
        media_list = house.media or []
        image_count = sum(1 for item in media_list if item.get('media_type') == 'image')
        model_count = sum(1 for item in media_list if item.get('media_type') == '3d_model')
        new_image_count = sum(1 for file in files if file.name.split('.')[-1].lower() not in ['glb', 'gltf'])
        new_model_count = sum(1 for file in files if file.name.split('.')[-1].lower() in ['glb', 'gltf'])
        if image_count + new_image_count > 6:
            return Response({"error": "Maximum of 6 images allowed per house."}, status=status.HTTP_400_BAD_REQUEST)
        if model_count + new_model_count > 1:
            return Response({"error": "Only one 3D model allowed per house."}, status=status.HTTP_400_BAD_REQUEST)
        for idx, file in enumerate(files):
            ext = file.name.split('.')[-1].lower()
            resource_type = 'raw' if ext in ['glb', 'gltf'] else 'image'
            media_type = '3d_model' if ext in ['glb', 'gltf'] else 'image'
            upload_result = cloudinary.uploader.upload(file, resource_type=resource_type)
            media_list.append({
                'media_type': media_type,
                'file_url': upload_result['secure_url'],
                'caption': captions[idx] if idx < len(captions) else '',
                'uploaded_at': timezone.now().isoformat()
            })
        house.media = media_list
        house.save()
        return Response(HouseSerializer(house, context={'request': request}).data, status=status.HTTP_201_CREATED)

class HouseUpdateDeleteAPIView(APIView):
    permission_classes = [IsAdminUser]

    def put(self, request, house_id):
        house = get_object_or_404(House, house_id=house_id)
        serializer = HouseSerializer(house, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            house = serializer.save()
            if 'media' in request.FILES:
                return HouseCreateAPIView().handle_media_upload(request, house)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, house_id):
        house = get_object_or_404(House, house_id=house_id)
        house.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class HouseMediaUploadAPIView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, house_id):
        house = get_object_or_404(House, house_id=house_id)
        return HouseCreateAPIView().handle_media_upload(request, house)

class ReserveHouseAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, house_id):
        house = get_object_or_404(House, house_id=house_id)
        transaction = Transaction.objects.filter(
            user=request.user,
            house=house,
            transaction_type='reserve',
            payment_status='SUCCESSFUL'
        ).first()
        if not transaction:
            return Response({"error": "No successful payment found for reservation"}, status=status.HTTP_400_BAD_REQUEST)
        serializer = ReservationSerializer(Reservation.objects.get(house=house, user=request.user))
        return Response(serializer.data, status=status.HTTP_200_OK)

class UserReservationsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        reservations = Reservation.objects.filter(user=request.user)
        serializer = ReservationSerializer(reservations, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class TransactionCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data.copy()
        house_id = data.get('house')
        house = get_object_or_404(House, house_id=house_id)
        transaction_type = data.get('transaction_type')
        if transaction_type == 'tour':
            active_reservation = Reservation.objects.filter(
                house=house,
                is_active=True,
                expiry_date__gt=timezone.now()
            ).first()
            if active_reservation and active_reservation.user != request.user:
                return Response({"error": "Cannot book a tour; house is reserved by another user"}, status=status.HTTP_400_BAD_REQUEST)
        serializer = TransactionSerializer(data=data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserTransactionsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        transactions = Transaction.objects.filter(user=request.user)
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class SaveHouseAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, house_id):
        house = get_object_or_404(House, house_id=house_id)
        saved_home, created = SavedHome.objects.get_or_create(
            user=request.user,
            house=house
        )
        if not created:
            return Response({"message": "House already saved"}, status=status.HTTP_200_OK)
        serializer = SavedHomeSerializer(saved_home)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class UnsaveHouseAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, house_id):
        house = get_object_or_404(House, house_id=house_id)
        saved_home = get_object_or_404(SavedHome, user=request.user, house=house)
        saved_home.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class UserSavedHomesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        saved_homes = SavedHome.objects.filter(user=request.user)
        serializer = SavedHomeSerializer(saved_homes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class InitiatePaymentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, house_id):
        try:
            house = House.objects.get(house_id=house_id)
            amount = request.data.get('amount')
            phone_number = request.data.get('phone_number')
            transaction_type = request.data.get('transaction_type')
            errors = []
            try:
                amount = float(amount) if amount else None
                if not amount or amount != 100:
                    errors.append('Amount must be exactly 100 FCFA for demo account')
            except (TypeError, ValueError):
                errors.append('Amount must be a valid number')
            if not phone_number or not phone_number.startswith('+'):
                errors.append('Phone number must include country code (e.g., +237)')
            if transaction_type not in ['reserve', 'tour']:
                errors.append("Transaction type must be 'reserve' or 'tour'")
            if errors:
                return Response({'error': errors}, status=status.HTTP_400_BAD_REQUEST)
            if transaction_type == 'tour':
                active_reservation = Reservation.objects.filter(
                    house=house,
                    is_active=True,
                    expiry_date__gt=timezone.now()
                ).first()
                if active_reservation and active_reservation.user != request.user:
                    return Response({"error": "Cannot book a tour; house is reserved by another user"}, status=status.HTTP_400_BAD_REQUEST)
            existing_transaction = Transaction.objects.filter(
                payment_reference__isnull=False,
                house=house,
                user=request.user,
                transaction_type=transaction_type,
                payment_status='PENDING'
            ).first()
            if existing_transaction:
                existing_transaction.delete()
            try:
                payment_response = campay.initCollect({
                    "amount": str(amount),
                    "currency": "XAF",
                    "from": phone_number,
                    "description": f"Payment for {transaction_type} - {house.house_name}",
                    "external_reference": str(house.house_id),
                })
            except Exception as e:
                return Response({'error': f'Failed to initiate payment: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
            reference = payment_response.get('reference')
            if not reference:
                return Response({'error': 'Failed to initiate payment: No reference returned'}, status=status.HTTP_400_BAD_REQUEST)
            transaction = Transaction.objects.create(
                user=request.user,
                house=house,
                amount_paid=amount,
                transaction_type=transaction_type,
                payment_reference=reference,
                payment_status='PENDING',
            )
            return Response({
                'reference': reference,
                'transaction_id': str(transaction.transaction_id),
                'message': 'Payment initiated. Please complete payment via mobile money.'
            }, status=status.HTTP_201_CREATED)
        except House.DoesNotExist:
            return Response({'error': 'House not found'}, status=status.HTTP_404_NOT_FOUND)

class VerifyPaymentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, reference):
        try:
            transaction = Transaction.objects.filter(
                payment_reference=reference,
                user=request.user
            ).order_by('-payment_date').first()
            if not transaction:
                return Response({'error': 'Transaction not found'}, status=status.HTTP_404_NOT_FOUND)
            try:
                payment_data = campay.get_transaction_status({
                    "reference": reference
                })
            except Exception as e:
                return Response({'error': f'Failed to verify payment: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
            transaction_status = payment_data.get('status')
            if not transaction_status:
                return Response({'error': 'Failed to verify payment: No status returned'}, status=status.HTTP_400_BAD_REQUEST)
            transaction.payment_status = transaction_status
            transaction.save()
            if transaction_status == 'SUCCESSFUL':
                if transaction.transaction_type == 'reserve':
                    active_reservation = Reservation.objects.filter(
                        house=transaction.house,
                        is_active=True,
                        expiry_date__gt=timezone.now()
                    ).first()
                    if active_reservation and active_reservation.user != request.user:
                        return Response({"error": "House is reserved by another user"}, status=status.HTTP_400_BAD_REQUEST)
                    reservation = Reservation.objects.create(
                        user=transaction.user,
                        house=transaction.house,
                        is_active=True,
                        expiry_date=timezone.now() + timedelta(days=7)
                    )
                    transaction.house.is_reserved = True
                    transaction.house.save()
                    send_mail(
                        subject="Payment Approved for Your Reservation",
                        message=(
                            f"Dear {transaction.user.username},\n\n"
                            f"Your payment of {transaction.amount_paid} XAF for reservation {reservation.reservation_id} "
                            f"(House: {transaction.house.house_name}) has been approved.\n\n"
                            f"Thank you for booking with StudHome!\n\nBest regards,\nStudHome Team"
                        ),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[transaction.user.email],
                        fail_silently=False,
                    )
                elif transaction.transaction_type == 'tour':
                    send_mail(
                        subject="Payment Approved for Your Tour",
                        message=(
                            f"Dear {transaction.user.username},\n\n"
                            f"Your payment of {transaction.amount_paid} XAF for booking a tour "
                            f"of house '{transaction.house.house_name}' has been approved.\n\n"
                            f"Thank you for using StudHome!\n\nBest regards,\nStudHome Team"
                        ),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[transaction.user.email],
                        fail_silently=False,
                    )
            return Response({
                'status': transaction_status,
                'transaction_id': str(transaction.transaction_id),
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': f'Unexpected error during verification: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PaymentWebhookAPIView(APIView):
    permission_classes = []

    def post(self, request):
        data = request.data
        reference = data.get("reference")
        status_update = data.get("status")
        if not reference or not status_update:
            return Response({"error": "Invalid payload"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            transaction = Transaction.objects.get(payment_reference=reference)
            transaction.payment_status = status_update
            transaction.save()
            if status_update == 'SUCCESSFUL':
                if transaction.transaction_type == 'reserve':
                    reservation = Reservation.objects.create(
                        user=transaction.user,
                        house=transaction.house,
                        is_active=True,
                        expiry_date=timezone.now() + timedelta(days=7)
                    )
                    transaction.house.is_reserved = True
                    transaction.house.save()
                    send_mail(
                        subject="Payment Approved for Your Reservation",
                        message=(
                            f"Dear {transaction.user.username},\n\n"
                            f"Your payment of {transaction.amount_paid} XAF for reservation {reservation.reservation_id} "
                            f"(House: {transaction.house.house_name}) has been approved.\n\n"
                            f"Thank you for booking with StudHome!\n\nBest regards,\nStudHome Team"
                        ),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[transaction.user.email],
                        fail_silently=False,
                    )
                elif transaction.transaction_type == 'tour':
                    send_mail(
                        subject="Payment Approved for Your Tour",
                        message=(
                            f"Dear {transaction.user.username},\n\n"
                            f"Your payment of {transaction.amount_paid} XAF for booking a tour "
                            f"of house '{transaction.house.house_name}' has been approved.\n\n"
                            f"Thank you for using StudHome!\n\nBest regards,\nStudHome Team"
                        ),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[transaction.user.email],
                        fail_silently=False,
                    )
            return Response({"message": "Webhook received"}, status=status.HTTP_200_OK)
        except Transaction.DoesNotExist:
            return Response({"error": "Transaction not found"}, status=status.HTTP_404_NOT_FOUND)

class ChangePasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')

        if not old_password or not new_password:
            return Response(
                {'error': 'Both old_password and new_password are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        if not request.user.check_password(old_password):
            return Response(
                {'error': 'Current password is incorrect'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(new_password) < 8:
            return Response(
                {'error': 'New password must be at least 8 characters long'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        request.user.set_password(new_password)
        request.user.save()

        return Response(
            {'message': 'Password changed successfully'}, 
            status=status.HTTP_200_OK
        )