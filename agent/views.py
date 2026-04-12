"""Agent portal views."""
from django.shortcuts import render
from member.decorators import agent_required
from member.models import Booking, Voucher, Mutamer, Hotel, Flight, Transport

@agent_required
def dashboard(request):
    agent = request.user
    context = {
        "page_title": "Agent Dashboard",
        "my_bookings": Booking.objects.filter(agent=agent).count(),
        "my_vouchers": Voucher.objects.filter(agent=agent).count(),
        "my_mutamers": Mutamer.objects.filter(agent=agent).count(),
        "pending_vouchers": Voucher.objects.filter(agent=agent, status="pending").count(),
    }
    return render(request, "agent/dashboard.html", context)


@agent_required
def bookings(request):
    agent = request.user
    agency = agent.agency
    qs = Booking.objects.filter(agent=agent).order_by("-created_at")
    hotel_list = Hotel.objects.filter(agency=agency) if agency else Hotel.objects.none()
    flight_list = Flight.objects.filter(agency=agency) if agency else Flight.objects.none()
    transport_list = Transport.objects.filter(agency=agency) if agency else Transport.objects.none()
    mutamer_list = Mutamer.objects.filter(agent=agent)
    return render(request, "agent/bookings.html", {
        "bookings": qs, "page_title": "My Bookings",
        "hotels": hotel_list, "flights": flight_list,
        "transports": transport_list, "mutamers": mutamer_list,
    })


@agent_required
def vouchers(request):
    agent = request.user
    qs = Voucher.objects.filter(agent=agent).select_related("mutamer").order_by("-created_at")
    mutamer_list = Mutamer.objects.filter(agent=agent)
    return render(request, "agent/vouchers.html", {"vouchers": qs, "mutamers": mutamer_list, "page_title": "My Vouchers"})


@agent_required
def mutamers(request):
    agent = request.user
    qs = Mutamer.objects.filter(agent=agent).order_by("-created_at")
    return render(request, "agent/mutamers.html", {"mutamers": qs, "page_title": "My Mutamers"})
