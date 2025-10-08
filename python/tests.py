import pytest
import datetime
from hotel_mgmt import Customer, Hotel

@pytest.fixture
def test_hotel() -> Hotel:
    test_rooms_data = [
        {"room_number": 101, "room_type": "Single", "price_per_night": 100, "is_available": True, "max_guests": 2},
        {"room_number": 102, "room_type": "Double", "price_per_night": 150, "is_available": False, "max_guests": 4}
    ]
    return Hotel(name="სატესტო სასტუმრო", rooms_data=test_rooms_data)

@pytest.fixture
def tester() -> Customer:
    return Customer(name="ტესტერი", budget=1000.0)

def test_successful_booking_and_payment(tester, test_hotel, monkeypatch):
    room_to_book = 101
    initial_budget = tester.get_budget()
    room_object = next(r for r in test_hotel.rooms if r.room_number == room_to_book)
    room_price = room_object.calculate_price(nights=2, check_in_date=datetime.date.today())
    expected_budget = initial_budget - room_price
    monkeypatch.setattr('builtins.input', lambda _: 'yes')
    booking_result = test_hotel.book_room_for_customer(
        tester,
        room_to_book,
        nights=2,
        check_in_date=datetime.date.today()
    )

    assert booking_result is True
    assert tester.get_budget() == expected_budget
    assert not room_object.is_available

def test_booking_fails_for_occupied_room(tester, test_hotel):
    occupied_room_number = 102
    booking_result = test_hotel.book_room_for_customer(
        tester,
        occupied_room_number,
        nights=1,
        check_in_date=datetime.date.today()
    )

    assert booking_result is False