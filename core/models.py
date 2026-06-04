from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    class Meta:
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='Пользователь',
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        verbose_name='Аватар',
    )
    bio = models.TextField(blank=True, verbose_name='О себе')
    city = models.CharField(max_length=120, blank=True, verbose_name='Город')

    def __str__(self):
        return f'Профиль: {self.user.username}'


class NewsletterSubscriber(models.Model):
    class Meta:
        verbose_name = 'Подписчик на рассылку'
        verbose_name_plural = 'Подписчики на рассылку'
        ordering = ['-created_at']

    email = models.EmailField(unique=True, verbose_name='Электронная почта')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата подписки')

    def __str__(self):
        return self.email


class Course(models.Model):
    class Meta:
        verbose_name = 'Курс'
        verbose_name_plural = 'Курсы'
        ordering = ['order', '-created_at']

    title = models.CharField(max_length=255, verbose_name='Название')
    slug = models.SlugField(unique=True, verbose_name='URL-идентификатор (slug)')
    level = models.CharField(max_length=50, default='A1-A2', verbose_name='Уровень')
    short_description = models.CharField(max_length=300, verbose_name='Краткое описание')
    description = models.TextField(verbose_name='Полное описание')
    duration = models.CharField(max_length=80, verbose_name='Длительность (текст)')
    price = models.PositiveIntegerField(
        default=1500,
        verbose_name='Цена (₽)',
        help_text='Справочная цена разовой покупки курса',
    )
    thumbnail = models.ImageField(
        upload_to='courses/',
        blank=True,
        null=True,
        verbose_name='Превью',
    )
    published = models.BooleanField(default=True, verbose_name='Опубликован')
    is_premium = models.BooleanField(default=False, verbose_name='Премиум-курс')
    teachers = models.ManyToManyField(
        User,
        blank=True,
        related_name='teaching_courses',
        verbose_name='Преподаватели',
    )
    order = models.PositiveIntegerField(default=1, verbose_name='Порядок сортировки')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')

    def __str__(self):
        return self.title


class Lesson(models.Model):
    class Meta:
        verbose_name = 'Урок'
        verbose_name_plural = 'Уроки'
        ordering = ['order']

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='lessons',
        verbose_name='Курс',
    )
    title = models.CharField(max_length=255, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Краткое описание (для каталога)')
    material = models.TextField(
        blank=True,
        verbose_name='Материал урока',
        help_text='HTML-контент: текст, изображения, таблицы, видео, кнопки (редактор конструктора).',
    )
    duration_minutes = models.PositiveIntegerField(default=10, verbose_name='Длительность, мин.')
    video_url = models.URLField(blank=True, verbose_name='Ссылка на видео')
    exercise_url = models.URLField(blank=True, verbose_name='Ссылка на упражнение')
    order = models.PositiveIntegerField(default=1, verbose_name='Порядок в курсе')

    def __str__(self):
        return f'{self.course.title} — {self.title}'


class CourseTest(models.Model):
    class Meta:
        verbose_name = 'Тест курса'
        verbose_name_plural = 'Тесты курсов'
        ordering = ['order']

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='tests',
        verbose_name='Курс',
    )
    title = models.CharField(max_length=255, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    order = models.PositiveIntegerField(default=1, verbose_name='Порядок')

    def __str__(self):
        return self.title


class Question(models.Model):
    class Meta:
        verbose_name = 'Вопрос'
        verbose_name_plural = 'Вопросы'
        ordering = ['order']

    test = models.ForeignKey(
        CourseTest,
        on_delete=models.CASCADE,
        related_name='questions',
        verbose_name='Тест',
    )
    text = models.CharField(max_length=500, verbose_name='Текст вопроса')
    order = models.PositiveIntegerField(default=1, verbose_name='Порядок')

    def __str__(self):
        return self.text


class AnswerOption(models.Model):
    class Meta:
        verbose_name = 'Вариант ответа'
        verbose_name_plural = 'Варианты ответов'

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='options',
        verbose_name='Вопрос',
    )
    text = models.CharField(max_length=400, verbose_name='Текст варианта')
    is_correct = models.BooleanField(default=False, verbose_name='Верный ответ')

    def __str__(self):
        return self.text


class Review(models.Model):
    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ['-created_at']

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='reviews',
        verbose_name='Пользователь',
    )
    name = models.CharField(max_length=120, verbose_name='Имя в отзыве')
    text = models.TextField(verbose_name='Текст отзыва')
    rating = models.PositiveSmallIntegerField(default=5, verbose_name='Оценка')
    created_at = models.DateField(auto_now_add=True, verbose_name='Дата')
    is_published = models.BooleanField(default=True, verbose_name='Опубликован')

    def __str__(self):
        return f'{self.name} ({self.rating}/5)'

    @property
    def author_avatar_url(self):
        """URL аватара автора из профиля, если есть пользователь и загруженный аватар."""
        if not self.user_id:
            return None
        try:
            avatar = self.user.profile.avatar
        except UserProfile.DoesNotExist:
            return None
        if avatar:
            return avatar.url
        return None


class CourseEnrollment(models.Model):
    class Meta:
        verbose_name = 'Запись на курс'
        verbose_name_plural = 'Записи на курсы'
        unique_together = ('user', 'course')
        ordering = ['-created_at']

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='course_enrollments',
        verbose_name='Пользователь',
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='enrollments',
        verbose_name='Курс',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата записи')

    def __str__(self):
        return f'{self.user.username} → {self.course.title}'


class UserLessonProgress(models.Model):
    class Meta:
        verbose_name = 'Прогресс по уроку'
        verbose_name_plural = 'Прогресс по урокам'
        unique_together = ('user', 'lesson')
        ordering = ['-completed_at']

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='lesson_progress',
        verbose_name='Пользователь',
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='progress_records',
        verbose_name='Урок',
    )
    is_completed = models.BooleanField(default=False, verbose_name='Завершён')
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name='Дата завершения')
    score = models.PositiveSmallIntegerField(default=0, verbose_name='Баллы')

    def __str__(self):
        return f'{self.user.username} — {self.lesson.title}'


class UserTestResult(models.Model):
    class Meta:
        verbose_name = 'Результат теста'
        verbose_name_plural = 'Результаты тестов'
        ordering = ['-completed_at']

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='test_results',
        verbose_name='Пользователь',
    )
    test = models.ForeignKey(
        CourseTest,
        on_delete=models.CASCADE,
        related_name='results',
        verbose_name='Тест',
    )
    score = models.PositiveIntegerField(default=0, verbose_name='Результат (%)')
    total_questions = models.PositiveIntegerField(default=0, verbose_name='Всего вопросов')
    correct_answers = models.PositiveIntegerField(default=0, verbose_name='Верных ответов')
    completed_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата прохождения')

    def __str__(self):
        return f'{self.user.username} — {self.test.title} ({self.correct_answers}/{self.total_questions})'


class TariffPlan(models.Model):
    class Meta:
        verbose_name = 'Тарифный план'
        verbose_name_plural = 'Тарифные планы'
        ordering = ['order', 'price']

    slug = models.SlugField(unique=True, verbose_name='Код (slug)')
    name = models.CharField(max_length=120, verbose_name='Название')
    price = models.PositiveIntegerField(
        verbose_name='Цена (₽)',
        help_text='Цена в рублях за период',
    )
    billing_days = models.PositiveIntegerField(
        verbose_name='Период (дней)',
        help_text='Длительность подписки в днях',
    )
    access_all = models.BooleanField(
        default=False,
        verbose_name='Доступ ко всем курсам',
        help_text='Если да — без лимита по числу курсов',
    )
    max_courses = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name='Макс. число курсов',
        help_text='Для базового тарифа: сколько курсов можно выбрать; пусто, если доступ ко всем',
    )
    tagline = models.CharField(max_length=255, blank=True, verbose_name='Краткий слоган')
    perks = models.TextField(
        blank=True,
        verbose_name='Преимущества',
        help_text='По одному пункту на строку',
    )
    order = models.PositiveSmallIntegerField(default=0, verbose_name='Порядок')

    def __str__(self):
        return self.name


class CourseGroup(models.Model):
    class Meta:
        verbose_name = 'Группа курсов'
        verbose_name_plural = 'Группы курсов'
        ordering = ['order', 'name']

    name = models.CharField(max_length=255, verbose_name='Название')
    slug = models.SlugField(max_length=80, unique=True, verbose_name='URL-идентификатор (slug)')
    description = models.TextField(blank=True, verbose_name='Описание')
    courses = models.ManyToManyField(
        Course,
        blank=True,
        related_name='course_groups',
        verbose_name='Курсы',
    )
    tariff_plan = models.ForeignKey(
        TariffPlan,
        on_delete=models.PROTECT,
        related_name='course_groups',
        verbose_name='Тариф',
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_course_groups',
        verbose_name='Создал',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создана')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')

    def __str__(self):
        return self.name


class UserSubscription(models.Model):
    class Meta:
        verbose_name = 'Подписка пользователя'
        verbose_name_plural = 'Подписки пользователей'
        ordering = ['-started_at']

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name='Пользователь',
    )
    plan = models.ForeignKey(
        TariffPlan,
        on_delete=models.PROTECT,
        related_name='subscriptions',
        verbose_name='Тариф',
    )
    course_group = models.ForeignKey(
        CourseGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subscriptions',
        verbose_name='Группа курсов',
        help_text='Выбранная при оформлении подписки; сохраняется для истории, если группу удалят.',
    )
    started_at = models.DateTimeField(auto_now_add=True, verbose_name='Начало')
    expires_at = models.DateTimeField(verbose_name='Окончание')
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    setup_completed = models.BooleanField(
        default=False,
        verbose_name='Выбор курсов завершён',
        help_text='Пользователь выбрал группу или набор курсов при оформлении подписки.',
    )

    def __str__(self):
        return f'{self.user.username} — {self.plan.slug} до {self.expires_at.date()}'


class UserSubscriptionCourse(models.Model):
    class Meta:
        verbose_name = 'Курс в подписке'
        verbose_name_plural = 'Курсы в подписках'
        unique_together = ('subscription', 'course')

    subscription = models.ForeignKey(
        UserSubscription,
        on_delete=models.CASCADE,
        related_name='picked_courses',
        verbose_name='Подписка',
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='subscription_picks',
        verbose_name='Курс',
    )


class FAQ(models.Model):
    class Meta:
        verbose_name = 'Вопрос и ответ (FAQ)'
        verbose_name_plural = 'Вопросы и ответы (FAQ)'
        ordering = ['order']

    question = models.CharField(max_length=300, verbose_name='Вопрос')
    answer = models.TextField(verbose_name='Ответ')
    order = models.PositiveIntegerField(default=1, verbose_name='Порядок')

    def __str__(self):
        return self.question


class WorkStage(models.Model):
    class Meta:
        verbose_name = 'Этап «Как это работает»'
        verbose_name_plural = 'Этапы «Как это работает»'
        ordering = ['order']

    step = models.PositiveIntegerField(default=1, verbose_name='Номер шага')
    title = models.CharField(max_length=200, verbose_name='Заголовок')
    icon = models.ImageField(upload_to='stages/', blank=True, null=True, verbose_name='Иконка')
    description = models.TextField(verbose_name='Описание')
    action_url = models.URLField(blank=True, verbose_name='Ссылка действия')
    order = models.PositiveIntegerField(default=1, verbose_name='Порядок')

    def __str__(self):
        return self.title


FLASHCARD_LEVELS = (
    ('A1', 'A1'),
    ('A2', 'A2'),
    ('B1', 'B1'),
    ('B2', 'B2'),
    ('C1', 'C1'),
    ('C2', 'C2'),
)


class FlashcardGroup(models.Model):
    class Meta:
        verbose_name = 'Группа карточек'
        verbose_name_plural = 'Группы карточек'
        ordering = ['order', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['slug'],
                condition=models.Q(owner__isnull=True),
                name='unique_default_flashcard_group_slug',
            ),
            models.UniqueConstraint(
                fields=['owner', 'slug'],
                condition=models.Q(owner__isnull=False),
                name='unique_user_flashcard_group_slug',
            ),
        ]

    name = models.CharField(max_length=120, verbose_name='Название')
    slug = models.SlugField(max_length=80, verbose_name='URL-идентификатор (slug)')
    level = models.CharField(
        max_length=2,
        choices=FLASHCARD_LEVELS,
        blank=True,
        verbose_name='Уровень',
        help_text='Для стандартных групп по уровням CEFR',
    )
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='flashcard_groups',
        verbose_name='Владелец',
        help_text='Пусто — стандартная группа сайта',
    )
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')

    def __str__(self):
        return self.name

    @property
    def is_default(self):
        return self.owner_id is None


class Flashcard(models.Model):
    class Meta:
        verbose_name = 'Карточка'
        verbose_name_plural = 'Карточки'
        ordering = ['order', 'id']

    group = models.ForeignKey(
        FlashcardGroup,
        on_delete=models.CASCADE,
        related_name='cards',
        verbose_name='Группа',
    )
    word_en = models.CharField(max_length=200, verbose_name='Слово (EN)')
    word_ru = models.CharField(max_length=200, verbose_name='Перевод (RU)')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')

    def __str__(self):
        return f'{self.word_en} — {self.word_ru}'


class UserMatchProgress(models.Model):
    class Meta:
        verbose_name = 'Прогресс «Сопоставь слова»'
        verbose_name_plural = 'Прогресс «Сопоставь слова»'
        unique_together = ('user', 'flashcard')
        ordering = ['-learned_at']

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='match_progress',
        verbose_name='Пользователь',
    )
    flashcard = models.ForeignKey(
        Flashcard,
        on_delete=models.CASCADE,
        related_name='match_progress_records',
        verbose_name='Слово',
    )
    is_learned = models.BooleanField(default=False, verbose_name='Изучено')
    learned_at = models.DateTimeField(blank=True, null=True, verbose_name='Дата изучения')

    def __str__(self):
        status = 'изучено' if self.is_learned else 'не изучено'
        return f'{self.user.username} — {self.flashcard.word_en} ({status})'


class UserMatchGameStat(models.Model):
    class Meta:
        verbose_name = 'Статистика игр «Сопоставь слова»'
        verbose_name_plural = 'Статистика игр «Сопоставь слова»'
        unique_together = ('user', 'level')
        ordering = ['level']

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='match_game_stats',
        verbose_name='Пользователь',
    )
    level = models.CharField(
        max_length=2,
        choices=FLASHCARD_LEVELS,
        verbose_name='Уровень',
    )
    games_completed = models.PositiveIntegerField(default=0, verbose_name='Игр завершено')

    def __str__(self):
        return f'{self.user.username} — {self.level}: {self.games_completed} игр'


class UserFlashcardProgress(models.Model):
    class Meta:
        verbose_name = 'Прогресс по карточке'
        verbose_name_plural = 'Прогресс по карточкам'
        unique_together = ('user', 'flashcard')
        ordering = ['-learned_at']

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='flashcard_progress',
        verbose_name='Пользователь',
    )
    flashcard = models.ForeignKey(
        Flashcard,
        on_delete=models.CASCADE,
        related_name='progress_records',
        verbose_name='Карточка',
    )
    is_learned = models.BooleanField(default=False, verbose_name='Выучено')
    learned_at = models.DateTimeField(blank=True, null=True, verbose_name='Дата изучения')

    def __str__(self):
        status = 'выучено' if self.is_learned else 'в процессе'
        return f'{self.user.username} — {self.flashcard.word_en} ({status})'


SENTENCE_LEVELS = (
    ('beginner', 'Начальный (A1–A2)'),
    ('intermediate', 'Средний (B1–B2)'),
    ('advanced', 'Продвинутый (C1–C2)'),
)


class SentenceGameTask(models.Model):
    class Meta:
        verbose_name = 'Задание «Составь предложение»'
        verbose_name_plural = 'Задания «Составь предложение»'
        ordering = ['level', 'order', 'id']

    level = models.CharField(
        max_length=20,
        choices=SENTENCE_LEVELS,
        verbose_name='Уровень',
    )
    sentence_text = models.CharField(
        max_length=500,
        verbose_name='Предложение',
        help_text='Полный текст, например: The cat is sleeping.',
    )
    correct_order = models.JSONField(
        verbose_name='Слова по порядку',
        help_text='Список слов в правильном порядке, например: ["The", "cat", "is", "sleeping."]',
    )
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')
    is_published = models.BooleanField(default=True, verbose_name='Опубликовано')

    def __str__(self):
        return f'{self.get_level_display()}: {self.sentence_text[:60]}'


class UserSentenceProgress(models.Model):
    class Meta:
        verbose_name = 'Прогресс по предложению'
        verbose_name_plural = 'Прогресс по предложениям'
        unique_together = ('user', 'task')
        ordering = ['-solved_at']

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sentence_progress',
        verbose_name='Пользователь',
    )
    task = models.ForeignKey(
        SentenceGameTask,
        on_delete=models.CASCADE,
        related_name='progress_records',
        verbose_name='Задание',
    )
    is_solved = models.BooleanField(default=False, verbose_name='Решено')
    solved_at = models.DateTimeField(blank=True, null=True, verbose_name='Дата решения')

    def __str__(self):
        status = 'решено' if self.is_solved else 'не решено'
        return f'{self.user.username} — {self.task.sentence_text[:40]} ({status})'
