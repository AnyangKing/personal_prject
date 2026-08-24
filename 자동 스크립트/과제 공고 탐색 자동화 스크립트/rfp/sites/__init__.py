# -*- coding: utf-8 -*-
"""사이트 수집 모듈 레지스트리."""

import importlib


def load(site_id):
    """rfp/sites/<site_id>.py 를 불러옵니다."""
    return importlib.import_module(f".{site_id}", __name__)
