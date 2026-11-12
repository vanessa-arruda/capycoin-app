from models.enums import UserRole


class TestListMembers:
    def test_lists_everyone_with_the_admin_first(
        self, client, make_user, make_household, auth_headers
    ):
        mom = make_user(email="mom@example.com", display_name="Mom")
        dad = make_user(email="dad@example.com", display_name="Dad")
        kid = make_user(
            role=UserRole.KID, username="lia", password="x" * 8, display_name="Lia"
        )
        household = make_household(mom, kid, dad)

        body = client.get(
            f"/households/{household.id}/members", headers=auth_headers(dad)
        ).json()

        assert [(m["display_name"], m["role"], m["is_admin"]) for m in body] == [
            ("Mom", "parent", True),
            ("Dad", "parent", False),
            ("Lia", "kid", False),
        ]
        assert set(body[0]) == {
            "user_id",
            "role",
            "display_name",
            "username",
            "email",
            "is_admin",
            "joined_at",
        }


class TestRemoveMember:
    def test_admin_removes_a_parent(
        self, client, make_user, make_household, auth_headers
    ):
        admin = make_user(email="mom@example.com")
        dad = make_user(email="dad@example.com")
        household = make_household(admin, dad)
        dad_headers = auth_headers(dad)

        response = client.delete(
            f"/households/{household.id}/members/{dad.id}", headers=auth_headers(admin)
        )

        assert response.status_code == 204
        assert (
            client.get(f"/households/{household.id}", headers=dad_headers).status_code
            == 404
        )

    def test_admin_cannot_remove_themselves(
        self, client, make_user, make_household, auth_headers
    ):
        admin = make_user(email="mom@example.com")
        household = make_household(admin)

        response = client.delete(
            f"/households/{household.id}/members/{admin.id}",
            headers=auth_headers(admin),
        )

        assert response.status_code == 409

    def test_kids_are_not_removed_here(
        self, client, make_user, make_household, auth_headers
    ):
        admin = make_user(email="mom@example.com")
        kid = make_user(role=UserRole.KID, username="lia", password="x" * 8)
        household = make_household(admin, kid)

        response = client.delete(
            f"/households/{household.id}/members/{kid.id}",
            headers=auth_headers(admin),
        )

        assert response.status_code == 422
