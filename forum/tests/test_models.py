from django.contrib.auth import get_user_model
from django.test import TestCase

from forum.models import Reply, Thread


User = get_user_model()


class ForumModelTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            username="autor",
            email="autor@example.com",
            password="Senha@123",
        )
        self.thread = Thread.objects.create(
            title="Topico 1",
            slug="topico-1",
            body="Mensagem",
            author=self.author,
        )

    def test_reply_str(self):
        reply = Reply.objects.create(thread=self.thread, reply="Resposta", author=self.author)
        self.assertEqual(str(reply), "Resposta")

    def test_post_save_reply_atualiza_answers(self):
        Reply.objects.create(thread=self.thread, reply="Resp 1", author=self.author)
        self.thread.refresh_from_db()
        self.assertEqual(self.thread.answers, 1)

    def test_post_delete_reply_atualiza_answers(self):
        reply = Reply.objects.create(thread=self.thread, reply="Resp 1", author=self.author)
        reply.delete()
        self.thread.refresh_from_db()
        self.assertEqual(self.thread.answers, 0)

    def test_apenas_uma_resposta_correta(self):
        reply1 = Reply.objects.create(
            thread=self.thread,
            reply="Resp 1",
            author=self.author,
            correct=True,
        )
        reply2 = Reply.objects.create(
            thread=self.thread,
            reply="Resp 2",
            author=self.author,
            correct=True,
        )
        reply1.refresh_from_db()
        reply2.refresh_from_db()
        self.assertFalse(reply1.correct)
        self.assertTrue(reply2.correct)
