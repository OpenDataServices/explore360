from django.shortcuts import render, redirect
from grantnav.search import get_es
from django.utils.http import urlencode
from django.conf import settings
from django.http import Http404, JsonResponse
from elasticsearch.helpers import scan
import elasticsearch.exceptions
import jsonref
import json
import copy
import math
import collections
import dateutil.parser as date_parser
import datetime
import re
from django.http import HttpResponse, StreamingHttpResponse
from grantnav import provenance, csv_layout
import csv

BASIC_FILTER = [
    {"bool": {"should": []}},  # Funding Orgs
    {"bool": {"should": []}},  # Recipient Orgs
    {"bool": {"should": []}},  # Amount Awarded Fixed
    {"bool": {"should": {"range": {"amountAwarded": {}}}}},  # Amount Awarded
    {"bool": {"should": []}},  # Award Year
    {"bool": {"should": []}},  # recipientRegionName
    {"bool": {"should": []}}   # recipientDistrictName
]


BASIC_QUERY = {"query": {"bool": {"must":
                                  {"query_string": {"query": "", "default_field": "_all"}}, "filter": BASIC_FILTER}},
               "extra_context": {"awardYear_facet_size": 3, "amountAwardedFixed_facet_size": 3},
               "sort": {"_score": {"order": "desc"}},
               "aggs": {
                   "fundingOrganization": {"terms": {"field": "fundingOrganization.id_and_name", "size": 3}},
                   "recipientOrganization": {"terms": {"field": "recipientOrganization.id_and_name", "size": 3}},
                   "recipientRegionName": {"terms": {"field": "recipientRegionName", "size": 3}},
                   "recipientDistrictName": {"terms": {"field": "recipientDistrictName", "size": 3}}}}

SIZE = 20

FIXED_AMOUNT_RANGES = [
    {"from": 0, "to": 500},
    {"from": 500, "to": 1000},
    {"from": 1000, "to": 5000},
    {"from": 5000, "to": 10000},
    {"from": 10000, "to": 50000},
    {"from": 50000, "to": 100000},
    {"from": 100000, "to": 500000},
    {"from": 1000000, "to": 10000000},
    {"from": 10000000}
]


SEARCH_SUMMARY_AGGREGATES = {
    "recipient_orgs": {"cardinality": {"field": "recipientOrganization.id", "precision_threshold": 40000}},
    "funding_orgs": {"cardinality": {"field": "fundingOrganization.id", "precision_threshold": 40000}},
    "total_amount": {"sum": {"field": "amountAwarded"}},
    "avg_amount": {"avg": {"field": "amountAwarded"}},
    "min_amount": {"min": {"field": "amountAwarded"}},
    "max_amount": {"max": {"field": "amountAwarded"}},
    "min_date": {"min": {"field": "awardDate"}},
    "max_date": {"max": {"field": "awardDate"}}
}


def get_results(json_query, size=10, from_=0):
    es = get_es()
    extra_context = json_query.pop('extra_context', None)
    results = es.search(body=json_query, size=size, from_=from_, index=settings.ES_INDEX)
    if extra_context is not None:
        json_query['extra_context'] = extra_context
    return results


def get_request_type_and_size(request):
    results_size = SIZE

    match = re.search('\.(\w+)$', request.path)
    if match:
        result_format = match.group(1)
        results_size = settings.FLATTENED_DOWNLOAD_LIMIT
    else:
        result_format = "html"

    return [result_format, results_size]


def get_data_from_path(path, data):
    current_pos = data
    for part in path.split("."):
        try:
            part = int(part)
        except ValueError:
            pass
        try:
            current_pos = current_pos[part]
        except (KeyError, IndexError, TypeError):
            return ""
    return current_pos


def grants_csv_generator(query):
    yield csv_layout.grant_csv_titles
    es = get_es()
    for result in scan(es, query, index=settings.ES_INDEX):
        result_with_provenance = {
            "result": result["_source"],
            "dataset": provenance.by_identifier.get(result['_source']['filename'].split('.')[0], {})
        }
        line = []
        for path in csv_layout.grant_csv_paths:
            line.append(get_data_from_path(path, result_with_provenance))
        yield line


def grants_json_generator(query):
    yield '''{
    "license": "See dataset/license within each grant. This file also contains OS data © Crown copyright and database right 2016, Royal Mail data © Royal Mail copyright and Database right 2016, National Statistics data © Crown copyright and database right 2016, see http://grantnav.org/datasets/ for more information.",
    "grants": [\n'''
    es = get_es()
    for num, result in enumerate(scan(es, query, index=settings.ES_INDEX)):
        result["_source"]["dataset"] = provenance.by_identifier.get(result['_source']['filename'].split('.')[0], {})
        if num == 0:
            yield json.dumps(result["_source"]) + "\n"
        else:
            yield ", " + json.dumps(result["_source"]) + "\n"
    yield ']}'


class Echo(object):
    def write(self, value):
        return value


def grants_csv_paged(query):
    query.pop('extra_context', None)
    query.pop('aggs', None)
    pseudo_buffer = Echo()
    writer = csv.writer(pseudo_buffer)
    response = StreamingHttpResponse((writer.writerow(row) for row in grants_csv_generator(query)), content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="grantnav-{0}.csv"'.format(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
    return response


def grants_json_paged(query):
    query.pop('extra_context', None)
    query.pop('aggs', None)
    response = StreamingHttpResponse(grants_json_generator(query), content_type='text/json')
    response['Content-Disposition'] = 'attachment; filename="grantnav-{0}.json"'.format(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
    return response


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
    response = StreamingHttpResponse((writer.writerow(row) for row in org_csv_generator(data, org_type)), content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="grantnav-{0}.csv"'.format(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
    return response


def get_pagination(request, context, page):
    total_pages = math.ceil(context['results']['hits']['total'] / SIZE)
    if page < total_pages:
        context['next_page'] = request.path + '?' + urlencode({"json_query": context['json_query'], 'page': page + 1})
    if page != 1 and total_pages > 1:
        context['prev_page'] = request.path + '?' + urlencode({"json_query": context['json_query'], 'page': page - 1})


def get_terms_facet_size(request, context, json_query, page):
    json_query = copy.deepcopy(json_query)
    see_more_url = {}
    try:
        aggs = json_query["aggs"]
    except KeyError:
        aggs = BASIC_QUERY['aggs']
    for agg_name, agg in aggs.items():
        new_aggs = copy.deepcopy(aggs)
        if "terms" not in agg:
            continue
        size = agg["terms"]["size"]
        if size == 3:
            new_size = 50
            see_more_url[agg_name] = {"more": True}
        else:
            new_size = 3
            see_more_url[agg_name] = {"more": False}
        new_aggs[agg_name]["terms"]["size"] = new_size

        json_query["aggs"] = new_aggs
        see_more_url[agg_name]["url"] = request.path + '?' + urlencode({"json_query": json.dumps(json_query), 'page': page}) + '#' + agg_name

    context['see_more_url'] = see_more_url


def get_non_terms_facet_size(request, context, json_query, page, agg_name):
    see_more = {}
    new_json_query = copy.deepcopy(json_query)
    facet_size = new_json_query['extra_context'][agg_name + '_facet_size']
    if facet_size == 3:
        facet_size = 50
        see_more["more"] = True
    else:
        facet_size = 3
        see_more["more"] = False

    new_json_query['extra_context'][agg_name + '_facet_size'] = facet_size
    new_url = request.path + '?' + urlencode({"json_query": json.dumps(new_json_query), 'page': page}) + '#' + agg_name
    see_more['url'] = new_url
    context['see_more_url'][agg_name] = see_more


def create_amount_aggregate(json_query):
    json_query["aggs"]["amountAwardedFixed"] = {"range": {"field": "amountAwarded", "ranges": FIXED_AMOUNT_RANGES}}


def get_amount_facet_fixed(request, context, original_json_query):
    json_query = copy.deepcopy(original_json_query)
    json_query["aggs"]["amountAwardedFixed"] = {"range": {"field": "amountAwarded", "ranges": FIXED_AMOUNT_RANGES}}
    try:
        current_filter = json_query["query"]["bool"]["filter"][2]["bool"]["should"]
    except KeyError:
        json_query["query"]["bool"]["filter"] = copy.deepcopy(BASIC_FILTER)
        current_filter = json_query["query"]["bool"]["filter"][2]["bool"]["should"]

    main_results = context["results"]
    if current_filter:
        json_query["query"]["bool"]["filter"][2]["bool"]["should"] = []
        results = get_results(json_query)
    else:
        results = context["results"]

    input_range = json_query["query"]["bool"]["filter"][3]["bool"]["should"]["range"]["amountAwarded"]
    new_filter = copy.deepcopy(current_filter)
    if new_filter or input_range:
        new_json_query = copy.deepcopy(original_json_query)
        new_json_query["query"]["bool"]["filter"][2]["bool"]["should"] = []
        new_json_query["query"]["bool"]["filter"][3]["bool"]["should"]["range"]["amountAwarded"] = {}
        results["aggregations"]["amountAwardedFixed"]["clear_url"] = request.path + '?' + urlencode({"json_query": json.dumps(new_json_query)})

    for bucket in results["aggregations"]["amountAwardedFixed"]['buckets']:
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

        json_query["query"]["bool"]["filter"][2]["bool"]["should"] = new_filter
        bucket["url"] = request.path + '?' + urlencode({"json_query": json.dumps(json_query)})

        if bucket.get("selected"):
            display_value = "£{:,}".format(int(bucket["from"]))
            if to_:
                display_value = str(display_value) + " - " + "£{:,}".format(int(to_))
            else:
                display_value = str(display_value) + "+"

            context["selected_facets"]["Amounts"].append({"url": bucket["url"], "display_value": display_value})

    if input_range:
        json_query = copy.deepcopy(original_json_query)
        lte, gte = input_range.get('lte'), input_range.get('gte')
        if not gte:
            gte = 0
        display_value = "£{:,}".format(int(gte))
        if lte:
            display_value = str(display_value) + " - " + "£{:,}".format(int(lte))
        else:
            display_value = str(display_value) + "+"
        json_query["query"]["bool"]["filter"][3]["bool"]["should"]["range"]["amountAwarded"] = {}
        context["selected_facets"]["Amounts"].append({"url": request.path + '?' + urlencode({"json_query": json.dumps(json_query)}), "display_value": display_value})

    main_results["aggregations"]["amountAwardedFixed"] = results["aggregations"]["amountAwardedFixed"]


def create_date_aggregate(json_query):
    json_query["aggs"]["awardYear"] = {"date_histogram": {"field": "awardDate", "format": "yyyy", "interval": "year", "order": {"_key": "desc"}}}


def get_date_facets(request, context, json_query):
    json_query = copy.deepcopy(json_query)
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
    else:
        results = context["results"]

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
        bucket["url"] = request.path + '?' + urlencode({"json_query": json.dumps(json_query)})

        if bucket.get("selected"):
            context["selected_facets"]["Award Year"].append({"url": bucket["url"], "display_value": value})

    if current_filter:
        json_query["query"]["bool"]["filter"][4]["bool"]["should"] = []
        results['aggregations']["awardYear"]['clear_url'] = request.path + '?' + urlencode({"json_query": json.dumps(json_query)})
    main_results['aggregations']["awardYear"] = results['aggregations']["awardYear"]


def get_terms_facets(request, context, json_query, field, aggregate, bool_index, display_name, is_json=False):
    json_query = copy.deepcopy(json_query)
    try:
        current_filter = json_query["query"]["bool"]["filter"][bool_index]["bool"]["should"]
    except KeyError:
        json_query["query"]["bool"]["filter"] = copy.deepcopy(BASIC_FILTER)
        current_filter = json_query["query"]["bool"]["filter"][bool_index]["bool"]["should"]

    main_results = context["results"]
    if current_filter:
        json_query["query"]["bool"]["filter"][bool_index]["bool"]["should"] = []
        results = get_results(json_query)
    else:
        results = context["results"]

    for filter in current_filter:
        new_filter = [x for x in current_filter if x != filter]
        json_query["query"]["bool"]["filter"][bool_index]["bool"]["should"] = new_filter
        display_value = filter["term"][field]
        if is_json:
            display_value = json.loads(display_value)[0]
        context["selected_facets"][display_name].append(
            {"url": request.path + '?' + urlencode({"json_query": json.dumps(json_query)}),
             "display_value": display_value}
        )

    for bucket in results['aggregations'][aggregate]['buckets']:
        facet_value = bucket['key']
        filter_values = [filter["term"][field] for filter in current_filter]
        if facet_value in filter_values:
            bucket["selected"] = True
            filter_values.remove(facet_value)
        else:
            filter_values.append(facet_value)

        new_filter = [{"term": {field: value}} for value in filter_values]
        json_query["query"]["bool"]["filter"][bool_index]["bool"]["should"] = new_filter
        bucket["url"] = request.path + '?' + urlencode({"json_query": json.dumps(json_query)})
    if current_filter:
        json_query["query"]["bool"]["filter"][bool_index]["bool"]["should"] = []
        results['aggregations'][aggregate]['clear_url'] = request.path + '?' + urlencode({"json_query": json.dumps(json_query)})
    main_results['aggregations'][aggregate] = results['aggregations'][aggregate]


def get_clear_all(request, context, json_query):
    json_query = copy.deepcopy(json_query)
    try:
        current_filter = json_query["query"]["bool"]["filter"]
    except KeyError:
        json_query["query"]["bool"]["filter"] = copy.deepcopy(BASIC_FILTER)
        current_filter = json_query["query"]["bool"]["filter"]

    if current_filter != BASIC_FILTER:
        json_query["query"]["bool"]["filter"] = copy.deepcopy(BASIC_FILTER)
        context["results"]["clear_all_facet_url"] = request.path + '?' + urlencode({"json_query": json.dumps(json_query)})


def home(request):
    context = {}
    query = {"query": {"match_all": {}},
             "aggs": {
                 "recipient_count": {"cardinality": {"field": "recipientOrganization.id", "precision_threshold": 40000}},
                 "funder_count": {"cardinality": {"field": "fundingOrganization.id", "precision_threshold": 40000}},
        }
    }
    results = get_results(query)
    context['results'] = results

    return render(request, "home.html", context=context)


def search(request):

    [result_format, results_size] = get_request_type_and_size(request)

    context = {}

    query = request.GET.urlencode()
    if query:
        context['query_string'] = query
    else:
        context['query_string'] = ""

    json_query = request.GET.get('json_query') or ""
    try:
        json_query = json.loads(json_query)
    except ValueError:
        json_query = {}

    default_field = request.GET.get('default_field')
    text_query = request.GET.get('text_query')
    if text_query is not None or not json_query:
        if not text_query:
            text_query = '*'
        try:
            json_query["query"]["bool"]["must"]["query_string"]["query"] = text_query
        except KeyError:
            json_query = copy.deepcopy(BASIC_QUERY)
            json_query["query"]["bool"]["must"]["query_string"]["query"] = text_query

        if default_field:
            json_query["query"]["bool"]["must"]["query_string"]["default_field"] = default_field
        return redirect(request.path + '?' + urlencode({"json_query": json.dumps(json_query)}))

    min_amount = request.GET.get('min_amount')
    max_amount = request.GET.get('max_amount')
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
        return redirect(request.path + '?' + urlencode({"json_query": json.dumps(json_query)}))

    sort_order = request.GET.get('sort', '').split()
    if sort_order and len(sort_order) == 2:
        json_query["sort"] = {sort_order[0]: {"order": sort_order[1]}}
        return redirect(request.path + '?' + urlencode({"json_query": json.dumps(json_query)}))

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
            context['default_field'] = json_query["query"]["bool"]["must"]["query_string"]["default_field"]
        except KeyError:
            json_query = copy.deepcopy(BASIC_QUERY)
            json_query["query"]["bool"]["must"]["query_string"]["query"] = ''
            context['text_query'] = ''
            if default_field:
                json_query["query"]["bool"]["must"]["query_string"]["default_field"] = default_field
            context['default_field'] = json_query["query"]["bool"]["must"]["query_string"]["default_field"]

        if result_format == "csv":
            return grants_csv_paged(json_query)
        elif result_format == "json":
            return grants_json_paged(json_query)

        if context['text_query'] == '*':
            context['text_query'] = ''

        try:
            create_amount_aggregate(json_query)
            create_date_aggregate(json_query)

            json_query['aggs'].update(SEARCH_SUMMARY_AGGREGATES)

            results = get_results(json_query, results_size, (page - 1) * SIZE)
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

        context['selected_facets'] = collections.defaultdict(list)
        get_clear_all(request, context, json_query)

        get_terms_facets(request, context, json_query, "fundingOrganization.id_and_name", "fundingOrganization", 0, "Funders", True)
        get_terms_facets(request, context, json_query, "recipientOrganization.id_and_name", "recipientOrganization", 1, "Recipients", True)

        get_terms_facets(request, context, json_query, "recipientRegionName", "recipientRegionName", 5, "Regions")
        get_terms_facets(request, context, json_query, "recipientDistrictName", "recipientDistrictName", 6, "Districts")

        get_amount_facet_fixed(request, context, json_query)
        get_date_facets(request, context, json_query)
        get_terms_facet_size(request, context, json_query, page)
        get_non_terms_facet_size(request, context, json_query, page, 'awardYear')
        get_non_terms_facet_size(request, context, json_query, page, 'amountAwardedFixed')

        get_pagination(request, context, page)

        context['selected_facets'] = dict(context['selected_facets'])

        return render(request, "search.html", context=context)


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


def stats(request):
    text_query = request.GET.get('text_query')
    if not text_query:
        text_query = '*'
    context = {'text_query': text_query or ''}

    es = get_es()
    mapping = es.indices.get_mapping(index=settings.ES_INDEX)
    all_fields = list(flatten_mapping(mapping[settings.ES_INDEX]['mappings']['grant']['properties']))

    query = {"query": {"bool": {"must":
                {"query_string": {"query": text_query}}, "filter": {}}},
             "aggs": {}}

    schema = jsonref.load_uri(settings.GRANT_SCHEMA)
    schema_fields = set(flatten_schema(schema))

    for field in all_fields:
        query["aggs"][field + ":terms"] = {"terms": {"field": field, "size": 5}}
        query["aggs"][field + ":missing"] = {"missing": {"field": field}}
        query["aggs"][field + ":cardinality"] = {"cardinality": {"field": field}}

    if context['text_query'] == '*':
        context['text_query'] = ''

    field_info = collections.defaultdict(dict)
    results = es.search(body=query, index=settings.ES_INDEX, size=0)
    for field, aggregation in results['aggregations'].items():
        field_name, agg_type = field.split(':')
        field_info[field_name]["in_schema"] = field_name in schema_fields
        if agg_type == 'terms':
            field_info[field_name]["terms"] = aggregation["buckets"]
        if agg_type == 'missing':
            field_info[field_name]["found"] = results['hits']['total'] - aggregation["doc_count"]
        if agg_type == 'cardinality':
            field_info[field_name]["distinct"] = aggregation["value"]

    context['field_info'] = sorted(field_info.items(), key=lambda val: -val[1]["found"])
    context['results'] = results
    return render(request, "stats.html", context=context)


def grant(request, grant_id):
    query = {"query": {"bool": {"filter":
                [{"term": {"id": grant_id}}]
    }}}
    results = get_results(query, -1)
    if results['hits']['total'] == 0:
        raise Http404
    context = {}
    for hit in results['hits']['hits']:
        hit['source'] = hit['_source']
    context['grants'] = results['hits']['hits']
    return render(request, "grant.html", context=context)


def funder(request, funder_id):

    [result_format, results_size] = get_request_type_and_size(request)

    if result_format != "html":
        funder_id = re.match('(.*)\.\w*$', funder_id).group(1)

    query = {"query": {"bool": {"filter":
                [{"term": {"fundingOrganization.id": funder_id}}]}},
            "aggs": {
                "recipient_orgs": {"cardinality": {"field": "recipientOrganization.id", "precision_threshold": 40000}},
                "filenames": {"terms": {"field": "filename", "size": 10}},
                "total_amount": {"sum": {"field": "amountAwarded"}},
                "avg_amount": {"avg": {"field": "amountAwarded"}},
                "min_amount": {"min": {"field": "amountAwarded"}},
                "max_amount": {"max": {"field": "amountAwarded"}},
                "min_date": {"min": {"field": "awardDate"}},
                "max_date": {"max": {"field": "awardDate"}},
                "currencies": {"terms": {"field": "currency", "size": 0}},
                "recipients": {"terms": {"field": "recipientOrganization.id_and_name", "size": 10},
                               "aggs": {"recipient_stats": {"stats": {"field": "amountAwarded"}}}}
        }
    }
    if result_format == "csv":
        return grants_csv_paged(query)
    elif result_format == "json":
        return grants_json_paged(query)

    results = get_results(query, results_size)

    if results['hits']['total'] == 0:
        raise Http404
    context = {}
    context['results'] = results
    context['funder'] = results['hits']['hits'][0]["_source"]["fundingOrganization"][0]
    try:
        context['publisher'] = provenance.by_identifier[results['aggregations']['filenames']['buckets'][0]['key'].split('.')[0]]['publisher']
    except KeyError:
        pass

    return render(request, "funder.html", context=context)


def funder_recipients_datatables(request):

    match = re.search('\.(\w+)$', request.path)
    if match:
        result_format = match.group(1)
    else:
        result_format = "ajax"

    order = ["_term", "recipient_stats.count", "recipient_stats.sum", "recipient_stats.avg", "recipient_stats.max", "recipient_stats.min"]

    if result_format == "ajax":
        start = int(request.GET['start'])
        length = int(request.GET['length'])
        order_field = order[int(request.GET['order[0][column]'])]
        search_value = request.GET['search[value]']
        order_dir = request.GET['order[0][dir]']
    else:
        start = 0
        length = 0
        order_field = order[0]
        search_value = ""
        order_dir = "desc"

    funder_id = request.GET.get('funder_id')
    if funder_id:
        filter = {"term": {"fundingOrganization.id": funder_id}}
    else:
        filter = {}

    query = {"query": {
             "bool": {
                 "filter":
                     filter,
                 "must":
                     {"match": {"recipientOrganization.name": {"query": search_value, "operator": "and"}}},
                 },
             },
             "aggs": {
                 "recipient_count": {"cardinality": {"field": "recipientOrganization.id", "precision_threshold": 40000}},
                 "recipient_stats":
                     {"terms": {"field": "recipientOrganization.id_and_name", "size": start + length, "shard_size": 0,
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
                    stats[key] = "£ {:,.0f}".format(int(stats[key]))
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
    match = re.search('\.(\w+)$', request.path)
    if match:
        result_format = match.group(1)
    else:
        result_format = "ajax"

    order = ["_term", "funder_stats.count", "funder_stats.sum", "funder_stats.avg", "funder_stats.max", "funder_stats.min"]

    if result_format == "ajax":
        start = int(request.GET['start'])
        length = int(request.GET['length'])
        order_field = order[int(request.GET['order[0][column]'])]
        search_value = request.GET['search[value]']
        order_dir = request.GET['order[0][dir]']
    else:
        start = 0
        length = 0
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
                     filter,
                 "must":
                     {"match": {"fundingOrganization.name": {"query": search_value, "operator": "and"}}},
                 },
             },
             "aggs": {
                 "funder_count": {"cardinality": {"field": "fundingOrganization.id", "precision_threshold": 40000}},
                 "funder_stats":
                     {"terms": {"field": "fundingOrganization.id_and_name", "size": start + length, "shard_size": 0,
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
            if key != 'count':
                if result_format == "ajax":
                    stats[key] = "£ {:,.0f}".format(int(stats[key]))
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
        "term": "recipientRegionName",
        "order": ["awardDate", "amountAwarded", "fundingOrganization.id_and_name", "recipientOrganization.id_and_name", "title", "description"],
    },
    "recipientDistrictName": {
        "term": "recipientDistrictName",
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
            results = {"hits": {"total": 0, "hits": []}}

    result_list = []
    for result in results["hits"]["hits"]:
        grant = result["_source"]
        try:
            grant["awardDate"] = date_parser.parse(grant["awardDate"]).strftime("%d %b %Y")
        except ValueError:
            pass
        try:
            grant["amountAwarded"] = "£" + "{:,.0f}".format(grant["amountAwarded"])
        except ValueError:
            pass
        grant["description"] = grant.get("description", "")
        grant["title"] = grant.get("title", "")
        result_list.append(grant)

    return JsonResponse(
        {'data': result_list,
         'draw': request.GET['draw'],
         'recordsTotal': results["hits"]["total"],
         'recordsFiltered': results["hits"]["total"]}
    )


def recipient(request, recipient_id):
    [result_format, results_size] = get_request_type_and_size(request)
    if result_format != "html":
        recipient_id = re.match('(.*)\.\w*$', recipient_id).group(1)

    query = {"query": {"bool": {"filter":
                 [{"term": {"recipientOrganization.id": recipient_id}}]}},
             "aggs": {
                 "funder_orgs": {"cardinality": {"field": "fundingOrganization.id"}},
                 "total_amount": {"sum": {"field": "amountAwarded"}},
                 "avg_amount": {"avg": {"field": "amountAwarded"}},
                 "min_amount": {"min": {"field": "amountAwarded"}},
                 "max_amount": {"max": {"field": "amountAwarded"}},
                 "min_date": {"min": {"field": "awardDate"}},
                 "max_date": {"max": {"field": "awardDate"}},
                 "currencies": {"terms": {"field": "currency", "size": 0}},
                 "funders": {"terms": {"field": "fundingOrganization.id_and_name", "size": 10},
                             "aggs": {"funder_stats": {"stats": {"field": "amountAwarded"}}}}
                 }}

    if result_format == "csv":
        return grants_csv_paged(query)
    elif result_format == "json":
        return grants_json_paged(query)

    results = get_results(query, results_size)

    if results['hits']['total'] == 0:
        raise Http404
    context = {}
    context['results'] = results
    context['recipient'] = results['hits']['hits'][0]["_source"]["recipientOrganization"][0]

    return render(request, "recipient.html", context=context)


def recipients(request):
    return render(request, "recipients.html")


def funders(request):
    return render(request, "funders.html")


def region(request, region):
    [result_format, results_size] = get_request_type_and_size(request)
    if result_format != "html":
        region = re.match('(.*)\.\w*$', region).group(1)

    query = {"query": {"bool": {"filter":
                [{"term": {"recipientRegionName": region}}]}},
            "aggs": {
                "recipient_orgs": {"cardinality": {"field": "recipientOrganization.id", "precision_threshold": 40000}},
                "funding_orgs": {"cardinality": {"field": "fundingOrganization.id", "precision_threshold": 40000}},
                "total_amount": {"sum": {"field": "amountAwarded"}},
                "avg_amount": {"avg": {"field": "amountAwarded"}},
                "min_amount": {"min": {"field": "amountAwarded"}},
                "max_amount": {"max": {"field": "amountAwarded"}},
                "min_date": {"min": {"field": "awardDate"}},
                "max_date": {"max": {"field": "awardDate"}},
        }
    }

    if result_format == "csv":
        return grants_csv_paged(query)
    elif result_format == "json":
        return grants_json_paged(query)

    results = get_results(query, results_size)

    if results['hits']['total'] == 0:
        raise Http404
    context = {}
    context['results'] = results
    context['region'] = region

    return render(request, "region.html", context=context)


def district(request, district):
    [result_format, results_size] = get_request_type_and_size(request)
    if result_format != "html":
        district = re.match('(.*)\.\w*$', district).group(1)

    query = {"query": {"bool": {"filter":
                [{"term": {"recipientDistrictName": district}}]}},
            "aggs": {
                "recipient_orgs": {"cardinality": {"field": "recipientOrganization.id", "precision_threshold": 40000}},
                "funding_orgs": {"cardinality": {"field": "fundingOrganization.id", "precision_threshold": 40000}},
                "total_amount": {"sum": {"field": "amountAwarded"}},
                "avg_amount": {"avg": {"field": "amountAwarded"}},
                "min_amount": {"min": {"field": "amountAwarded"}},
                "max_amount": {"max": {"field": "amountAwarded"}},
                "min_date": {"min": {"field": "awardDate"}},
                "max_date": {"max": {"field": "awardDate"}},
        }
    }

    if result_format == "csv":
        return grants_csv_paged(query)
    elif result_format == "json":
        return grants_json_paged(query)

    results = get_results(query, results_size)

    if results['hits']['total'] == 0:
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
        results = es.search(body=query, index=settings.ES_INDEX, size=0)
        dataset['funders'] = [json.loads(bucket['key']) for bucket in results['aggregations']['funders']['buckets']]


def publisher(request, publisher_id):
    publisher = provenance.by_publisher[publisher_id]
    get_funders_for_datasets(publisher['datasets'])

    if publisher_id not in provenance.by_publisher:
        raise Http404
    return render(request, "publisher.html", context={
        'publisher': publisher,
    })


def datasets(request):
    get_funders_for_datasets(provenance.datasets)
    return render(request, "datasets.html", context={
        'publishers': provenance.by_publisher.values(),
        'datasets': provenance.datasets,
    })


def api_grants(request):
    [result_format, results_size] = get_request_type_and_size(request)
    query = {"query": {"match_all": {}}}
    if result_format == "csv":
        return grants_csv_paged(query)
    elif result_format == "json":
        return grants_json_paged(query)
