import collections
import copy
import csv
import datetime
import json
import re
import urllib
from itertools import chain
import dateutil.parser as date_parser
from dateutil.relativedelta import relativedelta

from django.http import Http404, JsonResponse
from django.http import HttpResponse, StreamingHttpResponse
from django.views.decorators.clickjacking import xframe_options_exempt
from django.shortcuts import render, redirect
from django.utils.http import urlencode
from django.urls import reverse
from django.core.cache import cache

from elasticsearch.helpers import scan
import elasticsearch.exceptions

from grantnav import provenance, csv_layout, utils
from grantnav.search import get_es
from grantnav.index import get_index
from grantnav.frontend.search_helpers import get_results, get_request_type_and_size, get_terms_facets, get_data_from_path
import grantnav.frontend.search_helpers as helpers
from grantnav.frontend.org_utils import new_ordered_names, new_org_ids, new_stats_by_currency, get_org, OrgNotFoundError
from dataload.import_to_elasticsearch import AGE_BIN_LABELS


BASIC_FILTER = [
    {"bool": {"should": []}},  # Funding Orgs
    {"bool": {"should": []}},  # Recipient Orgs
    {"bool": {"should": [], "must": {}, "minimum_should_match": 1}},  # Amount Awarded Fixed
    {"bool": {"should": {"range": {"amountAwarded": {}}}, "must": {}, "minimum_should_match": 1}},  # Amount Awarded
    {"bool": {"should": []}},  # Award Year
    {"bool": {"should": []}},  # additional_data.recipientRegionName
    {"bool": {"should": []}},  # additional_data.recipientDistrictName
    {"bool": {"should": []}},  # currency
    {"bool": {"should": []}},  # additional_data.TSGFundingOrgType
    {"bool": {"should": {"range": {"awardDate": {}}}, "must": {}, "minimum_should_match": 1}},   # Date range
    {"bool": {"should": []}},  # Programme Title
    {"bool": {"should": []}},  # additional_data.TSGRecipientType
    {"bool": {"should": []}},  # simple_grant_type
    # Used for Aggregates API
    {"bool": {"should": []}},  # additional_data.recipientOrgInfos.organisationTypePrimary
    {"bool": {"should": []}},  # additional_data.GNRecipientOrgInfo0.ageWhenAwarded
    # End used for Aggregates

    {"bool": {"should": []}},  # additional_data.GNRecipientOrgRegionName
    {"bool": {"should": []}},  # additional_data.GNRecipientOrgDistrictName
    {"bool": {"should": []}},  # additional_data.GNBeneficiaryRegionName
    {"bool": {"should": []}},  # additional_data.GNBeneficiaryDistrictName
    # County
    {"bool": {"should": []}},  # additional_data.GNBeneficiaryCountyName
    {"bool": {"should": []}},  # additional_data.GNRecipientCountyName
    {"bool": {"should": []}},  # additional_data.GNBestCountyName
]

TermFacet = collections.namedtuple('TermFacet', 'field_name param_name filter_index display_name is_json facet_size')

TERM_FACETS = [
    TermFacet("fundingOrganization.id_and_name", "fundingOrganization", 0, "Funders", True, 1),  # facet size 1 so template knows if there are results.
    TermFacet("recipientOrganization.id_and_name", "recipientOrganization", 1, "Recipients", True, 1),
    TermFacet("grantProgramme.title_keyword", "grantProgramme", 10, "Programme Titles", False, 1),
    TermFacet("additional_data.recipientRegionName", "recipientRegionName", 5, "Regions", False, 5000),
    TermFacet("additional_data.recipientDistrictName", "recipientDistrictName", 6, "Districts", False, 5000),
    TermFacet("additional_data.TSGFundingOrgType", "fundingOrganizationTSGType", 8, "Organisation Type", False, 5000),
    TermFacet("currency", "currency", 7, "Currency", False, 5000),
    TermFacet("additional_data.TSGRecipientType", "recipientTSGType", 11, "Recipient Type", False, 5000),
    TermFacet("simple_grant_type", "simple_grant_type", 12, "Regrant Type", False, 5000),
    TermFacet("additional_data.recipientOrgInfos.organisationTypePrimary", "recipientOrganizationType", 13, "Recipient Organisation Type", False, 5000),
    TermFacet("additional_data.GNRecipientOrgInfo0.ageWhenAwarded", "orgAgeWhenAwarded", 14, "Age of Recipient Org", False, 5000),
    TermFacet("additional_data.GNRecipientOrgRegionName", "recipientOrgRegionName", 15, "Recipient Organisation Country and Region", False, 5000),
    TermFacet("additional_data.GNRecipientOrgDistrictName", "recipientOrgDistrictName", 16, "Recipient Organisation District", False, 5000),
    TermFacet("additional_data.GNBeneficiaryRegionName", "beneficiaryRegionName", 17, "Beneficiary Region and Country", False, 5000),
    TermFacet("additional_data.GNBeneficiaryDistrictName", "beneficiaryDistrictName", 18, "Beneficiary District", False, 5000),
    TermFacet("additional_data.GNBeneficiaryCountyName", "beneficiaryCountyName", 19, "Beneficiary County", False, 5000),
    TermFacet("additional_data.GNRecipientOrgCountyName", "recipientOrgCountyName", 20, "Recipient County", False, 5000),
    TermFacet("additional_data.GNBestCountyName", "bestCountyName", 21, "Best County", False, 5000),
]

SIZE = 20

BASIC_QUERY = {"query": {"bool": {"must":
                                  {"query_string": {"query": "", "default_field": "*"}},
                                  "filter": BASIC_FILTER}},
               "sort": {"_score": {"order": "desc"}},
               "aggs": {}}

for term_facet in TERM_FACETS:
    BASIC_QUERY['aggs'][term_facet.param_name] = {"terms": {"field": term_facet.field_name,
                                                            "size": term_facet.facet_size}}

FIXED_AMOUNT_RANGES = [
    {"from": 0, "to": 500},
    {"from": 500, "to": 1000},
    {"from": 1000, "to": 5000},
    {"from": 5000, "to": 10000},
    {"from": 10000, "to": 50000},
    {"from": 50000, "to": 100000},
    {"from": 100000, "to": 1000000},
    {"from": 1000000, "to": 10000000},
    {"from": 10000000}
]

CHARITY_INCOME_FIXED_AMOUNT_RANGES = [
    {"from": 0, "to": 10000},
    {"from": 10000, "to": 100000},
    {"from": 100000, "to": 250000},
    {"from": 250000, "to": 500000},
    {"from": 500000, "to": 1000000},
    {"from": 1000000, "to": 10000000},
    {"from": 10000000}
]

SEARCH_SUMMARY_AGGREGATES = {
    "recipient_orgs": {"cardinality": {"field": "additional_data.GNCanonicalRecipientOrgId", "precision_threshold": 40000}},
    "funding_orgs": {"cardinality": {"field": "additional_data.GNCanonicalFundingOrgId", "precision_threshold": 40000}},
    "recipient_indi": {"cardinality": {"field": "recipientIndividual.id", "precision_threshold": 40000}},
    "currency_stats": {
        "terms": {"field": "currency"},
        "aggs": {
            "amount_stats": {"stats": {"field": "amountAwarded"}},
            "largest_grant": {"top_hits": {"size": 1, "sort": [{"amountAwarded": {"order": "desc"}}]}},
            "smallest_grant": {"top_hits": {"size": 1, "sort": [{"amountAwarded": {"order": "asc"}}]}},
        }
    },
    "min_date": {"min": {"field": "awardDate"}},
    "max_date": {"max": {"field": "awardDate"}},
    "earliest_grant": {"top_hits": {"size": 1, "sort": [{"awardDate": {"order": "asc"}}]}},
    "latest_grant": {"top_hits": {"size": 1, "sort": [{"awardDate": {"order": "desc"}}]}},
}


def grants_csv_generator(query, grant_csv_titles, grant_csv_paths):
    yield grant_csv_titles
    es = get_es()
    for result in scan(es, query, index=get_index()):
        result_with_provenance = {
            "result": result["_source"],
            "dataset": provenance.by_identifier.get(provenance.identifier_from_filename(result['_source']['filename']), {})
        }
        line = []
        for path in grant_csv_paths:
            line.append(helpers.get_data_from_path(path, result_with_provenance))
        yield line


def grants_json_generator(query):
    yield '''{
    "license": "See dataset/license within each grant. This file also contains OS data © Crown copyright and database right 2016, Royal Mail data © Royal Mail copyright and Database right 2016, National Statistics data © Crown copyright and database right 2016, see http://grantnav.org/datasets/ for more information.",
    "grants": [\n'''
    es = get_es()
    for num, result in enumerate(scan(es, query, index=get_index())):
        result["_source"]["dataset"] = provenance.by_identifier.get(provenance.identifier_from_filename(result['_source']['filename']), {})
        if num == 0:
            yield json.dumps(result["_source"]) + "\n"
        else:
            yield ", " + json.dumps(result["_source"]) + "\n"
    yield ']}'


class Echo(object):
    def write(self, value):
        return value


def grants_csv_paged(query, grant_csv_paths=csv_layout.grant_csv_paths, grant_csv_titles=csv_layout.grant_csv_titles):
    query.pop('extra_context', None)
    query.pop('aggs', None)
    query['query']['bool']['filter'].append({"term": {"dataType": {"value": "grant"}}})
    pseudo_buffer = Echo()
    writer = csv.writer(pseudo_buffer)
    response = StreamingHttpResponse(
        chain(
            ["\ufeff"],
            (
                writer.writerow(row)
                for row in grants_csv_generator(
                    helpers.clean_for_es(query),
                    grant_csv_paths=grant_csv_paths,
                    grant_csv_titles=grant_csv_titles,
                )
            ),
        ),
        content_type="text/csv",
    )
    response['Content-Disposition'] = 'attachment; filename="grantnav-{0}.csv"'.format(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
    return response


def grants_json_paged(query):
    query.pop('extra_context', None)
    query.pop('aggs', None)
    query['query']['bool']['filter'].append({"term": {"dataType": {"value": "grant"}}})
    response = StreamingHttpResponse(grants_json_generator(helpers.clean_for_es(query)), content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename="grantnav-{0}.json"'.format(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
    return response


def grants_json(query, length, start):
    query.pop('extra_context', None)
    query.pop('aggs', None)
    query['query']['bool']['filter'].append({"term": {"dataType": {"value": "grant"}}})
    try:
        results = get_results(helpers.clean_for_es(query), length, start)
    except elasticsearch.exceptions.RequestError as e:
        if e.error == 'search_phase_execution_exception':
            results = {"hits": {"total": {"value": 0}, "hits": []}}
    result_list = []
    for result in results["hits"]["hits"]:
        grant = result["_source"]
        try:
            grant["awardDate"] = date_parser.parse(grant["awardDate"]).strftime("%d %b %Y")
        except ValueError:
            pass
        try:
            grant["amountAwarded"] = utils.currency_prefix(grant.get("currency")) + "{:,.0f}".format(grant["amountAwarded"])
        except ValueError:
            pass
        grant["description"] = grant.get("description", "")
        grant["title"] = grant.get("title", "")
        result_list.append(grant)

    return {'data': result_list,
            'recordsTotal': results["hits"]["total"]['value'],
            'recordsFiltered': results["hits"]["total"]['value']}


def org_csv_generator(data, org_type):
    if org_type == 'funder':
        yield csv_layout.funder_csv_titles
    elif org_type == 'recipient':
        yield csv_layout.recipient_csv_titles

    for result in data:
        line = []
        for path in csv_layout.org_csv_paths:
            line.append(get_data_from_path(path, result))
        yield line


def orgs_csv_paged(data, org_type):
    pseudo_buffer = Echo()
    writer = csv.writer(pseudo_buffer)
    response = StreamingHttpResponse(chain(['\ufeff'], (writer.writerow(row) for row in org_csv_generator(data, org_type))), content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="grantnav-{0}.csv"'.format(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
    return response


def create_amount_aggregate(json_query):
    json_query["aggs"]["amountAwardedFixed"] = {"range": {"field": "amountAwarded", "ranges": FIXED_AMOUNT_RANGES}}


def create_latest_charity_income_aggregate(json_query):
    json_query["aggs"]["latestCharityIncomeFixed"] = {"range": {"field": "additional_data.GNRecipientOrgInfo0.latestIncome", "ranges": CHARITY_INCOME_FIXED_AMOUNT_RANGES}}


def get_amount_facet_fixed(request, context, original_json_query):
    json_query = copy.deepcopy(original_json_query)
    json_query["aggs"]["amountAwardedFixed"] = {"range": {"field": "amountAwarded", "ranges": FIXED_AMOUNT_RANGES}}
    try:
        current_filter = json_query["query"]["bool"]["filter"][2]["bool"]["should"]
    except KeyError:
        json_query["query"]["bool"]["filter"] = copy.deepcopy(BASIC_FILTER)
        current_filter = json_query["query"]["bool"]["filter"][2]["bool"]["should"]

    main_results = context["results"]

    json_query["query"]["bool"]["filter"][2]["bool"]["should"] = []

    existing_currency, current_currency = context['existing_currency'], context['current_currency']

    if current_currency and not existing_currency:
        json_query["query"]["bool"]["filter"][2]["bool"]["must"] = {"term": {"currency": current_currency}}

    json_query["query"]["bool"]["filter"][2]["bool"]["minimum_should_match"] = 0

    if current_filter:
        results = get_results(json_query)
    else:
        results = main_results

    input_range = json_query["query"]["bool"]["filter"][3]["bool"]["should"]["range"]["amountAwarded"]
    new_filter = copy.deepcopy(current_filter)
    if new_filter or input_range:
        new_json_query = copy.deepcopy(original_json_query)
        new_json_query["query"]["bool"]["filter"][2]["bool"]["should"] = []
        new_json_query["query"]["bool"]["filter"][2]["bool"]["must"] = {}
        new_json_query["query"]["bool"]["filter"][3]["bool"]["should"]["range"]["amountAwarded"] = {}
        new_json_query["query"]["bool"]["filter"][3]["bool"]["must"] = {}
        results["aggregations"]["amountAwardedFixed"]["clear_url"] = request.path + '?' + create_parameters_from_json_query(new_json_query)

    for bucket in results["aggregations"]["amountAwardedFixed"]['buckets']:
        new_json_query = copy.deepcopy(original_json_query)
        new_filter = []
        new_range = {"gte": bucket["from"]}
        to_ = bucket.get("to")
        if to_:
            new_range["lt"] = to_
        for filter in current_filter:
            if filter["range"]["amountAwarded"] == new_range:
                bucket["selected"] = True
            else:
                new_filter.append(filter)
        if not bucket.get("selected"):
            new_filter.append({"range": {"amountAwarded": new_range}})

        new_json_query["query"]["bool"]["filter"][2]["bool"]["should"] = new_filter
        if not new_filter:
            new_json_query["query"]["bool"]["filter"][2]["bool"]["must"] = {}
        elif not existing_currency and current_currency:
            new_json_query["query"]["bool"]["filter"][2]["bool"]["must"] = {"term": {"currency": current_currency}}

        bucket["url"] = request.path + '?' + create_parameters_from_json_query(new_json_query)

        if bucket.get("selected"):
            display_value = "{}{:,}".format(utils.currency_prefix(current_currency), int(bucket["from"]))
            if to_:
                display_value = str(display_value) + " - " + "{}{:,}".format(utils.currency_prefix(current_currency), int(to_))
            else:
                display_value = str(display_value) + "+"

            context["selected_facets"]["Amounts"].append({"url": bucket["url"], "display_value": display_value})

    if input_range:
        new_json_query = copy.deepcopy(original_json_query)
        lte, gte = input_range.get('lte'), input_range.get('gte')
        if not gte:
            gte = 0
        display_value = "{}{:,}".format(utils.currency_prefix(current_currency), int(gte))
        if lte:
            display_value = str(display_value) + " - " + "{}{:,}".format(utils.currency_prefix(current_currency), int(lte))
        else:
            display_value = str(display_value) + "+"
        new_json_query["query"]["bool"]["filter"][3]["bool"]["should"]["range"]["amountAwarded"] = {}
        new_json_query["query"]["bool"]["filter"][3]["bool"]["must"] = {}

        context["selected_facets"]["Amounts"].append({"url": request.path + '?' + create_parameters_from_json_query(new_json_query), "display_value": display_value})

    main_results["aggregations"]["amountAwardedFixedOriginal"] = main_results["aggregations"]["amountAwardedFixed"]
    main_results["aggregations"]["amountAwardedFixed"] = results["aggregations"]["amountAwardedFixed"]


def create_date_aggregate(json_query):
    json_query["aggs"]["awardYear"] = {"date_histogram": {"field": "awardDate", "format": "yyyy", "interval": "year", "order": {"_key": "desc"}}}


def get_date_facets(request, context, json_query):
    json_query = copy.deepcopy(json_query)

    # Year filter
    try:
        current_filter = json_query["query"]["bool"]["filter"][4]["bool"]["should"]
    except KeyError:
        json_query["query"]["bool"]["filter"] = copy.deepcopy(BASIC_FILTER)
        current_filter = json_query["query"]["bool"]["filter"][4]["bool"]["should"]
    main_results = context["results"]
    if current_filter:
        json_query["query"]["bool"]["filter"][4]["bool"]["should"] = []
        create_date_aggregate(json_query)
        results = get_results(json_query)

        # Look for current filters applied, and add them to selected_facets
        # This must be done independently of checking the years buckets available (the next step).
        # It's possible to get in a state in the no results page where the year filter is applied
        # but the buckets that come back don't include that filter.
        # In that case the filter isn't shown as a selected facet to the user and they can't clear it.
        # eg search for "dogs", filter by "2020", search for "parrots" - no grants for parrots were made in 2020
        #    so it doesn't appear in the buckets but we must show "2020" as on selected facet to the user!
        for filter in current_filter:
            try:
                year = filter['range']['awardDate']['gte'].split("|")[0]
                filter_values = [f for f in current_filter if f['range']['awardDate']['gte'].split("|")[0] != year]
                new_json_query = copy.deepcopy(json_query)
                new_json_query["query"]["bool"]["filter"][4]["bool"]["should"] = filter_values
                url = request.path + '?' + create_parameters_from_json_query(new_json_query)
                context["selected_facets"]["Award Year"].append({"url": url, "display_value": year})
            except KeyError:
                pass

    else:
        results = context["results"]

    # Check year buckets available, add URL
    for bucket in results['aggregations']['awardYear']['buckets']:
        range = {'format': 'year'}
        value = bucket.get("key_as_string")
        range["gte"] = value + "||/y"
        range["lte"] = value + "||/y"

        filter_values = [filter["range"]['awardDate'] for filter in current_filter]

        if range in filter_values:
            bucket["selected"] = True
            range['format'] = 'year'
            filter_values.remove(range)
        else:
            range['format'] = 'year'
            filter_values.append(range)

        new_filter = [{"range": {"awardDate": value}} for value in filter_values]
        json_query["query"]["bool"]["filter"][4]["bool"]["should"] = new_filter
        bucket["url"] = request.path + '?' + create_parameters_from_json_query(json_query)

    # Get Custom Filter
    try:
        input_range = json_query["query"]["bool"]["filter"][9]["bool"]["should"]["range"]["awardDate"]
    except IndexError:
        # old json_query do not have the new filter
        input_range = []

    # If either Year or Custom filter, add clear_url
    if current_filter or input_range:
        json_query["query"]["bool"]["filter"][4]["bool"]["should"] = []
        json_query["query"]["bool"]["filter"][9]["bool"]["should"]["range"]["awardDate"] = {}
        results['aggregations']["awardYear"]['clear_url'] = request.path + '?' + create_parameters_from_json_query(json_query)

    # If custom filter, add to selected_facets
    if input_range:
        new_json_query = copy.deepcopy(json_query)
        new_json_query["query"]["bool"]["filter"][4]["bool"]["should"] = []
        new_json_query["query"]["bool"]["filter"][9]["bool"]["should"]["range"]["awardDate"] = {}

        lt, gte = input_range.get('lt'), input_range.get('gte')
        display_value = ''
        if gte:
            display_value += f'From: {utils.date_to_yearmonth(gte)} '
        if lt:
            display_value += f'To: {utils.date_to_yearmonth(lt, max=True)}'

        context["selected_facets"]["Award Date"].append({"url": request.path + '?' + create_parameters_from_json_query(new_json_query), "display_value": display_value})

    # We may have changed year buckets available or clear URL - put our changes back in the main results for the user
    main_results['aggregations']["awardYearOriginal"] = main_results['aggregations']["awardYear"]
    main_results['aggregations']["awardYear"] = results['aggregations']["awardYear"]


def totals_query():
    query = {"query": {"match_all": {}}}

    counts = {
        'grants': get_results(query)['hits']['total'],
        'funders': get_results(query, data_type='funder')['hits']['total'],
        'recipient_orgs': get_results(query, data_type='recipient')['hits']['total'],
        'recipient_indi': get_results(
            {
                "size": 0,  # Don't return the docs just the agg
                "aggs": {
                    "recipient_indi": {
                        "cardinality": {
                            "field": "recipientIndividual.id", "precision_threshold": 40000
                        }
                    }
                }
            }
        )["aggregations"]["recipient_indi"]["value"]
    }
    return counts


def home(request):
    results = totals_query()

    context = {}
    context['results'] = results

    return render(request, "home.html", context=context)


def add_advanced_search_information_in_context(context):
    """
    When a user's search query is 2+ words without quotes, with 'and' or 'or'.
    Advanced search information is displayed.
    """
    text_query = context.get('text_query').lower()
    if text_query is not None and len(text_query) > 1:
        if re.search(r'\b and \b', text_query):
            context["advanced_search_info"] = 'The AND keyword (not case-sensitive) means that results must have ' \
                'both words present. If you\'re looking for a phrase that has the word "and" in it, put quotes ' \
                'around the phrase (e.g. "fees and costs").'
        elif re.search(r'\b or \b', text_query):
            context["advanced_search_info"] = 'The OR keyword (not case-sensitive) means that results must have one ' \
                'of the words present. This is the default. If you\'re looking for a phrase that has the word "or" ' \
                'in (e.g. "children or adults"), put quotes around it.'
        elif ' ' in context.get('text_query') \
                and not (text_query.startswith("'") and text_query.endswith("'")) \
                and not (text_query.startswith('"') and text_query.endswith('"')) \
                or '-' in context.get('text_query'):
            context["advanced_search_info"] = 'If you\'re looking for a specific phrase, put quotes around it to ' \
                'refine your search. e.g. "youth clubs".'
    return context


def amount_facet_from_parameters(request, json_query):
    new_filter = []
    for value in request.GET.getlist('amountAwarded'):
        for item in FIXED_AMOUNT_RANGES:
            if value == str(item['from']):
                new_range = {"gte": item["from"]}
                to_ = item.get("to")
                if to_:
                    new_range["lt"] = to_
                new_filter.append({"range": {"amountAwarded": new_range}})

    json_query["query"]["bool"]["filter"][2]["bool"]["should"] = new_filter


def date_facet_from_parameters(request, json_query):
    new_filter = []
    for value in request.GET.getlist("awardDate"):
        new_filter.append(
            {"range": {
                "awardDate": {"format": "year",
                              "gte": value + "||/y",
                              "lte": value + "||/y"}
            }
            }
        )

    json_query["query"]["bool"]["filter"][4]["bool"]["should"] = new_filter


def create_json_query_from_parameters(request):
    ''' Transforms the URL GET parameters of the request into an object (json_query) that is to be used by elasticsearch  '''

    json_query = copy.deepcopy(BASIC_QUERY)
    json_query["query"]["bool"]["must"]["query_string"]["query"] = request.GET.get('query', '*')
    json_query["query"]["bool"]["must"]["query_string"]["default_field"] = request.GET.get('default_field', '*')

    sort_order = request.GET.get('sort', '').split()
    if sort_order and len(sort_order) == 2:
        sort = {sort_order[0]: {"order": sort_order[1]}}
        json_query["sort"] = sort

    amount_filter = {}
    min_amount = request.GET.get('min_amount')
    if min_amount:
        amount_filter['gte'] = min_amount
    max_amount = request.GET.get('max_amount')
    if max_amount:
        amount_filter['lte'] = max_amount
    json_query["query"]["bool"]["filter"][3]["bool"]["should"]["range"]["amountAwarded"] = amount_filter

    date_filter = {}
    recency_period = request.GET.get('recency_period')
    if recency_period:
        min_date = (datetime.datetime.today() - relativedelta(months=int(recency_period))).strftime('%Y-%m-%d')
        max_date = datetime.datetime.today().strftime('%Y-%m-%d')
    else:
        min_date = utils.yearmonth_to_date(request.GET.get('min_date', ''))
        max_date = utils.yearmonth_to_date(request.GET.get('max_date', ''), True)

    if min_date:
        date_filter['gte'] = min_date
    if max_date:
        date_filter['lt'] = max_date

    json_query["query"]["bool"]["filter"][9]["bool"]["should"]["range"]["awardDate"] = date_filter

    for term_facet in TERM_FACETS:
        helpers.term_facet_from_parameters(request, json_query, term_facet.field_name, term_facet.param_name,
                                           term_facet.filter_index, term_facet.display_name, term_facet.is_json)

    amount_facet_from_parameters(request, json_query)
    date_facet_from_parameters(request, json_query)

    return json_query


def amount_parameters_from_json_query(parameters, json_query):
    values = []
    for filter in json_query["query"]["bool"]["filter"][2]["bool"]["should"]:
        values.append(int(filter['range']['amountAwarded']['gte']))
    parameters['amountAwarded'] = values


def date_parameters_from_json_query(parameters, json_query):
    values = []
    for filter in json_query["query"]["bool"]["filter"][4]["bool"]["should"]:
        values.append(filter['range']['awardDate']['gte'][:-4])  # remove the ||/y from the end
    parameters['awardDate'] = values


def create_parameters_from_json_query(json_query, **extra_parameters):
    ''' Transforms json_query (the query that is passed to elasticsearch) to URL GET parameters'''

    parameters = {}

    must_query = json_query["query"]["bool"]["must"]

    # For the funder/recipient filter ajax request a new must clause is added here making this a list not a dict.
    # would be better for it to be a list always but will be difficult for backwards compatibility currently.
    if isinstance(must_query, list):
        # second search terms should not go in paremeters.
        must_query = must_query[0]

    parameters['query'] = [must_query["query_string"]["query"]]
    parameters['default_field'] = [must_query["query_string"]["default_field"]]

    sort_key = list(json_query["sort"].keys())[0]
    parameters['sort'] = [sort_key + ' ' + json_query['sort'][sort_key]['order']]

    min_amount = json_query["query"]["bool"]["filter"][3]["bool"]["should"]["range"]["amountAwarded"].get('gte')
    if min_amount:
        parameters['min_amount'] = [str(min_amount)]
    max_amount = json_query["query"]["bool"]["filter"][3]["bool"]["should"]["range"]["amountAwarded"].get('lte')
    if max_amount:
        parameters['max_amount'] = [str(max_amount)]

    # Date range filter was only added recently and old URL's will not have it in the JSON. So check it is there first:
    if len(json_query["query"]["bool"]["filter"]) >= 10:
        min_date = json_query["query"]["bool"]["filter"][9]["bool"]["should"]["range"]["awardDate"].get('gte')
        if min_date:
            parameters['min_date'] = [utils.date_to_yearmonth(min_date)]
        max_date = json_query["query"]["bool"]["filter"][9]["bool"]["should"]["range"]["awardDate"].get('lt')
        if max_date:
            parameters['max_date'] = [utils.date_to_yearmonth(max_date, True)]

    for term_facet in TERM_FACETS:
        helpers.term_parameters_from_json_query(parameters, json_query, term_facet.field_name, term_facet.param_name,
                                                term_facet.filter_index, term_facet.display_name, term_facet.is_json)

    amount_parameters_from_json_query(parameters, json_query)
    date_parameters_from_json_query(parameters, json_query)

    parameter_list = []

    for parameter, list_value in parameters.items():
        for value in list_value:
            parameter_list.append((parameter, value))
    for parameter, value in extra_parameters.items():
        parameter_list.append((parameter, value))

    return urlencode(parameter_list)


@xframe_options_exempt
def search_wrapper_xframe_exempt(request, template_name="search.html"):
    response = search(request, template_name)
    return response


def widget_search(request, json_query):
    COLUMN_ORDER = ["_score", "amountAwarded", "awardDate", "fundingOrganization.id_and_name", "recipientOrganization.id_and_name", "description"]
    start = int(request.GET['start'])
    length = int(request.GET['length'])
    search_value = request.GET['search[value]']
    if 'sort' in request.GET:
        order_field = COLUMN_ORDER[int(request.GET['order[0][column]'])]
        order_dir = request.GET['order[0][dir]']
        json_query["sort"] = [{order_field: order_dir}]
    if search_value:
        current_query = json_query["query"]["bool"]["must"]["query_string"]['query']
        json_query["query"]["bool"]["must"] = {"query_string": {"query": current_query + " " + search_value, "default_operator": "and"}}

    json_response = grants_json(json_query, length, start)
    json_response['draw'] = request.GET['draw'],

    return JsonResponse(json_response)


def reorder_recipient_org_age_when_awarded(context):
    """ Put the ES results into a fixed order determined by AGE_BIN_LABELS
        Note this is not a sort - it's a specific ordering.
    """
    org_age_when_awarded_buckets = context["results"]["aggregations"]["orgAgeWhenAwarded"]["buckets"]
    ordered = []

    def find_in_buckets(key):
        for bucket in org_age_when_awarded_buckets:
            if bucket["key"] == key:
                return bucket

    for age in AGE_BIN_LABELS:
        age_found = find_in_buckets(age)
        if age_found:
            ordered.append(age_found)

    context["results"]["aggregations"]["orgAgeWhenAwarded"]["buckets"] = ordered


def redirect_request_to_include_all_org_ids(request):
    """ If someone provides an org-id append all other known org-ids to the query
    This is done so that it doesn't matter which org-id of many for a certain org
    is provided we can still return the results.
    """
    do_redirect = False
    request_get_copy = request.GET.copy()

    for entity_type in [("fundingOrganization", "funder"), ("recipientOrganization", "recipient")]:
        # Match the supplied org-id to any other org-ids in use
        if org_ids := request.GET.getlist(entity_type[0]):
            for org_id in org_ids:
                try:
                    for additional_org_id in get_org(org_id, entity_type[1])["orgIDs"]:
                        if additional_org_id not in org_ids:
                            request_get_copy.appendlist(entity_type[0], additional_org_id)
                            do_redirect = True
                except OrgNotFoundError:
                    pass

    if do_redirect:
        return request.path + '?' + request_get_copy.urlencode()


def search(request, template_name="search.html"):
    [result_format, results_size] = get_request_type_and_size(request)

    context = {}

    try_cache = False

    query = request.GET.urlencode()
    if query:
        context['query_string'] = query
    else:
        context['query_string'] = ""
        try_cache = True

    json_query = {}

    json_query_param = request.GET.get('json_query')
    if json_query_param:
        try:
            # This allows GrantNav to be backward compatible with
            # pre-2020-sprint urls. This isn't ideal and json_query as a GET
            # parameter will need to be phased out including where used in
            # hidden fields in forms in the templates.
            json_query_param = json_query_param.replace('"recipientRegionName"', '"additional_data.recipientRegionName"')
            json_query_param = json_query_param.replace('"recipientDistrictName"', '"additional_data.recipientDistrictName"')
            json_query = json.loads(json_query_param)
            filter_ = json_query['query']['bool']['filter']
            # There were originally 8 filters with the old urls ES now expects all so append
            # the new ones
            if len(filter_) == 8:
                filter_.append({"bool": {"should": []}})  # additional_data.TSGFundingOrgType
                filter_.append({"bool": {"should": {"range": {"awardDate": {}}}, "must": {}, "minimum_should_match": 1}})   # Date range
                filter_.append({"bool": {"should": []}})  # Programme Title
                filter_.append({"bool": {"should": []}})  # additional_data.TSGRecipientType
                filter_.append({"bool": {"should": []}})  # simple_grant_type
                filter_.append({"bool": {"should": []}})  # additional_data.recipientOrgInfos.primaryOrganisationType
                filter_.append({"bool": {"should": []}})  # additional_data.GNRecipientOrgInfo0.ageWhenAwarded
                filter_.append({"bool": {"should": []}})  # additional_data.GNRecipientOrgRegionName
                filter_.append({"bool": {"should": []}})  # additional_data.GNRecipientOrgDistrictName
                filter_.append({"bool": {"should": []}})  # additional_data.GNBeneficiaryRegionName
                filter_.append({"bool": {"should": []}})  # additional_data.GNBeneficiaryDistrictName
                filter_.append({"bool": {"should": []}})  # additional_data.GNBeneficiaryCountyName
                filter_.append({"bool": {"should": []}})  # additional_data.GNRecipientCountyName
                filter_.append({"bool": {"should": []}})  # additional_data.GNBestCountyName
            json_query['aggs'] = {}
            for term_facet in TERM_FACETS:
                json_query['aggs'][term_facet.param_name] = {"terms": {"field": term_facet.field_name,
                                                             "size": term_facet.facet_size}}
        except (ValueError, KeyError):
            json_query = {}

    if not json_query:
        json_query = create_json_query_from_parameters(request)

    default_field = request.GET.get('default_field')

    # URL query backwards compatibility
    # https://github.com/ThreeSixtyGiving/grantnav/issues/541
    # Subsitute _all for * in default_field
    try:
        if "_all" in json_query["query"]["bool"]["must"]["query_string"]["default_field"]:
            json_query["query"]["bool"]["must"]["query_string"]["default_field"] = "*"
            return redirect(request.path + '?' + create_parameters_from_json_query(json_query))
    except KeyError:
        pass
    # End URL query backwards compatibility

    text_query = request.GET.get('text_query')
    if text_query is not None:
        if not text_query:
            text_query = '*'
        try:
            json_query["query"]["bool"]["must"]["query_string"]["query"] = text_query
        except KeyError:
            json_query = copy.deepcopy(BASIC_QUERY)
            json_query["query"]["bool"]["must"]["query_string"]["query"] = text_query

        if default_field:
            json_query["query"]["bool"]["must"]["query_string"]["default_field"] = default_field
        return redirect(request.path + '?' + create_parameters_from_json_query(json_query))

    sort_order = request.GET.get('sort', '').split()
    if sort_order and len(sort_order) == 2:
        new_sort = {sort_order[0]: {"order": sort_order[1]}}
        old_sort = json_query["sort"]
        if new_sort != old_sort:
            json_query["sort"] = new_sort
            return redirect(request.path + '?' + create_parameters_from_json_query(json_query))

    if new_org_ids_included := redirect_request_to_include_all_org_ids(request):
        return redirect(new_org_ids_included)

    results = None
    if json_query:
        try:
            page = int(request.GET.get('page', 1))
            if page < 1:
                page = 1
        except ValueError:
            page = 1

        try:
            context['text_query'] = json_query["query"]["bool"]["must"]["query_string"]["query"]
            default_field = json_query["query"]["bool"]["must"]["query_string"]["default_field"]
        except KeyError:
            json_query = copy.deepcopy(BASIC_QUERY)
            json_query["query"]["bool"]["must"]["query_string"]["query"] = ''
            context['text_query'] = ''
            if default_field:
                json_query["query"]["bool"]["must"]["query_string"]["default_field"] = default_field
            default_field = json_query["query"]["bool"]["must"]["query_string"]["default_field"]

        if result_format == "csv":
            return grants_csv_paged(json_query)
        elif result_format == "json":
            return grants_json_paged(json_query)
        elif result_format == "widgets_api":
            return widget_search(request, json_query)

        if context['text_query'] == '*':
            context['text_query'] = ''

        try:
            create_amount_aggregate(json_query)
            create_date_aggregate(json_query)
            # These aggs are currently only used for display and are not filterable in GN frontend
            create_latest_charity_income_aggregate(json_query)

            json_query['aggs'].update(SEARCH_SUMMARY_AGGREGATES)
            # Actually fetch the results from elasticsearch
            results = None

            if try_cache:
                results = cache.get("empty-query-cache")
                if results:
                    print("Cache hit")

            if not results:
                results = get_results(json_query, results_size, (page - 1) * SIZE)

                # This needs further logic to control cache set
                # if try_cache:
                #    cache.set("empty-query-cache", results)

            for key in SEARCH_SUMMARY_AGGREGATES:
                json_query["aggs"].pop(key)

            json_query["aggs"].pop("awardYear")
            json_query["aggs"].pop("amountAwardedFixed")
        except elasticsearch.exceptions.RequestError as e:
            if e.error == 'search_phase_execution_exception':
                context['search_error'] = True
                return render(request, "search.html", context=context)
            raise

        for hit in results['hits']['hits']:
            hit['source'] = hit['_source']
        context['results'] = results
        context['json_query'] = json.dumps(json_query)
        context['query'] = json_query

        if (view_mode := request.GET.get('view_mode')):
            request.session['view_mode'] = view_mode
            context['view_mode'] = view_mode
        elif 'view_mode' in request.session.keys():
            context['view_mode'] = request.session['view_mode']
        else:
            context['view_mode'] = 'cards'

        current_currency = None
        existing_currency = None
        if json_query["query"]["bool"]["filter"][2]["bool"]["must"]:
            existing_currency = json_query["query"]["bool"]["filter"][2]["bool"]["must"]["term"]["currency"]
            current_currency = existing_currency
        currency_facets = context["results"]['aggregations']['currency']['buckets']
        if not current_currency and currency_facets:
            current_currency = currency_facets[0]['key']
        context['existing_currency'] = existing_currency
        context['current_currency'] = current_currency

        min_amount = request.GET.get('new_min_amount')
        max_amount = request.GET.get('new_max_amount')
        if min_amount or max_amount:
            new_filter = {}
            if min_amount:
                try:
                    new_filter['gte'] = int(min_amount)
                except ValueError:
                    pass
            if max_amount:
                try:
                    new_filter['lte'] = int(max_amount)
                except ValueError:
                    pass
            json_query["query"]["bool"]["filter"][3]["bool"]["should"]["range"]["amountAwarded"] = new_filter
            json_query["query"]["bool"]["filter"][3]["bool"]["must"] = {"term": {"currency": current_currency}}
            return redirect(request.path + '?' + create_parameters_from_json_query(json_query))

        min_date = utils.yearmonth_to_date(request.GET.get('new_min_date', ''))
        max_date = utils.yearmonth_to_date(request.GET.get('new_max_date', ''), True)
        if min_date or max_date:
            new_filter = {}
            if min_date:
                try:
                    new_filter['gte'] = min_date
                except ValueError:
                    pass
            if max_date:
                try:
                    new_filter['lt'] = max_date
                except ValueError:
                    pass
            json_query["query"]["bool"]["filter"][9]["bool"]["should"]["range"]["awardDate"] = new_filter
            return redirect(request.path + '?' + create_parameters_from_json_query(json_query))

        context['selected_facets'] = collections.defaultdict(list)
        helpers.get_clear_all(request, context, json_query, BASIC_FILTER, create_parameters_from_json_query)

        for term_facet in TERM_FACETS:
            get_terms_facets(request, context, json_query, term_facet.field_name, term_facet.param_name,
                             term_facet.filter_index, term_facet.display_name, BASIC_FILTER, create_parameters_from_json_query, term_facet.is_json)

        get_amount_facet_fixed(request, context, json_query)
        get_date_facets(request, context, json_query)

        helpers.get_pagination(request, context, page, create_parameters_from_json_query)

        context['selected_facets'] = dict(context['selected_facets'])

        get_radio_items(context, default_field)
        get_dropdown_filters(context)

        add_advanced_search_information_in_context(context)
        reorder_recipient_org_age_when_awarded(context)

        if result_format == "aggregates_api":
            return context

        context["export_default_fields"] = csv_layout.grants_csv_dict

        return render(request, template_name, context=context)


def filter_search_ajax(request, parent_field=None, child_field=None):
    ''' Ajax request returning the format that select2 libary wants '''

    [result_format, results_size] = get_request_type_and_size(request)

    # We can get these values from the function call or from the GET params
    if not parent_field:
        parent_field = request.GET.get('parent_field', 'fundingOrganization')
    if not child_field:
        child_field = request.GET.get('child_field', 'id_and_name')

    json_query = create_json_query_from_parameters(request)

    size_limit = 100

    if result_format == "aggregates_api":
        size_limit = 100000

    # Only need single aggregate to run for this query
    json_query['aggs'] = {}
    json_query['aggs'][parent_field] = {"terms": {"field": f'{parent_field}.{child_field}', "size": size_limit}}

    new_json_query = copy.deepcopy(json_query)

    new_must = [new_json_query["query"]["bool"]["must"]]

    # the users search from select2
    filter_search = request.GET.get("filter_search")

    if filter_search:
        # split search term by space.
        # for each word in the split add wildcard (*) before and after
        # allow both the original search term and a capitalized version of the word using OR
        # AND all the individual word queries together.
        and_terms = " AND ".join([f"(*{part}* OR *{part.capitalize()}* OR *{part.upper()}* OR *{part.lower()}*)" for part in filter_search.split()])

        new_must.append(
            {"query_string":
                {"query": and_terms, "default_field": f"{parent_field}.{child_field}", "analyze_wildcard": True}}
        )

    new_json_query["query"]["bool"]["must"] = new_must

    results = get_results(new_json_query, 0)

    context = {}

    context['selected_facets'] = collections.defaultdict(list)
    context['results'] = results

    # bool_index is the index # of the facet in BASIC_FILTER
    is_json = True
    if parent_field == 'fundingOrganization':
        bool_index, display_name = 0, 'Funders'
    elif parent_field == 'recipientOrganization':
        bool_index, display_name = 1, 'Recipients'
    elif parent_field == 'grantProgramme':
        bool_index, display_name = 10, 'Grant Programme Titles'
        is_json = False
    elif parent_field == 'additional_data':
        bool_index, display_name = 6, 'District'
        is_json = False

    get_terms_facets(request, context, new_json_query, f'{parent_field}.{child_field}', parent_field, bool_index, display_name,
                     BASIC_FILTER, create_parameters_from_json_query, is_json=is_json, path='/search')

    context['selected_facets'] = dict(context['selected_facets'])

    if result_format == "aggregates_api":
        return results

    output = []

    for bucket in results['aggregations'][parent_field]['buckets']:
        if child_field == 'id_and_name':
            name, id = json.loads(bucket['key'])
            text = name
        else:
            text = bucket['key']
            id = text

        output.append({
            "id": id,
            "text": text,
            "count": bucket['doc_count'],
            "url": bucket['url'],
            "selected": bucket.get("selected", False)
        })

    return JsonResponse(
        {"results": output}
    )


def get_radio_items(context, default_field):
    context['searchRadio'] = []
    context['searchRadio'].append({"value": "*", "name": "All grant fields", "checked": True if default_field == "*" else False})
    context['searchRadio'].append({"value": "additional_data.recipientLocation", "name": "Locations", "checked": True if default_field == "additional_data.recipientLocation" else False})
    context['searchRadio'].append({"value": "recipientOrganization.name", "name": "Recipients", "checked": True if default_field == "recipientOrganization.name" else False})
    context['searchRadio'].append({"value": "grantProgramme.title", "name": "Grant Programme Titles", "checked": True if default_field == "grantProgramme.title" else False})
    context['searchRadio'].append({"value": "title_and_description", "name": "Titles & Descriptions", "checked": True if default_field == "title_and_description" else False})
    context['default_field_name'] = [radioItem['name'] for radioItem in context['searchRadio'] if radioItem['checked'] is True][0]


def get_dropdown_filters(context):
    context['dropdownFilterOptions'] = []
    context['dropdownFilterOptions'].append({"value": "_score desc", "label": "Best Match"})
    context['dropdownFilterOptions'].append({"value": "amountAwarded desc", "label": "Amount - Highest First"})
    context['dropdownFilterOptions'].append({"value": "amountAwarded asc", "label": "Amount - Lowest First"})
    context['dropdownFilterOptions'].append({"value": "awardDate desc", "label": "Award Date - Latest First"})
    context['dropdownFilterOptions'].append({"value": "awardDate asc", "label": "Award Date - Earliest First"})


def flatten_mapping(mapping, current_path=''):
    for key, value in mapping.items():
        sub_properties = value.get('properties')
        if sub_properties:
            yield from flatten_mapping(sub_properties, current_path + "." + key)
        else:
            yield (current_path + "." + key).lstrip(".")


def flatten_schema(schema, path=''):
    for field, property in schema['properties'].items():
        if property['type'] == 'array':
            if property['items']['type'] == 'object':
                yield from flatten_schema(property['items'], path + '.' + field)
            else:
                yield (path + '.' + field).lstrip('.')
        if property['type'] == 'object':
            yield from flatten_schema(property, path + '/' + field)
        else:
            yield (path + '.' + field).lstrip('.')


def grant(request, grant_id):
    query = {"query": {"bool": {"filter":
                [{"term": {"id": grant_id}}]
    }}}
    results = get_results(query, -1)
    if results['hits']['total']['value'] == 0:
        raise Http404
    context = {}
    for hit in results['hits']['hits']:
        hit['source'] = hit['_source']
    context['grants'] = results['hits']['hits']

    # dev feature
    if request.GET.get("json"):
        return JsonResponse({"grants": context["grants"]})

    return render(request, "grant.html", context=context)


def augment_org(org):
    if not org:
        return
    org["stats_by_currency"] = new_stats_by_currency(org)
    org["org_ids"] = new_org_ids(org)
    org["names"] = new_ordered_names(org)
    org["main_currency"] = org["stats_by_currency"][0]['currency']
    return org


def get_funder_info(funder_org_ids):
    query = {
        "query": {
            "bool": {
                "filter":
                    [{"terms": {"fundingOrganization.id": funder_org_ids}}]
            },
        },
        "aggs": {
            "filenames": {"terms": {"field": "filename", "size": 10}},
            "recipient_orgs": {"cardinality": {"field": "recipientOrganization.id", "precision_threshold": 40000}}
        }
    }

    results = get_results(query, 0)

    output = {'funder_publisher': {},
              'recipients': results['aggregations']['recipient_orgs']['value']}
    try:
        output['funder_publisher'] = provenance.by_identifier[provenance.identifier_from_filename(results['aggregations']['filenames']['buckets'][0]['key'])]['publisher']
    except (KeyError, IndexError):
        pass

    return output


def get_recipient_funders(recipient_org_ids):

    # Dynamically limit the required size to the total number of possible funders
    max_funders = get_results({"query": {"match_all": {}}}, data_type='funder')['hits']['total']["value"]

    query = {
        "query": {
            "bool": {
                "filter":
                    [{"terms": {"recipientOrganization.id": recipient_org_ids}}]
                },
        },
        "aggs": {
            "currency": {
                "terms": {"field": "currency"},
                "aggs": {
                    "funders": {
                        "terms": {
                            "field": "fundingOrganization.id_and_name", "size": max_funders
                        },
                        "aggs": {
                            "funder_stats": {
                                "stats": {"field": "amountAwarded"}
                            }
                        }
                    }
                }
            }
        }
    }

    results = get_results(query, 0)

    results_by_currency = {}

    for currency_bucket in results['aggregations']['currency']['buckets']:
        funder_list = []
        for funder_bucket in currency_bucket['funders']['buckets']:
            name, org_id = json.loads(funder_bucket['key'])
            funder = {"name": name, "org_id": org_id}
            funder.update(funder_bucket['funder_stats'])
            funder_list.append(funder)
        results_by_currency[currency_bucket['key']] = funder_list

    return results_by_currency


def org(request, org_id):

    org_query = {
        "query": {
            "bool": {"filter":
                [{"term": {"orgIDs": urllib.parse.unquote(org_id)}}]
            }
        }
    }

    funder_results = get_results(org_query, data_type="funder")
    recipient_results = get_results(org_query, data_type="recipient")

    org_types = []
    org_names = []
    org_ids = []
    funder = {}
    recipient = {}
    recipient_funders = {}

    if funder_results['hits']['hits']:
        org_types.append('Funder')
        funder = funder_results['hits']['hits'][0]['_source']
        org_ids = new_org_ids(funder)
        parameters = [("fundingOrganization", org_id) for org_id in org_ids]
        funder["grant_search_parameters"] = urlencode(parameters)
        funder_info = get_funder_info(org_ids)
        funder.update(funder_info)

    if recipient_results['hits']['hits']:
        org_types.append('Recipient')
        recipient = recipient_results['hits']['hits'][0]['_source']
        org_ids = new_org_ids(recipient)
        parameters = [("recipientOrganization", org_id) for org_id in org_ids]
        recipient["grant_search_parameters"] = urlencode(parameters)
        recipient_funders = get_recipient_funders(org_ids)

    ftc_data = None
    publisher_prefix = None

    for org in (funder, recipient):
        if org:
            augment_org(org)
            if not publisher_prefix:
                publisher_prefix = org.get("publisherPrefix")
            if not ftc_data:
                # Fetch the FTC data from the first org that has it (it should be the same)
                ftc_data = org.get("ftcData")

    for org in (funder, recipient):
        if org:
            org_ids = new_org_ids(org)
            org_names = new_ordered_names(org)
            break

    # see if we've been supplied a publisher prefix instead of an org-id
    if publisher_prefix is None:
        publisher_prefix = org_id

    publisher = provenance.by_publisher.get(publisher_prefix, {})
    if publisher:
        get_funders_for_datasets(publisher['datasets'])
        org_types.append('Publisher')
        if not org_names:
            org_names = [publisher["name"]]
            org_ids = [publisher_prefix]  # Fixme when we have a datasource for this

    if not org_types:
        raise Http404

    # first org name is our selection
    main_name = org_names[0]
    other_names = org_names[1:]

    context = {"funder": funder,
               "recipient": recipient,
               "publisher": publisher,
               "recipient_funders": recipient_funders,
               "org_types": org_types,
               "org_ids": org_ids,
               "org_ids_json": json.dumps(org_ids),
               "org_names": org_names,
               "main_name": main_name,
               "other_names": other_names,
               "ftc_data": ftc_data,
               "requested_org_id": org_id,
               }

    return render(request, "org.html", context=context)


def funder_recipients_datatables(request):
    # Make 100k the default max length. Overrideable by setting ?length= parameter
    MAX_DEFAULT_FUNDER_RECIPIENTS_LENGTH = 500000

    match = re.search(r'\.(\w+)$', request.path)
    if match:
        result_format = match.group(1)
    else:
        result_format = "ajax"

    order = ["_term", "recipient_stats.count", "recipient_stats.sum", "recipient_stats.max", "recipient_stats.min"]

    length = int(request.GET.get('length', MAX_DEFAULT_FUNDER_RECIPIENTS_LENGTH))

    if result_format == "ajax":
        start = int(request.GET['start'])
        order_field = order[int(request.GET['order[0][column]'])]
        search_value = request.GET['search[value]']
        order_dir = request.GET['order[0][dir]']
    else:
        start = 0
        order_field = order[0]
        search_value = ""
        order_dir = "desc"

    funder_id = request.GET.get('funder_id')

    if funder_id:
        # Allow multiple funder ids
        funder_id = json.loads(urllib.parse.unquote(funder_id))
        filter = {"terms": {"fundingOrganization.id": funder_id}}
    else:
        filter = {}

    currency = request.GET.get('currency')
    if not currency:
        currency = 'GBP'

    query = {"query": {
             "bool": {
                 "filter":
                     [filter, {"term": {"currency": currency}}],
                 "must":
                     {"match": {"recipientOrganization.name": {"query": search_value, "operator": "and"}}},
                 },
             },
             "aggs": {
                 "recipient_count": {"cardinality": {"field": "recipientOrganization.id", "precision_threshold": 40000}},
                 "recipient_stats":
                     {"terms": {"field": "recipientOrganization.id_and_name", "size": start + length, "shard_size": (start + length) * 10,
                                "order": {order_field: order_dir}},
                      "aggs": {"recipient_stats": {"stats": {"field": "amountAwarded"}}}}
        }
    }
    if not search_value:
        query["query"]["bool"].pop("must")

    results = get_results(query, 1)
    result_list = []

    for result in results["aggregations"]["recipient_stats"]["buckets"][-length:]:
        stats = result["recipient_stats"]
        for key in list(stats):
            if key != 'count':
                if result_format == "ajax":
                    stats[key] = "{}{:,.0f}".format(utils.currency_prefix(currency), int(stats[key]))
                else:
                    stats[key] = "{:.0f}".format(int(stats[key]))
        org_name, org_id = json.loads(result["key"])
        stats["org_name"] = org_name
        stats["org_id"] = org_id
        result_list.append(stats)

    if result_format == "ajax":
        return JsonResponse(
            {'data': result_list,
             'draw': request.GET['draw'],
             'recordsTotal': results["aggregations"]["recipient_count"]["value"],
             'recordsFiltered': results["aggregations"]["recipient_count"]["value"]}
        )
    elif result_format == "csv":
        return orgs_csv_paged(result_list, "recipient")
    elif result_format == "json":
        response = HttpResponse(json.dumps({'data': result_list}), content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="grantnav-{0}.json"'.format(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
        return response


def funders_datatables(request):
    match = re.search(r'\.(\w+)$', request.path)
    # Make 100k the default max length. Overrideable by setting ?length= parameter
    MAX_DEFAULT_FUNDERS_LENGTH = 500000

    if match:
        result_format = match.group(1)
    else:
        result_format = "ajax"

    order = ["_term", "funder_stats.count", "funder_stats.sum", "funder_stats.avg", "funder_stats.max", "funder_stats.min"]

    length = int(request.GET.get('length', MAX_DEFAULT_FUNDERS_LENGTH))

    if result_format == "ajax":
        start = int(request.GET['start'])
        order_field = order[int(request.GET['order[0][column]'])]
        search_value = request.GET['search[value]']
        order_dir = request.GET['order[0][dir]']
    else:
        start = 0
        order_field = order[0]
        search_value = ""
        order_dir = "desc"

    recipient_id = request.GET.get('recipient_id')
    if recipient_id:
        filter = {"term": {"recipientOrganization.id": recipient_id}}
    else:
        filter = {}

    query = {"query": {
             "bool": {
                 "filter":
                     [filter, {"term": {"currency": "GBP"}}],
                 "must":
                     {"match": {"fundingOrganization.name": {"query": search_value, "operator": "and"}}},
                 },
             },
             "aggs": {
                 "funder_count": {"cardinality": {"field": "fundingOrganization.id", "precision_threshold": 40000}},
                 "funder_stats":
                     {"terms": {"field": "fundingOrganization.id_and_name", "size": start + length, "shard_size": (start + length) * 10,
                                "order": {order_field: order_dir}},
                      "aggs": {"funder_stats": {"stats": {"field": "amountAwarded"}}}}
        }
    }
    if not search_value:
        query["query"]["bool"].pop("must")

    results = get_results(query, 1)
    result_list = []

    for result in results["aggregations"]["funder_stats"]["buckets"][-length:]:
        stats = result["funder_stats"]
        for key in list(stats):
            if result_format == "ajax":
                if "count" in key:
                    stats[key] = "{:,}".format(stats[key])
                else:
                    stats[key] = "£ {:,.0f}".format(int(stats[key]))
            else:
                if "count" not in key:
                    stats[key] = "{:.0f}".format(int(stats[key]))

        org_name, org_id = json.loads(result["key"])
        stats["org_name"] = org_name
        stats["org_id"] = org_id
        result_list.append(stats)

    if result_format == "ajax":
        return JsonResponse(
            {'data': result_list,
             'draw': request.GET['draw'],
             'recordsTotal': results["aggregations"]["funder_count"]["value"],
             'recordsFiltered': results["aggregations"]["funder_count"]["value"]}
        )
    elif result_format == "csv":
        return orgs_csv_paged(result_list, "funder")
    elif result_format == "json":
        response = HttpResponse(json.dumps({'data': result_list}), content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="grantnav-{0}.json"'.format(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
        return response


grant_datatables_metadata = {
    "funder": {
        "term": "fundingOrganization.id",
        "order": ["awardDate", "amountAwarded", "recipientOrganization.id_and_name", "title", "description"],
    },
    "recipient": {
        "term": "recipientOrganization.id",
        "order": ["awardDate", "amountAwarded", "fundingOrganization.id_and_name", "title", "description"],
    },
    "recipientRegionName": {
        "term": "additional_data.recipientRegionName",
        "order": ["awardDate", "amountAwarded", "fundingOrganization.id_and_name", "recipientOrganization.id_and_name", "title", "description"],
    },
    "recipientDistrictName": {
        "term": "additional_data.recipientDistrictName",
        "order": ["awardDate", "amountAwarded", "fundingOrganization.id_and_name", "recipientOrganization.id_and_name", "title", "description"],
    }
}


def grants_datatables(request):
    for field, metadata in grant_datatables_metadata.items():
        if field in request.GET:
            value = request.GET[field]
            order = metadata["order"]
            term = metadata["term"]
            break

    order_field = order[int(request.GET['order[0][column]'])]
    search_value = request.GET['search[value]']
    order_dir = request.GET['order[0][dir]']
    start = int(request.GET['start'])
    length = int(request.GET['length'])
    query = {"query": {
             "bool": {
                 "filter":
                     {"term": {term: value}},
                 "must":
                     {"query_string": {"query": search_value, "default_operator": "and"}},
                 },
             },
             "sort": [{order_field: order_dir}]}
    if not search_value:
        query["query"]["bool"].pop("must")

    try:
        results = get_results(query, length, start)
    except elasticsearch.exceptions.RequestError as e:
        if e.error == 'search_phase_execution_exception':
            results = {"hits": {"total": {"value": 0}, "hits": []}}

    result_list = []
    for result in results["hits"]["hits"]:
        grant = result["_source"]
        try:
            grant["awardDate"] = date_parser.parse(grant["awardDate"]).strftime("%d %b %Y")
        except ValueError:
            pass
        try:
            grant["amountAwarded"] = utils.currency_prefix(grant.get("currency")) + "{:,.0f}".format(grant["amountAwarded"])
        except ValueError:
            pass
        grant["description"] = grant.get("description", "")
        grant["title"] = grant.get("title", "")
        result_list.append(grant)

    return JsonResponse(
        {'data': result_list,
         'draw': request.GET['draw'],
         'recordsTotal': results["hits"]["total"]['value'],
         'recordsFiltered': results["hits"]["total"]['value']}
    )


def region(request, region):
    [result_format, results_size] = get_request_type_and_size(request)
    if result_format != "html":
        region = re.match(r'(.*)\.\w*$', region).group(1)

    query = {"query": {"bool": {"filter":
                [{"term": {"additional_data.recipientRegionName": region}}]}},
            "aggs": {
                "recipient_orgs": {"cardinality": {"field": "recipientOrganization.id", "precision_threshold": 40000}},
                "funding_orgs": {"cardinality": {"field": "fundingOrganization.id", "precision_threshold": 40000}},
                "currency_stats": {"terms": {"field": "currency"}, "aggs": {"amount_stats": {"stats": {"field": "amountAwarded"}}}},
                "min_date": {"min": {"field": "awardDate"}},
                "max_date": {"max": {"field": "awardDate"}},
        }
    }

    if result_format == "csv":
        return grants_csv_paged(query)
    elif result_format == "json":
        return grants_json_paged(query)

    results = get_results(query, results_size)

    if results['hits']['total']['value'] == 0:
        raise Http404
    context = {}
    context['results'] = results
    context['region'] = region

    return render(request, "region.html", context=context)


def district(request, district):
    [result_format, results_size] = get_request_type_and_size(request)
    if result_format != "html":
        district = re.match(r'(.*)\.\w*$', district).group(1)

    query = {"query": {"bool": {"filter":
                [{"term": {"additional_data.recipientDistrictName": district}}]}},
            "aggs": {
                "recipient_orgs": {"cardinality": {"field": "recipientOrganization.id", "precision_threshold": 40000}},
                "funding_orgs": {"cardinality": {"field": "fundingOrganization.id", "precision_threshold": 40000}},
                "currency_stats": {"terms": {"field": "currency"}, "aggs": {"amount_stats": {"stats": {"field": "amountAwarded"}}}},
                "min_date": {"min": {"field": "awardDate"}},
                "max_date": {"max": {"field": "awardDate"}},
        }
    }

    if result_format == "csv":
        return grants_csv_paged(query)
    elif result_format == "json":
        return grants_json_paged(query)

    results = get_results(query, results_size)

    if results['hits']['total']['value'] == 0:
        raise Http404
    context = {}
    context['results'] = results
    context['district'] = district

    return render(request, "district.html", context=context)


def get_funders_for_datasets(datasets):
    es = get_es()

    for dataset in datasets:
        query = {"query": {"bool": {
            "filter": [{"term": {"filename": dataset['identifier'] + '.json'}}]}},
            "aggs": {
                "funders": {"terms": {"field": "fundingOrganization.id_and_name", "size": 10}}
            }
        }
        results = es.search(body=query, index=get_index(), size=0)
        dataset['funders'] = [json.loads(bucket['key']) for bucket in results['aggregations']['funders']['buckets']]


# Backwards compatibility
def publisher(request, publisher_id):
    return redirect(reverse("org", args=[publisher_id]))


def recipient(request, recipient_id):
    return redirect(reverse("org", args=[recipient_id]))


def funder(request, funder_id):
    return redirect(reverse("org", args=[funder_id]))


def datasets(request):
    get_funders_for_datasets(provenance.datasets)
    return render(request, "datasets.html", context={
        'publishers': provenance.by_publisher.values(),
        'datasets': provenance.datasets,
    })


def individuals(request):
    search_page = reverse("search")
    return redirect(f"{search_page}?recipientTSGType=Individual")
