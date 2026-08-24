# -*- coding: utf-8 -*-
"""윈도우 토스트 알림."""

from winotify import Notification, audio

APP_ID = "공고 모니터"


def notify(title, message, link=None):
    toast = Notification(app_id=APP_ID, title=title, msg=message, duration="short")
    toast.set_audio(audio.Default, loop=False)
    if link:
        toast.add_actions(label="리포트 열기", launch=str(link))
    toast.show()
