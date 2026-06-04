from django.contrib import admin

admin.site.site_header = 'Администрирование EngVibe'
admin.site.site_title = 'EngVibe'
admin.site.index_title = 'Панель управления'

from .models import (
    AnswerOption,
    Course,
    CourseEnrollment,
    CourseGroup,
    CourseTest,
    FAQ,
    Flashcard,
    FlashcardGroup,
    Lesson,
    SentenceGameTask,
    NewsletterSubscriber,
    Question,
    Review,
    TariffPlan,
    UserFlashcardProgress,
    UserMatchGameStat,
    UserMatchProgress,
    UserProfile,
    UserSentenceProgress,
    UserSubscription,
    UserSubscriptionCourse,
    WorkStage,
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'city')
    search_fields = ('user__username', 'user__email', 'city')


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'created_at')
    search_fields = ('email',)


@admin.register(CourseGroup)
class CourseGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'tariff_plan', 'created_by', 'order', 'created_at')
    list_filter = ('tariff_plan', 'created_by')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ('courses',)
    raw_id_fields = ('created_by',)


@admin.register(TariffPlan)
class TariffPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'price', 'billing_days', 'access_all', 'max_courses', 'order')
    list_editable = ('order', 'price')


class UserSubscriptionCourseInline(admin.TabularInline):
    model = UserSubscriptionCourse
    extra = 0


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'started_at', 'expires_at', 'is_active')
    list_filter = ('is_active', 'plan')
    search_fields = ('user__username', 'user__email')
    inlines = [UserSubscriptionCourseInline]
    date_hierarchy = 'started_at'


@admin.register(CourseEnrollment)
class CourseEnrollmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'created_at')
    list_filter = ('course',)
    search_fields = ('user__username', 'user__email', 'course__title')
    raw_id_fields = ('user', 'course')


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'level', 'price', 'duration', 'published', 'is_premium', 'order', 'created_at')
    list_filter = ('published', 'is_premium', 'level', 'created_at')
    search_fields = ('title', 'short_description', 'description')
    list_editable = ('order', 'price', 'published')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [LessonInline]


class AnswerOptionInline(admin.TabularInline):
    model = AnswerOption
    extra = 2


@admin.register(CourseTest)
class CourseTestAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order')
    list_filter = ('course',)
    search_fields = ('title', 'course__title')


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'test', 'order')
    list_filter = ('test',)
    search_fields = ('text',)
    inlines = [AnswerOptionInline]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'duration_minutes', 'order')
    list_filter = ('course',)
    search_fields = ('title', 'course__title', 'material')
    fields = (
        'course', 'title', 'description', 'material', 'duration_minutes',
        'video_url', 'exercise_url', 'order',
    )


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('name', 'rating', 'created_at', 'is_published')
    list_filter = ('rating', 'is_published', 'created_at')
    search_fields = ('name', 'text')


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'order')
    list_editable = ('order',)
    search_fields = ('question', 'answer')


@admin.register(WorkStage)
class WorkStageAdmin(admin.ModelAdmin):
    list_display = ('step', 'title', 'order', 'action_url')
    list_editable = ('order',)
    search_fields = ('title', 'description')


class FlashcardInline(admin.TabularInline):
    model = Flashcard
    extra = 3


@admin.register(FlashcardGroup)
class FlashcardGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'level', 'owner', 'order')
    list_filter = ('level', 'owner')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [FlashcardInline]


@admin.register(UserFlashcardProgress)
class UserFlashcardProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'flashcard', 'is_learned', 'learned_at')
    list_filter = ('is_learned',)
    search_fields = ('user__username', 'flashcard__word_en')
    raw_id_fields = ('user', 'flashcard')


@admin.register(UserMatchProgress)
class UserMatchProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'flashcard', 'is_learned', 'learned_at')
    list_filter = ('is_learned',)
    search_fields = ('user__username', 'flashcard__word_en')
    raw_id_fields = ('user', 'flashcard')


@admin.register(UserMatchGameStat)
class UserMatchGameStatAdmin(admin.ModelAdmin):
    list_display = ('user', 'level', 'games_completed')
    list_filter = ('level',)
    search_fields = ('user__username',)


@admin.register(SentenceGameTask)
class SentenceGameTaskAdmin(admin.ModelAdmin):
    list_display = ('sentence_text', 'level', 'order', 'is_published')
    list_filter = ('level', 'is_published')
    search_fields = ('sentence_text',)
    list_editable = ('order', 'is_published')


@admin.register(UserSentenceProgress)
class UserSentenceProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'task', 'is_solved', 'solved_at')
    list_filter = ('is_solved', 'task__level')
    search_fields = ('user__username', 'task__sentence_text')
    raw_id_fields = ('user', 'task')
