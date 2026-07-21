import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from projects.models import Project, ProjectMembership
from tasks.models import Task, Comment

User = get_user_model()

DEMO_USERS = [
    {'username': 'alice', 'email': 'alice@demo.taskflow.local'},
    {'username': 'bob', 'email': 'bob@demo.taskflow.local'},
    {'username': 'carol', 'email': 'carol@demo.taskflow.local'},
]

TASK_TITLES = [
    "Set up CI pipeline", "Fix login redirect bug", "Design onboarding flow",
    "Write API documentation", "Optimize database queries", "Add dark mode support",
    "Migrate to new payment provider", "Fix memory leak in worker process",
    "Implement rate limiting", "Add export to PDF feature", "Refactor auth middleware",
    "Set up error monitoring", "Improve test coverage", "Add multi-language support",
    "Fix flaky integration tests",
]

COMMENTS = [
    "Started looking into this, will update soon.",
    "Blocked on the API key from the vendor.",
    "This looks good — approved from my side.",
    "Can we get a second review on this before merging?",
    "Ran into an edge case, investigating further.",
]


class Command(BaseCommand):
    help = "Seeds the database with a realistic demo project, users, tasks, and comments."

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Delete existing demo data before seeding.')

    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write("Removing existing demo users and their data...")
            User.objects.filter(username__in=[u['username'] for u in DEMO_USERS]).delete()

        self.stdout.write("Creating demo users...")
        users = []
        for u in DEMO_USERS:
            user, created = User.objects.get_or_create(
                username=u['username'], defaults={'email': u['email']}
            )
            if created:
                user.set_password('demopass123')
                user.save()
            users.append(user)

        self.stdout.write("Creating demo project...")
        project, _ = Project.objects.get_or_create(
            name="TaskFlow Demo — Website Relaunch",
            defaults={'owner': users[0], 'description': "Demo project showcasing TaskFlow's full feature set."}
        )

        roles = ['owner', 'admin', 'member']
        for user, role in zip(users, roles):
            ProjectMembership.objects.get_or_create(project=project, user=user, defaults={'role': role})

        self.stdout.write("Creating demo tasks...")
        statuses = ['todo', 'in_progress', 'done']
        priorities = ['low', 'medium', 'high']
        created_tasks = []

        for title in TASK_TITLES:
            task, created = Task.objects.get_or_create(
                project=project, title=title,
                defaults={
                    'description': f"Demo task: {title.lower()}.",
                    'status': random.choice(statuses),
                    'priority': random.choice(priorities),
                    'assigned_to': random.choice(users),
                    'due_date': timezone.now() + timedelta(days=random.randint(-5, 20)),
                }
            )
            created_tasks.append(task)

        self.stdout.write("Adding demo comments...")
        for task in random.sample(created_tasks, k=min(8, len(created_tasks))):
            Comment.objects.get_or_create(
                task=task, author=random.choice(users),
                defaults={'body': random.choice(COMMENTS)}
            )

        self.stdout.write(self.style.SUCCESS(
            f"\nDemo data ready:\n"
            f"  Project: {project.name} (id={project.id})\n"
            f"  Users: {', '.join(u.username for u in users)} (password: demopass123)\n"
            f"  Tasks: {len(created_tasks)}\n"
        ))
