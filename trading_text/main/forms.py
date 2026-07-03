from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from .models import Book, ChatMessage, Profile, Transaction


OSAKA_EMAIL_DOMAIN = "@osaka-u.ac.jp"


class OsakaEmailMixin:
    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if not email.endswith(OSAKA_EMAIL_DOMAIN):
            raise forms.ValidationError("大阪大学メール（@osaka-u.ac.jp）のみ利用できます。")
        return email


class SignupForm(OsakaEmailMixin, forms.Form):
    display_name = forms.CharField(label="表示名", max_length=80)
    email = forms.EmailField(label="大阪大学メール")
    department = forms.CharField(label="所属", max_length=120, required=False)
    year = forms.IntegerField(label="学年", min_value=1, max_value=8, required=False)
    password = forms.CharField(label="パスワード", widget=forms.PasswordInput)

    def clean_email(self):
        email = super().clean_email()
        if User.objects.filter(username=email).exists():
            raise forms.ValidationError("このメールアドレスは登録済みです。")
        return email

    def save(self):
        user = User.objects.create_user(
            username=self.cleaned_data["email"],
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password"],
            first_name=self.cleaned_data["display_name"],
        )
        Profile.objects.create(
            user=user,
            display_name=self.cleaned_data["display_name"],
            department=self.cleaned_data.get("department", ""),
            year=self.cleaned_data.get("year"),
        )
        return user


class LoginForm(OsakaEmailMixin, forms.Form):
    email = forms.EmailField(label="大阪大学メール")
    password = forms.CharField(label="パスワード", widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        password = cleaned_data.get("password")
        if not email or not password:
            return cleaned_data

        user = authenticate(username=email, password=password)
        if user is None:
            raise forms.ValidationError("メールアドレスまたはパスワードが正しくありません。")

        cleaned_data["user"] = user
        return cleaned_data


class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ["title", "author", "price", "category", "campus", "condition", "description"]


class ScheduleForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ["scheduled_at", "meeting_place"]
        widgets = {
            "scheduled_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


class ChatMessageForm(forms.ModelForm):
    class Meta:
        model = ChatMessage
        fields = ["body"]
        widgets = {
            "body": forms.Textarea(attrs={"rows": 3, "placeholder": "メッセージを入力"}),
        }
