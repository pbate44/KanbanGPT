
from PIL import Image as PilImage

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import CardLogEntry, Board


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text="Required. Provide a valid email address.")

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class CardLogEntryForm(forms.ModelForm):
    class Meta:
        model = CardLogEntry
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }


class BoardCreationForm(forms.ModelForm):
    
    class Meta:
        model = Board
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter board name',
                'maxlength': 100,
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Optional board description',
                'rows': 3,
                'maxlength': 500
            }),
        }
        labels = {
            'name': 'Board Name *',
            'description': 'Description'
        }
        help_texts = {
            'description': 'Briefly describe what this board will be used for.'
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        self.fields['name'].widget.attrs.update({
            'autocomplete': 'off',
            'data-validation': 'required'
        })
    
    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        
        if not name:
            raise forms.ValidationError("Board name is required.")
        
        if len(name) < 2:
            raise forms.ValidationError("Board name must be at least 2 characters long.")
        
        if len(name) > 100:
            raise forms.ValidationError("Board name must be less than 100 characters.")
        
        if self.user and Board.objects.filter(owner=self.user, name__iexact=name).exists():
            raise forms.ValidationError("You already have a board with this name.")
        
        return name
    
    def clean_description(self):
        description = self.cleaned_data.get('description', '').strip()
        
        if len(description) > 500:
            raise forms.ValidationError("Description must be less than 500 characters.")
        
        return description
    
    def save(self, commit=True):
        board = super().save(commit=False)
        if self.user:
            board.owner = self.user
        if commit:
            board.save()
        return board


class BoardUpdateForm(forms.ModelForm):
    
    class Meta:
        model = Board
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter board name',
                'maxlength': 100,
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Optional board description',
                'rows': 3,
                'maxlength': 500
            }),
        }
        labels = {
            'name': 'Board Name *',
            'description': 'Description'
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.original_name = kwargs.pop('original_name', None)
        super().__init__(*args, **kwargs)
        
        if self.instance and self.instance.pk:
            self.original_name = self.instance.name
    
    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        
        if not name:
            raise forms.ValidationError("Board name is required.")
        
        if len(name) < 2:
            raise forms.ValidationError("Board name must be at least 2 characters long.")
        
        if len(name) > 100:
            raise forms.ValidationError("Board name must be less than 100 characters.")

        if self.user and name.lower() != (self.original_name or '').lower():
            if Board.objects.filter(owner=self.user, name__iexact=name).exists():
                raise forms.ValidationError("You already have a board with this name.")
        
        return name
    
    def clean_description(self):
        description = self.cleaned_data.get('description', '').strip()
        
        if len(description) > 500:
            raise forms.ValidationError("Description must be less than 500 characters.")
        
        return description


class BoardImageUploadForm(forms.ModelForm):
    
    image = forms.ImageField(
        required=True,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
            'id': 'imageFile'
        }),
        help_text='Supported formats: JPEG, PNG, GIF, WebP. Maximum size: 5MB.'
    )
    
    class Meta:
        model = Board
        fields = ['image']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['image'].label = 'Board Image'
    
    def clean_image(self):
        image = self.cleaned_data.get('image')

        if not image:
            raise forms.ValidationError("Please select an image file.")

        max_size = 5 * 1024 * 1024
        if image.size > max_size:
            raise forms.ValidationError("File size too large. Maximum size is 5MB.")

        allowed_formats = {'JPEG', 'PNG', 'GIF', 'WEBP'}
        try:
            img = PilImage.open(image)
            fmt = img.format
            img.verify()
        except Exception:
            raise forms.ValidationError("File is not a valid image.")
        finally:
            image.seek(0)

        if fmt not in allowed_formats:
            raise forms.ValidationError("Invalid image type. Please upload a JPEG, PNG, GIF, or WebP image.")

        try:
            img = PilImage.open(image)
            width, height = img.size

            min_width, min_height = 200, 150
            if width < min_width or height < min_height:
                raise forms.ValidationError(
                    f"Image too small. Minimum size is {min_width}x{min_height} pixels."
                )

            max_width, max_height = 2000, 2000
            if width > max_width or height > max_height:
                raise forms.ValidationError(
                    f"Image too large. Maximum size is {max_width}x{max_height} pixels."
                )
        except forms.ValidationError:
            raise
        except Exception:
            raise forms.ValidationError("Invalid image file or corrupted image.")
        finally:
            image.seek(0)

        return image


class BoardSearchForm(forms.Form):
    
    SORT_CHOICES = [
        ('updated', 'Recently Updated'),
        ('created', 'Recently Created'),
        ('name', 'Name (A-Z)'),
        ('name_desc', 'Name (Z-A)'),
    ]
    
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search boards...',
            'id': 'boardSearch'
        })
    )
    
    sort_by = forms.ChoiceField(
        choices=SORT_CHOICES,
        required=False,
        initial='updated',
        widget=forms.RadioSelect(attrs={
            'class': 'btn-check'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['search'].label = ''
        self.fields['sort_by'].label = 'Sort by'


class BoardDeleteConfirmationForm(forms.Form):
    
    confirm_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter board name to confirm deletion',
            'id': 'deleteConfirmInput'
        }),
        label='Confirmation'
    )
    
    def __init__(self, board_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.board_name = board_name
        self.fields['confirm_name'].help_text = f'Type "{board_name}" to confirm deletion.'
    
    def clean_confirm_name(self):
        confirm_name = self.cleaned_data.get('confirm_name', '').strip()
        
        if confirm_name != self.board_name:
            raise forms.ValidationError(
                f'Please type "{self.board_name}" exactly to confirm deletion.'
            )
        
        return confirm_name
        

class ContactForm(forms.Form):
    name = forms.CharField(max_length=100)
    email = forms.EmailField()
    subject = forms.CharField(max_length=150)
    message = forms.CharField(widget=forms.Textarea, max_length=5000)