from django.test import TestCase
from django.core.urlresolvers import reverse


class TheTest(TestCase):
    def test_polar_bear_results(self):
        data = self.client.get(reverse('results') + '?q=polar+bear')
        content = str(data.content)
        # Check results count
        self.assertIn('109 results', content)
        self.assertIn('<span class="badge">12</span>', content)
        self.assertIn('<span class="badge">97</span>', content)
        # Check for the first result: Agreement on Conservation of Polar Bears
        assert False # TODO
        # Check the filters
        # Check pagination
