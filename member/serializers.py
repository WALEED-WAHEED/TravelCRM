from rest_framework import serializers

from .models import Flight, Hotel, LedgerEntry, Package, Transport, Voucher


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


class VoucherSerializer(serializers.ModelSerializer):
    """Voucher read/update serializer for approvals and directory."""

    class Meta:
        model = Voucher
        fields = [
            "id",
            "voucher_number",
            "agent",
            "mutamer_name",
            "mutamer_passport_number",
            "mutamer_visa_number",
            "mutamer_nationality",
            "mutamer_gender",
            "mutamer_phone",
            "mutamer_email",
            "status",
            "total_amount",
            "paid_amount",
            "notes",
            "rejection_reason",
            "approved_by",
            "approved_at",
            "public_token",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "voucher_number",
            "rejection_reason",
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
            "fx_currency",
            "fx_amount",
            "pax",
            "type_code",
            "description",
            "category",
            "booking",
            "voucher",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "currency", "type_code", "created_at", "updated_at"]
        extra_kwargs = {
            # Derived from fx_amount * rate when a foreign amount is given.
            "amount": {"required": False},
            "fx_currency": {"required": False, "allow_blank": True},
            "fx_amount": {"required": False, "allow_null": True},
            "pax": {"required": False, "allow_null": True},
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

    def validate(self, attrs):
        def current(field):
            if field in attrs:
                return attrs[field]
            return getattr(self.instance, field, None)

        fx_amount, rate = current("fx_amount"), current("rate")
        if fx_amount is not None:
            if not rate:
                raise serializers.ValidationError({"rate": "Enter the exchange rate for the foreign amount."})
            if not current("fx_currency"):
                raise serializers.ValidationError({"fx_currency": "Choose the currency of the foreign amount."})
            # The model recomputes this on save; set it so `amount` passes validation.
            attrs["amount"] = fx_amount * rate
        elif current("amount") is None:
            raise serializers.ValidationError({"amount": "Enter an amount."})
        else:
            # Switching back from a foreign amount must not leave stale FX fields.
            attrs.setdefault("fx_currency", "")

        if current("bucket") == "lein_dein" and not (current("counterparty_name") or "").strip():
            raise serializers.ValidationError({"counterparty_name": "Choose or type the party name."})
        if current("bucket") == "company_expense":
            attrs["direction"] = "debit"
        return attrs



class PackageSerializer(serializers.ModelSerializer):
    """Umrah/Hajj package. Hotel/flight/transport choices are limited to the
    caller's own agency because those models' default managers are tenant-scoped."""

    inclusions = serializers.MultipleChoiceField(choices=Package.INCLUSIONS, required=False)

    class Meta:
        model = Package
        fields = [
            "id", "code", "name", "package_type", "group_leader", "makkah_nights", "madina_nights",
            "makkah_hotel", "madina_hotel", "makkah_distance", "makkah_shuttle", "madina_distance", "madina_shuttle",
            "flight", "return_flight", "baggage", "transport", "inclusions", "extra_services",
            "price_sharing", "price_double", "price_triple", "price_quad", "price_quint",
            "price_child", "price_infant", "cost_price",
            "departure_date", "return_date", "total_seats", "notes", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "code", "created_at", "updated_at"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["inclusions"] = sorted(data.get("inclusions") or [])
        return data

    def validate_inclusions(self, value):
        order = [key for key, _label in Package.INCLUSIONS]
        return [key for key in order if key in value]

    def validate(self, attrs):
        dep = attrs.get("departure_date", getattr(self.instance, "departure_date", None))
        ret = attrs.get("return_date", getattr(self.instance, "return_date", None))
        if dep and ret and ret < dep:
            raise serializers.ValidationError({"return_date": "Return date must be after departure."})
        prices = [attrs.get(f, getattr(self.instance, f, None)) for f, _label in Package.SHARING_FIELDS]
        if all(p is None for p in prices):
            raise serializers.ValidationError({"price_quad": "Enter a price for at least one room sharing."})
        return attrs
