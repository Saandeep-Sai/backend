from django.urls import path
from .views import GreetView, GenerateQRCode, Ticket

urlpatterns = [
    path('chatbot/', GreetView.as_view(), name='greet'),
    path('ticket/', GenerateQRCode.as_view(), name="QR_code"),
    path('getTicket/', Ticket.as_view(), name="display")
]
