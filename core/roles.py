def is_admin(user):
    return user.is_authenticated and user.groups.filter(name='admin_group').exists()


ROLE_LABELS = {
    'admin_group': 'Админ',
    'teacher_group': 'Преподаватель',
    'user_group': 'Ученик',
}


def role_label(group_name):
    if not group_name:
        return 'без роли'
    return ROLE_LABELS.get(group_name, group_name)


def is_teacher(user):
    return user.is_authenticated and user.groups.filter(name='teacher_group').exists()


def is_student(user):
    return user.is_authenticated and user.groups.filter(name='user_group').exists()


def can_manage_course(user, course):
    return is_admin(user) or (is_teacher(user) and course.teachers.filter(pk=user.pk).exists())


def is_teacher_or_admin(user):
    return is_teacher(user) or is_admin(user)


def can_manage_course_group(user, group):
    """Админ — любая группа; преподаватель — своя или с его курсами."""
    if not user.is_authenticated:
        return False
    if is_admin(user):
        return True
    if not is_teacher(user):
        return False
    if group.created_by_id == user.pk:
        return True
    return group.courses.filter(teachers=user).exists()
