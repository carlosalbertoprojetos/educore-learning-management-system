from django.test import TestCase
from django.test.client import Client
from django.urls import reverse


class HomeViewTest(TestCase):
    def test_home_status_code(self):
        client = Client()
        response = client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    def test_home_template_used(self):
        client = Client()
        response = client.get(reverse("home"))
        self.assertTemplateUsed(response, "home.html")
        self.assertTemplateUsed(response, "base.html")


class ContatoViewTest(TestCase):
    def test_contato_status_code(self):
        client = Client()
        response = client.get(reverse("contato"))
        self.assertEqual(response.status_code, 200)

    def test_contato_template_used(self):
        client = Client()
        response = client.get(reverse("contato"))
        self.assertTemplateUsed(response, "contato.html")
        self.assertTemplateUsed(response, "base.html")
