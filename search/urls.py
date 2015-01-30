from django.conf.urls import patterns, url

from search import views
from search.views import SearchView
from search.views import SearchViewWithResults

urlpatterns = patterns('',
    url(r'^$', SearchView.as_view(), name="homepage"),
    url(r'^result/', SearchViewWithResults.as_view(), name="results"),
    url(r'^p/(?P<slug>\w+)/', views.page, name="page"),
)
