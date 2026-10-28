from app.models.profile import UserProfile


class ProfileStore:

    def __init__(self):
        self.profiles: dict[str, UserProfile] = {}

    def get_or_create(
        self,
        user_id: str,
    ) -> UserProfile:

        if user_id not in self.profiles:

            self.profiles[user_id] = UserProfile(
                user_id=user_id
            )

        return self.profiles[user_id]

    def save(
        self,
        profile: UserProfile,
    ):

        self.profiles[profile.user_id] = profile