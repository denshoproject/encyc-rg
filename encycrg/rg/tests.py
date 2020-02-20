from django.test import TestCase
from django.urls import reverse


class APIView(TestCase):

    def test_index(self):
        assert self.client.get(reverse('rg-api-index')).status_code == 200

    def test_articles(self):
        data = {}
        response = self.client.get(reverse('rg-api-articles'), data)
        assert response.status_code == 200
        data = {'offset': 25}
        response = self.client.get(reverse('rg-api-articles'), data)
        assert response.status_code == 200

    def test_article(self):
        assert self.client.get(
            reverse('rg-api-article', args=['12-1-A (play)'])
        ).status_code == 200

    def test_authors(self):
        data = {}
        response = self.client.get(reverse('rg-api-authors'), data)
        assert response.status_code == 200
        data = {'offset': 25}
        response = self.client.get(reverse('rg-api-authors'), data)
        assert response.status_code == 200

    def test_author(self):
        assert self.client.get(
            reverse('rg-api-author', args=['Kaori Akiyama'])
        ).status_code == 200

    def test_sources(self):
        data = {}
        response = self.client.get(reverse('rg-api-sources'), data)
        assert response.status_code == 200
        data = {'offset': 25}
        response = self.client.get(reverse('rg-api-sources'), data)
        assert response.status_code == 200

    #def test_source(self):
    #    assert self.client.get(
    #        reverse('rg-api-source', args=['en-littletokyousa-1'])
    #    ).status_code == 200

    def test_browse(self):
        assert self.client.get(reverse('rg-api-browse')).status_code == 200

    def test_browse_field(self):
        assert self.client.get(
            reverse('rg-api-browse-field', args=['genre'])
        ).status_code == 200

    def test_browse_field_objects(self):
        r = self.client.get(
            reverse('rg-api-browse-fieldvalue', args=['genre', 'Art']), {}
        )
        assert r.status_code == 200
        r = self.client.get(
            reverse('rg-api-browse-fieldvalue', args=['genre', 'Art']),
            {'limit': 25}
        )
        assert r.status_code == 200

    def test_search_index(self):
        data = {}
        response = self.client.get(reverse('rg-api-search'), data)
        assert response.status_code == 200

    def test_search_fulltext(self):
        data = {'fulltext': 'camp'}
        response = self.client.get(reverse('rg-api-search'), data)
        assert response.status_code == 200
        data = {'fulltext': 'camp', 'offset': 25}
        response = self.client.get(reverse('rg-api-search'), data)
        assert response.status_code == 200

    def test_search_fulltext_filter(self):
        data = {'fulltext': 'camp', 'rg_rgmediatype': 'books'}
        response = self.client.get(reverse('rg-api-search'), data)
        assert response.status_code == 200
        data = {'fulltext': 'camp', 'rg_rgmediatype': 'books', 'offset': 25}
        response = self.client.get(reverse('rg-api-search'), data)
        assert response.status_code == 200


class WikiPageTitles(TestCase):
    """Test that characters in MediaWiki titles are matched correctly
    """
    
    def test_index(self):
        response = self.client.get(reverse('rg-index'))
        self.assertEqual(response.status_code, 200)

    def test_articles(self):
        assert self.client.get(reverse('rg-articles')).status_code == 200

    def test_article(self):
        assert self.client.get(
            reverse('rg-article', args=['12-1-A (play)'])
        ).status_code == 200

    #def test_authors(self):
    #    assert self.client.get(reverse('rg-authors')).status_code == 200

    #def test_author(self):
    #    assert self.client.get(
    #        reverse('rg-author', args=['Kaori Akiyama'])
    #    ).status_code == 200

    #def test_sources(self):
    #    assert self.client.get(reverse('rg-sources')).status_code == 200

    #def test_source(self):
    #    assert self.client.get(
    #        reverse('rg-source', args=['en-littletokyousa-1'])
    #    ).status_code == 200

    def test_browse(self):
        assert self.client.get(reverse('rg-browse')).status_code == 200

    def test_browse_field(self):
        assert self.client.get(
            reverse('rg-browse-field', args=['genre'])
        ).status_code == 200

    def test_browse_field_value(self):
        assert self.client.get(
            reverse('rg-browse-fieldvalue', args=['genre', 'Art'])
        ).status_code == 200

    def test_search_index(self):
        data = {}
        response = self.client.get(reverse('rg-search'), data)
        assert response.status_code == 200

    def test_search_fulltext(self):
        data = {'fulltext': 'camp'}
        response = self.client.get(reverse('rg-search'), data)
        assert response.status_code == 200

    def test_search_fulltext_filter(self):
        data = {'fulltext': 'camp', 'rg_rgmediatype': 'books'}
        response = self.client.get(reverse('rg-search'), data)
        assert response.status_code == 200
