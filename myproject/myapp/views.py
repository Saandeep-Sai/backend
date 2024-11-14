import base64
from django.views import View
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from django.core.files.base import ContentFile
from pymongo import MongoClient
import qrcode
import uuid
import os
from django.conf import settings
from io import BytesIO
from datetime import datetime, timedelta
from .models import *

# MongoDB connection
client = MongoClient("mongodb+srv://saandeepsaiturpu:simadi123@chatbot.dt3n1.mongodb.net/?retryWrites=true&w=majority&appName=chatbot")
db = client['saandeepsaiturpu']
collection = db['QR_Codes']
rate = db['museums']

class GenerateQRCode(View):
    def time_date(self, time, date):
        try:
            # Convert string time to datetime object and add 2 hours
            time = datetime.strptime(time, "%H:%M")
            updated_time = time + timedelta(hours=2)
            _, actual_time = str(updated_time).split(" ")
            hour, minutes, _ = actual_time.split(":")
            
            # Adjust date if time goes past midnight
            input_date = datetime.strptime(date, "%Y-%m-%d")
            if int(hour) >= 0:
                date = input_date + timedelta(days=1)
            
            date = date.strftime("%Y-%m-%d")
            return actual_time, date
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    def get(self, request, *args, **kwargs):
        try:
            # Retrieve query params
            time = request.GET.get('time')
            date = request.GET.get('date')
            total_members = int(request.GET.get('totalmembers', 0))
            children = int(request.GET.get('children', 0))
            adults = int(request.GET.get('adults', 0))
            foreigner = int(request.GET.get('foreigner', 0))
            museum = request.GET.get('museum')
            userid = request.GET.get('userid')

            # Find museum rates in the MongoDB collection
            rates = rate.find_one({'name':museum})  # Ensure proper museum name field in DB
            if rates:
                c_rate = rates['data']['children']  # Correct way to access nested data
                a_rate = rates['data']['adults']
                f_rate = rates['data']['foreigner']

                # Calculate total price based on group categories
                c_prize = children * c_rate
                a_prize = adults * a_rate
                f_prize = foreigner * f_rate
                total_prize = c_prize + a_prize + f_prize

                # Unique QR code generation
                code = str(uuid.uuid4())
                for i in range(total_members):
                    pass  # You can further process members if needed

                # Update booking time and date
                book_time, book_date = self.time_date(time, date)
                
                # Generate unique data for the QR code
                is_unique = False
                data = str(uuid.uuid4())
                while not is_unique:
                    data = str(uuid.uuid4())
                    if not collection.find_one({"code": data}):  # Ensure uniqueness
                        is_unique = True

                # Create QR Code
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=7.5,
                    border=0.5,
                )

                # Save QR code to file
                image_dir = os.path.join(settings.MEDIA_ROOT, 'qr_codes')
                if not os.path.exists(image_dir):
                    os.makedirs(image_dir)
                
                qr.add_data(data)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                image_path = os.path.join(image_dir, f"{data}.png")
                img.save(image_path)

                # URL to the QR code image
                qr_code_url = f"http://localhost:8000/media/qr_codes/{data}.png"

                # Insert record into MongoDB
                QR_dict = {
                    'code': data,
                    'time': book_time,
                    'date': book_date,
                    'validation': 'valid',
                    'total_price': total_prize
                }

                qr_db = client[userid]
                qr_collection = qr_db['QR_Codes']
                
                qr_collection.insert_one(QR_dict)
                
                return JsonResponse({"url": qr_code_url, "total_price": total_prize}, status=200)

            else:
                return JsonResponse({"error": "Museum rates not found"}, status=404)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


class GreetView(APIView):
    def post(self, request):
        name = request.data.get('name')
        userid = str(request.data.get('userid'))
        if name:
            predict = PredictClass(name)
            chatbot = ASTRAChatbot(userid)
            predict_class = predict.predict_class()
            if predict_class == "Ticketing and Reservations":
                return JsonResponse({"message": "(https://example.com/book-tickets)"}, status=status.HTTP_200_OK) 
            else:
                response = chatbot.get_response(name)
                return Response({"message": f"{response}"}, status=status.HTTP_200_OK)
        return Response({"error": "Name not provided"}, status=status.HTTP_400_BAD_REQUEST)

class Ticket(APIView):
    def get(self, request, *args, **kwargs):
        user_id = request.GET.get('userid')  # Use GET request parameter
        if not user_id:
            return JsonResponse({"error": "User ID not provided"}, status=400)

        try:
            # Connect to the user's database and retrieve QR codes
            db = client[user_id]
            code_collection = db['QR_Codes']
            codes = [doc['code'] for doc in code_collection.find({}, {'code': 1})]
            
            # Construct URLs for the QR codes
            qr_code_urls = [
                f"http://localhost:8000/media/qr_codes/{code}.png" for code in codes
            ]

            if not qr_code_urls:
                return JsonResponse({"message": "No tickets found for the user"}, status=404)

            return JsonResponse({"tickets": qr_code_urls}, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
