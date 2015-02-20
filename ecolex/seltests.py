from django_selenium.testcases import SeleniumTestCase
from django.core.urlresolvers import reverse

class SimpleQuery(SeleniumTestCase):
    def find_css(self, css_selector):
        """ Shortcut to find elements by CSS. Returns either the first matching el or None.
        """
        elems = self.driver.find_elements_by_css_selector(css_selector)
        found = len(elems)
        if found > 0:
            return elems[0]
        elif not elems:
            return None

    def test_query_and_back(self):
        self.driver.get(self.live_server_url)
        assert "Ecolex" in self.driver.title

        # search for polar bears
        self.find_css(".search-form #search").send_keys("polar bear")
        self.find_css(".search-form").submit()

        assert self.find_css(".search-result")

        self.driver.back()
        el = self.find_css(".homepage")
        assert el
