from unittest.mock import Mock, patch
import pytest
import requests
from agroshift.geography import search_places
from agroshift.climate import Window
from agroshift.power import DataError


def test_place_search_and_country_filter():
    response = Mock()
    response.json.return_value = {'results': [{'name':'Anuradhapura','latitude':8.3,'longitude':80.4}]}
    with patch('agroshift.geography.requests.get', return_value=response) as call:
        assert search_places('Anuradhapura','LK')[0]['latitude']==8.3
        assert call.call_args.kwargs['params']['countryCode']=='LK'


@pytest.mark.parametrize('payload', [[], {'results':'bad'}, {'results':[{'name':'bad','latitude':999,'longitude':0}]}])
def test_malformed_place_response(payload):
    response=Mock()
    response.json.return_value=payload
    with patch('agroshift.geography.requests.get',return_value=response), pytest.raises(DataError):
        search_places('Town')


def test_place_timeout_fallback():
    with patch('agroshift.geography.requests.get',side_effect=requests.Timeout), pytest.raises(DataError,match='Enter coordinates'):
        search_places('Town')


def test_invalid_recurring_date_is_actionable():
    with pytest.raises(DataError,match='February 28'):
        Window(2,29,5,30).dates(2023)
