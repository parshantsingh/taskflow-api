from celery import shared_task
from django.core.mail import send_mail
from django.utils import timezone
from .models import Task


@shared_task
def send_due_date_reminder(task_id):
    try:
        task = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return f"Task {task_id} no longer exists."

    send_mail(
        subject=f"Reminder: '{task.title}' is due soon",
        message=f"Task '{task.title}' in project '{task.project.name}' is due on {task.due_date}.",
        from_email='noreply@taskflow.local',
        recipient_list=[task.assigned_to.email] if task.assigned_to and task.assigned_to.email else [],
    )
    return f"Reminder sent for task {task_id}"


@shared_task
def check_overdue_tasks():
    overdue = Task.objects.filter(due_date__lt=timezone.now(), status__in=['todo', 'in_progress'])
    for task in overdue:
        send_due_date_reminder.delay(task.id)
    return f"Checked {overdue.count()} overdue tasks"
