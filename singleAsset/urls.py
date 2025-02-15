from django.urls import path
from . import views  # Importa la vista desde __init__.py

urlpatterns = [
    path("transactions/<str:session_code>/", views.get_transactions, name="get_transactions"),
]
