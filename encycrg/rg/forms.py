import logging
logger = logging.getLogger(__name__)

from django import forms
from django.conf import settings


class SearchFormBasic(forms.Form):
    fulltext = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(
            attrs={
                'id': 'id_query',
                'class': 'form-control',
                'placeholder': 'Search...',
            }
        )
    )


CATEGORY_CHOICES = [
    ('Arts', 'Arts'),
    ('Camps', 'Camps'),
    ('Chroniclers', 'Chroniclers'),
    ('Definitions', 'Definitions'),
    ('Legal', 'Legal'),
    ('Military', 'Military'),
    ('Newspapers', 'Newspapers'),
    ('Organizations', 'Organizations'),
    ('People', 'People'),
    ('Prewar', 'Prewar'),
]
GENRE_CHOICES = []
TOPICS_CHOICES = [
]
FACILITY_CHOICES = [
    ('Manzanar', 'Manzanar'),
    ('Minidoka', 'Minidoka'),
]

class SearchForm(forms.Form):
    fulltext = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(
            attrs={
                'id': 'id_query',
                'class': 'form-control',
                'placeholder': 'Search...',
            }
        )
    )
    
    filter_category = forms.MultipleChoiceField(
        choices=CATEGORY_CHOICES,
        required=False,
    )
    filter_genre = forms.MultipleChoiceField(
        choices=GENRE_CHOICES,
        required=False,
    )
    filter_topics = forms.MultipleChoiceField(
        choices=TOPICS_CHOICES,
        required=False,
    )
    filter_facility = forms.MultipleChoiceField(
        choices=FACILITY_CHOICES,
        required=False,
    )
