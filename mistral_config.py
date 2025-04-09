from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage
from rate_limiter import RateLimiter

# Создаем глобальный экземпляр RateLimiter
rate_limiter = RateLimiter(min_interval=1.0)

def create_mistral_client(api_key):
    return MistralClient(api_key=api_key)

def create_chat_message(role, content):
    return ChatMessage(role=role, content=content)

def make_api_request(func):
    """
    Декоратор для ограничения частоты запросов к API
    """
    def wrapper(*args, **kwargs):
        rate_limiter.wait()
        return func(*args, **kwargs)
    return wrapper 