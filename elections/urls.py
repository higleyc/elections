from django.conf.urls import patterns, url
from elections import views

urlpatterns = patterns(
    "",
    url(r"^$", views.IndexView.as_view(), name="index"),
    url(r"^manageelection/$", views.manage_election, name="manage_election"),
    url(r"^login/$", "django.contrib.auth.views.login",
        {"template_name" : "elections/login.html"})
)