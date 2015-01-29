from django.conf.urls import patterns, url

from search import views

urlpatterns = patterns('',
    url(r'^$', views.search, name="search"),
    url(r'^result/', views.result, name="result"),
)
