import re

from django import forms
from django.forms import formset_factory
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group

from .lesson_html import sanitize_lesson_html
from .models import (
    AnswerOption,
    Course,
    CourseGroup,
    CourseTest,
    Flashcard,
    FlashcardGroup,
    Lesson,
    Question,
    Review,
    TariffPlan,
    UserProfile,
)


User = get_user_model()


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True, label='Электронная почта')

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'input-field'})
        self.fields['username'].label = 'Имя пользователя'
        self.fields['password1'].label = 'Пароль'
        self.fields['password2'].label = 'Подтверждение пароля'

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Аккаунт с такой почтой уже зарегистрирован.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            group, _ = Group.objects.get_or_create(name='user_group')
            user.groups.add(group)
        return user


class DemoPaymentForm(forms.Form):
    """Демо-оплата: данные карты не сохраняются и никуда не отправляются."""

    card_number = forms.CharField(
        label='Номер карты',
        max_length=23,
        widget=forms.TextInput(
            attrs={
                'class': 'input-field',
                'placeholder': '0000 0000 0000 0000',
                'inputmode': 'numeric',
                'autocomplete': 'cc-number',
            },
        ),
    )
    card_expiry = forms.CharField(
        label='Срок действия',
        max_length=7,
        widget=forms.TextInput(
            attrs={
                'class': 'input-field',
                'placeholder': 'ММ / ГГ',
                'autocomplete': 'cc-exp',
            },
        ),
    )
    card_cvv = forms.CharField(
        label='CVC / CVV',
        max_length=4,
        widget=forms.PasswordInput(
            attrs={
                'class': 'input-field',
                'placeholder': '•••',
                'autocomplete': 'cc-csc',
            },
        ),
    )
    confirm_purchase = forms.BooleanField(
        label='Я подтверждаю оплату и согласен(на) со списанием указанной суммы',
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'bento-form-check-input'}),
    )

    def clean_card_number(self):
        raw = re.sub(r'\D', '', self.cleaned_data.get('card_number', ''))
        if len(raw) != 16:
            raise forms.ValidationError('Введите 16 цифр номера карты.')
        return raw

    def clean_card_expiry(self):
        raw = self.cleaned_data.get('card_expiry', '').strip().replace(' ', '')
        if not re.match(r'^(0[1-9]|1[0-2])[/\-]?\d{2}$', raw):
            raise forms.ValidationError('Формат: ММ/ГГ, например 12/28.')
        return raw

    def clean_card_cvv(self):
        raw = re.sub(r'\D', '', self.cleaned_data.get('card_cvv', ''))
        if len(raw) not in (3, 4):
            raise forms.ValidationError('CVC: 3 или 4 цифры.')
        return raw


class LoginForm(forms.Form):
    username_or_email = forms.CharField(label='Логин или email')
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'input-field'})

    def clean(self):
        cleaned_data = super().clean()
        username_or_email = cleaned_data.get('username_or_email')
        password = cleaned_data.get('password')

        if not username_or_email or not password:
            return cleaned_data

        username = username_or_email
        if '@' in username_or_email:
            user = User.objects.filter(email__iexact=username_or_email).first()
            if user:
                username = user.username

        user = authenticate(username=username, password=password)
        if user is None:
            raise forms.ValidationError('Неверный логин/email или пароль.')

        cleaned_data['user'] = user
        return cleaned_data


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = (
            'title',
            'slug',
            'level',
            'short_description',
            'description',
            'duration',
            'price',
            'thumbnail',
            'published',
            'is_premium',
            'order',
        )

    def __init__(self, *args, user=None, **kwargs):
        self._user = user
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == 'published':
                field.widget.attrs.update({'class': 'bento-form-check-input'})
            elif name == 'is_premium':
                field.widget.attrs.update({'class': 'bento-form-check-input'})
            elif name == 'thumbnail':
                field.widget = forms.FileInput(
                    attrs={
                        'class': 'image-upload__input',
                        'accept': 'image/*',
                    }
                )
            elif name == 'description':
                field.widget.attrs.update({'class': 'input-field', 'rows': 5})
            else:
                field.widget.attrs.update({'class': 'input-field'})
        if 'price' in self.fields:
            self.fields['price'].help_text = (
                'Цена разовой покупки курса без подписки (демо-оплата на сайте). Доступ к нескольким курсам — только через тарифы.'
            )
        if user is not None:
            is_admin = user.groups.filter(name='admin_group').exists()
            is_teacher_only = user.groups.filter(name='teacher_group').exists() and not is_admin
            if is_teacher_only and 'is_premium' in self.fields:
                del self.fields['is_premium']


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ('course', 'title', 'description', 'material', 'duration_minutes', 'video_url', 'exercise_url', 'order')
        labels = {
            'description': 'Краткое описание (каталог курса)',
            'material': 'Материал урока (конструктор)',
        }
        help_texts = {
            'material': 'Текст, изображения, таблицы, видео YouTube, кнопки и выноски.',
            'description': 'Короткий текст для списка уроков в курсе.',
        }

    def __init__(self, *args, user=None, **kwargs):
        self._user = user
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == 'description':
                field.widget.attrs.update({'class': 'input-field', 'rows': 3})
            elif name == 'material':
                field.widget = forms.Textarea(
                    attrs={
                        'class': 'lesson-editor-field',
                        'rows': 16,
                        'id': 'id_material',
                    }
                )
            else:
                field.widget.attrs.update({'class': 'input-field'})
        if user is not None and not user.groups.filter(name='admin_group').exists():
            self.fields['course'].queryset = Course.objects.filter(teachers=user).distinct()

    def clean_material(self):
        raw = self.cleaned_data.get('material', '')
        return sanitize_lesson_html(raw)


class CourseTestForm(forms.ModelForm):
    class Meta:
        model = CourseTest
        fields = ('course', 'title', 'description', 'order')

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == 'description':
                field.widget.attrs.update({'class': 'input-field', 'rows': 3})
            else:
                field.widget.attrs.update({'class': 'input-field'})
        if user is not None and not user.groups.filter(name='admin_group').exists():
            self.fields['course'].queryset = Course.objects.filter(teachers=user).distinct()


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ('test', 'text', 'order')

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'input-field'})
        if user is not None and not user.groups.filter(name='admin_group').exists():
            self.fields['test'].queryset = CourseTest.objects.filter(course__teachers=user).distinct()


class AnswerOptionForm(forms.ModelForm):
    class Meta:
        model = AnswerOption
        fields = ('question', 'text', 'is_correct')

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'input-field'})
        if user is not None and not user.groups.filter(name='admin_group').exists():
            self.fields['question'].queryset = Question.objects.filter(test__course__teachers=user).distinct()


class StarRatingWidget(forms.Widget):
    template_name = 'core/widgets/star_rating.html'

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        try:
            context['widget']['value'] = int(value) if value not in (None, '') else 5
        except (TypeError, ValueError):
            context['widget']['value'] = 5
        context['widget']['stars'] = range(1, 6)
        return context


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ('text', 'rating')
        labels = {
            'text': 'Текст отзыва',
            'rating': 'Оценка',
        }
        widgets = {
            'text': forms.Textarea(
                attrs={
                    'class': 'reviews-field-input reviews-field-input--area',
                    'rows': 5,
                    'placeholder': 'Например: удобный формат, понятные уроки, поддержка кураторов…',
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        initial_rating = 5
        if self.instance and getattr(self.instance, 'pk', None):
            initial_rating = self.instance.rating or 5
        self.fields['rating'].widget = StarRatingWidget()
        self.fields['rating'].initial = initial_rating


class ProfileForm(forms.ModelForm):
    username = forms.CharField(label='Имя пользователя', max_length=150)
    email = forms.EmailField(label='Электронная почта')

    class Meta:
        model = UserProfile
        fields = ('avatar', 'bio', 'city')

    def __init__(self, *args, user=None, **kwargs):
        self._user = user
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields['username'].initial = user.username
            self.fields['email'].initial = user.email
        for name, field in self.fields.items():
            if name != 'avatar':
                field.widget.attrs.update({'class': 'input-field'})
            else:
                field.widget = forms.FileInput(
                    attrs={
                        'class': 'image-upload__input',
                        'accept': 'image/*',
                    }
                )
        self.fields['bio'].widget.attrs.update({'rows': 4})

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exclude(pk=self._user.pk).exists():
            raise forms.ValidationError('Это имя пользователя уже занято.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email__iexact=email).exclude(pk=self._user.pk).exists():
            raise forms.ValidationError('Этот email уже используется.')
        return email

    def save(self, commit=True):
        profile = super().save(commit=False)
        u = self._user
        u.username = self.cleaned_data['username']
        u.email = self.cleaned_data['email']
        if commit:
            u.save()
            profile.user = u
            profile.save()
        return profile


class UserRoleForm(forms.Form):
    ROLE_CHOICES = (
        ('admin_group', 'Админ'),
        ('teacher_group', 'Преподаватель'),
        ('user_group', 'Ученик'),
    )
    role = forms.ChoiceField(label='Роль пользователя', choices=ROLE_CHOICES)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].widget.attrs.update({'class': 'input-field'})


class QuestionAnswersForm(forms.Form):
    """Один вопрос и до четырёх вариантов ответа внутри общей формы создания теста."""

    text = forms.CharField(
        required=False,
        max_length=500,
        label='Текст вопроса',
        widget=forms.Textarea(attrs={'rows': 2, 'class': 'input-field', 'placeholder': 'Введите формулировку вопроса'}),
    )
    order = forms.IntegerField(
        required=False,
        min_value=1,
        label='Порядок в тесте',
        help_text='Оставьте пустым — проставится по порядку блоков.',
    )
    opt1 = forms.CharField(required=False, max_length=400, label='Вариант A')
    opt2 = forms.CharField(required=False, max_length=400, label='Вариант B')
    opt3 = forms.CharField(required=False, max_length=400, label='Вариант C')
    opt4 = forms.CharField(required=False, max_length=400, label='Вариант D')
    correct_choice = forms.ChoiceField(
        choices=[('1', 'A'), ('2', 'B'), ('3', 'C'), ('4', 'D')],
        widget=forms.RadioSelect,
        required=False,
        label='Правильный вариант',
        initial='1',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == 'text':
                continue
            if name == 'correct_choice':
                field.widget.attrs.update({'class': 'test-compose-radio'})
            else:
                field.widget.attrs.update({'class': 'input-field'})

    def clean(self):
        cd = super().clean()
        text = (cd.get('text') or '').strip()
        if not text:
            return cd

        opts_raw = [cd.get('opt1'), cd.get('opt2'), cd.get('opt3'), cd.get('opt4')]
        opts_stripped = [str(o).strip() if o else '' for o in opts_raw]
        filled_count = sum(1 for o in opts_stripped if o)
        if filled_count < 2:
            raise forms.ValidationError('Нужно минимум два варианта ответа с текстом.')

        correct = cd.get('correct_choice') or '1'
        try:
            ci = int(correct) - 1
        except (TypeError, ValueError):
            raise forms.ValidationError('Укажите корректный правильный вариант.')
        if ci < 0 or ci > 3 or not opts_stripped[ci]:
            raise forms.ValidationError('Правильный вариант должен иметь непустой текст.')

        cd['text'] = text
        cd['opts_stripped'] = opts_stripped
        cd['correct_index'] = ci
        return cd


class BaseQuestionAnswersFormSet(forms.BaseFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        filled = 0
        for form in self.forms:
            cd = form.cleaned_data
            if not cd:
                continue
            if (cd.get('text') or '').strip():
                filled += 1
        if filled < 1:
            raise forms.ValidationError('Добавьте хотя бы один вопрос с вариантами ответов.')


QuestionAnswersFormSet = formset_factory(
    QuestionAnswersForm,
    formset=BaseQuestionAnswersFormSet,
    extra=1,
    min_num=1,
    max_num=100,
    absolute_max=120,
)


class CourseGroupForm(forms.ModelForm):
    class Meta:
        model = CourseGroup
        fields = ('name', 'description', 'tariff_plan', 'courses', 'order')
        labels = {
            'name': 'Название группы',
            'description': 'Описание',
            'tariff_plan': 'Тариф',
            'courses': 'Курсы в группе',
            'order': 'Порядок сортировки',
        }
        help_texts = {
            'courses': 'При выборе группы по тарифу пользователь получит доступ ко всем отмеченным курсам.',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'courses': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, user=None, is_admin_user=False, **kwargs):
        self._user = user
        self._is_admin_user = is_admin_user
        super().__init__(*args, **kwargs)
        from .course_group_utils import available_courses_for_group_form

        for name, field in self.fields.items():
            if name == 'courses':
                continue
            if isinstance(field.widget, forms.CheckboxSelectMultiple):
                continue
            field.widget.attrs.setdefault('class', 'input-field')
        self.fields['tariff_plan'].queryset = TariffPlan.objects.all().order_by('order', 'price')
        if user is not None:
            self.fields['courses'].queryset = available_courses_for_group_form(
                user,
                is_admin_user=is_admin_user,
            )
        else:
            self.fields['courses'].queryset = Course.objects.filter(published=True).order_by('title')

    def clean_courses(self):
        courses = self.cleaned_data.get('courses')
        if not courses:
            raise forms.ValidationError('Выберите хотя бы один курс.')
        return courses


class FlashcardGroupForm(forms.Form):
    name = forms.CharField(
        max_length=120,
        label='Название группы',
        widget=forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Например: Слова с работы'}),
    )


class FlashcardForm(forms.ModelForm):
    class Meta:
        model = Flashcard
        fields = ('word_en', 'word_ru')
        labels = {
            'word_en': 'Слово (англ.)',
            'word_ru': 'Перевод (рус.)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            'word_en': 'hello',
            'word_ru': 'привет',
        }
        for name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'input-field',
                'placeholder': placeholders.get(name, ''),
            })
