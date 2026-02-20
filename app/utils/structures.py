"""
GreenSkills 2026

Файл для хранения структур ответа
"""


class Status:
    OK = "OK"
    ERROR = "ERROR"


def resp(status: Status = "OK", data: dict | list | str = {}) -> dict:
    """
    Стандартный ответ приложения
    """
    if status == Status.OK:
        return {"status": status, "data": data}
    else:
        return {"status": status, "message": data}
