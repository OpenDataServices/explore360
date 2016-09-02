from django import template
import math
import datetime
import dateutil.parser as date_parser
import strict_rfc3339
import json
from grantnav import provenance
import jsonref
from django.conf import settings

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


def flatten_dict(data, path=tuple()):
    schema = jsonref.load_uri(settings.GRANT_SCHEMA)
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

ADDITIONAL_FIELDS = {"recipientDistrictName": "Recipient District",
                     "recipientRegionName": "Recipient Region",
                     "recipientWardName": "Recipient Ward"}

SKIP_KEYS = ["Identifier", "Title", "Description", "filename",
             "amountAwarded", "Currency",
             "awardDate", "Recipient Org: Name",
             "Recipient Org: Identifier",
             "recipientOrganization: id_and_name",
             "Funding Org: Name",
             "Funding Org: Identifier",
             "fundingOrganization: id_and_name", "recipientLocation"] + list(ADDITIONAL_FIELDS.keys())


@register.filter(name='flatten')
def flatten(d):
    return sorted([(key, value) for key, value in flatten_dict(d)
                  if key not in SKIP_KEYS])


@register.filter(name='get_additional_fields')
def get_additional_fields(data):
    additional_fields = []
    try:
        facet_org_name = get_facet_org_name(data['recipientOrganization'][0]["id_and_name"])
        if facet_org_name != data['recipientOrganization'][0]["name"]:
            additional_fields.append(('Alternate Recipient Name', facet_org_name))
    except (KeyError, IndexError, TypeError):
        pass

    for field_name, name in sorted(ADDITIONAL_FIELDS.items()):
        value = data.get(field_name)
        if value:
            additional_fields.append((name, value))
    return additional_fields


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


@register.filter(name='get_amount')
def get_amount(amount):
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


@register.filter(name='get_amount_range')
def get_amount_range(bucket):
    from_ = get_amount(int(bucket.get('from')))
    to_ = bucket.get('to')
    if to_:
        to_ = get_amount(int(to_))
    if to_ == from_:
        return from_
    if not to_:
        return '£' + from_ + ' +'
    return '£' + from_ + ' - ' + '£' + to_


@register.filter(name='get_facet_org_name')
def get_facet_org_name(facet):
    return json.loads(facet)[0]


@register.filter(name='get_currency_list')
def get_currency_list(aggregate):
    return ", ".join(bucket["key"].upper() for bucket in aggregate["buckets"])


@register.filter(name='get_dataset')
def get_dataset(grant):
    try:
        return provenance.by_identifier[grant['source']['filename'].split('.')[0]]
    except KeyError:
        return None


@register.filter(name='get_current_sort')
def get_current_sort(query):
    for key, value in query['sort'].items():
        return key + " " + value["order"]
