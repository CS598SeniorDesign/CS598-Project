from django.conf import settings

# TODO: Note this in PR:
# I am not actually sure if having this file in a new core/ directory is the best solution. I am considering moving
# this into config/

VALID_STATUS_CODES: list[int] = [200, 202]

BGG_TOKEN = settings.BGG_API_TOKEN

REQUEST_HEADERS: dict[str, str] = {
    "User-Agent": "QuestLog/0.1",
    "Authorization": f"Bearer {BGG_TOKEN}"
}
