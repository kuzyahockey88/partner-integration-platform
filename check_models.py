from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

MODELS_TO_TEST = [
    "GigaChat",
    "GigaChat-Pro",
    "GigaChat-Plus",
    "GigaChat-Max",
    "GigaChat-2",
    "GigaChat-2-Pro",
    "GigaChat:latest",
]

for model_name in MODELS_TO_TEST:
    try:
        client = GigaChat(
            credentials="MDFhMGQzNjEtMWYzZC03Y2Y1LWFhYzAtYjFiMjg2YTc5NGUwOjhhZjc1Y2VhLTA3NjktNDQ3Yi05YjBlLTI1NmRiZDZlNDk5NA==",
            scope="GIGACHAT_API_PERS",
            model=model_name,
            verify_ssl_certs=False,
        )
        chat = Chat(
            messages=[Messages(role=MessagesRole.USER, content="Hi")],
            temperature=0.1,
        )
        response = client.chat(chat)
        # Не выводим content — только статус
        print(f"[OK] {model_name}")
    except Exception as e:
        # Кодируем ошибку в ASCII безопасно
        error_msg = str(e).encode("ascii", "ignore").decode("ascii")
        print(f"[FAIL] {model_name} - {type(e).__name__}: {error_msg[:150]}")