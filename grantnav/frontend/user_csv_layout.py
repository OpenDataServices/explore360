from django.http import Http404
from . import views
import json
from grantnav.csv_layout import grant_csv_paths, grant_csv_titles


# Process the custom download request
def process(request):
    fields = json.loads(request.POST.get("selection", {}))

    # Check the incoming data is known to us
    for field in fields:
        if field["column_title"] not in grant_csv_titles or field["path"] not in grant_csv_paths:
            raise Http404("The field(s) requested are not available.")

    return views.grants_csv_paged(
        json.loads(request.POST.get("json_query", {})),
        grant_csv_titles=[item["column_title"] for item in fields] + grant_csv_titles[-2:],
        grant_csv_paths=[item["path"] for item in fields],
    )
