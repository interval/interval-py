from datetime import datetime
from typing import Optional
from typing_extensions import TypedDict
import re
from uuid import UUID

from faker import Faker


class MockDb:
    class User(TypedDict):
        id: UUID
        firstName: str
        lastName: str
        email: str
        createdAt: datetime

    _users: dict[UUID, User]

    def __init__(self, faker: Faker):
        users = [
            MockDb.User(
                id=faker.uuid4(),
                firstName=faker.first_name(),
                lastName=faker.last_name(),
                email=faker.email(),
                createdAt=faker.date_time(),
            )
            for _ in range(313)
        ]
        users.sort(key=lambda user: user["createdAt"])
        self._users = {u["id"]: u for u in users}

    def get_users(self) -> list[User]:
        return list(self._users.values())

    def create_or_update_user(self, user: User):
        self._users[user["id"]] = user

    def get_user(self, id: UUID | str) -> Optional[User]:
        if not isinstance(id, UUID):
            id = UUID(id)

        return self._users.get(id, None)

    def find_users(self, query: str) -> list[User]:
        query_re = re.compile(query, re.I)
        return [
            u
            for u in self._users.values()
            if query_re.match(u["firstName"])
            or query_re.match(u["lastName"])
            or query_re.match(u["email"])
        ]
