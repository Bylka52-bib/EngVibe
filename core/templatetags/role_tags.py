from django import template

from core.roles import role_label

register = template.Library()


@register.filter
def user_role(user):
    group = user.groups.first()
    return role_label(group.name if group else None)
