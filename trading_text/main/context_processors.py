from django.contrib.messages import get_messages


def flash_messages(request):
    return {"flash_messages": get_messages(request)}
