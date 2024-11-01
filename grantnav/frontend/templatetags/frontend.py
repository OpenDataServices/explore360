import datetime
import json
import math

import dateutil.parser as date_parser
import jsonref
import strict_rfc3339
from django import template
from django.conf import settings

from grantnav import provenance
from grantnav import utils

register = template.Library()


@register.filter(name='get')
def get(d, k):
    return d.get(k, None)


def flatten_schema_titles(schema, path='', title_path=''):
    for field, property in schema['properties'].items():
        title = property.get('title') or field
        if property['type'] == 'array':
            if property['items']['type'] == 'object':
                yield from flatten_schema_titles(property['items'], path + ': ' + field, title_path + ': ' + title)
            else:
                yield ((path + ': ' + field).lstrip(': '), (title_path + ': ' + title).lstrip(': '))
        if property['type'] == 'object':
            yield from flatten_schema_titles(property, path + '/' + field, title_path + ': ' + title)
        else:
            yield ((path + ': ' + field).lstrip(': '), (title_path + ': ' + title).lstrip(': '))


# Load/fetch the schema once on module loading instead of per run
# of the function
schema = jsonref.load_uri(settings.GRANT_SCHEMA)


def flatten_dict(data, path=tuple()):
    schema_titles = dict(flatten_schema_titles(schema))

    for key, value in data.items():
        field = ": ".join(path + (key,))
        if isinstance(value, list):
            string_list = []
            for item in value:
                if isinstance(item, dict):
                    yield from flatten_dict(item, path + (key,))
                if isinstance(item, str):
                    string_list.append(item)
            if string_list:
                yield schema_titles.get(field) or field, ", ".join(string_list)
        elif isinstance(value, dict):
            yield from flatten_dict(value, path + (key,))
        else:
            yield schema_titles.get(field) or field, value


SKIP_KEYS = ["Identifier", "Title", "Description", "filename",
             "amountAwarded", "Currency",
             "awardDate", "Recipient Org: Name",
             "Recipient Org: Identifier",
             "recipientOrganization: id_and_name",
             "Funding Org: Name",
             "Funding Org: Identifier",
             "fundingOrganization: id_and_name", "recipientLocation",
             "awardDateDateOnly", "plannedDates: endDateDateOnly",
             "plannedDates: startDateDateOnly",
             "additional_data_added", "title_and_description",
             # https://github.com/ThreeSixtyGiving/grantnav/issues/795
             "grantProgramme: title_keyword",
             "simple_grant_type",
             ]


@register.filter(name='flatten')
def flatten(d):
    return sorted([(key, value) for key, value in flatten_dict(d)
                  if key not in SKIP_KEYS])


@register.filter(name='half_sorted_items')
def half_grant(grant, half):
    sorted_list = sorted(grant.items(), key=lambda a: a[0].lower())
    if half == 1:
        return sorted_list[:math.floor(len(grant) / 2)]
    else:
        return sorted_list[math.floor(len(grant) / 2):]


@register.filter(name='get_title')
def get_title(d):
    title = d.get('title')
    if title:
        return title
    else:
        return d.get('id')


@register.filter(name='get_name')
def get_name(d):
    name = d.get('name')
    if name:
        return name
    else:
        return d.get('id')


@register.filter(name='get_currency')
def get_currency(d):
    currency = d.get('currency')
    if not currency:
        return ''
    if currency.lower() == 'gbp':
        return '£'
    else:
        return currency + ' '


@register.filter(name='reverse_minus')
def reverse_minus(minus_value, value):
    return value - minus_value


@register.filter(name='get_amount')
def get_amount(amount):
    if isinstance(amount, dict):
        amount = amount['value']
    try:
        return "{:,.0f}".format(amount)
    except ValueError:
        return amount


@register.filter(name='get_date')
def get_date(date):
    valid = strict_rfc3339.validate_rfc3339(date)
    if not valid:
        try:
            datetime.datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return date
    return date_parser.parse(date).strftime("%d %b %Y")


@register.filter(name='get_year')
def get_year(date):
    valid = strict_rfc3339.validate_rfc3339(date)
    if not valid:
        try:
            datetime.datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return date
    return date.split("-")[0]


@register.filter(name='currency_symbol')
def currency_symbol(currency):
    return utils.CURRENCY_SYMBOLS.get(currency.upper(), '')


@register.filter(name='get_amount_range')
def get_amount_range(bucket, currency):
    from_ = get_amount(int(bucket.get('from')))
    to_ = bucket.get('to')
    prefix = utils.currency_prefix(currency)
    if to_:
        to_ = get_amount(int(to_))
    if to_ == from_:
        return from_
    if not to_:
        return prefix + from_ + ' +'
    return prefix + from_ + ' - ' + prefix + to_


@register.filter(name='get_facet_org_name')
def get_facet_org_name(facet):
    return json.loads(facet)[0]


@register.filter(name='get_facet_org_id')
def get_facet_org_id(facet):
    return json.loads(facet)[1]


@register.filter(name='get_currency_list')
def get_currency_list(aggregate):
    return ", ".join(bucket["key"].upper() for bucket in aggregate["buckets"])


@register.filter(name='get_dataset')
def get_dataset(grant):
    try:
        return provenance.by_identifier[provenance.identifier_from_filename(grant['source']['filename'])]
    except KeyError:
        return None


@register.filter(name='get_current_sort')
def get_current_sort(query):
    if query:
        for key, value in query['sort'].items():
            return key + " " + value["order"]
    else:
        return None


@register.filter(name='min_yearmonth')
def min_yearmonth(date):
    return utils.date_to_yearmonth(date)


@register.filter(name='max_yearmonth')
def max_yearmonth(date):
    return utils.date_to_yearmonth(date, True)


@register.filter(name='human_format')
def human_format(num):
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return '%.0f%s' % (num, ['', 'k', 'm', 'b'][magnitude])


@register.filter(name='concat')
def concat(str_a, str_b):
    """concat two strings"""
    return f"{str_a}{str_b}"


@register.filter(name="to_json")
def to_json(data):
    return json.dumps(data)


@register.filter(name="estimate_csv_file_size")
def estimate_csv_file_size(num_grants):
    return num_grants * 430
