from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from forum.models import Reply, Thread


User = get_user_model()


class ForumViewsTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            username="autor",
            email="autor@example.com",
            password="Senha@123",
        )
        self.other = User.objects.create_user(
            username="viewer",
            email="viewer@example.com",
            password="Senha@123",
        )
        self.thread1 = Thread.objects.create(
            title="Topico 1",
            slug="topico-1",
            body="Mensagem",
            author=self.author,
            views=5,
            answers=2,
        )
        self.thread2 = Thread.objects.create(
            title="Topico 2",
            slug="topico-2",
            body="Mensagem",
            author=self.author,
            views=10,
            answers=1,
        )
        self.thread1.tags.add("django")
        self.reply = Reply.objects.create(
            thread=self.thread1,
            reply="Resposta",
            author=self.other,
        )

    def test_forum_list_order_by_views(self):
        url = reverse("forum:forum_index") + "?order=views"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["object_list"][0], self.thread2)

    def test_forum_list_filter_by_tag(self):
        url = reverse("forum:index_tagged", args=["django"])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Topico 1")

    def test_thread_view_incrementa_visualizacoes_para_visitante(self):
        url = reverse("forum:thread", args=[self.thread1.slug])
        self.client.get(url)
        self.thread1.refresh_from_db()
        self.assertEqual(self.thread1.views, 6)

    def test_thread_view_nao_incrementa_para_autor(self):
        self.client.login(username="autor", password="Senha@123")
        url = reverse("forum:thread", args=[self.thread1.slug])
        self.client.get(url)
        self.thread1.refresh_from_db()
        self.assertEqual(self.thread1.views, 5)

    def test_post_reply_requer_login(self):
        url = reverse("forum:thread", args=[self.thread1.slug])
        response = self.client.post(url, {"reply": "Minha resposta"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Reply.objects.count(), 1)

    def test_post_reply_cria_resposta(self):
        self.client.login(username="viewer", password="Senha@123")
        url = reverse("forum:thread", args=[self.thread1.slug])
        response = self.client.post(url, {"reply": "Minha resposta"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Reply.objects.count(), 2)

    def test_reply_correct_ajax(self):
        self.client.login(username="autor", password="Senha@123")
        url = reverse("forum:reply_correct", args=[self.reply.pk])
        response = self.client.get(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 200)
        self.reply.refresh_from_db()
        self.assertTrue(self.reply.correct)

    def test_reply_incorrect_redirect(self):
        self.reply.correct = True
        self.reply.save()
        self.client.login(username="autor", password="Senha@123")
        url = reverse("forum:reply_incorrect", args=[self.reply.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.reply.refresh_from_db()
        self.assertFalse(self.reply.correct)

    def test_forum_list_order_by_answers(self):
        url = reverse("forum:forum_index") + "?order=answers"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["object_list"][0], self.thread1)
