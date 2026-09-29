import logging
import re

import requests
from django.core.cache import cache

logger = logging.getLogger(__name__)

VIACEP_URL = 'https://viacep.com.br/ws/{cep}/json/'
BRASILAPI_URL = 'https://brasilapi.com.br/api/cep/v2/{cep}'
PROVIDER_TIMEOUT_SECONDS = 3
CACHE_TTL_SECONDS = 60 * 60 * 24


class InvalidCep(Exception):
    pass


class CepNotFound(Exception):
    pass


class CepServiceUnavailable(Exception):
    pass


class _ProviderUnavailable(Exception):
    pass


def _clean(value):
    return (value or '').strip()


def _get_json(url, ok_statuses=(200,)):
    """Returns (status_code, parsed_json); raises _ProviderUnavailable on any failure."""
    try:
        response = requests.get(url, timeout=PROVIDER_TIMEOUT_SECONDS)
    except requests.Timeout as err:
        raise _ProviderUnavailable('timeout') from err
    except requests.RequestException as err:
        raise _ProviderUnavailable(f'connection error: {err}') from err

    if response.status_code not in ok_statuses:
        raise _ProviderUnavailable(f'unexpected status {response.status_code}')
    if response.status_code == 404:
        return 404, None
    try:
        return response.status_code, response.json()
    except ValueError as err:
        raise _ProviderUnavailable('invalid JSON') from err


def _fetch_viacep(cep):
    _, data = _get_json(VIACEP_URL.format(cep=cep))
    if not isinstance(data, dict):
        raise _ProviderUnavailable('unexpected payload')
    if data.get('erro') in (True, 'true'):
        return None
    return {
        'address': _clean(data.get('logradouro')),
        'neighborhood': _clean(data.get('bairro')),
        'city': _clean(data.get('localidade')),
        'state': _clean(data.get('uf')),
    }


def _fetch_brasilapi(cep):
    status_code, data = _get_json(BRASILAPI_URL.format(cep=cep), ok_statuses=(200, 404))
    if status_code == 404:
        return None
    if not isinstance(data, dict):
        raise _ProviderUnavailable('unexpected payload')
    return {
        'address': _clean(data.get('street')),
        'neighborhood': _clean(data.get('neighborhood')),
        'city': _clean(data.get('city')),
        'state': _clean(data.get('state')),
    }


_PROVIDERS = (('viacep', _fetch_viacep), ('brasilapi', _fetch_brasilapi))


def lookup_cep(raw_cep):
    digits = re.sub(r'\D', '', raw_cep or '')
    if len(digits) != 8:
        raise InvalidCep(raw_cep)

    cache_key = f'cep:{digits}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    not_found = False
    for name, fetch in _PROVIDERS:
        try:
            address = fetch(digits)
        except _ProviderUnavailable as err:
            logger.warning('CEP provider %s failed: %s', name, err)
            continue
        if address is None:
            not_found = True
            continue
        result = {'postal_code': digits, **address}
        cache.set(cache_key, result, CACHE_TTL_SECONDS)
        return result

    if not_found:
        raise CepNotFound(digits)
    raise CepServiceUnavailable(digits)
