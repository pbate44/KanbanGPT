"""
Shared pytest fixtures for KanbanGPT tests.

Fixtures are available to all test files automatically.
Import them by name in any test function — pytest injects them.
"""

import pytest
from django.contrib.auth.models import User
from frontend.models import Board, Column, Card, Swimlane, Subtask, UserProfile


# ── Users ─────────────────────────────────────────────────────────────────────

@pytest.fixture
def user(db):
    """A basic authenticated user. UserProfile is created automatically via signal."""
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpassword123",
    )


@pytest.fixture
def user_profile(user):
    """The UserProfile associated with the test user."""
    return user.profile


@pytest.fixture
def other_user(db):
    """A second user — useful for testing permission boundaries."""
    return User.objects.create_user(
        username="otheruser",
        email="other@example.com",
        password="otherpassword123",
    )


# ── Authenticated client ───────────────────────────────────────────────────────

@pytest.fixture
def auth_client(client, user):
    """Django test client pre-logged-in as `user`."""
    client.force_login(user)
    return client


# ── Board hierarchy ────────────────────────────────────────────────────────────

@pytest.fixture
def board(user):
    """A board owned by `user`."""
    return Board.objects.create(name="Test Board", owner=user)


@pytest.fixture
def column(board):
    """A column inside `board`."""
    return Column.objects.create(name="To Do", board=board, position=0)


@pytest.fixture
def card(column):
    """A card inside `column`."""
    return Card.objects.create(
        title="Test Card",
        column=column,
        position=0,
    )


@pytest.fixture
def swimlane(board):
    """A swimlane inside `board`."""
    return Swimlane.objects.create(name="Test Lane", board=board, position=0)


@pytest.fixture
def subtask(card):
    """A subtask on `card`."""
    return Subtask.objects.create(title="Test Subtask", card=card)
