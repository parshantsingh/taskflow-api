import anthropic
from django.conf import settings

MODEL = "claude-sonnet-4-5"


def get_client():
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def generate_task_description(title, project_name, existing_context=""):
    """Given a task title, generate a helpful, actionable description."""
    client = get_client()
    prompt = f"""You are helping a software team write clear task descriptions.

Project: {project_name}
Task title: {title}
{f"Additional context: {existing_context}" if existing_context else ""}

Write a concise, actionable 2-3 sentence task description. Include what "done" looks like.
Return ONLY the description text, no preamble, no headers."""

    message = client.messages.create(
        model=MODEL,
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text.strip()


def summarize_project(project_name, tasks_data):
    """Given a list of task dicts, produce a short status summary for standups."""
    client = get_client()
    task_lines = "\n".join(
        f"- [{t['status']}] {t['title']} (priority: {t['priority']})" for t in tasks_data
    )
    prompt = f"""You are a project management assistant. Summarize this project's current state
for a team standup update.

Project: {project_name}

Tasks:
{task_lines}

Write a 3-4 sentence summary covering: overall progress, any blockers or concerning patterns
(e.g. many high-priority tasks stuck in todo), and one suggested focus area.
Return ONLY the summary text, no preamble, no headers."""

    message = client.messages.create(
        model=MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text.strip()


def suggest_priority(title, description):
    """Given a task's title/description, suggest a priority level with reasoning."""
    client = get_client()
    prompt = f"""Classify the priority of this task as exactly one of: low, medium, high.

Title: {title}
Description: {description or "(none provided)"}

Respond in this exact format on two lines:
PRIORITY: <low|medium|high>
REASON: <one sentence reasoning>"""

    message = client.messages.create(
        model=MODEL,
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}]
    )
    text = message.content[0].text.strip()

    priority = "medium"
    reason = ""
    for line in text.split("\n"):
        if line.startswith("PRIORITY:"):
            value = line.replace("PRIORITY:", "").strip().lower()
            if value in ("low", "medium", "high"):
                priority = value
        elif line.startswith("REASON:"):
            reason = line.replace("REASON:", "").strip()

    return priority, reason


def answer_project_question(question, project_name, retrieved_chunks):
    client = get_client()
    context = "\n\n".join(f"- {chunk}" for chunk in retrieved_chunks)
    prompt = f"""You are answering a question about the project "{project_name}" using only the
context below, retrieved from the project's tasks and comments. If the context doesn't contain
enough information to answer, say so honestly rather than guessing.

Context:
{context}

Question: {question}

Give a direct, concise answer grounded in the context above."""

    message = client.messages.create(
        model=MODEL,
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text.strip()