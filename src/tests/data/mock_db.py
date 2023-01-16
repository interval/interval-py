from datetime import datetime
from typing import Optional, TypedDict
import re
from uuid import UUID

from faker import Faker


class User(TypedDict):
    id: UUID
    first_name: str
    last_name: str
    email: str
    created_at: datetime


class MockDb:
    _users: dict[UUID, User]

    def __init__(self, faker: Faker):
        users = [
            User(
                id=faker.uuid4(),
                first_name=faker.first_name(),
                last_name=faker.last_name(),
                email=faker.email(),
                created_at=faker.date_time(),
            )
            for _ in range(313)
        ]
        users.sort(key=lambda user: user["created_at"])
        self._users = {u["id"]: u for u in users}

    def get_users(self) -> list[User]:
        return list(self._users.values())

    def create_or_update_user(self, user: User):
        self._users[user["id"]] = user

    def get_user(self, id: UUID | str) -> Optional[User]:
        if not isinstance(id, UUID):
            id = UUID(id)

        return self._users.get(id, None)

    def find_user(self, query: str) -> list[User]:
        query_re = re.compile(query, re.I)
        return [
            u
            for u in self._users.values()
            if query_re.match(u["first_name"])
            or query_re.match(u["last_name"])
            or query_re.match(u["email"])
        ]
