from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^debug/', views.debug, name='debug'),
    url(r'^$', views.Index.as_view(), name='index'),
]

handler400 = views.Error400.as_view()
handler403 = views.Error403.as_view()
handler404 = views.Error404.as_view()
handler500 = views.Error500.as_view()
