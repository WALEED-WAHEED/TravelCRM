from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from .views import HotelViewSet, HotelRoomViewSet, HotelImageViewSet

# Main router for hotels
router = DefaultRouter()
router.register("hotels", HotelViewSet, basename="hotels")

# Nested router for hotel rooms
hotels_router = routers.NestedDefaultRouter(router, "hotels", lookup="hotel")
hotels_router.register("rooms", HotelRoomViewSet, basename="hotel-rooms")

# Nested router for hotel images
hotels_router.register("images", HotelImageViewSet, basename="hotel-images")

urlpatterns = router.urls + hotels_router.urls
