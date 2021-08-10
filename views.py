# creating views to respond to different kinds of requests from the user

from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponseNotFound
from faunadb import query as q
import pytz
from faunadb.objects import Ref
from faunadb.client import FaunaClient
import hashlib
import datetime


def login(request):
    if request.method == "POST":
        username = request.POST.get("username").strip().lower()
        password = request.POST.get("password")

        try:
            user = client.query(q.get(q.match(q.index("users_index"), username)))
            if hashlib.sha512(password.encode()).hexdigest() == user["data"]["password"]:
                request.session["user"] = {
                    "id": user["ref"].id(),
                    "username": user["data"]["username"]
                }
                return redirect("App:dashboard")
            else:
                raise Exception()
        except:
            messages.add_message(request, messages.INFO,
                                 "You have supplied invalid login credentials, please try again!",
                                 "danger")
            return redirect("App:login")
    return render(request, "login.html")

#Let’s now give our create-appointment page the functionality to schedule new appointments
def create_appointment(request):
    if "user" in request.session:
        if request.method == "POST":
            name = request.POST.get("name")
            description = request.POST.get("description")
            time = request.POST.get("time")
            date = request.POST.get("date")
            try:
                user = client.query(q.get(q.match(q.index("events_index"), date, time)))
                messages.add_message(request, messages.INFO,
                                     'An Event is already scheduled for the specified time.')
                return redirect("App:create-appointment")
            except:
                user = client.query(q.create(q.collection("Events"), {
                    "data": {
                        "name": name,
                        "description": description,
                        "time": time,
                        "date": date,
                        "user": request.session["user"]["username"],
                        "status": 'False',
                    }
                }))
                messages.add_message(request, messages.INFO, 'Appointment Scheduled Successfully.')
                return redirect("App:create-appointment")
        return render(request, "appoint/create-appointment.html")
    else:
        return HttpResponseNotFound("Page not found")


def dashboard(request):
    return render(request, "index.html")


# We need to allow users to see their appointments scheduled for the current day.
# To do this, in the today_appointment function update the python code as seen below.
def today_appointment(request):
    if "user" in request.session:
        appointments = client.query(q.paginate(
            q.match(q.index("events_today_paginate"), request.session["user"]["username"],
                    str(datetime.date.today()))))["data"]
        appointments_count = len(appointments)
        page_number = int(request.GET.get('page', 1))
        appointment = client.query(q.get(q.ref(q.collection("Events"), appointments[page_number - 1].id())))["data"]
        context = {"count": appointments_count, "appointment": appointment, "page_num": page_number,
                   "next_page": min(appointments_count, page_number + 1), "prev_page": max(1, page_number - 1)}
        return render(request, "today-appointment.html", context)
    else:
        return HttpResponseNotFound("Page not found")

# We need to allow users to see all their appointments scheduled for the current day
def all_appointment(request):
 if "user" in request.session:
  appointments = \
  client.query(q.paginate(q.match(q.index("events_index_paginate"), request.session["user"]["username"])))["data"]
  appointments_count = len(appointments)
  page_number = int(request.GET.get('page', 1))
  appointment = client.query(q.get(q.ref(q.collection("Events"), appointments[page_number - 1].id())))["data"]
  if request.GET.get("delete"):
   client.query(q.delete(q.ref(q.collection("Events"), appointments[page_number - 1].id())))
   return redirect("App:all-appointment")
  context = {"count": appointments_count, "appointment": appointment,
             "next_page": min(appointments_count, page_number + 1), "prev_page": max(1, page_number - 1)}
  return render(request, "all-appointment.html", context)
 else:
  return HttpResponseNotFound("Page not found")


# The first action the user takes when opening the web app is to register if they haven't already
def register(request):
    if request.method == "POST":
        username = request.POST.get("username").strip().lower()
        email = request.POST.get("email").strip().lower()
        password = request.POST.get("password")

        try:
            user = client.query(q.get(q.match(q.index("users_index"), username)))
            messages.add_message(request, messages.INFO, 'User already exists with that username.')
            return redirect("App:register")
        except:
            user = client.query(q.create(q.collection("users"), {
                "data": {
                    "username": username,
                    "email": email,
                    "password": hashlib.sha512(password.encode()).hexdigest(),
                    "date": datetime.datetime.now(pytz.UTC)
                }
            }))
            messages.add_message(request, messages.INFO, 'Registration successful.')
            return redirect("App:login")
    return render(request, "register.html")


client = FaunaClient(secret="SECRET_KEY")
indexes = client.query(q.paginate(q.indexes()))
