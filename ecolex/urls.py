from django.conf.urls import patterns, include, url
from django.contrib import admin
from .views import SearchView, SearchViewWithResults, page


urlpatterns = patterns('',
    url(r'^$', SearchView.as_view(), name="homepage"),
    url(r'^result/', SearchViewWithResults.as_view(), name="results"),
    url(r'^p/(?P<slug>\w+)/', page, name="page"),
)
