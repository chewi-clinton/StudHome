from django.contrib import admin
from django import forms
from django.utils import timezone
import cloudinary.uploader
from .models import User, House, Reservation, Transaction

class HouseAdminForm(forms.ModelForm):
    image_1 = forms.FileField(
        widget=forms.ClearableFileInput(attrs={'accept': 'image/jpeg,image/png'}),
        required=False,
        label='Image 1 (.jpg/.png)'
    )
    image_2 = forms.FileField(
        widget=forms.ClearableFileInput(attrs={'accept': 'image/jpeg,image/png'}),
        required=False,
        label='Image 2 (.jpg/.png)'
    )
    image_3 = forms.FileField(
        widget=forms.ClearableFileInput(attrs={'accept': 'image/jpeg,image/png'}),
        required=False,
        label='Image 3 (.jpg/.png)'
    )
    image_4 = forms.FileField(
        widget=forms.ClearableFileInput(attrs={'accept': 'image/jpeg,image/png'}),
        required=False,
        label='Image 4 (.jpg/.png)'
    )
    image_5 = forms.FileField(
        widget=forms.ClearableFileInput(attrs={'accept': 'image/jpeg,image/png'}),
        required=False,
        label='Image 5 (.jpg/.png)'
    )
    image_6 = forms.FileField(
        widget=forms.ClearableFileInput(attrs={'accept': 'image/jpeg,image/png'}),
        required=False,
        label='Image 6 (.jpg/.png)'
    )

    model_3d = forms.FileField(
        widget=forms.ClearableFileInput(attrs={'accept': '.glb,.gltf'}),
        required=False,
        label='3D Model (max 1, .glb/.gltf)'
    )

    image_caption_1 = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Caption for Image 1'}),
        required=False,
        label='Image 1 Caption'
    )
    image_caption_2 = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Caption for Image 2'}),
        required=False,
        label='Image 2 Caption'
    )
    image_caption_3 = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Caption for Image 3'}),
        required=False,
        label='Image 3 Caption'
    )
    image_caption_4 = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Caption for Image 4'}),
        required=False,
        label='Image 4 Caption'
    )
    image_caption_5 = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Caption for Image 5'}),
        required=False,
        label='Image 5 Caption'
    )
    image_caption_6 = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Caption for Image 6'}),
        required=False,
        label='Image 6 Caption'
    )
    model_caption = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Caption for 3D model'}),
        required=False,
        label='3D Model Caption'
    )

    class Meta:
        model = House
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
       
        images = [
            cleaned_data.get(f'image_{i}') for i in range(1, 7) if cleaned_data.get(f'image_{i}')
        ]
        model_3d = cleaned_data.get('model_3d')
        current_media = self.instance.media if self.instance.pk else []

        image_count = sum(1 for item in current_media if item.get('media_type') == 'image')
        model_count = sum(1 for item in current_media if item.get('media_type') == '3d_model')

        if image_count + len(images) > 6:
            raise forms.ValidationError("Maximum of 6 images allowed per house.")
        if model_3d and model_count >= 1:
            raise forms.ValidationError("Only one 3D model allowed per house.")

        return cleaned_data

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'phone_number']
    search_fields = ['username', 'email']

@admin.register(House)
class HouseAdmin(admin.ModelAdmin):
    form = HouseAdminForm
    list_display = ['house_name', 'room_type', 'price', 'availability', 'is_reserved', 'remove']
    list_editable = ['remove']
    search_fields = ['house_name']
    list_filter = ['room_type', 'availability', 'is_reserved', 'remove']

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        images = [
            form.cleaned_data.get(f'image_{i}') for i in range(1, 7) if form.cleaned_data.get(f'image_{i}')
        ]
        captions = [
            form.cleaned_data.get(f'image_caption_{i}') for i in range(1, 7)
        ]
        model_3d = form.cleaned_data.get('model_3d')
        model_caption = form.cleaned_data.get('model_caption', '')
        media_list = obj.media or []

        for idx, image in enumerate(images):
            ext = image.name.split('.')[-1].lower()
            if ext not in ['jpg', 'jpeg', 'png']:
                continue  
            upload_result = cloudinary.uploader.upload(image, resource_type='image')
            media_list.append({
                'media_type': 'image',
                'file_url': upload_result['secure_url'],
                'caption': captions[idx] if idx < len(captions) and captions[idx] else '',
                'uploaded_at': timezone.now().isoformat()
            })

        if model_3d:
            ext = model_3d.name.split('.')[-1].lower()
            if ext in ['glb', 'gltf']:
                upload_result = cloudinary.uploader.upload(model_3d, resource_type='raw')
                media_list.append({
                    'media_type': '3d_model',
                    'file_url': upload_result['secure_url'],
                    'caption': model_caption,
                    'uploaded_at': timezone.now().isoformat()
                })

        obj.media = media_list
        obj.save()

    def remove(self, obj):
        return obj.remove
    remove.boolean = True
    remove.short_description = 'Remove from Frontend'

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ['reservation_id', 'user', 'house', 'reservation_date', 'is_active']
    search_fields = ['user__username', 'house__house_name']
    list_filter = ['is_active']

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'user', 'house', 'amount_paid', 'transaction_type']
    search_fields = ['user__username', 'house__house_name']
    list_filter = ['transaction_type']