"""Serves the static single-page app from API Gateway when CloudFront is not available.

Used only with enable_cloudfront = false (AWS Academy Learner Lab denies cloudfront:CreateDistribution).
The SPA files are packaged into the Lambda zip under static/ by scripts/build.sh; config.js is
generated from the FRONTEND_CONFIG environment variable that Terraform sets.
"""
import base64
import os

STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
TYPES = {
    "html": "text/html; charset=utf-8", "js": "application/javascript", "css": "text/css",
    "svg": "image/svg+xml", "png": "image/png", "ico": "image/x-icon", "json": "application/json",
}
SECURITY_HEADERS = {
    "strict-transport-security": "max-age=31536000; includeSubDomains",
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "strict-origin-when-cross-origin",
}


def _resp(status, body, ctype, cache="no-cache", binary=False):
    return {
        "statusCode": status,
        "headers": {"content-type": ctype, "cache-control": cache, **SECURITY_HEADERS},
        "body": base64.b64encode(body).decode() if binary else body,
        "isBase64Encoded": binary,
    }


def handler(event, context):
    path = event.get("rawPath") or "/"
    if path == "/config.js":
        return _resp(200, f"window.APP_CONFIG = {os.environ['FRONTEND_CONFIG']};\n", TYPES["js"])
    name = os.path.normpath(path.lstrip("/") or "index.html")
    full = os.path.join(STATIC, name)
    # Reject path traversal; unknown paths fall back to the SPA's index.html.
    if name.startswith("..") or not os.path.realpath(full).startswith(STATIC + os.sep) or not os.path.isfile(full):
        if "." in os.path.basename(name):
            return _resp(404, "not found", "text/plain")
        full, name = os.path.join(STATIC, "index.html"), "index.html"
    ext = name.rsplit(".", 1)[-1].lower()
    ctype = TYPES.get(ext, "application/octet-stream")
    cache = "no-cache" if ext == "html" else "public, max-age=300"
    with open(full, "rb") as f:
        data = f.read()
    if ctype.startswith(("text/", "application/javascript", "application/json", "image/svg")):
        return _resp(200, data.decode(), ctype, cache)
    return _resp(200, data, ctype, cache, binary=True)
