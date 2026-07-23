from django import forms
from django.utils import timezone
from django.core.files.uploadedfile import UploadedFile

from .models import Book, UserProfile


ALLOWED_EMAIL_DOMAIN = "@ecs.osaka-u.ac.jp"


class EcsUserCreationForm(forms.Form):
    display_name = forms.CharField(label="名前", max_length=80)
    email = forms.EmailField(label="大阪大学 ECS メール")
    password1 = forms.CharField(label="パスワード", widget=forms.PasswordInput, min_length=8)
    password2 = forms.CharField(label="パスワード確認", widget=forms.PasswordInput, min_length=8)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if not email.endswith(ALLOWED_EMAIL_DOMAIN):
            raise forms.ValidationError("@ecs.osaka-u.ac.jp のメールアドレスのみ登録できます。")
        return email

    def clean_display_name(self):
        display_name = self.cleaned_data["display_name"].strip()
        if not display_name:
            raise forms.ValidationError("名前を入力してください。")
        return display_name

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
    display_name = forms.CharField(label="名前", max_length=80)
    school_year = forms.ChoiceField(
        label="学年",
        choices=[("", "学年を選択してください"), *((f"{year}年", f"{year}年") for year in range(1, 7))],
        widget=forms.Select(attrs={"class": "form-control"}),
        error_messages={
            "required": "学年を選択してください。",
            "invalid_choice": "一覧から正しい学年を選択してください。",
        },
    )
    faculty_group = forms.ChoiceField(
        label="学部",
        choices=[("", "学部を選択してください"), *((name, name) for name in UserProfile.FACULTY_DEPARTMENTS)],
        widget=forms.Select(attrs={"class": "form-control"}),
        error_messages={
            "required": "学部を選択してください。",
            "invalid_choice": "一覧から正しい学部を選択してください。",
        },
    )
    department = forms.ChoiceField(
        label="学科",
        choices=[
            ("", "学科を選択してください"),
            *(
                (department, department)
                for departments in UserProfile.FACULTY_DEPARTMENTS.values()
                for department in departments
            ),
        ],
        widget=forms.Select(attrs={"class": "form-control"}),
        error_messages={
            "required": "学科を選択してください。",
            "invalid_choice": "一覧から正しい学科を選択してください。",
        },
    )

    class Meta:
        model = UserProfile
        fields = ("display_name", "school_year")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        combined_value = self.instance.faculty if self.instance and self.instance.pk else ""
        for faculty, departments in UserProfile.FACULTY_DEPARTMENTS.items():
            for department in departments:
                if combined_value == f"{faculty} {department}":
                    self.fields["faculty_group"].initial = faculty
                    self.fields["department"].initial = department
                    return

    def clean_display_name(self):
        return self.cleaned_data["display_name"].strip()

    def clean(self):
        cleaned_data = super().clean()
        faculty = cleaned_data.get("faculty_group")
        department = cleaned_data.get("department")
        if faculty and department and department not in UserProfile.FACULTY_DEPARTMENTS.get(faculty, []):
            self.add_error("department", "選択した学部に所属する学科を選択してください。")
        return cleaned_data

    def save(self, commit=True):
        self.instance.faculty = f"{self.cleaned_data['faculty_group']} {self.cleaned_data['department']}"
        return super().save(commit=commit)


class MessageForm(forms.Form):
    content = forms.CharField(
        label="メッセージ",
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "購入相談の内容を入力"}),
        max_length=1000,
    )


class TradeOfferForm(forms.Form):
    price = forms.IntegerField(label="取引価格", min_value=0, max_value=1_000_000)


class HandoffProposalForm(forms.Form):
    handoff_at = forms.DateTimeField(
        label="受け渡し日時",
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
    )
    location = forms.CharField(label="受け渡し場所", max_length=200)

    def clean_handoff_at(self):
        handoff_at = self.cleaned_data["handoff_at"]
        if handoff_at <= timezone.now():
            raise forms.ValidationError("現在より後の日時を指定してください。")
        return handoff_at

    def clean_location(self):
        return self.cleaned_data["location"].strip()
