import json
import datetime
from datetime import timedelta
import logging

logging.basicConfig(filename='bookings.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s', encoding='utf-8')

# ჩავტვირთოთ მონაცემთა ბაზა
file_path = "db.json"
try:
    with open(file_path, 'r', encoding='utf-8') as file:
        rooms_db = json.load(file)
except FileNotFoundError:
    print(f"შეცდომა: ფაილი '{file_path}' ვერ მოიძებნა.")
    rooms_db = []
except json.JSONDecodeError:
    print(f"შეცდომა: არასწორი JSON ფორმატი.")
    rooms_db = []

customers = {}

# ფასდაკლების თარიღებისთვის ვიყენებ დღის რიგით ნომერს
def calculate_price_adjustement(check_date=None) -> float:
    if check_date is None: check_date = datetime.date.today()
    day_of_year = check_date.timetuple().tm_yday
    if day_of_year >= 362 or day_of_year <= 3: return 1.8
    elif 13 <= day_of_year <= 15: return 1.5
    elif 60 <= day_of_year <= 151: return 0.9
    elif 152 <= day_of_year <= 243: return 1.0
    elif 244 <= day_of_year <= 358: return 1.2
    else: return 0.7

class Room:
    def __init__(self, room_number: int, room_type: str, price_per_night: float, is_available: bool, max_guests: int):
        self.room_number = room_number
        self.room_type = room_type
        self.price_per_night = price_per_night
        self.is_available = is_available
        self.max_guests = max_guests

    def book_room(self):
        if self.is_available: self.is_available = False; return True
        return False

    def release_room(self):
        self.is_available = True

    def calculate_price(self, nights: int, check_in_date: datetime.date) -> float:
        total_price = sum(self.price_per_night * calculate_price_adjustement(check_in_date + timedelta(days=i)) for i in
                          range(nights))
        return round(total_price, 2)

    def __str__(self):
        return (f"ოთახი №{self.room_number}, ტიპი: {self.room_type}, "
                f"გათვლილია {self.max_guests} სტუმარზე. ერთი ღამის ფასი "
                f"{self.price_per_night}.")

class Hotel:
    def __init__(self, name: str, rooms_data: list):
        self.name = name
        self.rooms = [Room(**data) for data in rooms_data]
        self.bookings_log = []

    def show_available_rooms(self, room_type: str = None):
        available_rooms = [r for r in self.rooms if r.is_available and (room_type is None or r.room_type == room_type)]
        print("\nხელმისაწვდომი ოთახები:")
        if not available_rooms:
            print("  - ამჟამად თავისუფალი ოთახები არ არის.")
        else:
            for room in available_rooms: print(f"  - {room}")

    def book_room_for_customer(self, customer: 'Customer', room_number: int, nights: int,
                               check_in_date: datetime.date) -> bool:
        target_room = next((r for r in self.rooms if r.room_number == room_number), None)
        if target_room is None:
            print(f"შეცდომა: ოთახი №{room_number} ვერ მოიძებნა.")
            return False
        if not target_room.is_available:
            print(f"ოთახი №{room_number} დაკავებულია.")
            return False

        room_price = target_room.calculate_price(nights, check_in_date)

        # გამოვთვალოთ საშუალოდ რა ღირს ერთი ღამე ფასდაკლების მატრიცის გათვალისწინებით
        if nights > 0:
            avg_price_per_night = round(room_price / nights, 2)
            base_price = target_room.price_per_night
            if avg_price_per_night > base_price:
                print(f"არჩეულ პერიოდში ფასი გაზრდილია და ღამეში საშუალოდ {avg_price_per_night:.2f}₾-ს შეადგენს.")
            elif avg_price_per_night < base_price:
                print(f"არჩეულ პერიოდში ფასი შემცირებულია და ღამეში საშუალოდ {avg_price_per_night:.2f}₾-ს შეადგენს.")
            else:
                print("არჩეულ პერიოდში მოქმედებს სტანდარტული ფასი.")
            if nights != 1:
                print(f"№{target_room.room_number} ოთახის {nights} ღამით დაქირავების ღირებულებაა: {room_price:.2f}₾.")

        confirmation = input("გსურთ დაჯავშნა? (yes/no): ").lower()
        if confirmation != 'yes':
            print("ჯავშანი გაუქმებულია.")
            return False

        payment_successful = customer.pay_for_booking(room_price)
        if not payment_successful:
            print("თანხის გადახდა და ოთახის დაჯავშნა ვერ მოხერხდა.")
            return False

        # ვჯავშნით ოთახს და ვარიცხავთ ბონუსს
        customer.add_room(target_room, room_price, nights, check_in_date, 0)
        target_room.book_room()
        self.log_booking(customer, target_room, room_price, "დაიჯავშნა")
        print(f"🎉 ოთახი №{room_number} წარმატებით დაიჯავშნა.")
        return True

    def log_booking(self, customer: 'Customer', room: Room, price: float, action: str):
        log_message = f"{action}: მომხმარებელი '{customer.name}' ({room.room_number}), ფასი: {price:.2f} GEL."
        logging.info(log_message)
        self.bookings_log.append(log_message)

class Customer:
    def __init__(self, name: str, budget: float):
        self.name = name
        self.__budget__ = budget
        self.active_bookings = []
        self.__bonus_balance__ = 0.0

    def add_budget(self, amount: float):
        if amount > 0: self.__budget__ += amount

    def add_room(self, room: Room, room_price: float, nights: int, check_in_date: datetime.date, bonus_earned: float):
        booking_details = {
            "room": room, "room_price": room_price, "nights": nights,
            "check_in_date": check_in_date, "check_out_date": check_in_date + timedelta(days=nights),
            "bonus_earned": bonus_earned
        }
        self.active_bookings.append(booking_details)

    def remove_room(self, hotel: Hotel):
        if not self.active_bookings:
            print("გასაუქმებელი ჯავშნები არ გაქვთ.")
            return
        self.show_booking_summary()
        try:
            choice = int(input("აირჩიეთ გასაუქმებელი ჯავშნის ნომერი (0 - გასვლა): "))
            if choice == 0: return
            if 1 <= choice <= len(self.active_bookings):
                # ჯავშნის გაუქმებისას ვაჭრით 10% და ჩამოვაჭრით დარიცხულ ბონუსს
                booking_to_cancel = self.active_bookings.pop(choice - 1)
                room_to_release = booking_to_cancel["room"]
                price_paid = booking_to_cancel["room_price"]
                bonus_to_deduct = booking_to_cancel.get("bonus_earned", 0)
                refund_amount = round(price_paid * 0.90, 2)
                self.add_budget(refund_amount)
                self.__bonus_balance__ -= bonus_to_deduct
                room_to_release.release_room()
                hotel.log_booking(self, room_to_release, refund_amount, "ჯავშანი გაუქმდა/თანხა დაბრუნდა")
                print(f"\n№{room_to_release.room_number} ოთახის ჯავშანი გაუქმდა.")
                print(f"თქვენ დაგიბრუნდათ {refund_amount:.2f}₾.")
                if bonus_to_deduct > 0:
                    print(f"ასევე გაუქმდა დარიცხული ბონუსი: {bonus_to_deduct:.2f}₾.")
            else:
                print("არასწორი ნომერი.")
        except ValueError:
            print("გთხოვთ, შეიყვანოთ რიცხვი.")

    def pay_for_booking(self, total_price: float) -> float | None:
        if not self.has_sufficient_funds(total_price):
            print(f"გადახდა ვერ ხერხდება. საჭიროა: {total_price:.2f}₾, ბალანსზეა: {self.get_budget()}₾.")
            funds_added = self._add_funds()
            if not funds_added or not self.has_sufficient_funds(total_price):
                return None
        self.__budget__ -= total_price
        bonus_earned = round(total_price * 0.05, 2)
        if bonus_earned > 0:
            self.__bonus_balance__ += bonus_earned
            print(f"თქვენ დაგერიცხათ ბონუსი {bonus_earned}₾. ბონუსის ბალანსია: {self.__bonus_balance__:.2f}₾.\n")
        return bonus_earned

    def show_booking_summary(self):
        if not self.active_bookings:
            print("\nამჟამად აქტიური ჯავშნები არ გაქვთ.")
            return
        print(f"\n--- {self.name}-ის აქტიური ჯავშნები ---")
        for i, booking in enumerate(self.active_bookings, 1):
            room = booking["room"]
            check_in = booking['check_in_date'].strftime('%Y-%m-%d')
            check_out = booking['check_out_date'].strftime('%Y-%m-%d')
            print(
                f"{i}. ოთახი №{room.room_number} | პერიოდი: {check_in}-{check_out} | გადახდილია: {booking['room_price']:.2f}₾")
        print(f"თქვენი ბიუჯეტი: {self.get_budget():.2f}₾")
        print(f"დარიცხული ბონუსი: {self.__bonus_balance__:.2f}₾.")

    def has_sufficient_funds(self, amount: float) -> bool:
        return self.__budget__ >= amount

    def get_budget(self) -> float:
        return self.__budget__

    # ვაძლევთ თანხის დამატების საშუალებას
    def _add_funds(self) -> bool:
        choice = input("გსურთ ბიუჯეტის შევსება? (yes/no): ").lower()
        if choice == 'yes':
            try:
                amount = float(input("შეიყვანეთ დასამატებელი თანხა: "))
                if amount > 0:
                    self.__budget__ += amount
                    print(f"ბალანსი წარმატებით შეივსო. ახალი ბიუჯეტია: {self.__budget__:.2f}₾.")
                    return True
                else:
                    print("გთხოვთ, შეიყვანოთ დადებითი რიცხვი.")
            except ValueError:
                print("არასწორი ფორმატია.")
        return False

# უბრალოდ ვალიდაცია
def get_numeric_input(prompt: str, input_type: type):
    while True:
        try:
            return input_type(input(prompt))
        except ValueError:
            print("გთხოვთ, შეიყვანოთ სწორი რიცხვითი მნიშვნელობა.")

# ვქმნით დამატებით "ცხრილს" მომხმარებლების შესანახად
def get_or_create_customer(customers_db: dict) -> Customer:
    name = input("შეიყვანეთ თქვენი სახელი: ")
    if name in customers_db:
        print(f"მოგესალმებით, {name}!")
        return customers_db[name]
    else:
        print(f"მოგესალმებით, {name}! (შეიქმნა ახალი ანგარიში)")
        budget = get_numeric_input("შეიყვანეთ თქვენი ბიუჯეტი: ", float)
        new_customer = Customer(name, budget)
        customers_db[name] = new_customer
        return new_customer

# if პირობა, რომ ტესტმა კორექტულად იმუშაოს
if __name__ == "__main__":
    new_hotel = Hotel("რქები და ჩლიქები", rooms_db)
    print(f"მოგესალმებით სასტუმროში \"{new_hotel.name}!\"")

    while True:
        choice = input("\nაირჩიეთ მოქმედება:\n"
                       "  (1) თავისუფალი ნომრების ნახვა\n"
                       "  (2) ოთახის დაჯავშნა\n"
                       "  (3) ჩემი ჯავშნების ნახვა\n"
                       "  (4) ჯავშნის გაუქმება\n"
                       "  (0) სისტემიდან გასვლა\n"
                       "თქვენი არჩევანი: ")
        if choice == "0":
            print("ნახვამდის!")
            break
        elif choice == "1":
            new_hotel.show_available_rooms()
        elif choice == "2":
            current_customer = get_or_create_customer(customers)
            new_hotel.show_available_rooms()
            room_number = get_numeric_input("\nსასურველი ოთახის ნომერი: ", int)
            nights = get_numeric_input("რამდენი ღამით გსურთ დარჩენა?: ", int)
            try:
                month, day = map(int, input("შეიყვანეთ თვე და რიცხვი (მაგ: 4 29): ").split())
                check_in_date = datetime.date(datetime.date.today().year, month, day)
                new_hotel.book_room_for_customer(current_customer, room_number, nights, check_in_date)
            except ValueError:
                print("თარიღის არასწორი ფორმატი.")
        elif choice == "3":
            current_customer = get_or_create_customer(customers)
            current_customer.show_booking_summary()
        elif choice == "4":
            current_customer = get_or_create_customer(customers)
            current_customer.remove_room(new_hotel)
        else:
            print("გთხოვთ, შეიყვანოთ მხოლოდ მენიუს ციფრები!")