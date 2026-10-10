import os

import pytest
import requests


def _erp_up():
    try:
        return requests.get(os.getenv("ERP_URL", "http://localhost:8080") + "/api/method/ping", timeout=3).ok
    except requests.RequestException:
        return False


def pytest_collection_modifyitems(config, items):
    if _erp_up():
        return
    skip = pytest.mark.skip(reason="ERPNext not reachable on ERP_URL")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip)
