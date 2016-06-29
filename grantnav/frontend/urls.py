from django.conf.urls import url

from . import views
from django.views.generic import TemplateView

urlpatterns = [
    url(r'^$', views.home, name='home'),
    url(r'search$', views.search, name='search'),
    url(r'^grant/(.*)$', views.grant, name='grant'),
    url(r'^grants_datatables$', views.grants_datatables, name='grants_datatables'),
    url(r'^funder/(.*)$', views.funder, name='funder'),
    url(r'^funder_recipients_datatables$', views.funder_recipients_datatables, name='funder_recipients_datatables'),
    url(r'^recipient/(.*)$', views.recipient, name='recipient'),
    url(r'^region/(.*)$', views.region, name='region'),
    url(r'^district/(.*)$', views.district, name='district'),
    url(r'^stats', views.stats, name='stats'),
    url(r'^terms', TemplateView.as_view(template_name='terms.html'), name='terms'),
]
