from django import forms
from django.core.files.uploadedfile import UploadedFile

from .models import Book, UserProfile


ALLOWED_EMAIL_DOMAIN = "@ecs.osaka-u.ac.jp"


class EcsUserCreationForm(forms.Form):
    email = forms.EmailField(label="大阪大学 ECS メール")
    password1 = forms.CharField(label="パスワード", widget=forms.PasswordInput, min_length=8)
    password2 = forms.CharField(label="パスワード確認", widget=forms.PasswordInput, min_length=8)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if not email.endswith(ALLOWED_EMAIL_DOMAIN):
            raise forms.ValidationError("@ecs.osaka-u.ac.jp のメールアドレスのみ登録できます。")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("確認用パスワードが一致しません。")
        return cleaned_data


class EcsLoginForm(forms.Form):
    email = forms.EmailField(label="大阪大学 ECS メール")
    password = forms.CharField(label="パスワード", widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if not email.endswith(ALLOWED_EMAIL_DOMAIN):
            raise forms.ValidationError("@ecs.osaka-u.ac.jp のメールアドレスのみログインできます。")
        return email


def validate_uploaded_image(uploaded_file):
    if not uploaded_file or not isinstance(uploaded_file, UploadedFile):
        return uploaded_file

    max_size = 5 * 1024 * 1024
    if uploaded_file.size > max_size:
        raise forms.ValidationError("画像サイズは5MB以下にしてください。")

    position = uploaded_file.tell()
    header = uploaded_file.read(16)
    uploaded_file.seek(position)
    image_signatures = (
        b"\xff\xd8\xff",
        b"\x89PNG\r\n\x1a\n",
        b"GIF87a",
        b"GIF89a",
        b"RIFF",
    )
    if not header.startswith(image_signatures):
        raise forms.ValidationError("画像ファイル（jpg/png/gif/webp）を選択してください。")
    return uploaded_file


class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = (
            "title",
            "author",
            "price",
            "category",
            "campus",
            "condition",
            "description",
            "image",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def clean_image(self):
        return validate_uploaded_image(self.cleaned_data.get("image"))


class BookEditForm(BookForm):
    class Meta(BookForm.Meta):
        fields = BookForm.Meta.fields + ("status",)


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ("display_name", "faculty", "school_year")


class MessageForm(forms.Form):
    content = forms.CharField(
        label="メッセージ",
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "購入相談の内容を入力"}),
        max_length=1000,
    )
