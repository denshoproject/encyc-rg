from collections import OrderedDict
import logging
logger = logging.getLogger(__name__)

from django import forms
from django.conf import settings

from . import models


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


class SearchForm(forms.Form):
    field_order = models.PAGE_SEARCH_FIELDS
    search_results = None
    
    def __init__( self, *args, **kwargs ):
        if kwargs.get('search_results'):
            self.search_results = kwargs.pop('search_results')
        super(SearchForm, self).__init__(*args, **kwargs)
        self.fields = self.construct_form(self.search_results)

    def construct_form(self, search_results):
        fields = [
            (
                'fulltext',
                forms.CharField(
                    max_length=255,
                    required=False,
                    widget=forms.TextInput(
                        attrs={
                            'id': 'id_query',
                            'class': 'form-control',
                            'placeholder': 'Search...',
                        }
                    ),
                )
            )
        ]
        
        # fill in options and doc counts from aggregations
        if search_results and search_results.aggregations:
            for fieldname in search_results.aggregations.keys():
                choices = [
                    (
                        item['key'],
                        '%s (%s)' % (item['key'], item['doc_count'])
                    )
                    for item in search_results.aggregations[fieldname]
                ]
                if choices:
                    fields.append((
                        fieldname,
                        forms.MultipleChoiceField(
                            label=models.PAGE_BROWSABLE_FIELDS.get(
                                fieldname, fieldname),
                            choices=choices,
                            required=False,
                            widget=forms.SelectMultiple(
                                attrs={
                                    'class': 'form-control border-color-2',
                                }
                            ),
                        ),
                    ))
        
        # Django Form object takes an OrderedDict rather than list
        fields = OrderedDict(fields)
        return fields
