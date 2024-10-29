from grantnav.frontend.search_helpers import get_results


def new_stats_by_currency(org_result):
    """ Takes a org dict and creates a sorted and ease of use in templates list"""
    stats_by_currency = []

    for currency, stat in org_result["aggregate"]["currencies"].items():
        stat["currency"] = currency
        stats_by_currency.append(stat)

    # sort the list with the largest total amount currency first
    stats_by_currency.sort(key=lambda i: i["total"], reverse=True)

    return stats_by_currency


def new_ordered_names(org_result):
    # Name ordering is important: Publisher, FTC, Grant
    names = []

    if org_result["publisherName"] and org_result["publisherName"] not in names:
        names.append(org_result["publisherName"])

    if org_result["ftcData"] and org_result["ftcData"]["name"] not in names:
        names.append(org_result["ftcData"]["name"])

    if org_result["additionalData"]["alternative_names"]:
        names.extend(org_result["additionalData"]["alternative_names"])

    if org_result["name"] not in names:
        names.append(org_result["name"])

    if len(names) == 0:
        names = [org_result["id"]]

    return names


def new_org_ids(org_result):
    return [org_result["id"], *org_result.get("non_primary_org_ids", [])]


class OrgNotFoundError(Exception):
    pass


orgs_cache = {"funder": {}, "recipient": {}}


def get_org(org_id, org_type):
    """ org_type: recipient, funder
    returns an organisation match
    """
    # Don't allow the memory cache to grow infinitely
    if len(orgs_cache[org_type].keys()) > 300000:
        orgs_cache[org_type] = {}

    try:
        org = orgs_cache[org_type][org_id]
        return org
    except KeyError:
        pass

    query = {
        "query": {
            "bool": {
                "filter": [
                    {"term": {"orgIDs": org_id}}
                ]
            }
        }
    }

    try:
        org = get_results(query, data_type=org_type)["hits"]["hits"][0]["_source"]
        # Save the org to the cache
        orgs_cache[org_type][org_id] = org
        return org
    except (IndexError, KeyError):
        # Failed to find org
        raise OrgNotFoundError
