"""Quickstart Scenario 5 — deletion splits correctly.

FR-024 and FR-025 are the compliance-critical requirements in this feature:
immigration-related fields must be destroyed on the request path, and everything
else must survive exactly as long as the recovery window.
"""

JAPAN_FIELDS = {
    "residence_status": "Permanent resident",
    "nationality": "Example nationality",
    "visa_type": "Example visa category",
    "visa_expires_on": "2030-01-01",
    "work_authorisation": True,
    "japanese_qualification": "Level 2",
}


def _profile_with_japan_data(client, headers):
    assert client.post("/api/v1/profile", headers=headers).status_code == 201
    saved = client.put("/api/v1/profile/japan", headers=headers, json=JAPAN_FIELDS)
    assert saved.status_code == 200
    return saved.json()


def test_disclosure_flags_default_closed(client, auth_headers):
    """FR-006: sensitive fields are withheld from generated documents by default."""
    japan = _profile_with_japan_data(client, auth_headers)
    assert japan["disclose_nationality"] is False
    assert japan["disclose_visa"] is False
    assert japan["disclose_residence_status"] is False


def test_deletion_receipt_states_what_is_lost(client, auth_headers):
    _profile_with_japan_data(client, auth_headers)

    receipt = client.delete("/api/v1/profile", headers=auth_headers)
    assert receipt.status_code == 200
    body = receipt.json()

    # FR-026: the user is told what goes immediately and when the window ends.
    assert set(body["erased_immediately"]) == {
        "residence_status",
        "nationality",
        "visa_type",
        "visa_expires_on",
    }
    assert body["recoverable_until"]


def test_deleted_profile_is_invisible(client, auth_headers):
    _profile_with_japan_data(client, auth_headers)
    client.delete("/api/v1/profile", headers=auth_headers)

    # FR-027: nothing may read a profile inside its recovery window.
    assert client.get("/api/v1/profile", headers=auth_headers).status_code == 404


def test_restore_returns_everything_except_the_erased_fields(client, auth_headers):
    _profile_with_japan_data(client, auth_headers)
    client.delete("/api/v1/profile", headers=auth_headers)

    restored = client.post("/api/v1/profile/restore", headers=auth_headers)
    assert restored.status_code == 200

    japan = client.get("/api/v1/profile", headers=auth_headers).json()["japan"]
    # FR-024: these were destroyed on the request path and cannot come back.
    assert japan["residence_status"] is None
    assert japan["nationality"] is None
    assert japan["visa_type"] is None
    assert japan["visa_expires_on"] is None
    # Everything else survived the round trip.
    assert japan["japanese_qualification"] == "Level 2"
    assert japan["work_authorisation"] is True


def test_deleting_twice_is_a_conflict(client, auth_headers):
    _profile_with_japan_data(client, auth_headers)
    assert client.delete("/api/v1/profile", headers=auth_headers).status_code == 200
    assert client.delete("/api/v1/profile", headers=auth_headers).status_code == 404


def test_export_includes_japan_fields_regardless_of_disclosure(client, auth_headers):
    """FR-037: disclosure governs generated documents, not the user's own copy."""
    import io
    import json
    import zipfile

    _profile_with_japan_data(client, auth_headers)

    response = client.post("/api/v1/profile/export", headers=auth_headers)
    assert response.status_code == 200

    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        names = set(archive.namelist())
        # FR-035: a structured file and a readable document, together.
        assert names == {"profile.json", "profile.md"}
        payload = json.loads(archive.read("profile.json"))

    assert payload["japan"]["nationality"] == "Example nationality"
    assert payload["japan"]["disclose_nationality"] is False
