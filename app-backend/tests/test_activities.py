import pytest


ACTIVITY_PAYLOAD = {
    "name": "Wash the dishes",
    "description": "Clean all dishes after dinner",
    "default_points": 10,
    "category": "chore",
}


class TestActivityCatalog:
    def test_parent_can_create_activity(self, client, parent_token):
        headers = {"Authorization": f"Bearer {parent_token}"}
        response = client.post("/activities", json=ACTIVITY_PAYLOAD, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == ACTIVITY_PAYLOAD["name"]
        assert data["default_points"] == ACTIVITY_PAYLOAD["default_points"]

    def test_child_cannot_create_activity(self, client, child_token):
        headers = {"Authorization": f"Bearer {child_token}"}
        response = client.post("/activities", json=ACTIVITY_PAYLOAD, headers=headers)
        assert response.status_code == 403

    def test_list_activities(self, client, parent_token):
        headers = {"Authorization": f"Bearer {parent_token}"}
        client.post("/activities", json=ACTIVITY_PAYLOAD, headers=headers)
        response = client.get("/activities", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) >= 1


class TestParentEnablesActivity:
    def test_parent_enables_activity_with_custom_points(self, client, parent_token):
        headers = {"Authorization": f"Bearer {parent_token}"}
        activity = client.post("/activities", json=ACTIVITY_PAYLOAD, headers=headers).json()
        config = {"points_override": 15, "max_per_day": 1}
        response = client.post(f"/activities/{activity['id']}/enable", json=config, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["points_override"] == 15
        assert data["is_active"] is True

    def test_parent_can_disable_activity(self, client, parent_token):
        headers = {"Authorization": f"Bearer {parent_token}"}
        activity = client.post("/activities", json=ACTIVITY_PAYLOAD, headers=headers).json()
        client.post(f"/activities/{activity['id']}/enable", json={}, headers=headers)
        response = client.post(f"/activities/{activity['id']}/disable", headers=headers)
        assert response.status_code == 200
        assert response.json()["is_active"] is False


class TestChildActivityFlow:
    @pytest.fixture
    def enabled_activity(self, client, parent_token):
        headers = {"Authorization": f"Bearer {parent_token}"}
        activity = client.post("/activities", json=ACTIVITY_PAYLOAD, headers=headers).json()
        client.post(f"/activities/{activity['id']}/enable", json={"points_override": 10}, headers=headers)
        return activity

    def test_child_picks_activity(self, client, child_token, enabled_activity):
        headers = {"Authorization": f"Bearer {child_token}"}
        response = client.post("/child-activities", json={"activity_id": enabled_activity["id"]}, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "PENDING"

    def test_child_submits_activity(self, client, child_token, enabled_activity):
        headers = {"Authorization": f"Bearer {child_token}"}
        child_activity = client.post(
            "/child-activities", json={"activity_id": enabled_activity["id"]}, headers=headers
        ).json()
        response = client.post(f"/child-activities/{child_activity['id']}/submit", headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "PENDING"

    def test_parent_approves_activity_awards_points(self, client, parent_token, child_token, enabled_activity, registered_child):
        child_headers = {"Authorization": f"Bearer {child_token}"}
        parent_headers = {"Authorization": f"Bearer {parent_token}"}

        child_activity = client.post(
            "/child-activities", json={"activity_id": enabled_activity["id"]}, headers=child_headers
        ).json()
        client.post(f"/child-activities/{child_activity['id']}/submit", headers=child_headers)

        response = client.patch(
            f"/child-activities/{child_activity['id']}/review",
            json={"status": "APPROVED"},
            headers=parent_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "APPROVED"

        child_response = client.get("/children/me", headers=child_headers)
        assert child_response.json()["points_total"] == 10

    def test_parent_rejects_activity_no_points(self, client, parent_token, child_token, enabled_activity):
        child_headers = {"Authorization": f"Bearer {child_token}"}
        parent_headers = {"Authorization": f"Bearer {parent_token}"}

        child_activity = client.post(
            "/child-activities", json={"activity_id": enabled_activity["id"]}, headers=child_headers
        ).json()
        client.post(f"/child-activities/{child_activity['id']}/submit", headers=child_headers)
        client.patch(
            f"/child-activities/{child_activity['id']}/review",
            json={"status": "REJECTED"},
            headers=parent_headers,
        )

        child_response = client.get("/children/me", headers=child_headers)
        assert child_response.json()["points_total"] == 0
