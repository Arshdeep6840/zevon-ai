"""Unit tests for local SQLite conversation storage and memory repository."""

import pytest

from packages.shared_schemas.models import Role


@pytest.mark.asyncio
async def test_conversation_lifecycle(memory_repo):
    # 1. Create conversation
    conv = await memory_repo.create_conversation(title="Test Project Planning", profile="developer")
    assert conv.id is not None
    assert conv.title == "Test Project Planning"
    assert conv.profile == "developer"

    # 2. Get conversation
    fetched = await memory_repo.get_conversation(conv.id)
    assert fetched is not None
    assert fetched.id == conv.id
    assert fetched.title == conv.title

    # 3. List conversations
    all_convs = await memory_repo.list_conversations()
    assert len(all_convs) >= 1
    assert any(c.id == conv.id for c in all_convs)

    # 4. Update conversation
    updated = await memory_repo.update_conversation(
        conv.id, title="Updated Title", profile="business"
    )
    assert updated.title == "Updated Title"
    assert updated.profile == "business"

    # 5. Delete conversation
    deleted = await memory_repo.delete_conversation(conv.id)
    assert deleted is True

    # 6. Verify non-existent
    assert await memory_repo.get_conversation(conv.id) is None


@pytest.mark.asyncio
async def test_messages_persistence_and_order(memory_repo):
    conv = await memory_repo.create_conversation(title="Chat Session", profile="personal")

    # Add messages
    await memory_repo.add_message(conv.id, Role.USER, "Hello Zevon")
    await memory_repo.add_message(conv.id, Role.ASSISTANT, "Hello! How can I help you today?")
    await memory_repo.add_message(conv.id, Role.USER, "What can you do?")

    messages = await memory_repo.get_messages(conv.id)
    assert len(messages) == 3
    assert messages[0].content == "Hello Zevon"
    assert messages[0].role == Role.USER
    assert messages[1].content == "Hello! How can I help you today?"
    assert messages[1].role == Role.ASSISTANT
    assert messages[2].content == "What can you do?"

    # Verify export format
    exported = await memory_repo.export_conversation(conv.id)
    assert exported is not None
    assert exported["conversation"]["id"] == conv.id
    assert len(exported["messages"]) == 3


@pytest.mark.asyncio
async def test_settings_storage(memory_repo):
    # Test default
    assert await memory_repo.get_setting("non_existent", "default_val") == "default_val"

    # Test set and get
    await memory_repo.set_setting("active_theme", "cyberpunk")
    assert await memory_repo.get_setting("active_theme") == "cyberpunk"

    # Test upsert overwrite
    await memory_repo.set_setting("active_theme", "light")
    assert await memory_repo.get_setting("active_theme") == "light"

    all_settings = await memory_repo.get_all_settings()
    assert all_settings.get("active_theme") == "light"


@pytest.mark.asyncio
async def test_clear_all_conversations(memory_repo):
    c1 = await memory_repo.create_conversation("Chat 1")
    c2 = await memory_repo.create_conversation("Chat 2")
    await memory_repo.add_message(c1.id, Role.USER, "Message 1")
    await memory_repo.add_message(c2.id, Role.USER, "Message 2")

    cleared = await memory_repo.clear_all_conversations()
    assert cleared == 2
    assert len(await memory_repo.list_conversations()) == 0
