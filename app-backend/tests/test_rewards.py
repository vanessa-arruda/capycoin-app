import pytest


REWARD_PAYLOAD = {
    "name": "Extra screen time",
    "description": "30 minutes of extra screen time",
    "points_cost": 50,
}


class TestRewardManagement:
    def test_parent_creates_reward(self, client, parent_token):
        headers = {"Authorization": f"Bearer {parent_token}"}
        response = client.post("/rewards", json=REWARD_PAYLOAD, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == REWARD_PAYLOAD["name"]
        assert data["points_cost"] == REWARD_PAYLOAD["points_cost"]

    def test_child_cannot_create_reward(self, client, child_token):
        headers = {"Authorization": f"Bearer {child_token}"}
        response = client.post("/rewards", json=REWARD_PAYLOAD, headers=headers)
        assert response.status_code == 403

    def test_list_rewards(self, client, parent_token, child_token):
        parent_headers = {"Authorization": f"Bearer {parent_token}"}
        child_headers = {"Authorization": f"Bearer {child_token}"}
        client.post("/rewards", json=REWARD_PAYLOAD, headers=parent_headers)
        response = client.get("/rewards", headers=child_headers)
        assert response.status_code == 200
        assert len(response.json()) >= 1


class TestRewardRedemption:
    @pytest.fixture
    def reward(self, client, parent_token):
        headers = {"Authorization": f"Bearer {parent_token}"}
        return client.post("/rewards", json=REWARD_PAYLOAD, headers=headers).json()

    @pytest.fixture
    def child_with_points(self, client, parent_token, child_token, registered_child):
        """Give child enough points via approved activities."""
        parent_headers = {"Authorization": f"Bearer {parent_token}"}
        child_headers = {"Authorization": f"Bearer {child_token}"}

        activity_payload = {"name": "Big chore", "description": "Big task", "default_points": 100, "category": "chore"}
        activity = client.post("/activities", json=activity_payload, headers=parent_headers).json()
        client.post(f"/activities/{activity['id']}/enable", json={"points_override": 100}, headers=parent_headers)

        child_activity = client.post(
            "/child-activities", json={"activity_id": activity["id"]}, headers=child_headers
        ).json()
        client.post(f"/child-activities/{child_activity['id']}/submit", headers=child_headers)
        client.patch(
            f"/child-activities/{child_activity['id']}/review",
            json={"status": "APPROVED"},
            headers=parent_headers,
        )
        return registered_child

    def test_child_redeems_reward(self, client, child_token, reward, child_with_points):
        headers = {"Authorization": f"Bearer {child_token}"}
        response = client.post(f"/rewards/{reward['id']}/redeem", headers=headers)
        assert response.status_code == 201

    def test_child_cannot_redeem_without_enough_points(self, client, child_token, reward):
        headers = {"Authorization": f"Bearer {child_token}"}
        response = client.post(f"/rewards/{reward['id']}/redeem", headers=headers)
        assert response.status_code == 400
        assert "points" in response.json()["detail"].lower()

    def test_parent_approves_redemption_deducts_points(self, client, parent_token, child_token, reward, child_with_points):
        parent_headers = {"Authorization": f"Bearer {parent_token}"}
        child_headers = {"Authorization": f"Bearer {child_token}"}

        redemption = client.post(f"/rewards/{reward['id']}/redeem", headers=child_headers).json()
        client.patch(f"/rewards/redemptions/{redemption['id']}", json={"status": "APPROVED"}, headers=parent_headers)

        child_response = client.get("/children/me", headers=child_headers)
        assert child_response.json()["points_total"] == 50  # 100 earned - 50 cost
