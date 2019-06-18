from django.test import TestCase
from django.urls import reverse


class APIView(TestCase):

    def test_index(self):
        assert self.client.get(reverse('rg-api-index')).status_code == 200

    def test_articles(self):
        assert self.client.get(reverse('rg-api-articles')).status_code == 200

    def test_article(self):
        assert self.client.get(
            reverse('rg-api-article', args=['12-1-A (play)'])
        ).status_code == 200

    def test_authors(self):
        assert self.client.get(reverse('rg-api-authors')).status_code == 200

    def test_author(self):
        assert self.client.get(
            reverse('rg-api-author', args=['Kaori Akiyama'])
        ).status_code == 200

    def test_sources(self):
        assert self.client.get(reverse('rg-api-sources')).status_code == 200

    #def test_source(self):
    #    assert self.client.get(
    #        reverse('rg-api-source', args=['en-littletokyousa-1'])
    #    ).status_code == 200

    def test_browse(self):
        assert self.client.get(reverse('rg-api-browse')).status_code == 200

    def test_browse_categories(self):
        assert self.client.get(
            reverse('rg-api-categories')
        ).status_code == 200

    def test_browse_category(self):
        assert self.client.get(
            reverse('rg-api-category', args=['Arts'])
        ).status_code == 200

    def test_browse_field(self):
        assert self.client.get(
            reverse('rg-api-browse-field', args=['genre'])
        ).status_code == 200

    def test_browse_field_value(self):
        assert self.client.get(
            reverse('rg-api-browse-fieldvalue', args=['genre', 'Art'])
        ).status_code == 200

    def test_facets(self):
        assert self.client.get(reverse('rg-api-facets')).status_code == 200

    def test_facet(self):
        assert self.client.get(
            reverse('rg-api-facet', args=['facility'])
        ).status_code == 200
        assert self.client.get(
            reverse('rg-api-facet', args=['topics'])
        ).status_code == 200

    def test_facet_terms(self):
        assert self.client.get(
            reverse('rg-api-terms', args=['facility'])
        ).status_code == 200
        assert self.client.get(
            reverse('rg-api-terms', args=['topics'])
        ).status_code == 200

    def test_term(self):
        assert self.client.get(
            reverse('rg-api-term', args=['facility-7'])
        ).status_code == 200
        assert self.client.get(
            reverse('rg-api-term', args=['topics-120'])
        ).status_code == 200

    def test_term_objects(self):
        assert self.client.get(
            reverse('rg-api-term-objects', args=['facility-7'])
        ).status_code == 200
        assert self.client.get(
            reverse('rg-api-term', args=['topics-120'])
        ).status_code == 200
