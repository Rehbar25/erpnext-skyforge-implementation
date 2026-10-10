"""Thin ERPNext REST client shared by configuration, migration and integration code."""

import json
import os

import requests


class ERPError(RuntimeError):
    pass


class ERPClient:
    def __init__(self, url=None, api_key=None, api_secret=None, user=None, password=None):
        self.url = (url or os.getenv("ERP_URL", "http://localhost:8080")).rstrip("/")
        self.s = requests.Session()
        key = api_key or os.getenv("ERP_API_KEY")
        secret = api_secret or os.getenv("ERP_API_SECRET")
        if key and secret:
            self.s.headers["Authorization"] = f"token {key}:{secret}"
        else:
            self.call_post("login", usr=user or os.getenv("ERP_USER", "Administrator"),
                           pwd=password or os.getenv("ERP_PASSWORD", "admin"))

    # ----------------------------------------------------------------- low level
    def _check(self, r):
        if r.ok:
            return r.json() if r.content else {}
        try:
            body = r.json()
            msg = body.get("exception") or body.get("_server_messages") or body
        except ValueError:
            msg = r.text[:500]
        raise ERPError(f"{r.status_code} {r.request.method} {r.url}: {msg}")

    def call(self, method, **params):
        r = self.s.get(f"{self.url}/api/method/{method}", params=params)
        return self._check(r).get("message")

    def call_post(self, method, **data):
        r = self.s.post(f"{self.url}/api/method/{method}", data=data)
        return self._check(r).get("message")

    # ----------------------------------------------------------------- documents
    def get_list(self, doctype, filters=None, fields=("name",), limit=0):
        params = {"fields": json.dumps(list(fields)), "limit_page_length": limit}
        if filters:
            params["filters"] = json.dumps(filters)
        r = self.s.get(f"{self.url}/api/resource/{doctype}", params=params)
        return self._check(r)["data"]

    def get(self, doctype, name):
        r = self.s.get(f"{self.url}/api/resource/{doctype}/{requests.utils.quote(name, safe='')}")
        return self._check(r)["data"]

    def exists(self, doctype, name):
        return bool(self.get_list(doctype, filters={"name": name}, limit=1))

    def insert(self, doctype, doc):
        r = self.s.post(f"{self.url}/api/resource/{doctype}", json=doc)
        return self._check(r)["data"]

    def update(self, doctype, name, changes):
        r = self.s.put(f"{self.url}/api/resource/{doctype}/{requests.utils.quote(name, safe='')}",
                       json=changes)
        return self._check(r)["data"]

    def upsert(self, doctype, name, doc):
        """Create the document if missing, else update it. Returns (doc, created)."""
        if self.exists(doctype, name):
            return self.update(doctype, name, doc), False
        return self.insert(doctype, doc), True

    def submit(self, doctype, name):
        return self.update(doctype, name, {"docstatus": 1})

    def set_single(self, doctype, values):
        return self.update(doctype, doctype, values)

    def delete(self, doctype, name):
        r = self.s.delete(f"{self.url}/api/resource/{doctype}/{requests.utils.quote(name, safe='')}")
        return self._check(r)

    # ----------------------------------------------------------------- server-side logic
    def call_json(self, method, **params):
        """POST a whitelisted method with JSON-encoded arguments (mappers, planners)."""
        data = {k: v if isinstance(v, str) else json.dumps(v) for k, v in params.items()}
        r = self.s.post(f"{self.url}/api/method/{method}", data=data)
        return self._check(r).get("message")

    def run_doc_method(self, doc, method, **args):
        """Run a whitelisted controller method (e.g. Production Plan.get_items) the way the UI does.

        Unsaved docs need a temporary name and __islocal, exactly as the browser sends them.
        Returns (updated_doc, message).
        """
        if not doc.get("name"):
            doc = {**doc, "name": f"new-{doc['doctype'].lower().replace(' ', '-')}-1", "__islocal": 1}
        data = {"docs": json.dumps(doc), "method": method}
        if args:
            data["args"] = json.dumps(args)
        body = self._check(self.s.post(f"{self.url}/api/method/run_doc_method", data=data))
        return (body.get("docs") or [doc])[0], body.get("message")

    def map_doc(self, mapper, source_name, **kw):
        """Use ERPNext's own document mapper (e.g. Sales Order -> Delivery Note)."""
        return self.call_json(mapper, source_name=source_name, **kw)

    def insert_submit(self, doctype, doc):
        doc = self.insert(doctype, doc)
        self.submit(doctype, doc["name"])
        return doc
