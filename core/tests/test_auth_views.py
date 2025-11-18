from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


User = get_user_model()


class RegistrationViewTests(TestCase):
    def test_register_creates_inactive_user_and_redirects_to_waiting(self):
        response = self.client.post(
            reverse("register"),
            {
                "email": "newuser@example.com",
                "first_name": "New",
                "last_name": "User",
                "password1": "StrongPass123",
                "password2": "StrongPass123",
            },
        )

        self.assertRedirects(response, reverse("waiting_activation"))

        created_user = User.objects.get(email="newuser@example.com")
        self.assertFalse(created_user.is_active)
        self.assertEqual(created_user.role, "default")


class LoginViewTests(TestCase):
    def test_login_redirects_pending_activation_user(self):
        User.objects.create_user(
            username="pending@example.com",
            email="pending@example.com",
            password="StrongPass123",
            role="default",
            is_active=False,
        )

        response = self.client.post(
            reverse("custom_login"),
            {"email": "pending@example.com", "password": "StrongPass123"},
        )

        self.assertRedirects(response, reverse("waiting_activation"))

    def test_login_allows_active_user(self):
        User.objects.create_user(
            username="active@example.com",
            email="active@example.com",
            password="StrongPass123",
            role="learner",
            is_active=True,
        )

        response = self.client.post(
            reverse("custom_login"),
            {"email": "active@example.com", "password": "StrongPass123"},
        )

        self.assertRedirects(response, reverse("student_dashboard"))

    def test_login_staff_without_role_redirects_to_admin(self):
        User.objects.create_user(
            username="staff@example.com",
            email="staff@example.com",
            password="StrongPass123",
            role="",
            is_active=True,
            is_staff=True,
        )

        response = self.client.post(
            reverse("custom_login"),
            {"email": "staff@example.com", "password": "StrongPass123"},
        )

        self.assertRedirects(response, reverse("admin_dashboard"))

    def test_login_unknown_user_returns_form_with_error(self):
        response = self.client.post(
            reverse("custom_login"),
            {"email": "missing@example.com", "password": "Whatever123"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "No account found with that email. Please sign up first.",
            html=False,
        )


class WaitingActivationViewTests(TestCase):
    def test_waiting_activation_renders_template(self):
        response = self.client.get(reverse("waiting_activation"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/login/awaiting_activation.html")


class AdminDashboardTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin@example.com",
            email="admin@example.com",
            password="AdminPass123",
            role="admin",
        )

    def _create_randomized_assessment(self):
        from core.models import Assessment, Paper, Qualification

        qualification = Qualification.objects.create(
            name="Test Qualification",
            saqa_id="TQ12345",
        )
        paper = Paper.objects.create(
            name="Randomized Paper",
            qualification=qualification,
            is_randomized=True,
            created_by=self.admin_user,
        )
        assessment = Assessment.objects.create(
            eisa_id="EISA-TEST123",
            qualification=qualification,
            paper="Randomized Paper",
            paper_type="randomized",
            paper_link=paper,
            created_by=self.admin_user,
            status="draft",
        )
        return assessment

    def test_admin_dashboard_shows_randomized_download_button(self):
        assessment = self._create_randomized_assessment()
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin_dashboard"))

        download_url = f"{reverse('download_randomized_pdf', args=[assessment.id])}?format=docx"
        self.assertContains(response, download_url)
        self.assertContains(response, "Download Word")
