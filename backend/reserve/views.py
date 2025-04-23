from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
import json
from django.http import JsonResponse
from users.models import User
from reserve.models import Reserve
from reserve.serializers import ReserveSerializer
# Create your views here.


class CreateReserve(APIView):
    def post(self, request):
        pass

class ListReserve(APIView):
    def get(self, request, user_id):
        if(user_id):
            user = User.objects.get(id=user)
            if user:
                reserves = Reserve.objects.filter(user=user.id, many=True)
                result = ReserveSerializer(reserves).data
                return JsonResponse({'data': result}, status=200)
            return JsonResponse({'error': 'User not found'}, status=404)

        reserves = Reserve.objects.all()
        result = ReserveSerializer(reserves).data 
        return JsonResponse({'data': result}, status=200)   

class UpdateReserve(APIView):
    def put(self, request, reserve_id):
        pass

class RemoveReserve(APIView):
    def delete(self, request, reserve_id):
        reserve = Reserve.objects.get(id=reserve_id)
        if reserve:
            reserve.delete()
            return JsonResponse({"data": "reserve deleted successfully"}, status=200)
        return JsonResponse({"error": "Result not found"}, status=404)