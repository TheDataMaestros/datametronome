"""Tests for user memory Celery tasks."""


def test_tasks_are_registered():
    from datametronome_podium.tasks.user_memory_tasks import (
        extract_user_memories,
        poll_conversations_for_extraction,
        rebuild_user_profile,
    )

    assert poll_conversations_for_extraction.name == "datametronome.poll_conversations_for_extraction"
    assert extract_user_memories.name == "datametronome.extract_user_memories"
    assert rebuild_user_profile.name == "datametronome.rebuild_user_profile"


def test_tasks_appear_in_celery_routes():
    """Verify task names are registered in the Celery task_routes config."""
    from datametronome_podium.core.celery_app import celery_app

    routes = celery_app.conf.task_routes
    assert "datametronome.poll_conversations_for_extraction" in routes
    assert "datametronome.extract_user_memories" in routes
    assert "datametronome.rebuild_user_profile" in routes


def test_beat_schedule_includes_memory_poll():
    """Verify the memory extraction poll is registered in the beat schedule."""
    from datametronome_podium.core.celery_app import celery_app

    schedule = celery_app.conf.beat_schedule
    assert "poll-conversations-for-memory-extraction" in schedule
    entry = schedule["poll-conversations-for-memory-extraction"]
    assert entry["task"] == "datametronome.poll_conversations_for_extraction"
    assert entry["options"]["queue"] == "intelligence.default"
