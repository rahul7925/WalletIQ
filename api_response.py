"""
api_response.py — Unified API Response Envelope for WalletIQ REST API
Format conforms to production REST API contracts:
Success:
  {
    "success": true,
    "data": { ... },
    "message": "..."
  }
Error:
  {
    "success": false,
    "error": {
      "code": "ERROR_CODE",
      "message": "Human readable message",
      "details": { ... }
    }
  }
"""

from flask import jsonify


def success_response(data=None, message: str = "Request successful", status_code: int = 200):
    payload = {
        "success": True,
        "data": data if data is not None else {},
        "message": message
    }
    return jsonify(payload), status_code


def error_response(code: str = "BAD_REQUEST", message: str = "An error occurred", status_code: int = 400, details=None):
    err_payload = {
        "code": code,
        "message": message
    }
    if details:
        err_payload["details"] = details

    payload = {
        "success": False,
        "error": err_payload
    }
    return jsonify(payload), status_code
