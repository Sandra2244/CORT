import os
from typing import List

AVATAR_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'avatars')

class AvatarService:
    def __init__(self):
        os.makedirs(AVATAR_DIR, exist_ok=True)

    def list_avatars(self) -> List[str]:
        files = [f for f in os.listdir(AVATAR_DIR) if os.path.isfile(os.path.join(AVATAR_DIR, f))]
        return files

    def save_avatar(self, filename: str, data: bytes) -> str:
        path = os.path.join(AVATAR_DIR, filename)
        with open(path, 'wb') as f:
            f.write(data)
        return path
