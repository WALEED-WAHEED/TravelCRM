from rest_framework import serializers

from .models import Flight, Hotel, Mutamer, Transport, Voucher, LedgerEntry


class HotelSerializer(serializers.ModelSerializer):
    """Hotels for agency inventory; `code` is generated on save when omitted."""

    class Meta:
        model = Hotel
        fields = [
            "id",
            "name",
            "code",
            "address",
            "city",
            "country",
            "phone",
            "email",
            "rating",
            "description",
            "amenities",
            "sale_price",
            "purchase_price",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "code", "created_at", "updated_at"]
        extra_kwargs = {
            "address": {"required": False, "allow_blank": True, "default": ""},
            "rating": {"required": False, "allow_null": True},
            "phone": {"required": False, "allow_null": True},
            "email": {"required": False, "allow_null": True},
            "description": {"required": False, "allow_null": True},
            "amenities": {"required": False},
        }

    def __init__(self, *args, **kwargs):
        data = kwargs.get("data")
        if data is not None and hasattr(data, "copy"):
            data = data.copy()
            if data.get("rating") == "":
                data["rating"] = None
            kwargs["data"] = data
        super().__init__(*args, **kwargs)


class FlightSerializer(serializers.ModelSerializer):
    """Agency flight inventory; optional fields use model defaults."""

    class Meta:
        model = Flight
        fields = [
            "id",
            "airline",
            "flight_number",
            "pnr_number",
            "departure_airport",
            "arrival_airport",
            "departure_city",
            "arrival_city",
            "departure_country",
            "arrival_country",
            "flight_type",
            "flight_class",
            "sale_price",
            "purchase_price",
            "currency",
            "available_seats",
            "total_seats",
            "status",
            "baggage_allowance",
            "meal_included",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "currency", "created_at", "updated_at"]
        extra_kwargs = {
            "flight_number": {"required": False, "allow_null": True, "allow_blank": True},
            "pnr_number": {"required": False, "allow_null": True, "allow_blank": True},
            "departure_airport": {"required": False},
            "arrival_airport": {"required": False},
            "departure_country": {"required": False},
            "arrival_country": {"required": False},
            "notes": {"required": False, "allow_blank": True},
            "baggage_allowance": {"required": False},
            "available_seats": {"required": False},
            "total_seats": {"required": False},
            "status": {"required": False},
            "meal_included": {"required": False},
        }


class TransportSerializer(serializers.ModelSerializer):
    """Ground transport inventory for an agency."""

    is_active = serializers.BooleanField(required=False, default=True)

    class Meta:
        model = Transport
        fields = [
            "id",
            "name",
            "transport_type",
            "capacity",
            "purchase_price",
            "sale_price",
            "amenities",
            "notes",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {
            "purchase_price": {"required": False, "allow_null": True},
            "sale_price": {"required": False, "allow_null": True},
            "notes": {"required": False, "allow_blank": True},
            "amenities": {"required": False},
        }

    def __init__(self, *args, **kwargs):
        data = kwargs.get("data")
        if data is not None and hasattr(data, "copy"):
            data = data.copy()
            for key in ("sale_price", "purchase_price"):
                if data.get(key) == "":
                    data[key] = None
            kwargs["data"] = data
        super().__init__(*args, **kwargs)


class MutamerSerializer(serializers.ModelSerializer):
    """Pilgrim profile; `agent` and `agency` are set on create from the request user."""

    is_active = serializers.BooleanField(required=False, default=True)
    is_family_head = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = Mutamer
        fields = [
            "id",
            "name",
            "passport_number",
            "visa_number",
            "nationality",
            "gender",
            "person_type",
            "date_of_birth",
            "phone",
            "email",
            "emergency_contact",
            "emergency_phone",
            "address",
            "city",
            "state",
            "country",
            "postal_code",
            "notes",
            "is_active",
            "family_id",
            "is_family_head",
            "family_head_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {
            "visa_number": {"required": False, "allow_null": True, "allow_blank": True},
            "person_type": {"required": False, "allow_null": True, "allow_blank": True},
            "date_of_birth": {"required": False, "allow_null": True},
            "phone": {"required": False, "allow_blank": True},
            "email": {"required": False, "allow_blank": True},
            "emergency_contact": {"required": False, "allow_blank": True},
            "emergency_phone": {"required": False, "allow_blank": True},
            "address": {"required": False, "allow_blank": True},
            "city": {"required": False, "allow_blank": True},
            "state": {"required": False, "allow_blank": True},
            "country": {"required": False, "allow_blank": True},
            "postal_code": {"required": False, "allow_blank": True},
            "notes": {"required": False, "allow_blank": True},
            "family_id": {"required": False, "allow_null": True, "allow_blank": True},
            "family_head_name": {"required": False, "allow_null": True, "allow_blank": True},
        }

    def __init__(self, *args, **kwargs):
        data = kwargs.get("data")
        if data is not None and hasattr(data, "copy"):
            data = data.copy()
            if data.get("person_type") == "":
                data["person_type"] = None
            if data.get("date_of_birth") == "":
                data["date_of_birth"] = None
            kwargs["data"] = data
        super().__init__(*args, **kwargs)


class VoucherSerializer(serializers.ModelSerializer):
    """Voucher read/update serializer for approvals and directory."""

    class Meta:
        model = Voucher
        fields = [
            "id",
            "voucher_number",
            "manual_number",
            "agent",
            "mutamer",
            "status",
            "total_amount",
            "paid_amount",
            "notes",
            "approved_by",
            "approved_at",
            "public_token",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "voucher_number",
            "public_token",
            "approved_by",
            "approved_at",
            "created_at",
            "updated_at",
        ]


class LedgerEntrySerializer(serializers.ModelSerializer):
    """Ledger entry for agency finance tracking."""

    class Meta:
        model = LedgerEntry
        fields = [
            "id",
            "transaction_date",
            "bucket",
            "direction",
            "counterparty_type",
            "counterparty_name",
            "transaction_type",
            "amount",
            "currency",
            "payment_method",
            "reference_number",
            "trans_no",
            "inv_ref",
            "rate",
            "description",
            "category",
            "booking",
            "voucher",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "currency", "created_at", "updated_at"]
        extra_kwargs = {
            "counterparty_type": {"required": False, "allow_blank": True},
            "counterparty_name": {"required": False, "allow_blank": True},
            "reference_number": {"required": False, "allow_blank": True},
            "trans_no": {"required": False, "allow_blank": True},
            "inv_ref": {"required": False, "allow_blank": True},
            "rate": {"required": False, "allow_null": True},
            "category": {"required": False, "allow_blank": True},
            "booking": {"required": False, "allow_null": True},
            "voucher": {"required": False, "allow_null": True},
        }

