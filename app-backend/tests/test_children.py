class TestChildProfile:
    def test_child_can_read_own_profile(self, client, child_token, registered_child):
        headers = {"Authorization": f"Bearer {child_token}"}
        response = client.get("/children/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == registered_child["name"]
        assert data["points_total"] == 0

    def test_child_starts_at_level_one(self, client, child_token):
        headers = {"Authorization": f"Bearer {child_token}"}
        response = client.get("/children/me", headers=headers)
        assert response.json()["level"] == 1

    def test_parent_cannot_access_child_profile_route(self, client, parent_token):
        headers = {"Authorization": f"Bearer {parent_token}"}
        response = client.get("/children/me", headers=headers)
        assert response.status_code == 403


class TestChildLeveling:
    def _approve_activity(self, client, parent_token, child_token, points):
        parent_headers = {"Authorization": f"Bearer {parent_token}"}
        child_headers = {"Authorization": f"Bearer {child_token}"}

        activity = client.post(
            "/activities",
            json={"name": "Task", "description": "", "default_points": points, "category": "chore"},
            headers=parent_headers,
        ).json()
        client.post(f"/activities/{activity['id']}/enable", json={"points_override": points}, headers=parent_headers)
        ca = client.post("/child-activities", json={"activity_id": activity["id"]}, headers=child_headers).json()
        client.post(f"/child-activities/{ca['id']}/submit", headers=child_headers)
        client.patch(f"/child-activities/{ca['id']}/review", json={"status": "APPROVED"}, headers=parent_headers)

    def test_child_levels_up_at_100_points(self, client, parent_token, child_token, registered_child):
        self._approve_activity(client, parent_token, child_token, points=100)
        response = client.get("/children/me", headers={"Authorization": f"Bearer {child_token}"})
        assert response.json()["level"] == 2

    def test_child_levels_up_at_300_points(self, client, parent_token, child_token, registered_child):
        self._approve_activity(client, parent_token, child_token, points=300)
        response = client.get("/children/me", headers={"Authorization": f"Bearer {child_token}"})
        assert response.json()["level"] >= 3


class TestParentChildRelationship:
    def test_parent_can_list_their_children(self, client, parent_token, registered_child):
        headers = {"Authorization": f"Bearer {parent_token}"}
        response = client.get("/parents/me/children", headers=headers)
        assert response.status_code == 200
        children = response.json()
        assert len(children) == 1
        assert children[0]["name"] == registered_child["name"]

    def test_parent_sees_child_points_summary(self, client, parent_token, registered_child):
        headers = {"Authorization": f"Bearer {parent_token}"}
        response = client.get("/parents/me/children", headers=headers)
        child_data = response.json()[0]
        assert "points_total" in child_data
        assert "level" in child_data
