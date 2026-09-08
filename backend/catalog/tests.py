from django.test import TestCase


class CatalogSmokeTest(TestCase):
	def test_django_test_environment_loads(self):
		self.assertTrue(self.client)
